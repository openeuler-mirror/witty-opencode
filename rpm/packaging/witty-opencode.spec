%global debug_package %{nil}
%global __strip /bin/true
%global __provides_exclude_from ^/opt/OpenCode/.*$
%global __requires_exclude_from ^/opt/OpenCode/.*$
%global upstream_name opencode
%global electron_mirror https://mirrors.huaweicloud.com/electron/
%global electron_builder_binaries_mirror https://mirrors.huaweicloud.com/electron-builder-binaries/
%{!?opencode_cache_dir:%global opencode_cache_dir %{_builddir}/%{name}-%{version}/.cache/opencode-rpm}
%global base_source_name witty-opencode-base
%global base_source_dir %{_builddir}/%{base_source_name}-%{version}
%global witty_managed_root %{_datadir}/witty/opencode
%global witty_managed_config_dropins %{witty_managed_root}/config.d
%global witty_managed_agents %{witty_managed_root}/agents
%global witty_managed_skills %{witty_managed_root}/skills
%global witty_managed_plugins %{witty_managed_root}/plugins
%global witty_managed_logo %{witty_managed_plugins}/logo/witty-logo.tsx
%global witty_managed_libexec %{_libexecdir}/witty-opencode

Name:           witty-opencode
Version:        1.3.17
Release:        2%{?dist}
Summary:        AI coding agent built for the terminal

License:        MIT AND MulanPSL-2.0
URL:            https://github.com/anomalyco/opencode
Source0:        %{name}-%{version}.tar.gz
# Build-time models.dev snapshot consumed by packages/opencode/script/build.ts.
Source1:        opencode-models-api.json
# Managed-config assets for the witty-opencode-base subpackage.
Source2:        %{base_source_name}-%{version}.tar.gz

ExclusiveArch:  aarch64 x86_64

BuildRequires:  findutils
BuildRequires:  git
BuildRequires:  gzip
BuildRequires:  cpio
BuildRequires:  chrpath
BuildRequires:  nodejs >= 20
BuildRequires:  npm
BuildRequires:  patch
BuildRequires:  tar
BuildRequires:  unzip
BuildRequires:  which
BuildRequires:  xz
BuildRequires:  zip

%ifarch aarch64
%global opencode_build_target opencode-linux-arm64
%global electron_builder_arch arm64
%global electron_rpm_arch aarch64
%endif
%ifarch x86_64
%global opencode_build_target opencode-linux-x64
%global electron_builder_arch x64
%global electron_rpm_arch x86_64
%endif

%package -n %{upstream_name}
Summary:        AI coding agent built for the terminal
License:        MIT
Requires:       git

%package -n %{upstream_name}-desktop
Summary:        Electron desktop app for OpenCode with bundled sidecar CLI
License:        MIT
Requires:       at-spi2-core
Requires:       gtk3
Requires:       libXScrnSaver
Requires:       libnotify
Requires:       nss
Requires:       xdg-utils
Requires:       (libXtst or libXtst6)
Requires:       (libuuid or libuuid1)

%package base
Summary:        Managed configuration and RPM integration assets for witty-opencode
License:        MulanPSL-2.0
BuildArch:      noarch
Requires:       %{upstream_name} = %{version}-%{release}
Requires:       nodejs >= 20

%description -n %{upstream_name}
OpenCode is an open source AI coding agent for the terminal. This package builds
the upstream CLI from the tagged source tree and installs the native OpenCode
binary as `/usr/bin/opencode` for openEuler.

%description -n %{upstream_name}-desktop
This subpackage builds and ships the OpenCode desktop application for openEuler.
It uses the upstream Electron desktop shell and bundles the matching `opencode`
CLI as a sidecar, so it does not require the system opencode package at runtime.

%description base
This subpackage ships the managed-config assets for witty-opencode on openEuler.
It owns the shared logo plugin, managed resource directories, the config
generator, and the RPM transaction hooks that rebuild `/etc/opencode/opencode.json`
and `/etc/opencode/tui.json` from installed config fragments and resource bundles.

%description
OpenCode CLI and desktop application for openEuler. See the opencode and
opencode-desktop subpackages for the actual installable components.

%prep
rm -rf %{name}-%{version}
mkdir -p %{name}-%{version}
tar -xzf %{SOURCE0} --strip-components=1 -C %{name}-%{version}
rm -rf %{base_source_dir}
mkdir -p %{base_source_dir}
tar -xzf %{SOURCE2} --strip-components=1 -C %{base_source_dir}
cd %{name}-%{version}

%build
cd %{name}-%{version}

export HOME="%{_builddir}/%{name}-%{version}/.home"
mkdir -p "$HOME"

export npm_config_registry="https://mirrors.huaweicloud.com/repository/npm/"
export NPM_CONFIG_REGISTRY="$npm_config_registry"
export npm_config_cache="%{opencode_cache_dir}/npm"
export NPM_CONFIG_CACHE="$npm_config_cache"
export NPM_CONFIG_PREFIX="%{opencode_cache_dir}/npm-global"
export PATH="$NPM_CONFIG_PREFIX/bin:$PATH"
export XDG_CACHE_HOME="%{opencode_cache_dir}/xdg"
mkdir -p "$NPM_CONFIG_PREFIX" "$npm_config_cache" "$XDG_CACHE_HOME"

