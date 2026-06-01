#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

load_env
require_cmd cmp
require_cmd curl
require_cmd git
require_cmd python3
require_cmd tar

usage() {
    cat <<'EOF'
Usage: prepare-opencode-dist.sh [--check] [--dry-run] [--force]

  --check    Only compare the packaged version with the latest upstream GitHub release.
  --dry-run  Preview the tracked packaging changes and local rpm/dist handoff updates.
  --force    Refresh the dist bundle even if versions already match.
EOF
}

check_only=false
dry_run=false
force_refresh=false

while [[ $# -gt 0 ]]; do
    case "$1" in
    --check)
        check_only=true
        ;;
    --dry-run)
        dry_run=true
        ;;
    --force)
        force_refresh=true
        ;;
    -h | --help)
        usage
        exit 0
        ;;
    *)
        usage >&2
        die "Unknown argument: $1"
        ;;
    esac
    shift
done

if [[ "$check_only" == true && "$dry_run" == true ]]; then
    die "--check and --dry-run cannot be used together. Use --check for a version-only comparison, or --dry-run to preview the full sync."
fi

[[ -f "$OPENCODE_PACKAGING_SPEC_FILE" ]] || die "Missing packaging spec: $OPENCODE_PACKAGING_SPEC_FILE"
[[ -f "$WITTY_PACKAGING_SPEC_FILE" ]] || die "Missing packaging spec: $WITTY_PACKAGING_SPEC_FILE"
[[ -d "$RPM_BASE_DIR" ]] || die "Missing base payload directory: $RPM_BASE_DIR"
[[ -f "$REPO_ROOT/LICENSE" ]] || die "Missing repository root license file: $REPO_ROOT/LICENSE"

release_json="$(mktemp)"
tarball_tmp="$(mktemp)"
models_tmp="$(mktemp)"
base_tmp="$(mktemp)"
cleanup() {
    rm -f "$release_json" "$tarball_tmp" "$models_tmp" "$base_tmp"
}
trap cleanup EXIT

log "Querying latest release metadata for ${OPENCODE_SOURCE_REPO}"
curl -fsSL "https://api.github.com/repos/${OPENCODE_SOURCE_REPO}/releases/latest" -o "$release_json"

release_metadata=()
while IFS= read -r line; do
    release_metadata+=("$line")
done < <(
    python3 - "$release_json" <<'PY'
import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    data = json.load(fh)

tag = data['tag_name']
version = tag[1:] if tag.startswith('v') else tag

print(tag)
print(version)
print(data.get('html_url', ''))
PY
)

tag="${release_metadata[0]}"
latest_version="${release_metadata[1]}"
release_url="${release_metadata[2]}"

spec_metadata=()
while IFS= read -r line; do
    spec_metadata+=("$line")
done < <(
    python3 - "$OPENCODE_PACKAGING_SPEC_FILE" "$WITTY_PACKAGING_SPEC_FILE" <<'PY'
import re
import sys
from pathlib import Path

for path in sys.argv[1:]:
    text = Path(path).read_text(encoding='utf-8')
    version_match = re.search(r'^Version:\s*(\S+)$', text, re.MULTILINE)
    release_match = re.search(r'^Release:\s*(\d+)', text, re.MULTILINE)
    if not version_match:
        raise SystemExit(f'Missing Version field in {path}')
    print(version_match.group(1))
    print(release_match.group(1) if release_match else '1')
PY
)

opencode_spec_version="${spec_metadata[0]}"
opencode_release_number="${spec_metadata[1]}"
witty_spec_version="${spec_metadata[2]}"
witty_release_number="${spec_metadata[3]}"

[[ "$opencode_spec_version" == "$witty_spec_version" ]] || die "Packaging spec versions differ: opencode.spec=${opencode_spec_version}, witty-opencode.spec=${witty_spec_version}. Reconcile them before preparing rpm/dist."
[[ "$opencode_release_number" == "$witty_release_number" ]] || die "Packaging spec release numbers differ: opencode.spec=${opencode_release_number}, witty-opencode.spec=${witty_release_number}. Reconcile them before preparing rpm/dist."

spec_version="$opencode_spec_version"
release_number="$opencode_release_number"

version_relation="$(
    python3 - "$spec_version" "$latest_version" <<'PY'
