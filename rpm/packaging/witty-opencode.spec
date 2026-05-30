%global source_dir %{_builddir}/%{name}-base-%{version}
%global witty_managed_root %{_datadir}/witty/opencode
%global witty_managed_config_dropins %{witty_managed_root}/config.d
%global witty_managed_agents %{witty_managed_root}/agents
%global witty_managed_skills %{witty_managed_root}/skills
%global witty_managed_plugins %{witty_managed_root}/plugins
%global witty_managed_logo %{witty_managed_plugins}/logo/witty-logo.tsx
%global witty_managed_libexec %{_libexecdir}/witty-opencode

Name:           witty-opencode
Version:        1.15.12
Release:        1%{?dist}
Summary:        Source package for witty-opencode-base managed-config assets

License:        MulanPSL-2.0
URL:            https://github.com/anomalyco/opencode
Source0:        %{name}-base-%{version}.tar.gz

%package base
Summary:        Managed configuration and RPM integration assets for witty-opencode
License:        MulanPSL-2.0
BuildArch:      noarch
Requires:       opencode
Requires:       nodejs >= 20

%description
This source package builds the `witty-opencode-base` managed-config RPM for
openEuler.

%description base
This package ships the managed-config assets for witty-opencode on openEuler.
It owns the shared logo plugin, managed resource directories, the config
generator, and the RPM transaction hooks that rebuild `/etc/opencode/opencode.json`
and `/etc/opencode/tui.json` from installed config fragments and resource bundles.

%prep
rm -rf %{source_dir}
mkdir -p %{source_dir}
tar -xzf %{SOURCE0} --strip-components=1 -C %{source_dir}

%install
cd %{source_dir}

install -d "%{buildroot}%{_licensedir}/%{name}-base"
install -Dm644 LICENSE "%{buildroot}%{_licensedir}/%{name}-base/LICENSE"
install -d "%{buildroot}%{_docdir}/%{name}-base"
install -Dm644 "%{source_dir}/docs/witty-opencode-base.md" "%{buildroot}%{_docdir}/%{name}-base/witty-opencode-base.md"
install -Dm644 "%{source_dir}/README.md" "%{buildroot}%{_docdir}/%{name}-base/base-source-layout.md"

install -d "%{buildroot}%{witty_managed_libexec}"
install -Dm755 "%{source_dir}/bin/rebuild-managed-config.mjs" "%{buildroot}%{witty_managed_libexec}/rebuild-managed-config.mjs"
install -Dm755 "%{source_dir}/bin/run-managed-config-hook.sh" "%{buildroot}%{witty_managed_libexec}/run-managed-config-hook.sh"

install -d "%{buildroot}%{_sysconfdir}/opencode"
install -d "%{buildroot}%{witty_managed_config_dropins}"
install -d "%{buildroot}%{witty_managed_agents}"
install -d "%{buildroot}%{witty_managed_skills}"
install -d "%{buildroot}%{witty_managed_plugins}/logo"
install -Dm644 "%{source_dir}/plugins/logo/witty-logo.tsx" "%{buildroot}%{witty_managed_logo}"

%check
test -f "%{buildroot}%{_licensedir}/%{name}-base/LICENSE"
test -f "%{buildroot}%{_docdir}/%{name}-base/witty-opencode-base.md"
test -f "%{buildroot}%{_docdir}/%{name}-base/base-source-layout.md"
test -x "%{buildroot}%{witty_managed_libexec}/rebuild-managed-config.mjs"
test -x "%{buildroot}%{witty_managed_libexec}/run-managed-config-hook.sh"
test -f "%{buildroot}%{witty_managed_logo}"

%posttrans -n %{name}-base
%{witty_managed_libexec}/run-managed-config-hook.sh posttrans

%transfiletriggerin -n %{name}-base -- %{witty_managed_config_dropins} %{witty_managed_agents} %{witty_managed_skills}
%{witty_managed_libexec}/run-managed-config-hook.sh transfiletriggerin

%transfiletriggerpostun -n %{name}-base -- %{witty_managed_config_dropins} %{witty_managed_agents} %{witty_managed_skills}
%{witty_managed_libexec}/run-managed-config-hook.sh transfiletriggerpostun

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
* Fri May 29 2026 SIG-Intelligence <intelligence@openeuler.org> - 1.15.12-1
- Sync to upstream v1.15.12 release

* Fri May 29 2026 hongyu-shi <shywzt@iCloud.com> - 1.15.10-2
- Keep witty-opencode.spec focused on witty-opencode-base only

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
