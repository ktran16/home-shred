#!/bin/sh
# Back up the prod stack (SPEC §19.9 N1): a Postgres dump (pg_dump -Fc) plus a tarball of
# the media volume (progress photos), skipping tts/ (voices re-download via
# `make prod-tts-voices`, cache regenerates). Each run writes one dated set into
# $BACKUP_DIR/daily; the first run in any 7-day window is also hard-linked into weekly/.
#
#   make prod-backup                          # → ./backups/{daily,weekly}/homeshred-<stamp>.*
#   BACKUP_DIR=/mnt/nas/homeshred make prod-backup
set -eu
cd "$(dirname "$0")/.."

PROD="docker compose -f docker-compose.prod.yml"
BACKUP_DIR="${BACKUP_DIR:-backups}"
# rationale (SPEC §19.9 N1): 7 daily + 4 weekly is a month of history at ~2 sets/week cost.
KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-4}"

DAILY="$BACKUP_DIR/daily"
WEEKLY="$BACKUP_DIR/weekly"
mkdir -p "$DAILY" "$WEEKLY"

base="$DAILY/homeshred-$(date +%Y%m%d-%H%M%S)"
# Write to .tmp and rename at the end so a failed run never leaves a truncated set.
trap 'rm -f "$base".dump.tmp "$base".media.tar.gz.tmp' EXIT

$PROD exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' >"$base.dump.tmp"
$PROD exec -T backend tar -C /app/media --exclude=./tts -czf - . >"$base.media.tar.gz.tmp"
mv "$base.dump.tmp" "$base.dump"
mv "$base.media.tar.gz.tmp" "$base.media.tar.gz"

if [ -z "$(find "$WEEKLY" -name 'homeshred-*.dump' -mtime -7)" ]; then
	ln -f "$base.dump" "$base.media.tar.gz" "$WEEKLY/"
fi

# Drop the oldest sets beyond the keep count (names sort chronologically).
prune() {
	ls -1 "$1"/homeshred-*.dump 2>/dev/null | sort | head -n -"$2" | while read -r f; do
		rm -f "$f" "${f%.dump}.media.tar.gz"
	done
}
prune "$DAILY" "$KEEP_DAILY"
prune "$WEEKLY" "$KEEP_WEEKLY"

echo "Backup written:"
ls -lh "$base.dump" "$base.media.tar.gz"
