# Deploying BookingMngr

The whole app runs as one Docker Compose stack: Caddy in front, the Next.js
frontend, the FastAPI backend, Postgres, and a nightly backup sidecar. Caddy
serves the UI and the API from **one origin**, so there is no CORS to configure
and no API URL baked into the frontend image.

```
        :80/:443
           │
        ┌──┴───┐   /api/*, /health*   ┌─────────┐      ┌────┐
        │ caddy├──────────────────────┤ backend ├──────┤ db │
        └──┬───┘                      └─────────┘      └─┬──┘
           │  everything else                            │
        ┌──┴─────┐                                  ┌────┴───┐
        │frontend│                                  │ backup │
        └────────┘                                  └────────┘
```

Nothing but Caddy publishes a port. Postgres is unreachable from outside the
Docker network.

---

## Run it locally first

```bash
cp .env.example .env          # SITE_ADDRESS=http://localhost is the default
# fill in SECRET_KEY, POSTGRES_PASSWORD, OWNER_PASSWORD — see the file for the
# openssl commands — then:
chmod 600 .env
mkdir -p backups

docker compose up -d --build
docker compose exec backend python -m app.db.init_db     # creates org + owner
docker compose exec backend python -m app.db.seed        # optional demo data
```

Open <http://localhost>. With `SITE_ADDRESS=http://localhost` Caddy serves plain
HTTP and skips certificate issuance entirely, so the routing you test here is
the routing you get in production.

To reach Postgres from the host (psql, or the Postgres-backed test run), add the
local overlay — it is the only thing that publishes 5432:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
```

---

## Deploy to a VPS

### 1. Provision

**Hetzner CAX11** (2 vCPU Ampere ARM64 / 4 GB / 40 GB, ~€4–5/mo), Ubuntu 24.04.
ARM is deliberate: it matches the development Mac, so images build natively.
**Add your SSH key at creation** and note the static IPv4.

Then run the bootstrap script — it creates a sudo user, copies your key over,
disables root and password SSH login, sets up ufw and unattended upgrades, and
installs Docker:

```bash
scp deploy/bootstrap-vps.sh root@<ip>:/tmp/
ssh root@<ip> 'bash /tmp/bootstrap-vps.sh deploy'
```

It refuses to disable password authentication unless it finds a working
authorized key first, and validates the sshd config with `sshd -t` before
restarting — so it cannot lock you out of your own server. Re-running it is
safe.

### 2. Hostname

Create a subdomain at [duckdns.org](https://www.duckdns.org) pointing at the VPS
IP. **Verify DNS resolves before starting Caddy** — a failed certificate attempt
counts against Let's Encrypt's rate limit:

```bash
dig +short bookingmngr.duckdns.org     # must return the VPS IP
```

DuckDNS is preferred over `nip.io`: it is on the Public Suffix List, so each
subdomain gets its own certificate budget instead of sharing one.

### 3. First deploy

```bash
sudo mkdir -p /opt/bookingmngr && sudo chown $USER /opt/bookingmngr
git clone <repo-url> /opt/bookingmngr && cd /opt/bookingmngr
mkdir -p backups
cp .env.example .env
```

Edit `.env`: set `SITE_ADDRESS=bookingmngr.duckdns.org` (**no scheme** — that is
what tells Caddy to get a certificate), `ACME_EMAIL`, and generate the secrets:

```bash
openssl rand -base64 48 | tr -d '\n'   # SECRET_KEY
openssl rand -base64 24                # POSTGRES_PASSWORD  (fixed once — changing it later needs ALTER ROLE)
openssl rand -base64 18                # OWNER_PASSWORD     (bootstrap only)
chmod 600 .env
```

Then:

```bash
docker compose up -d --build
docker compose logs -f caddy            # wait for "certificate obtained successfully"
docker compose logs migrate             # should show "Running upgrade -> f11406e0066a"
docker compose ps                       # all healthy; migrate exited (0)
docker compose exec backend python -m app.db.init_db
```

### 4. Verify

```bash
curl -fsS https://bookingmngr.duckdns.org/health          # {"status":"ok",...}
curl -so /dev/null -w '%{http_code}\n' https://bookingmngr.duckdns.org/docs   # 404
curl -I http://bookingmngr.duckdns.org                    # 308 redirect to https
sudo ss -ltnp                                             # only 22, 80, 443
```

### 5. Hand over

Your friend signs in with `OWNER_USERNAME` / `OWNER_PASSWORD` and immediately
uses **Change password** in the sidebar. Afterwards blank out `OWNER_PASSWORD`
in `.env` — it is only read when the account does not yet exist.

Then prove the backup path on day one (see below). Do not skip this.

---

## Building and shipping images

The CAX11 is ARM64, the same architecture as an Apple Silicon Mac, so images
build **natively** — no emulation, no cross-build flags to remember, and no
class of "works here, won't start there" failures. Both images build in about
50 seconds.

```bash
./deploy/build-images.sh ssh  deploy@<vps-ip>   # registry-free (default)
./deploy/build-images.sh ghcr <github-user>     # push to GHCR
./deploy/build-images.sh local                  # build only, for inspection
```

**`ssh` mode** streams the image straight into the remote Docker daemon
(`docker save | ssh … docker load`). No registry, no account, no storage quota.
This is the recommended default.

**`ghcr` mode** needs `docker login ghcr.io` with a Personal Access Token that
has `write:packages`. Note GHCR's free tier allows **500 MB of private package
storage** — these two images approach it, so either make the packages public,
prune old tags, or stay on `ssh` mode.

Either way, set the printed tags in the VPS `.env`:

```
BACKEND_IMAGE=bookingmngr-backend:<sha>
FRONTEND_IMAGE=bookingmngr-frontend:<sha>
```

**Always tag with the git SHA, never `latest`** — a rollback is then editing two
lines in `.env` and running `docker compose up -d`. The script refuses to build
from a dirty tree non-interactively, so a tag always names what actually shipped.

**The alternative** is building on the VPS itself (`docker compose up -d
--build`). The CAX11's 4 GB is enough for `next build`, which is the memory
hog. That skips the shipping step entirely at the cost of a slower deploy.

> If you ever move to an x86 box (Hetzner CX22, DigitalOcean, most providers),
> images must be rebuilt for it or they will not start:
> `PLATFORM=linux/amd64 ./deploy/build-images.sh ssh deploy@<ip>`.
> That path is tested and works; it just costs a little emulation time.

---

## Updating

```bash
docker compose exec backup /bin/sh /opt/backup/run-backup.sh   # ALWAYS before a migration
git pull
docker compose up -d --build      # or: docker compose pull && docker compose up -d
docker compose ps && curl -fsS https://$SITE_ADDRESS/health
docker image prune -f
```

`alembic upgrade head` runs on every start and is a no-op when already current.

**Rollback:** restore the previous image tags in `.env` and `docker compose up
-d`. If the deploy ran a migration, either `docker compose run --rm migrate
alembic downgrade -1` or restore the pre-deploy dump.

---

## Backups

A sidecar dumps the database nightly at `BACKUP_HOUR:BACKUP_MINUTE` (default
03:15 Europe/Sofia) into `./backups`, keeping `BACKUP_RETENTION_DAYS` (14) of
them. Each dump is checked with `pg_restore --list` before being kept, so a
truncated or disk-full dump fails loudly instead of sitting there looking fine.

```bash
docker compose exec backup /bin/sh /opt/backup/run-backup.sh   # dump now
ls -lh backups/
```

### The restore drill — run it the day you deploy, then monthly

An untested backup is not a backup. This restores into a scratch database and
never touches live data:

```bash
./deploy/backup/verify-restore.sh backups/bookingmngr-<stamp>.dump
```

It prints row counts for the restored copy and the live database side by side.
They should match.

### A real restore

```bash
docker compose stop caddy frontend backend backup    # stop all writers
docker compose exec -T db psql -U bookingmngr -d postgres \
  -c "DROP DATABASE bookingmngr;" -c "CREATE DATABASE bookingmngr OWNER bookingmngr;"
