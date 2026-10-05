#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p dist
python3 -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
printf '%s\n' "Wheel built in dist/. Install Raspberry Pi OS camera dependencies before running it."
