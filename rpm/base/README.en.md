# witty-opencode-base

This directory contains the source for the **`witty-opencode-base`** RPM package, which deploys the managed resources that accompany the `opencode` CLI as a system-managed installation.

## Goals

- `/etc/opencode/opencode.json` and `/etc/opencode/tui.json` are owned by exactly one package
- Multiple Agent/Skill sub-RPMs can install and uninstall cleanly without interfering with each other
- No per-package JSON editing in `%post` or `%postun` scripts
- The home logo is managed exclusively by the base RPM

## RPM directory layout

- `/usr/share/witty/opencode/skills/<rpm-name>/...` — skill assets from sub-RPMs
- `/usr/share/witty/opencode/agents/<rpm-name>/...` — prompt Markdown files and other file-based assets from sub-RPMs
- `/usr/share/witty/opencode/config.d/<rpm-name>.json` — `opencode.json`-compatible config fragments from sub-RPMs
- `/usr/share/witty/opencode/plugins/logo/witty-logo.tsx` — logo plugin, owned by the base RPM
- `/usr/libexec/witty-opencode/rebuild-managed-config.mjs` — config generator, owned by the base RPM
- `/etc/opencode/opencode.json` — generated managed config
- `/etc/opencode/tui.json` — generated managed TUI config

## How the generator works

`bin/rebuild-managed-config.mjs` scans `config.d/*.json`, treating each file as an `opencode.json`-compatible fragment. It rewrites relative `{file:...}` references to absolute paths and produces:

- `opencode.json`: a fixed `skills.paths` entry pointing at the shared skills root, plus all merged config sections (e.g. `agent`, `mcp`, `provider`, `permission`)
- `tui.json`: pointing at the base RPM logo plugin

The generator is designed to run from `%posttrans` or a file trigger, so a single RPM transaction only rebuilds the managed config once.

## RPM hook scripts

Two additional components ship with the base RPM:

- `bin/run-managed-config-hook.sh` — a shared shell wrapper for use in RPM scriptlets and file triggers
- `../docs/witty-opencode-addon-packaging.md` — packaging conventions and spec guidance for Agent/Skill/config sub-RPM maintainers, covering when a sub-package should stay data-only and when an optional `%posttrans` fallback is appropriate

### Why both `%posttrans` and file triggers?

- `%posttrans` handles the case where the **base RPM itself** is installed or upgraded and needs to create or refresh `/etc/opencode/*.json`.
- `%transfiletriggerin` and `%transfiletriggerpostun` are the right tool for **sub-RPM lifecycle events**: they fire when files under the managed Witty/OpenCode directories are added or removed, even when the base RPM is not part of the transaction.

This split keeps sub-RPMs as plain data packages while the base RPM remains the sole owner of generated config.

### Failure policy

The shared hook is **fail-open** by default: it logs errors but exits successfully, so a failed config rebuild never leaves an RPM transaction in an incomplete state.

Set `WITTY_OPENCODE_RPM_HOOK_STRICT=1` before invoking the hook if your policy requires hard failure instead.

## Drop-in format

See `examples/config.d/witty-example.json` for a working example.

Each drop-in must be a valid `opencode.json` fragment:

- `$schema` is optional and ignored during merging
- Top-level sections such as `agent`, `mcp`, `provider`, `permission`, and `command` can be included directly
- Relative `{file:...}` tokens are resolved against the drop-in file's directory and rewritten to absolute paths in the generated `/etc/opencode/opencode.json`

If any managed namespace (`agent`, `command`, `mode`, `mcp`) contains duplicate names, the generator aborts before any atomic rename, leaving the previous config intact.

## Directory contents

- `bin/rebuild-managed-config.mjs` — config generation script
- `bin/run-managed-config-hook.sh` — RPM hook wrapper script
- `plugins/logo/witty-logo.tsx` — logo plugin asset
- `examples/` — sample drop-in and prompt layout
- `../docs/witty-opencode-addon-packaging.md` — sub-RPM packaging conventions
