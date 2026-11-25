#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Install systemE's .debs over a stock Ubuntu system the way a user would, with
# apt, and boot the result. Answers the two questions packaging has to: does
# apt accept the swap, and does the machine come back up afterwards.
#
#   packaging/test-deb.sh [--suite noble] [--rootfs DIR] [--keep]
#
# Needs root, debootstrap, qemu-system-x86, a kernel in /boot with virtio-blk
# and ext4 built in, and packages already built in packaging/out/.

set -euo pipefail
cd "$(dirname "$0")/.."

SUITE=noble
MIRROR=http://archive.ubuntu.com/ubuntu
ROOTFS=
KEEP=0
while [ $# -gt 0 ]; do
        case "$1" in
        --suite) SUITE="$2"; shift 2 ;;
        --rootfs) ROOTFS="$2"; shift 2 ;;
        --keep) KEEP=1; shift ;;
        *) echo "test-deb.sh: unknown option $1" >&2; exit 1 ;;
        esac
done

# packaging/out/ keeps every build; test the most recently built one.
newest=$(ls -1t packaging/out/systeme_*.deb 2>/dev/null | head -1)
[ -n "$newest" ] || { echo "test-deb.sh: build the packages first (packaging/build-deb.sh)" >&2; exit 1; }
ver=$(dpkg-deb -f "$newest" Version)
debs=(packaging/out/systeme_"$ver"_*.deb packaging/out/libsysteme0_"$ver"_*.deb)
echo "==> testing version $ver"
KERNEL=$(ls -1 /boot/vmlinuz-* | tail -1)

WORK=$(mktemp -d)
cleanup() {
        for m in dev/pts dev proc sys; do umount "$R/$m" 2>/dev/null || true; done
        [ "$KEEP" -eq 1 ] || rm -rf "$WORK"
}
trap cleanup EXIT
R="${ROOTFS:-$WORK/rootfs}"

if [ ! -x "$R/usr/bin/apt-get" ]; then
        echo "==> debootstrap $SUITE with the distribution's own systemd"
        debootstrap --variant=minbase \
                --include=systemd,systemd-sysv,udev,dbus,systemd-resolved,systemd-timesyncd,libpam-systemd,libnss-systemd,login,passwd,iproute2 \
                "$SUITE" "$R" "$MIRROR" >"$WORK/debootstrap.log" 2>&1
fi

echo "==> before"
chroot "$R" dpkg-query -W -f '    ${Package} ${Version}\n' systemd udev libsystemd0 systemd-resolved 2>/dev/null || true

mount -t proc proc "$R/proc"; mount -t sysfs sys "$R/sys"
mount --bind /dev "$R/dev"; mount --bind /dev/pts "$R/dev/pts"
# Do not start services inside the chroot.
printf '#!/bin/sh\nexit 101\n' > "$R/usr/sbin/policy-rc.d"; chmod +x "$R/usr/sbin/policy-rc.d"

mkdir -p "$R/tmp/systeme"; cp "${debs[@]}" "$R/tmp/systeme/"
echo "==> apt install ./systeme*.deb"
# The glob has to expand inside the chroot: expanded by this shell it matches
# nothing on the host and apt is handed the literal pattern.
set +e
chroot "$R" sh -c 'DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends /tmp/systeme/*.deb' \
        >"$WORK/apt.log" 2>&1
rc=$?
set -e
grep -E "^(The following|  [a-z]|Removing|Unpacking systeme|Setting up (systeme|libsysteme))" "$WORK/apt.log" || true
rm -f "$R/usr/sbin/policy-rc.d"
for m in dev/pts dev proc sys; do umount "$R/$m"; done
if [ "$rc" -ne 0 ]; then
        echo "apt failed (exit $rc):" >&2; tail -20 "$WORK/apt.log" >&2; KEEP=1; exit 1
fi

echo "==> after"
chroot "$R" dpkg-query -W -f '    ${Package} ${Version} ${db:Status-Abbrev}\n' systeme libsysteme0 systemd udev libsystemd0 systemd-resolved 2>/dev/null | sed 's/ *$//' || true
status() { chroot "$R" dpkg-query -W -f '${db:Status-Abbrev}' "$1" 2>/dev/null | tr -d ' '; }
for p in systeme libsysteme0; do
        [ "$(status $p)" = ii ] || { echo "test-deb.sh: $p is not installed after apt" >&2; KEEP=1; exit 1; }
