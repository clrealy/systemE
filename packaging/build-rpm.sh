#!/bin/sh
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Build systemE's RPMs from this checkout's committed HEAD.
#
#   packaging/build-rpm.sh [extra rpmbuild arguments]
#
# The packages land in packaging/out/. As with build-deb.sh, the version is
# meson.version plus the commit, using RPM's ^ so a snapshot sorts after the
# version it is built from and before the next.

set -eu
cd "$(dirname "$0")/.."

upstream=$(tr -d ' \n' < meson.version)
commit=$(git rev-parse --short=7 HEAD)
stamp=$(git log -1 --format=%cd --date=format:%Y%m%d)
count=$(git rev-list --count HEAD)
# The commit count keeps two snapshots from the same day in order; the hash alone
# would sort them arbitrarily.
version="${upstream}^git${stamp}.${count}.${commit}"

top=$(mktemp -d)
trap 'rm -rf "$top"' EXIT
mkdir -p "$top/SOURCES"
git archive --format=tar.gz --prefix="systeme-${version}/" \
        -o "$top/SOURCES/systeme-${version}.tar.gz" HEAD

echo "==> building systeme ${version}"
rpmbuild -bb --define "_topdir $top" --define "ver ${version}" "$@" \
        packaging/fedora/systeme.spec

mkdir -p packaging/out
find "$top/RPMS" -name '*.rpm' -exec mv {} packaging/out/ \;
ls -1 packaging/out/*.rpm
