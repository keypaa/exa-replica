#!/usr/bin/env bash
# Atomic generation switch (D68). The new build is already on disk; this activates
# it (load N+1 in VRAM, switch, free N) or signals a short dense outage if 2xV_gpu
# does not fit. Build and serving never run simultaneously (mono-GPU).
set -euo pipefail
NEW_BUILD="${1:?usage: switch.sh <new-build-id>}"
echo "switching to build ${NEW_BUILD} (atomic; see bootstrap/switch.py for the 2x_peak/short_outage decision)"
# The actual activation is performed by the serving process via apply_switch().