export ELECTRON_MIRROR="%{electron_mirror}"
export ELECTRON_BUILDER_BINARIES_MIRROR="%{electron_builder_binaries_mirror}"
export ELECTRON_CACHE="%{opencode_cache_dir}/electron"
export ELECTRON_BUILDER_CACHE="%{opencode_cache_dir}/electron-builder"
mkdir -p "$ELECTRON_CACHE" "$ELECTRON_BUILDER_CACHE"

npm config set registry "$npm_config_registry"
npm config set cache "$npm_config_cache"
npm config set prefix "$NPM_CONFIG_PREFIX"

bun_version="$(node -p 'const manager = require("./package.json").packageManager || ""; if (!manager.startsWith("bun@")) { throw new Error("packageManager must be bun@<version>"); } manager.slice(4)')"
echo "Using bun version ${bun_version} from package.json"

if command -v bun >/dev/null 2>&1 && [ "$(bun --version)" = "$bun_version" ]; then
  echo "Reusing cached bun $(bun --version)"
else
  npm install -g "bun@${bun_version}"
fi

if command -v node-gyp >/dev/null 2>&1; then
  echo "Reusing cached node-gyp $(node-gyp --version)"
else
  npm install -g node-gyp
fi

bun --version
node-gyp --version

export BUN_INSTALL_CACHE_DIR="%{opencode_cache_dir}/bun/install/cache"
export BUN_RUNTIME_TRANSPILER_CACHE_PATH="%{opencode_cache_dir}/bun/runtime-cache"
export BUN_CONFIG_DISABLE_ANALYTICS=1
export MODELS_DEV_API_JSON="%{SOURCE1}"
export OPENCODE_VERSION="%{version}"
export OPENCODE_CHANNEL="prod"
export USE_HARD_LINKS=false
mkdir -p "$BUN_INSTALL_CACHE_DIR" "$(dirname "$BUN_RUNTIME_TRANSPILER_CACHE_PATH")"

attempt=1
until bun install --frozen-lockfile; do
  if [ "$attempt" -ge 3 ]; then
    echo "bun install failed after ${attempt} attempts" >&2
    exit 1
  fi

  echo "bun install failed, retrying ($attempt/3)" >&2
  attempt=$((attempt + 1))
  sleep 5
done

pushd packages/opencode
bun run script/build.ts --single --skip-install
popd

cp -f "packages/opencode/dist/%{opencode_build_target}/bin/opencode" "packages/desktop-electron/resources/opencode-cli"
pushd packages/desktop-electron
bun run build
bun x electron-builder --linux --config electron-builder.config.ts --publish never
popd

%install
cd %{name}-%{version}

install -d "%{buildroot}%{_bindir}"
install -Dm755 "packages/opencode/dist/%{opencode_build_target}/bin/opencode" "%{buildroot}%{_bindir}/opencode"
install -d "%{buildroot}%{_licensedir}/%{upstream_name}"
install -Dm644 LICENSE "%{buildroot}%{_licensedir}/%{upstream_name}/LICENSE"
install -d "%{buildroot}%{_licensedir}/%{upstream_name}-desktop"
install -Dm644 LICENSE "%{buildroot}%{_licensedir}/%{upstream_name}-desktop/LICENSE"
install -d "%{buildroot}%{_licensedir}/%{name}-base"
install -Dm644 "%{base_source_dir}/LICENSE" "%{buildroot}%{_licensedir}/%{name}-base/LICENSE"
install -d "%{buildroot}%{_docdir}/%{upstream_name}"
install -Dm644 README.md "%{buildroot}%{_docdir}/%{upstream_name}/README.md"
install -d "%{buildroot}%{_docdir}/%{name}-base"
install -Dm644 "%{base_source_dir}/docs/witty-opencode-base.md" "%{buildroot}%{_docdir}/%{name}-base/witty-opencode-base.md"
install -Dm644 "%{base_source_dir}/README.md" "%{buildroot}%{_docdir}/%{name}-base/base-source-layout.md"

install -d "%{buildroot}%{witty_managed_libexec}"
install -Dm755 "%{base_source_dir}/bin/rebuild-managed-config.mjs" "%{buildroot}%{witty_managed_libexec}/rebuild-managed-config.mjs"
install -Dm755 "%{base_source_dir}/bin/run-managed-config-hook.sh" "%{buildroot}%{witty_managed_libexec}/run-managed-config-hook.sh"

install -d "%{buildroot}%{_sysconfdir}/opencode"
install -d "%{buildroot}%{witty_managed_config_dropins}"
install -d "%{buildroot}%{witty_managed_agents}"
install -d "%{buildroot}%{witty_managed_skills}"
install -d "%{buildroot}%{witty_managed_plugins}/logo"
install -Dm644 "%{base_source_dir}/plugins/logo/witty-logo.tsx" "%{buildroot}%{witty_managed_logo}"

