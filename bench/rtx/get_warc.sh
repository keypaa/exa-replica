#!/usr/bin/env bash
# Fetch one Common Crawl WARC filename (CC-MAIN-2026-43 target, D28/D35).
# Prints the filename; download it with:
#   wget "https://data.commoncrawl.org/$(bash bench/rtx/get_warc.sh)"
# Or pass the full URL directly to run_b_passage_spec.py --warc.
set -euo pipefail
CRAWL="${1:-CC-MAIN-2026-43}"
curl -s "https://index.commoncrawl.org/${CRAWL}-index?url=example.com&output=json&limit=1" \
  | python3 -c "import sys,json; print(json.loads(sys.stdin.readline())['filename'])"