done
for p in systemd udev libsystemd0 systemd-resolved; do
        case "$(status $p)" in ii|iU|iF) echo "test-deb.sh: $p is still installed; the swap did not happen" >&2; KEEP=1; exit 1 ;; esac
done

# A unit that reports state and powers off, so the boot ends on its own.
mkdir -p "$R/usr/local/sbin"
cat > "$R/usr/local/sbin/systeme-verdict" <<'VERDICT'
#!/bin/sh
echo "PKG-TEST-PACKAGE: $(dpkg-query -W -f '${Package} ${Version}' systeme)"
echo "PKG-TEST-MANAGER: $(systemctl --version | head -1)"
echo "PKG-TEST-MULTIUSER: $(systemctl is-active multi-user.target)"
echo "PKG-TEST-STATE: $(systemctl is-system-running)"
systemctl --no-pager --no-legend --failed
echo PKG-TEST-END
VERDICT
chmod +x "$R/usr/local/sbin/systeme-verdict"
cat > "$R/etc/systemd/system/boot-verdict.service" <<'UNIT'
[Unit]
Description=systemE packaging boot verdict
After=multi-user.target
[Service]
Type=oneshot
StandardOutput=journal+console
ExecStart=/usr/local/sbin/systeme-verdict
ExecStopPost=/bin/sh -c 'systemctl poweroff || systemctl --force poweroff'
[Install]
WantedBy=multi-user.target
UNIT
ln -sf ../boot-verdict.service "$R/etc/systemd/system/multi-user.target.wants/boot-verdict.service"

echo "==> building a disk image"
truncate -s 3G "$WORK/disk.img"
mkfs.ext4 -q -F -d "$R" "$WORK/disk.img"

echo "==> booting it"
timeout 600 qemu-system-x86_64 -m 1536 -smp 2 -nographic -no-reboot \
        -kernel "$KERNEL" \
        -drive file="$WORK/disk.img",format=raw,if=virtio \
        -append "root=/dev/vda rw console=ttyS0 systemd.firstboot=no systemd.show_status=yes" \
        > "$WORK/boot.log" 2>&1 || true
sed -e 's/\x1b\[[0-9;:]*[a-zA-Z]//g' -e 's/\x1b\][^\x07]*\x07//g' "$WORK/boot.log" > "$WORK/boot.txt"

echo
sed -n '/PKG-TEST-PACKAGE/,/PKG-TEST-END/p' "$WORK/boot.txt" | sed 's/^ *//;s/^\[ *[0-9.]*\] *//;s/^[a-z]*\[[0-9]*\]: //;s/^/  /'
[ "$KEEP" -eq 1 ] && echo "  console log: $WORK/boot.txt"
# The verdict asks systemctl whether multi-user.target is active: status lines
# show unit descriptions, not names, so grepping for "multi-user.target" fails.
# Only systemE prints [$..] markers, and the verdict must name the systeme
# package, so a boot of the distribution's own systemd cannot pass. Both start
# ([$▶]) and done ([$▮]) markers are required: a done marker that never shows
# up means the job-result path is broken even if the boot gets there.
reached=0; grep -q "PKG-TEST-MULTIUSER: active" "$WORK/boot.txt" && reached=1
starting=$(grep -c '\[\$▶\]' "$WORK/boot.txt" || true)
done_ok=$(grep -c '\[\$▮\]' "$WORK/boot.txt" || true)
named=0; grep -q "PKG-TEST-PACKAGE: systeme " "$WORK/boot.txt" && named=1
echo "  multi-user active: $reached   [\$▶] lines: $starting   [\$▮] lines: $done_ok   verdict names systeme: $named"
if [ "$reached" = 1 ] && [ "$starting" -gt 0 ] && [ "$done_ok" -gt 0 ] && [ "$named" = 1 ]; then
        echo "systemE, installed by apt over $SUITE's systemd, reached multi-user.target."
        exit 0
fi
echo "FAILED: that was not a systemE boot reaching multi-user.target." >&2
KEEP=1; exit 1
