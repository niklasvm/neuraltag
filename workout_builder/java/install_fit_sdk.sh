#!/usr/bin/env bash
set -euo pipefail
# Installs the local Garmin FIT SDK jar into the user's local Maven repository
# so that the normal (non-system) dependency in pom.xml resolves and can be
# shaded into the final executable jar.
#
# Usage: ./install_fit_sdk.sh
# (Run from the java module root.)

FIT_VERSION=21.171.0
JAR_PATH="lib/fit.jar"
GROUP_ID="com.garmin.fit"
ARTIFACT_ID="fit"
PACKAGING="jar"

if [ ! -f "$JAR_PATH" ]; then
  echo "Error: $JAR_PATH not found. Run fetch_deps.sh first (or place fit.jar in lib/)." >&2
  exit 1
fi

echo "Installing $JAR_PATH into local Maven repo as $GROUP_ID:$ARTIFACT_ID:$FIT_VERSION"

mvn -q install:install-file \
  -Dfile="$JAR_PATH" \
  -DgroupId="$GROUP_ID" \
  -DartifactId="$ARTIFACT_ID" \
  -Dversion="$FIT_VERSION" \
  -Dpackaging="$PACKAGING" \
  -DgeneratePom=true

echo "Installed. You can now run: mvn -DskipTests package"
