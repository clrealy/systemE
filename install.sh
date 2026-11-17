#!/bin/sh
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Build and install systemE.
#
# By default this stages the install into ./dest so you can look at what you are
# about to put on a machine. Installing over a running system replaces PID 1, the
# NSS and PAM modules and libsystemd, so it is deliberately not the default: pass
# --system for that, as root.
#
#   ./install.sh                     build and stage into ./dest
#   ./install.sh --dest DIR          stage somewhere else
#   doas ./install.sh --system       install over this machine
#   ./install.sh --help

set -eu

BUILD=build
DEST=dest
SYSTEM=0
ASSUME_YES=0
CONFIGURE_ARGS=""

usage() {
        sed -n '3,14p' "$0" | sed 's/^# \{0,1\}//'
        exit "${1:-0}"
}

while [ $# -gt 0 ]; do
        case "$1" in
        --build) BUILD="${2:?--build needs a directory}"; shift 2 ;;
        --dest) DEST="${2:?--dest needs a directory}"; shift 2 ;;
        --system) SYSTEM=1; shift ;;
        -y|--yes) ASSUME_YES=1; shift ;;
        -h|--help) usage 0 ;;
        --) shift; CONFIGURE_ARGS="$*"; break ;;
        *) printf 'install.sh: unknown option %s\n\n' "$1" >&2; usage 1 ;;
        esac
done

# Check this before building: finding out you needed root after a five minute
# build, by way of a traceback from meson, is no way to learn it.
if [ "$SYSTEM" -eq 1 ] && [ "$(id -u)" -ne 0 ]; then
        printf 'install.sh: --system needs root. Try: doas %s --system\n' "$0" >&2
        exit 1
fi

for tool in meson ninja; do
        command -v "$tool" >/dev/null 2>&1 || {
                printf 'install.sh: %s is required and was not found\n' "$tool" >&2
                exit 1
        }
done

if [ ! -f "$BUILD/build.ninja" ]; then
        printf '==> configuring %s\n' "$BUILD"
        # shellcheck disable=SC2086
        meson setup "$BUILD" $CONFIGURE_ARGS
fi

printf '==> building\n'
ninja -C "$BUILD"

if [ "$SYSTEM" -eq 0 ]; then
        printf '==> staging into %s\n' "$DEST"
        rm -rf "$DEST"
        case "$DEST" in
        /*) destdir="$DEST" ;;
        *) destdir="$(pwd)/$DEST" ;;
        esac
        DESTDIR="$destdir" meson install -C "$BUILD" >/dev/null
        printf '\nStaged %s files in %s\n' \
                "$(find "$destdir" -type f | wc -l | tr -d ' ')" "$destdir"
        printf 'Nothing on this machine was changed. Re-run with --system, as root, to install.\n'
        exit 0
fi

# Replacing the init system of a running machine is not something to do by accident.
if [ -d /run/systemd/system ] && [ "$ASSUME_YES" -eq 0 ]; then
        printf '\n'
        printf 'This machine is running systemd right now (/run/systemd/system exists).\n'
        printf 'Installing will replace PID 1, libsystemd, and the NSS and PAM modules.\n'
        printf 'A systemE built without a feature your system depends on can leave it\n'
        printf 'unable to boot or unable to resolve users. Have a rescue medium ready.\n\n'
        printf 'Type "yes" to continue: '
        read -r reply
        [ "$reply" = "yes" ] || { printf 'Aborted.\n'; exit 1; }
fi

printf '==> installing over this machine\n'
meson install -C "$BUILD"
printf '\nInstalled. Reboot to run the new PID 1, or "systemctl daemon-reexec" to\n'
printf 'reload it in place.\n'
