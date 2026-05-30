#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd -- "$SKILL_DIR/../../.." && pwd)"
ENV_FILE="$REPO_ROOT/.agents/.env"
RPM_ROOT="$REPO_ROOT/rpm"
RPM_DIST_DIR="$RPM_ROOT/dist"
RPM_OPENCODE_DIST_DIR="$RPM_DIST_DIR/opencode"
RPM_WITTY_DIST_DIR="$RPM_DIST_DIR/witty-opencode"
RPM_BASE_DIR="$RPM_ROOT/base"
RPM_PACKAGING_DIR="$RPM_ROOT/packaging"
OPENCODE_PACKAGING_SPEC_FILE="$RPM_PACKAGING_DIR/opencode.spec"
WITTY_PACKAGING_SPEC_FILE="$RPM_PACKAGING_DIR/witty-opencode.spec"
OPENCODE_DIST_SPEC_FILE="$RPM_OPENCODE_DIST_DIR/opencode.spec"
WITTY_DIST_SPEC_FILE="$RPM_WITTY_DIST_DIR/witty-opencode.spec"
OPENCODE_DIST_MODELS_FILE="$RPM_OPENCODE_DIST_DIR/opencode-models-api.json"
BASE_SOURCE_NAME="witty-opencode-base"
OPENCODE_SOURCE_ARCHIVE_PREFIX="v"

export REPO_ROOT RPM_ROOT RPM_DIST_DIR RPM_OPENCODE_DIST_DIR RPM_WITTY_DIST_DIR RPM_BASE_DIR RPM_PACKAGING_DIR
export OPENCODE_PACKAGING_SPEC_FILE WITTY_PACKAGING_SPEC_FILE
export OPENCODE_DIST_SPEC_FILE WITTY_DIST_SPEC_FILE OPENCODE_DIST_MODELS_FILE
export BASE_SOURCE_NAME OPENCODE_SOURCE_ARCHIVE_PREFIX

log() {
    printf '[opencode-rpm] %s\n' "$*"
}

die() {
    printf '[opencode-rpm] ERROR: %s\n' "$*" >&2
    exit 1
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"
}

opencode_source_archive_name() {
    printf '%s%s.tar.gz\n' "$OPENCODE_SOURCE_ARCHIVE_PREFIX" "$1"
}

load_env() {
    if [[ -f "$ENV_FILE" ]]; then
        set -a
        # shellcheck disable=SC1090
        . "$ENV_FILE"
        set +a
    fi

    : "${OPENCODE_SOURCE_REPO:=anomalyco/opencode}"
    : "${OPENCODE_MODELS_URL:=https://models.dev/api.json}"
}
