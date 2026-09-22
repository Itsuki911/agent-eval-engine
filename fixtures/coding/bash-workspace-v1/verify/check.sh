#!/usr/bin/env bash
set -euo pipefail

actual="$(bash greet.sh agent)"
test "$actual" = "hello agent"