import itertools
import re
import sys

def normalize(value: str):
    return [int(part) for part in re.findall(r'\d+', value)]

current = normalize(sys.argv[1])
latest = normalize(sys.argv[2])

for lhs, rhs in itertools.zip_longest(current, latest, fillvalue=0):
    if lhs < rhs:
        print('older')
        raise SystemExit(0)
    if lhs > rhs:
        print('newer')
        raise SystemExit(0)

print('equal')
PY
)"

case "$version_relation" in
older)
    log "New upstream release detected: ${spec_version} -> ${latest_version}"
    [[ -n "$release_url" ]] && log "Release page: ${release_url}"
    ;;
equal)
    log "Packaging specs already track the latest upstream release ${tag}."
    ;;
newer)
    die "Packaging spec version ${spec_version} is newer than upstream latest ${latest_version}; refusing to downgrade automatically."
    ;;
*)
    die "Unexpected version comparison result: ${version_relation}"
    ;;
esac

if [[ "$check_only" == true ]]; then
    exit 0
fi

target_version="$spec_version"
target_release_number="$release_number"
if [[ "$version_relation" == "older" ]]; then
    target_version="$latest_version"
    target_release_number=1
fi

opencode_source_archive="$(opencode_source_archive_name "$target_version")"
source_tarball_url="https://github.com/${OPENCODE_SOURCE_REPO}/archive/refs/tags/${opencode_source_archive}"
target_opencode_tarball="$RPM_OPENCODE_DIST_DIR/${opencode_source_archive}"
target_base_tarball="$RPM_WITTY_DIST_DIR/${BASE_SOURCE_NAME}-${target_version}.tar.gz"
target_models_file="$OPENCODE_DIST_MODELS_FILE"

opencode_stale_tarballs=()
if [[ -d "$RPM_OPENCODE_DIST_DIR" ]]; then
    while IFS= read -r stale_tarball; do
        [[ -n "$stale_tarball" ]] || continue
        opencode_stale_tarballs+=("$stale_tarball")
    done < <(
        find "$RPM_OPENCODE_DIST_DIR" -maxdepth 1 -type f \( -name 'v*.tar.gz' -o -name 'opencode-*.tar.gz' \) \
            ! -name "$(basename "$target_opencode_tarball")" -print | sort
    )
fi

witty_stale_tarballs=()
if [[ -d "$RPM_WITTY_DIST_DIR" ]]; then
    while IFS= read -r stale_tarball; do
        [[ -n "$stale_tarball" ]] || continue
        witty_stale_tarballs+=("$stale_tarball")
    done < <(
        find "$RPM_WITTY_DIST_DIR" -maxdepth 1 -type f -name "${BASE_SOURCE_NAME}-*.tar.gz" \
            ! -name "$(basename "$target_base_tarball")" -print | sort
    )
fi

obsolete_flat_dist_files=()
if [[ -d "$RPM_DIST_DIR" ]]; then
    while IFS= read -r stale_file; do
        [[ -n "$stale_file" ]] || continue
        obsolete_flat_dist_files+=("$stale_file")
    done < <(
        find "$RPM_DIST_DIR" -maxdepth 1 -type f \( \
            -name 'opencode.spec' -o \
            -name 'witty-opencode.spec' -o \
            -name 'opencode-models-api.json' -o \
            -name 'v*.tar.gz' -o \
            -name 'opencode-*.tar.gz' -o \
            -name 'witty-opencode-*.tar.gz' -o \
            -name 'witty-opencode-base-*.tar.gz' \
            \) -print | sort
    )
fi

should_update_packaging_specs=false
[[ "$version_relation" == "older" ]] && should_update_packaging_specs=true

should_download_source0=false
if [[ "$force_refresh" == true || "$version_relation" == "older" || ! -f "$target_opencode_tarball" ]]; then
    should_download_source0=true
fi

should_refresh_models=false
if [[ "$force_refresh" == true || "$version_relation" == "older" || ! -f "$target_models_file" ]]; then
    should_refresh_models=true
fi

should_prepare_source2=false
if [[ "$force_refresh" == true || "$version_relation" == "older" || ! -f "$target_base_tarball" ]]; then
    should_prepare_source2=true
fi

