#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rm -f data/lab.sqlite3 logs/security-events.log
printf 'Lab database and logs reset. They will be recreated on next start.\n'
