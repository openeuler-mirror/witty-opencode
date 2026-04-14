---
name: opencode-rpm-dist-prep
description: Prepare the release bundle for anomalyco/opencode on openEuler. Use this whenever the user wants to check upstream GitHub releases, refresh Source0/Source1/Source2, update `rpm/packaging/witty-opencode.spec`, copy the finished spec into `rpm/dist`, or assemble files to hand off to CI or EulerMaker.
---

# OpenCode RPM dist preparation

Use this skill for source sync and release-bundle preparation. It updates `rpm/packaging/witty-opencode.spec` first, then mirrors the releasable inputs into the gitignored `rpm/dist/` handoff directory for local review, VM validation, or sending to another CI repository.

## Guardrails

- Do not run `rpmbuild` on macOS. This skill only prepares files.
- Prepare all shipping inputs in the gitignored `rpm/dist/` handoff directory; do not treat repository-root tarballs as the release source of truth.
- Update the changelog in `rpm/packaging/witty-opencode.spec` first, then copy that finished spec to `rpm/dist/witty-opencode.spec`.
- If the user wants to validate the build inside openEuler or OrbStack, switch to the `opencode-rpm-vm-build` skill.

## Files in this skill

- `scripts/prepare-opencode-dist.sh` — check the latest GitHub release, optionally preview the sync with `--dry-run`, download Source0 and Source1 into `rpm/dist`, generate Source2 from `rpm/base/` plus the repository-root `LICENSE`, update `rpm/packaging/witty-opencode.spec`, copy the finished spec into `rpm/dist`, and remove stale dist tarballs without trying to stage gitignored handoff artifacts.
- `scripts/common.sh` — shared helpers for repository paths plus developer-machine overrides such as upstream source or models snapshot URLs.

## Expected repo layout

- `rpm/packaging/witty-opencode.spec`
- `rpm/base/`
- `rpm/dist/witty-opencode.spec`
- `rpm/dist/witty-opencode-<version>.tar.gz`
- `rpm/dist/opencode-models-api.json`
- `rpm/dist/witty-opencode-base-<version>.tar.gz`
- optional `.agents/.env` for non-VM local overrides

## Standard sequence

1. Run `scripts/prepare-opencode-dist.sh --check` when you only need to compare the packaged version with GitHub's latest release.
2. Run `scripts/prepare-opencode-dist.sh --dry-run` when you want a no-write preview of what would change in tracked packaging files and the local `rpm/dist/` handoff directory.
3. Run `scripts/prepare-opencode-dist.sh` to sync to the latest release and prepare the full dist bundle.
4. Review the updated `rpm/packaging/witty-opencode.spec` plus the mirrored release inputs under `rpm/dist/`.
5. Hand the `rpm/dist/` contents to CI, another packaging repository, or the `opencode-rpm-vm-build` skill.

This skill does not need any VM selection or `OPENCODE_BUILDER_VM` setting.

## Notes for future refreshes

- Source2 is created from the current `rpm/base/` directory plus the repository-root `LICENSE`, so the base subpackage always ships the same repository snapshot and license text that the spec expects.
- Upstream `packages/opencode/script/build.ts` fetches `https://models.dev/api.json` unless `MODELS_DEV_API_JSON` is provided. Keeping `opencode-models-api.json` in `rpm/dist/` makes the build inputs explicit and easy to hand off.
- The script is intentionally conservative: it will not automatically downgrade the packaging spec if the local `Version` is newer than GitHub's latest release.
- The validated CI-safe mirror settings remain `ELECTRON_MIRROR=https://mirrors.huaweicloud.com/electron/` and `ELECTRON_BUILDER_BINARIES_MIRROR=https://mirrors.huaweicloud.com/electron-builder-binaries/`.