should_copy_opencode_dist_spec=false
if [[ "$should_update_packaging_specs" == true || "$force_refresh" == true || ! -f "$OPENCODE_DIST_SPEC_FILE" ]]; then
    should_copy_opencode_dist_spec=true
elif ! cmp -s "$OPENCODE_PACKAGING_SPEC_FILE" "$OPENCODE_DIST_SPEC_FILE"; then
    should_copy_opencode_dist_spec=true
fi

should_copy_witty_dist_spec=false
if [[ "$should_update_packaging_specs" == true || "$force_refresh" == true || ! -f "$WITTY_DIST_SPEC_FILE" ]]; then
    should_copy_witty_dist_spec=true
elif ! cmp -s "$WITTY_PACKAGING_SPEC_FILE" "$WITTY_DIST_SPEC_FILE"; then
    should_copy_witty_dist_spec=true
fi

should_remove_stale=false
[[ "${#opencode_stale_tarballs[@]}" -gt 0 ]] && should_remove_stale=true
[[ "${#witty_stale_tarballs[@]}" -gt 0 ]] && should_remove_stale=true
[[ "${#obsolete_flat_dist_files[@]}" -gt 0 ]] && should_remove_stale=true

if [[ "$should_update_packaging_specs" == false && "$should_download_source0" == false && "$should_refresh_models" == false && "$should_prepare_source2" == false && "$should_copy_opencode_dist_spec" == false && "$should_copy_witty_dist_spec" == false && "$should_remove_stale" == false ]]; then
    if [[ "$dry_run" == true ]]; then
        log "Dry run: rpm/dist already contains the current split release bundle; no file changes would be made."
    else
        log "Nothing to do. Re-run with --force to refresh rpm/dist anyway."
    fi
    exit 0
fi

if [[ "$dry_run" == true ]]; then
    log "Dry run summary"
    log "- Latest upstream release: ${tag} (${latest_version})"
    log "- Current packaging spec version: ${spec_version}"
    log "- Target dist version: ${target_version}"
    log "- Target packaging release: ${target_release_number}"
    log "- Packaging specs would be updated: ${should_update_packaging_specs}"
    log "- opencode Source0 would be downloaded to: rpm/dist/opencode/${opencode_source_archive} (${should_download_source0})"
    log "- opencode Source1 would be refreshed at: rpm/dist/opencode/$(basename "$target_models_file") (${should_refresh_models})"
    log "- witty-opencode-base source bundle would be prepared at: rpm/dist/witty-opencode/$(basename "$target_base_tarball") (${should_prepare_source2})"
    log "- opencode dist spec would be copied from packaging/: ${should_copy_opencode_dist_spec}"
    log "- witty-opencode dist spec would be copied from packaging/: ${should_copy_witty_dist_spec}"

    if [[ "${#opencode_stale_tarballs[@]}" -gt 0 || "${#witty_stale_tarballs[@]}" -gt 0 || "${#obsolete_flat_dist_files[@]}" -gt 0 ]]; then
        log "- Stale dist files that would be removed:"
        for stale_file in "${opencode_stale_tarballs[@]}" "${witty_stale_tarballs[@]}" "${obsolete_flat_dist_files[@]}"; do
            [[ -n "$stale_file" ]] || continue
            log "  * ${stale_file#$REPO_ROOT/}"
        done
    else
        log "- No stale dist files would be removed"
    fi

    exit 0
fi

mkdir -p "$RPM_OPENCODE_DIST_DIR" "$RPM_WITTY_DIST_DIR"

