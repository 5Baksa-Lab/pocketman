#!/usr/bin/env bash
set -euo pipefail

PART=""
STAGE=""
OWNER=""

usage() {
  cat <<USAGE
Usage:
  bash docs/develop_rule/scripts/init_stage_devlog.sh \\
    --part <frontend|backend|mlops|pm-devops> \\
    --stage <stage-id> \\
    --owner "<name>"
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --part)
      PART="${2:-}"
      shift 2
      ;;
    --stage)
      STAGE="${2:-}"
      shift 2
      ;;
    --owner)
      OWNER="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$PART" || -z "$STAGE" || -z "$OWNER" ]]; then
  echo "Error: --part, --stage, --owner are required." >&2
  usage
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TEMPLATE_PATH="$ROOT_DIR/docs/develop_rule/templates/DEVLOG_TEMPLATE.md"
TARGET_DIR="$ROOT_DIR/docs/development_logs/$PART/stage-$STAGE"
TARGET_FILE="$TARGET_DIR/DEVLOG.md"
TODAY="$(date +%F)"

mkdir -p "$TARGET_DIR"

if [[ ! -f "$TEMPLATE_PATH" ]]; then
  echo "Template not found: $TEMPLATE_PATH" >&2
  exit 1
fi

if [[ -f "$TARGET_FILE" ]]; then
  echo "Already exists: $TARGET_FILE"
  exit 0
fi

cp "$TEMPLATE_PATH" "$TARGET_FILE"

# Basic placeholder fill for first draft
sed -i '' "s|<frontend/backend/mlops/pm-devops>|$PART|g" "$TARGET_FILE"
sed -i '' "s|<예: f1-upload-top3>|$STAGE|g" "$TARGET_FILE"
sed -i '' "s|<이름>|$OWNER|g" "$TARGET_FILE"
sed -i '' "s|<YYYY-MM-DD>|$TODAY|g" "$TARGET_FILE"

echo "Created: $TARGET_FILE"
