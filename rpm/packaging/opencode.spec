%global debug_package %{nil}
%global __strip /bin/true
%global __provides_exclude_from ^/opt/OpenCode/.*$
%global __requires_exclude_from ^/opt/OpenCode/.*$
%global electron_mirror https://mirrors.huaweicloud.com/electron/
%global electron_builder_binaries_mirror https://mirrors.huaweicloud.com/electron-builder-binaries/
%global source_archive v%{version}.tar.gz
%{!?opencode_cache_dir:%global opencode_cache_dir %{_builddir}/%{name}-%{version}/.cache/opencode-rpm}

Name:           opencode
Version:        1.15.12
Release:        1%{?dist}
Summary:        AI coding agent built for the terminal

License:        MIT
URL:            https://github.com/anomalyco/opencode
Source0:        https://github.com/anomalyco/%{name}/archive/refs/tags/%{source_archive}
# Build-time models.dev snapshot consumed by packages/opencode/script/build.ts.
Source1:        opencode-models-api.json

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
Requires:       git

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

%package desktop
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

%description
OpenCode is an open source AI coding agent for the terminal. This package builds
the upstream CLI from the tagged source tree and installs the native OpenCode
binary as `/usr/bin/opencode` for openEuler.

%description desktop
This subpackage builds and ships the OpenCode desktop application for openEuler.
It uses the upstream Electron desktop shell and bundles the matching `opencode`
CLI as a sidecar, so it does not require the system opencode package at runtime.

%prep
rm -rf %{name}-%{version}
mkdir -p %{name}-%{version}
tar -xzf %{_sourcedir}/%{source_archive} --strip-components=1 -C %{name}-%{version}
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

cp -f "packages/opencode/dist/%{opencode_build_target}/bin/opencode" "packages/desktop/resources/opencode-cli"
pushd packages/desktop
bun run build
bun x electron-builder --linux --config electron-builder.config.ts --publish never
popd

%install
cd %{name}-%{version}

install -d "%{buildroot}%{_bindir}"
install -Dm755 "packages/opencode/dist/%{opencode_build_target}/bin/opencode" "%{buildroot}%{_bindir}/opencode"
install -d "%{buildroot}%{_licensedir}/%{name}"
install -Dm644 LICENSE "%{buildroot}%{_licensedir}/%{name}/LICENSE"
install -d "%{buildroot}%{_licensedir}/%{name}-desktop"
install -Dm644 LICENSE "%{buildroot}%{_licensedir}/%{name}-desktop/LICENSE"
install -d "%{buildroot}%{_docdir}/%{name}"
install -Dm644 README.md "%{buildroot}%{_docdir}/%{name}/README.md"

desktop_extract_dir="%{_builddir}/desktop-extract"
desktop_rpm="packages/desktop/dist/opencode-desktop-linux-%{electron_rpm_arch}.rpm"

rm -rf "$desktop_extract_dir"
mkdir -p "$desktop_extract_dir"
pushd "$desktop_extract_dir"
rpm2cpio "%{_builddir}/%{name}-%{version}/${desktop_rpm}" | cpio -idm --quiet
popd

cp -a "$desktop_extract_dir/opt" "%{buildroot}/"
install -d "%{buildroot}%{_datadir}"
cp -a "$desktop_extract_dir/usr/share/." "%{buildroot}%{_datadir}/"

desktop_app_root="%{buildroot}/opt/OpenCode"
desktop_launcher_name=""
for candidate in opencode OpenCode @opencode-aidesktop-electron; do
  if [ -x "$desktop_app_root/$candidate" ]; then
    desktop_launcher_name="$candidate"
    break
  fi
done

if [ -z "$desktop_launcher_name" ]; then
  desktop_launcher_path="$(find "$desktop_app_root" -maxdepth 1 -type f -executable ! -name 'chrome-sandbox' ! -name 'chrome_crashpad_handler' ! -name '*.so*' | head -n 1)"
  if [ -n "$desktop_launcher_path" ]; then
    desktop_launcher_name="$(basename "$desktop_launcher_path")"
  fi