update_spec_version() {
    local spec_path="$1"
    local new_version="$2"
    local new_release_number="$3"
    local tag="$4"

    python3 - "$spec_path" "$new_version" "$new_release_number" "$tag" <<'PY'
from datetime import datetime
from pathlib import Path
import re
import sys

spec_path = Path(sys.argv[1])
new_version = sys.argv[2]
new_release_number = sys.argv[3]
tag = sys.argv[4]

text = spec_path.read_text(encoding='utf-8')
text, count = re.subn(r'^(Version:\s*)(\S+)$', rf'\g<1>{new_version}', text, count=1, flags=re.MULTILINE)
if count != 1:
    raise SystemExit('Failed to update Version line in spec file')

text, count = re.subn(r'^(Release:\s*)(\d+)(.*)$', rf'\g<1>{new_release_number}\g<3>', text, count=1, flags=re.MULTILINE)
if count != 1:
    raise SystemExit('Failed to update Release line in spec file')

changelog_match = re.search(r'^%changelog\s*$', text, re.MULTILINE)
if not changelog_match:
    raise SystemExit('Missing %changelog section in spec file')

tail = text[changelog_match.end():].lstrip('\n')
header_match = re.search(r'^\* [A-Z][a-z]{2} [A-Z][a-z]{2} \d{2} \d{4} (.+?) - \S+\s*$', tail, re.MULTILINE)
author = header_match.group(1) if header_match else 'SIG-Intelligence <intelligence@openeuler.org>'
entry_date = datetime.now().strftime('%a %b %d %Y')
entry = (
    f'* {entry_date} {author} - {new_version}-{new_release_number}\n'
    f'- Sync to upstream {tag} release\n'
)

updated = f"{text[:changelog_match.end()]}\n{entry}\n{tail}"
spec_path.write_text(updated, encoding='utf-8')
PY
}

if [[ "$should_update_packaging_specs" == true ]]; then
    log "Updating rpm/packaging/opencode.spec to ${target_version}"
    update_spec_version "$OPENCODE_PACKAGING_SPEC_FILE" "$target_version" "$target_release_number" "$tag"
    log "Updating rpm/packaging/witty-opencode.spec to ${target_version}"
    update_spec_version "$WITTY_PACKAGING_SPEC_FILE" "$target_version" "$target_release_number" "$tag"
fi

if [[ "$should_download_source0" == true ]]; then
    log "Downloading opencode Source0 to rpm/dist/opencode/${opencode_source_archive}"
    curl -fL "$source_tarball_url" -o "$tarball_tmp"
    mv "$tarball_tmp" "$target_opencode_tarball"
fi

if [[ "$should_refresh_models" == true ]]; then
    log "Vendoring Source1 from ${OPENCODE_MODELS_URL}"
    curl -fL "$OPENCODE_MODELS_URL" -o "$models_tmp"
    mv "$models_tmp" "$target_models_file"
fi

if [[ "$should_prepare_source2" == true ]]; then
    log "Preparing witty-opencode-base source bundle from rpm/base/ plus the repository root LICENSE"
    staging_dir="$(mktemp -d)"
    cp -r "$RPM_BASE_DIR/." "$staging_dir/"
    cp "$REPO_ROOT/LICENSE" "$staging_dir/LICENSE"
    rpm_docs_file="$RPM_ROOT/docs/witty-opencode-base.md"
    if [[ -f "$rpm_docs_file" ]]; then
        mkdir -p "$staging_dir/docs"
        cp "$rpm_docs_file" "$staging_dir/docs/"
    fi
    tar -czf "$base_tmp" -C "$staging_dir" .
    rm -rf "$staging_dir"
    mv "$base_tmp" "$target_base_tarball"
fi

if [[ "$should_copy_opencode_dist_spec" == true ]]; then
    log "Copying opencode.spec into rpm/dist/opencode/"
    cp -f "$OPENCODE_PACKAGING_SPEC_FILE" "$OPENCODE_DIST_SPEC_FILE"
fi

if [[ "$should_copy_witty_dist_spec" == true ]]; then
    log "Copying witty-opencode.spec into rpm/dist/witty-opencode/"
    cp -f "$WITTY_PACKAGING_SPEC_FILE" "$WITTY_DIST_SPEC_FILE"
fi

if [[ "$should_remove_stale" == true ]]; then
    log "Removing stale dist files"
    for stale_file in "${opencode_stale_tarballs[@]}" "${witty_stale_tarballs[@]}" "${obsolete_flat_dist_files[@]}"; do
        [[ -n "$stale_file" ]] || continue
        rm -f "$stale_file"
    done
fi

if [[ "$should_update_packaging_specs" == true ]]; then
    log "Done. Packaging specs were updated to upstream ${tag}, and rpm/dist/{opencode,witty-opencode}/ was refreshed as a split local handoff bundle."
else
    log "Done. rpm/dist/{opencode,witty-opencode}/ now contains the refreshed split local handoff bundle for version ${target_version}."
fi
