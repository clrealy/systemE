# SPDX-License-Identifier: LGPL-2.1-or-later
#
# systemE for Fedora. Build with packaging/build-rpm.sh, which sets %{ver} from
# meson.version and the commit.

%{!?ver: %global ver 263~devel}

Name:           systeme
Version:        %{ver}
Release:        1%{?dist}
Summary:        systemE system and service manager, a fork of systemd
License:        LGPL-2.1-or-later AND GPL-2.0-or-later AND MIT-0
URL:            https://github.com/clrealy/systemE
Source0:        systeme-%{version}.tar.gz

BuildRequires:  gcc
BuildRequires:  meson >= 0.62
BuildRequires:  gperf
BuildRequires:  python3-jinja2
BuildRequires:  python3-pyelftools
BuildRequires:  libxslt
BuildRequires:  docbook-style-xsl
BuildRequires:  pkgconfig(libcap)
BuildRequires:  pkgconfig(mount)
BuildRequires:  pkgconfig(blkid)
BuildRequires:  pkgconfig(fdisk)
BuildRequires:  pkgconfig(libacl)
BuildRequires:  pkgconfig(audit)
BuildRequires:  pam-devel
BuildRequires:  pkgconfig(libseccomp)
BuildRequires:  pkgconfig(libselinux)
BuildRequires:  pkgconfig(libcryptsetup)
BuildRequires:  pkgconfig(openssl)
BuildRequires:  pkgconfig(libkmod)
BuildRequires:  pkgconfig(libidn2)
BuildRequires:  pkgconfig(libpcre2-8)
BuildRequires:  pkgconfig(libzstd)
BuildRequires:  pkgconfig(liblz4)
BuildRequires:  pkgconfig(liblzma)
BuildRequires:  bzip2-devel
BuildRequires:  elfutils-devel
BuildRequires:  pkgconfig(tss2-esys)
BuildRequires:  pkgconfig(libfido2)
BuildRequires:  pkgconfig(p11-kit-1)
BuildRequires:  pkgconfig(pwquality)
BuildRequires:  pkgconfig(libqrencode)
BuildRequires:  pkgconfig(libarchive)
BuildRequires:  pkgconfig(libcurl)
BuildRequires:  pkgconfig(xkbcommon)
BuildRequires:  pkgconfig(dbus-1)

Requires:       %{name}-libs%{?_isa} = %{version}-%{release}
Requires:       dbus
Recommends:     NetworkManager

# dnf protects systemd and refuses to remove it, but it lets a protected package
# be obsoleted. That is how systemE takes over. The bound keeps a later Fedora
# systemd free to replace systemE in turn.
Provides:       systemd = %{version}-%{release}
Provides:       systemd%{?_isa} = %{version}-%{release}
Provides:       systemd-udev = %{version}-%{release}
Provides:       systemd-pam = %{version}-%{release}
Provides:       systemd-oomd-defaults = %{version}-%{release}
Provides:       systemd-boot-unsigned = %{version}-%{release}
Provides:       systemd-ukify = %{version}-%{release}
Provides:       systemd-sysusers
Provides:       systemd-tmpfiles
Obsoletes:      systemd < %{version}-%{release}
Obsoletes:      systemd-udev < %{version}-%{release}
Obsoletes:      systemd-pam < %{version}-%{release}
Obsoletes:      systemd-oomd-defaults < %{version}-%{release}
Obsoletes:      systemd-boot-unsigned < %{version}-%{release}
Obsoletes:      systemd-ukify < %{version}-%{release}
# Components systemE removed. Obsoleted without being provided, so dnf removes
# them rather than leaving binaries linked against the old private library.
Obsoletes:      systemd-networkd < %{version}-%{release}
Obsoletes:      systemd-resolved < %{version}-%{release}
Obsoletes:      systemd-container < %{version}-%{release}
Obsoletes:      systemd-journal-remote < %{version}-%{release}
Obsoletes:      systemd-homed < %{version}-%{release}
Obsoletes:      systemd-repart < %{version}-%{release}
Obsoletes:      systemd-standalone-sysusers < %{version}-%{release}
Obsoletes:      systemd-standalone-tmpfiles < %{version}-%{release}

%description
systemE is a fork of systemd with a reduced set of components and every
external interface kept identical. It does not ship systemd-networkd or
systemd-resolved: set up NetworkManager and a resolver before switching.