docker compose exec -T db pg_restore -U bookingmngr -d bookingmngr --no-owner < backups/<stamp>.dump
docker compose up -d
curl -fsS https://$SITE_ADDRESS/health
```

Dumps live only on this server. If the VPS is lost, they go with it — copy them
off (`scp`, or a Backblaze B2 bucket) once there is real revenue in there.

---

## Recovering a forgotten password

`/auth/change-password` needs the current password, and `init_db` never
overwrites an existing account. The way back in:

```bash
docker compose exec -e NEW_PASSWORD='a-strong-new-password' backend \
  python -m app.db.reset_password --username owner
```

Or omit `NEW_PASSWORD` to be prompted (it is never echoed, and never passed as an
argument where it would land in shell history).

---

## Routine operations

```bash
docker compose logs -f backend          # application logs
docker compose ps                       # health
ls -lh backups/ && df -h                # backups and disk
docker compose exec db psql -U bookingmngr -c '\dt'
```

**`docker compose down -v` destroys the database.** Plain `docker compose down`
is safe — the data lives in the named `pgdata` volume, and `caddy_data` holds
the TLS certificates.

---

## Notes for whoever maintains this

- `SECRET_KEY` signs the session tokens. Changing it signs everyone out.
- The backend refuses to start with `ENVIRONMENT=production` if `SECRET_KEY` or
  `OWNER_PASSWORD` are still the placeholder values.
- `/docs`, `/redoc` and the OpenAPI schema are disabled in production, both in
  the app and again in the Caddyfile.
- Login is rate limited to 10 failures per 15 minutes per IP + username. The
  counter is in-process, so restarting the backend clears it.
- Changing a password does **not** invalidate existing tokens — they are signed,
  not stored. Adding a `tokens_valid_from` column would fix that if it matters.
- The overlap-prevention migration needs the `btree_gist` extension, which is
  why Postgres runs as its superuser. Do not swap in a low-privilege role
  without creating the extension first.
