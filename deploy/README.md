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

Hetzner CX22 (2 vCPU / 4 GB, ~€4.50/mo) or equivalent, Ubuntu 24.04. **4 GB
matters** if you build images on the box — `next build` is the memory hog. Add
your SSH key at creation and note the static IPv4.

```bash
# harden
sudo adduser deploy && sudo usermod -aG sudo deploy
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/;s/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable
sudo apt install -y unattended-upgrades
sudo timedatectl set-timezone Europe/Sofia

# docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # log out and back in
```

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

## Building images: the architecture trap

An Apple Silicon Mac builds `arm64` images. A Hetzner/DO VPS is `amd64`. Images
built on the Mac **will not run** on the VPS.

**Option A — build on the VPS** (simplest, no registry):
`docker compose up -d --build`. Needs the 4 GB box.

**Option B — cross-build and push to GHCR** (faster deploys, real rollbacks):

```bash
# on the Mac, once
docker buildx create --name bm --use --bootstrap
echo $CR_PAT | docker login ghcr.io -u <user> --password-stdin

export TAG=$(git rev-parse --short HEAD)
docker buildx build --platform linux/amd64 -t ghcr.io/<user>/bookingmngr-backend:$TAG  --push ./backend
docker buildx build --platform linux/amd64 -t ghcr.io/<user>/bookingmngr-frontend:$TAG --push ./frontend
```

Set `BACKEND_IMAGE` / `FRONTEND_IMAGE` in the VPS `.env` to those tags, then
`docker compose pull && docker compose up -d`.

**Always tag with the git SHA, never `latest`** — then a rollback is editing two
lines in `.env` and running `docker compose up -d`.

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
