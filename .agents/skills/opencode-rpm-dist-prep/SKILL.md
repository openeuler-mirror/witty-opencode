---
name: opencode-rpm-dist-prep
description: Prepare the release bundle for anomalyco/opencode on openEuler. Use this whenever the user wants to check upstream GitHub releases, refresh the split `rpm/dist/opencode/` and `rpm/dist/witty-opencode/` handoff directories, update `rpm/packaging/opencode.spec` and `rpm/packaging/witty-opencode.spec`, or assemble files to hand off to CI or EulerMaker.
---

# OpenCode RPM dist preparation

Use this skill for source sync and release-bundle preparation. It updates `rpm/packaging/opencode.spec` and `rpm/packaging/witty-opencode.spec` first, then mirrors the releasable inputs into the gitignored split handoff directories under `rpm/dist/` for local review, VM validation, or sending to another CI repository.

## Guardrails

- Do not run `rpmbuild` on macOS. This skill only prepares files.
- Prepare all shipping inputs in the gitignored split handoff directories `rpm/dist/opencode/` and `rpm/dist/witty-opencode/`; do not treat repository-root tarballs as the release source of truth.
- Update the changelog in `rpm/packaging/opencode.spec` and `rpm/packaging/witty-opencode.spec` first, then copy the finished specs into their matching dist subdirectories.
- If the user wants to validate the build inside openEuler or OrbStack, switch to the `opencode-rpm-vm-build` skill.

## Files in this skill

- `scripts/prepare-opencode-dist.sh` — check the latest GitHub release, optionally preview the sync with `--dry-run`, download the `opencode` Source0 archive `v<version>.tar.gz` plus Source1 into `rpm/dist/opencode/`, generate the `witty-opencode-base` source tarball into `rpm/dist/witty-opencode/`, update both tracked packaging specs, copy them into the matching dist subdirectories, and remove stale files from the old flat dist layout.
- `scripts/common.sh` — shared helpers for repository paths plus developer-machine overrides such as upstream source or models snapshot URLs.

## Expected repo layout

- `rpm/packaging/opencode.spec`
- `rpm/packaging/witty-opencode.spec`
- `rpm/base/`
- `rpm/dist/opencode/opencode.spec`
- `rpm/dist/opencode/v<version>.tar.gz`
- `rpm/dist/opencode/opencode-models-api.json`
- `rpm/dist/witty-opencode/witty-opencode.spec`
- `rpm/dist/witty-opencode/witty-opencode-base-<version>.tar.gz`
- optional `.agents/.env` for non-VM local overrides

## Standard sequence

1. Run `scripts/prepare-opencode-dist.sh --check` when you only need to compare the packaged version with GitHub's latest release.
2. Run `scripts/prepare-opencode-dist.sh --dry-run` when you want a no-write preview of what would change in the tracked packaging specs and the split `rpm/dist/` handoff directories.
3. Run `scripts/prepare-opencode-dist.sh` to sync to the latest release and prepare the full split dist bundle.
4. Review the updated `rpm/packaging/opencode.spec`, `rpm/packaging/witty-opencode.spec`, and the mirrored release inputs under `rpm/dist/opencode/` plus `rpm/dist/witty-opencode/`.
5. Hand the split `rpm/dist/` contents to CI, another packaging repository, or the `opencode-rpm-vm-build` skill.

This skill does not need any VM selection or `OPENCODE_BUILDER_VM` setting.

## Notes for future refreshes

- The `witty-opencode-base` source tarball is created from the current `rpm/base/` directory plus the repository-root `LICENSE`, so the base package always ships the same repository snapshot and license text that `rpm/packaging/witty-opencode.spec` expects.
- `rpm/packaging/opencode.spec` now points `Source0` at `https://github.com/anomalyco/%{name}/archive/refs/tags/v%{version}.tar.gz`, so the split handoff directory must carry the basename `v<version>.tar.gz` under `rpm/dist/opencode/`.
- Upstream `packages/opencode/script/build.ts` fetches `https://models.dev/api.json` unless `MODELS_DEV_API_JSON` is provided. Keeping `opencode-models-api.json` in `rpm/dist/opencode/` makes the build inputs explicit and easy to hand off.
- The script is intentionally conservative: it will not automatically downgrade either packaging spec if the local `Version` is newer than GitHub's latest release, and it resets `Release` back to `1` whenever a version bump is applied.
- The validated CI-safe mirror settings remain `ELECTRON_MIRROR=https://mirrors.huaweicloud.com/electron/` and `ELECTRON_BUILDER_BINARIES_MIRROR=https://mirrors.huaweicloud.com/electron-builder-binaries/`.
