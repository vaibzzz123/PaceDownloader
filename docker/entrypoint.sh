#!/bin/sh
set -eu

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
DATA_ROOT="${PACE_DATA_DIR:-/var/lib/pace-downloader}"
APP_USER="pace"
APP_GROUP="pace"

case "$PUID" in
    ''|*[!0-9]*)
        echo "PUID must be a numeric, non-root UID." >&2
        exit 1
        ;;
esac

case "$PGID" in
    ''|*[!0-9]*)
        echo "PGID must be a numeric, non-root GID." >&2
        exit 1
        ;;
esac

if [ "$PUID" = "0" ] || [ "$PGID" = "0" ]; then
    echo "PUID and PGID must not be 0. Pace Downloader should not run as root." >&2
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    exec "$@"
fi

group_name="$(getent group "$PGID" | cut -d: -f1 || true)"
if [ -z "$group_name" ]; then
    if getent group "$APP_GROUP" >/dev/null; then
        groupmod --gid "$PGID" "$APP_GROUP"
    else
        groupadd --gid "$PGID" "$APP_GROUP"
    fi
    group_name="$APP_GROUP"
fi

user_name="$(getent passwd "$PUID" | cut -d: -f1 || true)"
if [ -z "$user_name" ]; then
    if getent passwd "$APP_USER" >/dev/null; then
        usermod --uid "$PUID" --gid "$PGID" --home /home/pace "$APP_USER"
    else
        useradd --uid "$PUID" --gid "$PGID" --home-dir /home/pace --shell /usr/sbin/nologin "$APP_USER"
    fi
fi

mkdir -p "$DATA_ROOT" /home/pace
chown -R "$PUID:$PGID" "$DATA_ROOT" /home/pace

export HOME=/home/pace
exec gosu "$PUID:$PGID" "$@"
