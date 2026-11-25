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

debs=(packaging/out/systeme_*.deb packaging/out/libsysteme0_*.deb)
[ -e "${debs[0]}" ] || { echo "test-deb.sh: build the packages first (packaging/build-deb.sh)" >&2; exit 1; }
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
chroot "$R" env DEBIAN_FRONTEND=noninteractive \
        apt-get install -y --no-install-recommends /tmp/systeme/*.deb 2>&1 | tee "$WORK/apt.log" | \
        grep -E "^(The following|  [a-z]|Removing|Unpacking systeme|Setting up (systeme|libsysteme))" || true
rc=${PIPESTATUS[0]}
rm -f "$R/usr/sbin/policy-rc.d"
for m in dev/pts dev proc sys; do umount "$R/$m"; done
[ "$rc" -eq 0 ] || { echo "apt failed; see $WORK/apt.log" >&2; KEEP=1; exit 1; }

echo "==> after"
chroot "$R" dpkg-query -W -f '    ${Package} ${Version} ${db:Status-Abbrev}\n' systeme libsysteme0 systemd udev libsystemd0 systemd-resolved 2>/dev/null | sed 's/ *$//' || true

# A unit that reports state and powers off, so the boot ends on its own.
cat > "$R/etc/systemd/system/boot-verdict.service" <<'UNIT'
[Unit]
Description=systemE packaging boot verdict
After=multi-user.target
[Service]
Type=oneshot
StandardOutput=journal+console
ExecStart=/bin/sh -c 'echo "PKG-TEST-PACKAGE: $(dpkg-query -W -f "\${Package} \${Version}" systeme)"; echo "PKG-TEST-STATE: $(systemctl is-system-running)"; systemctl --no-pager --no-legend --failed; echo PKG-TEST-END'
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
if grep -q "Reached target .*multi-user.target" "$WORK/boot.txt"; then
        echo "systemE, installed by apt over $SUITE's systemd, reached multi-user.target."
        exit 0
fi
echo "It did NOT reach multi-user.target." >&2
KEEP=1; exit 1