fi

if [ -z "$desktop_launcher_name" ]; then
  echo "Could not determine desktop launcher under $desktop_app_root" >&2
  find "$desktop_app_root" -maxdepth 1 -type f >&2 || :
  exit 1
fi

ln -s "../../opt/OpenCode/${desktop_launcher_name}" "%{buildroot}%{_bindir}/@opencode-aidesktop-electron"
ln -s "../../opt/OpenCode/${desktop_launcher_name}" "%{buildroot}%{_bindir}/opencode-desktop"

%check
cd %{name}-%{version}

./packages/opencode/dist/%{opencode_build_target}/bin/opencode --version | grep -F "%{version}"
desktop_unpack_dir=""
for candidate in ./packages/desktop/dist/linux-unpacked ./packages/desktop/dist/linux-%{electron_builder_arch}-unpacked; do
  if [ -d "$candidate" ]; then
    desktop_unpack_dir="$candidate"
    break
  fi
done
test -n "$desktop_unpack_dir"

desktop_launcher_path=""
for candidate in opencode OpenCode @opencode-aidesktop-electron; do
  if [ -x "$desktop_unpack_dir/$candidate" ]; then
    desktop_launcher_path="$desktop_unpack_dir/$candidate"
    break
  fi
done

if [ -z "$desktop_launcher_path" ]; then
  desktop_launcher_path="$(find "$desktop_unpack_dir" -maxdepth 1 -type f -executable ! -name 'chrome-sandbox' ! -name 'chrome_crashpad_handler' ! -name '*.so*' | head -n 1)"
fi

test -n "$desktop_launcher_path"
test -x "$desktop_launcher_path"
test -f ./packages/desktop/dist/opencode-desktop-linux-%{electron_rpm_arch}.rpm

%post -n %{name}-desktop
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

%postun -n %{name}-desktop
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database %{_datadir}/applications >/dev/null 2>&1 || :
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q %{_datadir}/icons/hicolor >/dev/null 2>&1 || :
fi

%files
%license %{_licensedir}/%{name}/LICENSE
%doc %{_docdir}/%{name}/README.md
%{_bindir}/opencode

%files desktop
%license %{_licensedir}/%{name}-desktop/LICENSE
%{_bindir}/@opencode-aidesktop-electron
%{_bindir}/opencode-desktop
/opt/OpenCode
%{_datadir}/applications/*.desktop
%{_datadir}/icons/hicolor/*/apps/*

%changelog
* Fri May 29 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.15.12-1
- Sync to upstream v1.15.12 release

* Fri May 29 2026 hongyu-shi <shywzt@iCloud.com> - 1.15.10-2
- Split opencode and opencode-desktop into a standalone spec

* Wed May 27 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.15.10-1
- Sync to upstream v1.15.10 release

* Wed May 20 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.15.5-1
- Sync to upstream v1.15.5 release

* Wed May 13 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.14.48-1
- Sync to upstream v1.14.48 release

* Thu May 07 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.14.40-1
- Sync to upstream v1.14.40 release

* Mon Apr 20 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.14.18-1
- Sync to upstream v1.14.18 release

* Wed Apr 08 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.4.0-1
- Sync to upstream v1.4.0 release

* Wed Apr 08 2026 hongyu-shi <shywzt@iCloud.com> - 1.3.17-2
- Split per-subpackage license metadata and ship the base package license text

* Tue Apr 07 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.3.17-1
- Sync to upstream v1.3.17 release

* Thu Apr 02 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.3.13-1
- Sync to upstream v1.3.13 release

* Mon Mar 30 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.3.7-1
- Sync to upstream v1.3.7 release

* Wed Mar 25 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.3.2-1
- Sync to upstream v1.3.2 release

* Wed Mar 18 2026 hongyu-shi <shywzt@iCloud.com> - 1.2.27-1
- Add openEuler RPM packaging for OpenCode CLI & Desktop

* Wed Jan 21 2026 Wangkui <wangkui35@h-partners.com> - 1.1.28-1
- add opencode
