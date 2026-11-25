#!/bin/sh
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Build systemE's Debian/Ubuntu packages from this checkout.
#
#   packaging/build-deb.sh            build, running the test suite
#   DEB_BUILD_OPTIONS=nocheck packaging/build-deb.sh
#
# The packages land in packaging/out/. The version comes from meson.version plus
# the commit, so a package can never claim a different version from its source.

set -eu
cd "$(dirname "$0")/.."

if [ -e debian ] && [ ! -f debian/.systeme-generated ]; then
        echo "build-deb.sh: ./debian exists and was not made by this script; refusing to touch it" >&2
        exit 1
fi

upstream=$(tr -d ' \n' < meson.version)
commit=$(git rev-parse --short=7 HEAD 2>/dev/null || echo unknown)
stamp=$(git log -1 --format=%cd --date=format:%Y%m%d 2>/dev/null || date +%Y%m%d)
version="${upstream}+git${stamp}.${commit}"

rm -rf debian
cp -r packaging/debian debian
: > debian/.systeme-generated
trap 'rm -rf debian' EXIT

cat > debian/changelog <<CHANGELOG
systeme (${version}) UNRELEASED; urgency=medium

  * Snapshot of ${commit}.

 -- systemE developers <packaging@systeme.invalid>  $(date -R)
CHANGELOG

echo "==> building systeme ${version}"
dpkg-buildpackage -b -us -uc

mkdir -p packaging/out
mv ../systeme_"${version}"_*.deb ../libsysteme0_"${version}"_*.deb \
   ../systeme-dev_"${version}"_*.deb ../systeme*_"${version}"_*.buildinfo \
   ../systeme*_"${version}"_*.changes packaging/out/ 2>/dev/null || true
# debug symbol packages, if dh produced them
mv ../systeme*-dbgsym_"${version}"_*.*deb ../libsysteme0-dbgsym_"${version}"_*.*deb packaging/out/ 2>/dev/null || true

echo
ls -1 packaging/out/*"${version}"*
