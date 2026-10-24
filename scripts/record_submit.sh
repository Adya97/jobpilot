#!/bin/bash
# Usage: scripts/record_submit.sh <job_id> <form_screenshot> <confirmation_screenshot>
set -e
cd "$(dirname "$0")/.."
slug=$(echo "$1" | sed 's/[^A-Za-z0-9_-]/_/g')
cp "$2" "output/applications/$slug/form.jpg"
cp "$3" "output/applications/$slug/confirmation.jpg"
python3 scripts/jobs.py applied "$1"
