#!/usr/bin/env bash
# Prepare a fresh Ubuntu 24.04 server to run BookingMngr.
#
#   scp deploy/bootstrap-vps.sh root@<ip>:/tmp/
#   ssh root@<ip> 'bash /tmp/bootstrap-vps.sh <your-username>'
#
# Installs Docker, creates a sudo user, and closes off everything except SSH,
# HTTP and HTTPS. Idempotent — safe to re-run.
#
# IMPORTANT: it disables SSH password login. Your key must already work, or you
# will lock yourself out. The script refuses to proceed unless it finds one.
set -euo pipefail

USERNAME="${1:-deploy}"
TIMEZONE="${TIMEZONE:-Europe/Sofia}"

[ "$(id -u)" -eq 0 ] || { echo "Run as root." >&2; exit 1; }

echo "==> Creating user '$USERNAME'"
if ! id -u "$USERNAME" >/dev/null 2>&1; then
    adduser --disabled-password --gecos "" "$USERNAME"
fi
usermod -aG sudo "$USERNAME"

# Carry root's authorized keys over, so the new user can log in immediately.
if [ -f /root/.ssh/authorized_keys ]; then
    install -d -m 700 -o "$USERNAME" -g "$USERNAME" "/home/$USERNAME/.ssh"
    install -m 600 -o "$USERNAME" -g "$USERNAME" \
        /root/.ssh/authorized_keys "/home/$USERNAME/.ssh/authorized_keys"
fi

# Refuse to disable password auth if that would strand you.
if [ ! -s "/home/$USERNAME/.ssh/authorized_keys" ]; then
    echo "ERROR: /home/$USERNAME/.ssh/authorized_keys is missing or empty." >&2
    echo "Add your public key first, or disabling password login locks you out." >&2
    exit 1
fi

echo "==> Hardening SSH"
# Ubuntu's sshd_config ends with `Include /etc/ssh/sshd_config.d/*.conf`, so a
# drop-in survives package upgrades rewriting the main file.
mkdir -p /etc/ssh/sshd_config.d
sshd_conf=/etc/ssh/sshd_config.d/99-bookingmngr.conf
cat > "$sshd_conf" <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
EOF
# Validate before restarting: a bad config would otherwise kill remote access.
sshd -t
systemctl restart ssh || systemctl restart sshd

echo "==> Firewall"
apt-get update -qq
apt-get install -y -qq ufw >/dev/null
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw allow 443/udp >/dev/null   # HTTP/3, which Caddy serves
ufw --force enable >/dev/null

echo "==> Unattended security updates"
apt-get install -y -qq unattended-upgrades >/dev/null
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true

echo "==> Timezone: $TIMEZONE"
timedatectl set-timezone "$TIMEZONE"

echo "==> Docker"
if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
fi
usermod -aG docker "$USERNAME"
systemctl enable --now docker

echo "==> Application directory"
install -d -o "$USERNAME" -g "$USERNAME" /opt/bookingmngr

cat <<EOF

Done.

  user       : $USERNAME (sudo, docker)
  ssh        : key only, root login disabled
  firewall   : $(ufw status | head -1)
  docker     : $(docker --version)
  app dir    : /opt/bookingmngr

Next, from your machine:

  ssh $USERNAME@<this-host>
  git clone <repo-url> /opt/bookingmngr && cd /opt/bookingmngr
  cp .env.example .env    # fill in SITE_ADDRESS, ACME_EMAIL and the secrets
  chmod 600 .env && mkdir -p backups

Confirm DNS resolves to this server BEFORE starting the stack, or the failed
certificate attempt counts against the Let's Encrypt rate limit:

  dig +short <your-subdomain>.duckdns.org
EOF
