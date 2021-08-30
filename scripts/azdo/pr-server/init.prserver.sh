#!/bin/bash
set -euo pipefail

PRSERVER_DATA=/var/pr-server
PRSERVER_LOG="${PRSERVER_DATA}/prserv.log"
PRSERVER_HOST=${PRSERVER_HOST:-0.0.0.0}
PRSERVER_POST=${PRSERVER_PORT:-8585}
prserver_pidfile="/tmp/PRServer_${PRSERVER_HOST}_${PRSERVER_PORT}.pid"

touch "${PRSERVER_LOG}"

stop_server() {
	start-stop-daemon --stop \
		--oknodo \
		--pidfile "${prserver_pidfile}" \
		--remove-pidfile \
	""
	trap - SIGINT SIGTERM
}

start_server() {
	echo "INFO: Starting PR server on ${PRSERVER_HOST}:${PRSERVER_PORT}"
	local loglevel_args="--loglevel=INFO"
	[ "${VERBOSE}" == true ] && loglevel_args="--loglevel=DEBUG"

	start-stop-daemon --start \
		--startas /srv/bitbake/bin/bitbake-prserv \
		--oknodo \
		--pidfile "${prserver_pidfile}" \
		--user bitbake \
		python /srv/bitbake/bin/bitbake-prserv \
		-- \
			--start \
			--file="${PRSERVER_DATA}/prserv.sqlite3" \
			--log="${PRSERVER_LOG}" \
			${loglevel_args} \
			--host=${PRSERVER_HOST} \
			--port=${PRSERVER_PORT} \
	""
	trap stop_server SIGINT SIGTERM
}

stop_server
start_server

# Print diagnostic info
ps aux

# Monitor the pr-server log file and use it as the loop which keeps this init
# process alive until the pr-server is done.
read prserver_pid <"${prserver_pidfile}"
tail --pid=${prserver_pid} -f ${PRSERVER_LOG} -n 0 &
wait $!

stop_server