desktop_extract_dir="%{_builddir}/desktop-electron-extract"
desktop_rpm="packages/desktop-electron/dist/opencode-electron-linux-%{electron_rpm_arch}.rpm"

rm -rf "$desktop_extract_dir"
mkdir -p "$desktop_extract_dir"
pushd "$desktop_extract_dir"
rpm2cpio "%{_builddir}/%{name}-%{version}/${desktop_rpm}" | cpio -idm --quiet
popd

cp -a "$desktop_extract_dir/opt" "%{buildroot}/"
install -d "%{buildroot}%{_datadir}"
cp -a "$desktop_extract_dir/usr/share/." "%{buildroot}%{_datadir}/"

ln -s "../../opt/OpenCode/@opencode-aidesktop-electron" "%{buildroot}%{_bindir}/@opencode-aidesktop-electron"
ln -s "../../opt/OpenCode/@opencode-aidesktop-electron" "%{buildroot}%{_bindir}/opencode-desktop"

%check
cd %{name}-%{version}

./packages/opencode/dist/%{opencode_build_target}/bin/opencode --version | grep -F "%{version}"
test -x ./packages/desktop-electron/dist/linux-unpacked/@opencode-aidesktop-electron || \
test -x ./packages/desktop-electron/dist/linux-%{electron_builder_arch}-unpacked/@opencode-aidesktop-electron
test -f ./packages/desktop-electron/dist/opencode-electron-linux-%{electron_rpm_arch}.rpm

test -x "%{buildroot}%{witty_managed_libexec}/rebuild-managed-config.mjs"
test -x "%{buildroot}%{witty_managed_libexec}/run-managed-config-hook.sh"
test -f "%{buildroot}%{witty_managed_logo}"

%posttrans -n %{name}-base
%{witty_managed_libexec}/run-managed-config-hook.sh posttrans

%transfiletriggerin -n %{name}-base -- %{witty_managed_config_dropins} %{witty_managed_agents} %{witty_managed_skills}
%{witty_managed_libexec}/run-managed-config-hook.sh transfiletriggerin

%transfiletriggerpostun -n %{name}-base -- %{witty_managed_config_dropins} %{witty_managed_agents} %{witty_managed_skills}
%{witty_managed_libexec}/run-managed-config-hook.sh transfiletriggerpostun

%post -n %{upstream_name}-desktop
if command -v unshare >/dev/null 2>&1 && [[ -L /proc/self/ns/user ]] && unshare --user true >/dev/null 2>&1; then
  chmod 0755 /opt/OpenCode/chrome-sandbox || :
else
  chmod 4755 /opt/OpenCode/chrome-sandbox || :
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database %{_datadir}/applications >/dev/null 2>&1 || :
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q %{_datadir}/icons/hicolor >/dev/null 2>&1 || :
fi

%postun -n %{upstream_name}-desktop
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database %{_datadir}/applications >/dev/null 2>&1 || :
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q %{_datadir}/icons/hicolor >/dev/null 2>&1 || :
fi

%files -n %{upstream_name}
%license %{_licensedir}/%{upstream_name}/LICENSE
%doc %{_docdir}/%{upstream_name}/README.md
%{_bindir}/opencode

%files -n %{upstream_name}-desktop
%license %{_licensedir}/%{upstream_name}-desktop/LICENSE
%{_bindir}/@opencode-aidesktop-electron
%{_bindir}/opencode-desktop
/opt/OpenCode
%{_datadir}/applications/@opencode-aidesktop-electron.desktop
%{_datadir}/icons/hicolor/*/apps/@opencode-aidesktop-electron.png

%files base
%license %{_licensedir}/%{name}-base/LICENSE
%doc %{_docdir}/%{name}-base/witty-opencode-base.md
%doc %{_docdir}/%{name}-base/base-source-layout.md
%dir %{_sysconfdir}/opencode
%ghost %config(noreplace) %{_sysconfdir}/opencode/opencode.json
%ghost %config(noreplace) %{_sysconfdir}/opencode/tui.json
%{witty_managed_libexec}/rebuild-managed-config.mjs
%{witty_managed_libexec}/run-managed-config-hook.sh
%dir %{witty_managed_root}
%dir %{witty_managed_config_dropins}
%dir %{witty_managed_agents}
%dir %{witty_managed_skills}
%dir %{witty_managed_plugins}
%dir %{witty_managed_plugins}/logo
%{witty_managed_logo}

%changelog
* Wed Apr 08 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.3.17-2
- Split per-subpackage license metadata and ship the base package license text

* Tue Apr 07 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.3.17-1
- Sync to upstream v1.3.17 release

* Thu Apr 02 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.3.13-1
- Sync to upstream v1.3.13 release

* Mon Mar 30 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.3.7-1
- Sync to upstream v1.3.7 release

* Wed Mar 25 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.3.2-1
- Sync to upstream v1.3.2 release

* Wed Mar 18 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.2.27-1
- Initial openEuler RPM packaging for OpenCode CLI
