#!/usr/bin/env bash
# Build the production images and deliver them to the VPS.
#
#   ./deploy/build-images.sh ssh   deploy@1.2.3.4     # registry-free (default)
#   ./deploy/build-images.sh ghcr  <github-username>   # push to GHCR
#   ./deploy/build-images.sh local                     # build only, load locally
#
# The target is a Hetzner CAX11, which is ARM64 — the same architecture as an
# Apple Silicon Mac, so these build natively with no emulation. If you ever move
# to an x86 box, the images must be rebuilt for it:
#
#   PLATFORM=linux/amd64 ./deploy/build-images.sh ssh deploy@1.2.3.4
#
# Images are tagged with the short git SHA, never `latest`, so a rollback is
# editing two lines in the VPS .env and running `docker compose up -d`.
set -euo pipefail

PLATFORM="${PLATFORM:-linux/arm64}"
BUILDER="bookingmngr"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

mode="${1:-ssh}"
target="${2:-}"

usage() {
    echo "usage: $0 {ssh <user@host>|ghcr <github-username>|local}" >&2
    exit 1
}

# Validate arguments before doing anything slow or interactive.
case "$mode" in
ssh | ghcr) [ -n "$target" ] || usage ;;
local) ;;
*) usage ;;
esac

# The tag names a commit, so a dirty tree means the tag lies about what shipped.
if [ -n "$(git status --porcelain)" ]; then
    echo "WARNING: working tree is dirty — tag ${mode} would name a commit that"
    echo "         does not match what you are shipping. Commit first."
    if [ -t 0 ]; then
        printf "Continue anyway? [y/N] "
        read -r reply
        [ "$reply" = "y" ] || exit 1
    else
        echo "Refusing to build non-interactively with uncommitted changes." >&2
        exit 1
    fi
fi

TAG="$(git rev-parse --short HEAD)"

# Flag emulation, since it is the difference between a one-minute build and a
# long one — and a mismatch usually means the wrong target was assumed.
case "$(uname -m)" in
arm64 | aarch64) host_platform="linux/arm64" ;;
x86_64 | amd64) host_platform="linux/amd64" ;;
*) host_platform="unknown" ;;
esac

if [ "$PLATFORM" = "$host_platform" ]; then
    echo "Building ${PLATFORM} images at ${TAG}  (native)"
else
    echo "Building ${PLATFORM} images at ${TAG}  (emulated on ${host_platform})"
fi

# --bootstrap so a fresh machine works without a separate setup step.
docker buildx inspect "$BUILDER" >/dev/null 2>&1 \
    || docker buildx create --name "$BUILDER" --bootstrap >/dev/null

build() {   # build <context> <image-ref> [extra args...]
    local context="$1" ref="$2"; shift 2
    echo "  -> $ref"
    docker buildx build --builder "$BUILDER" --platform "$PLATFORM" \
        -t "$ref" "$@" "$context"
}

case "$mode" in
ghcr)
    # Requires: echo \$CR_PAT | docker login ghcr.io -u <user> --password-stdin
    # NOTE: GHCR's free tier allows 500 MB of *private* package storage. These
    # two images will approach that, so prune old tags or make them public.
    backend="ghcr.io/${target}/bookingmngr-backend:${TAG}"
    frontend="ghcr.io/${target}/bookingmngr-frontend:${TAG}"
    build ./backend  "$backend"  --push
    build ./frontend "$frontend" --push
    ;;

ssh)
    # No registry, no account, no storage quota: stream the image straight into
    # the remote docker daemon.
    backend="bookingmngr-backend:${TAG}"
    frontend="bookingmngr-frontend:${TAG}"
    for pair in "./backend:$backend" "./frontend:$frontend"; do
        context="${pair%%:*}"
        ref="${pair#*:}"
        echo "  -> $ref  (streaming to $target)"
        docker buildx build --builder "$BUILDER" --platform "$PLATFORM" \
            -t "$ref" -o type=docker,dest=- "$context" | ssh "$target" 'docker load'
    done
    ;;

local)
    backend="bookingmngr-backend:${TAG}"
    frontend="bookingmngr-frontend:${TAG}"
    build ./backend  "$backend"  --load
    build ./frontend "$frontend" --load
    ;;

esac

cat <<EOF

Done. On the VPS, set these in /opt/bookingmngr/.env:

  BACKEND_IMAGE=${backend}
  FRONTEND_IMAGE=${frontend}

then:

  docker compose exec backup /bin/sh /opt/backup/run-backup.sh   # before migrations
  docker compose up -d
EOF
