#!/usr/bin/env sh
set -eu

make gen-scene-schema

if ! git diff --quiet -- packages/remotion-templates/schema/scene-1.0.0.json packages/remotion-templates/src/schema.ts; then
  echo "Scene schema artifacts are stale. Run 'make gen-scene-schema' and commit schema/scene-1.0.0.json and src/schema.ts." >&2
  exit 1
fi