%package libs
Summary:        systemE client libraries (libsystemd, libudev)
Provides:       systemd-libs = %{version}-%{release}
Provides:       systemd-libs%{?_isa} = %{version}-%{release}
Obsoletes:      systemd-libs < %{version}-%{release}

%description libs
libsystemd and libudev as built by systemE, with upstream's ABI unchanged.

%package devel
Summary:        systemE development files
Requires:       %{name}-libs%{?_isa} = %{version}-%{release}
Provides:       systemd-devel = %{version}-%{release}
Provides:       systemd-devel%{?_isa} = %{version}-%{release}
Obsoletes:      systemd-devel < %{version}-%{release}

%description devel
Headers and pkg-config files for libsystemd and libudev.

%package rpm-macros
Summary:        RPM macros for packages that ship systemd units
BuildArch:      noarch
Provides:       systemd-rpm-macros = %{version}-%{release}
Obsoletes:      systemd-rpm-macros < %{version}-%{release}

%description rpm-macros
The %%systemd_post family of macros, which other packages' spec files use.

%prep
%autosetup -n systeme-%{version}

%build
%meson \
        -Dmode=release \
        -Dbootloader=enabled \
        -Dman=enabled \
        -Dhtml=disabled \
        -Drust=disabled \
        -Dbpf-framework=disabled \
        -Dxenctrl=disabled \
        -Dinstall-tests=false
%meson_build

%install
%meson_install
# Keep systemE itself protected the way systemd was.
mkdir -p %{buildroot}%{_sysconfdir}/dnf/protected.d
echo systeme > %{buildroot}%{_sysconfdir}/dnf/protected.d/systeme.conf

%check
%meson_test

%post
systemd-sysusers || :
systemd-hwdb update || :
journalctl --update-catalog || :
if [ $1 -eq 1 ]; then
        systemd-machine-id-setup || :
        systemctl preset-all --preset-mode=enable-only || :
fi
systemctl daemon-reexec 2>/dev/null || :

%files
%license LICENSES/*
%{_sysconfdir}/dnf/protected.d/systeme.conf
%config(noreplace) %{_sysconfdir}/systemd/*.conf
%config(noreplace) %{_sysconfdir}/udev/*.conf
%{_sysconfdir}/*
%exclude %{_sysconfdir}/systemd/*.conf
%exclude %{_sysconfdir}/udev/*.conf
%exclude %{_sysconfdir}/dnf/protected.d/systeme.conf
%{_bindir}/*
%{_sbindir}/*
%{_prefix}/lib/binfmt.d
%{_prefix}/lib/credstore
%{_prefix}/lib/environment.d
%{_prefix}/lib/kernel
%{_prefix}/lib/machine-tags.d
%{_prefix}/lib/modprobe.d
%{_prefix}/lib/modules-load.d
%{_prefix}/lib/nvpcr
%{_prefix}/lib/pam.d
%{_prefix}/lib/pcrlock.d
%{_prefix}/lib/sysctl.d
%{_prefix}/lib/systemd
%{_prefix}/lib/sysusers.d
%{_prefix}/lib/tmpfiles.d
%{_prefix}/lib/udev
%{_libdir}/cryptsetup
%{_libdir}/libnss_myhostname.so.2
%{_libdir}/libnss_systemd.so.2
%{_libdir}/security/*
%{_libdir}/systemd
%{_datadir}/bash-completion
%{_datadir}/dbus-1
%{_datadir}/factory
%{_datadir}/mime
%{_datadir}/polkit-1
%{_datadir}/systemd
%{_datadir}/user-tmpfiles.d
%{_datadir}/zsh
%{_mandir}/man*/*
%doc %{_docdir}/systemd
%dir /var/log/journal

%files libs
%{_libdir}/libsystemd.so.0*
%{_libdir}/libudev.so.1*

%files devel
%{_includedir}/systemd
%{_includedir}/libudev.h
%{_libdir}/libsystemd.so
%{_libdir}/libudev.so
%{_libdir}/pkgconfig/libsystemd.pc
%{_libdir}/pkgconfig/libudev.pc
%{_datadir}/pkgconfig/systemd.pc
%{_datadir}/pkgconfig/udev.pc

%files rpm-macros
%{_rpmmacrodir}/macros.systemd

%changelog
* Wed Nov 25 2026 systemE developers <packaging@systeme.invalid> - 263~devel-1
- Snapshot build from the systemE repository.
