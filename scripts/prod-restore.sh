#!/bin/sh
# Restore a set written by prod-backup.sh (SPEC §19.9 N1).
#
#   make prod-restore-test FILE=backups/daily/homeshred-<stamp>.dump
#       Restores into a throwaway postgres:17 container and prints per-table row counts.
#       Never touches prod — this is the acceptance test for a backup.
#   make prod-restore FILE=backups/daily/homeshred-<stamp>.dump CONFIRM=yes
#       Runs the test restore first, then REPLACES the prod DB (pg_restore --clean) and
#       unpacks the matching .media.tar.gz into the media volume.
set -eu
cd "$(dirname "$0")/.."

MODE="${1:-}"
FILE="${2:-}"
if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
	echo "usage: $0 test|prod <backups/.../homeshred-<stamp>.dump>" >&2
	exit 2
fi

PROD="docker compose -f docker-compose.prod.yml"
SCRATCH=homeshred-restore-test
# Exact row count for every public table (xpath/query_to_xml runs a count per table).
COUNTS_SQL="select table_name, (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from public.%I', table_name), false, true, '')))[1]::text::bigint as rows from information_schema.tables where table_schema = 'public' and table_type = 'BASE TABLE' order by 1;"

restore_test() {
	docker rm -f "$SCRATCH" >/dev/null 2>&1 || true
	docker run -d --name "$SCRATCH" -e POSTGRES_PASSWORD=scratch -e POSTGRES_DB=restore \
		postgres:17 >/dev/null
	trap 'docker rm -f "$SCRATCH" >/dev/null 2>&1 || true' EXIT
	# Probe over TCP: the image's init-time temp server is socket-only, so this only
	# succeeds once the real server is up.
	i=0
	until docker exec "$SCRATCH" pg_isready -h 127.0.0.1 -U postgres -d restore >/dev/null 2>&1; do
		i=$((i + 1))
		[ "$i" -lt 60 ] || { echo "scratch postgres did not start" >&2; exit 1; }
		sleep 1
	done
	docker exec -i "$SCRATCH" pg_restore -U postgres -d restore --no-owner --no-acl \
		--exit-on-error <"$FILE"
	docker exec "$SCRATCH" psql -U postgres -d restore -c "$COUNTS_SQL"
	echo "Restore test OK: $FILE"
}

restore_prod() {
	if [ "${CONFIRM:-}" != yes ]; then
		echo "Refusing: this REPLACES the prod database. Re-run with CONFIRM=yes." >&2
		exit 2
	fi
	restore_test
	media="${FILE%.dump}.media.tar.gz"
	$PROD stop frontend backend
	$PROD exec -T db sh -c \
		'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --exit-on-error' \
		<"$FILE"
	$PROD start backend frontend
	if [ -f "$media" ]; then
		$PROD exec -T backend tar -C /app/media -xzf - <"$media"
	fi
	echo "Prod restored from $FILE"
}

case "$MODE" in
test) restore_test ;;
prod) restore_prod ;;
*)
	echo "usage: $0 test|prod <file>" >&2
	exit 2
	;;
esac
