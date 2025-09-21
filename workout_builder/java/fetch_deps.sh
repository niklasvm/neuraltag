#!/usr/bin/env bash
set -euo pipefail

# Simple dependency fetch script (no Maven) to populate java/lib with pinned versions.
# Usage: ./fetch_deps.sh [--force]
# Re-downloads jars if missing or --force supplied.

FIT_VERSION=21.115.0
SNAKEYAML_VERSION=2.2
LIB_DIR="$(dirname "$0")/lib"
mkdir -p "$LIB_DIR"

FIT_JAR="$LIB_DIR/fit.jar"
SNAKEYAML_JAR="$LIB_DIR/snakeyaml-${SNAKEYAML_VERSION}.jar"

FORCE=0
if [[ "${1:-}" == "--force" ]]; then
  FORCE=1
fi

fetch() {
  local url="$1"; shift
  local out="$1"; shift
  if [[ $FORCE -eq 1 || ! -f "$out" ]]; then
    echo "Downloading $(basename "$out") from $url" >&2
    curl -L -o "$out" "$url"
  else
    echo "Already present: $(basename "$out")" >&2
  fi
}

# Garmin FIT SDK jar from Maven Central
fetch "https://repo1.maven.org/maven2/com/garmin/fit/fit/${FIT_VERSION}/fit-${FIT_VERSION}.jar" "$FIT_JAR.tmp"
# Normalize name to fit.jar for existing Makefile expectations
mv -f "$FIT_JAR.tmp" "$FIT_JAR"

# SnakeYAML jar
fetch "https://repo1.maven.org/maven2/org/yaml/snakeyaml/${SNAKEYAML_VERSION}/snakeyaml-${SNAKEYAML_VERSION}.jar" "$SNAKEYAML_JAR"

echo "Dependency fetch complete:"
ls -1 "$LIB_DIR"
