#!/usr/bin/env bash
#
# Superseded — kept only so a stale instruction does not become a rogue deploy.
#
# The MVP 0 draft of this file assumed `pgs.service`, a `127.0.0.1:8000` bind and
# DB_NAME/DB_USER/DB_PASSWORD variables. None of those are true of this app: the
# settings read DATABASE_URL, the box wants `<app>_web`, and nothing listens on a
# TCP port. The real script is deploy/deploy.sh, which also runs the gate.
#
set -euo pipefail
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/deploy/deploy.sh" "$@"
