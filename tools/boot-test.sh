#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Boot systemE as PID 1 in a virtual machine and report whether it reached its
# default target. Unit tests say the code is correct; this says it boots, which
# is a different question and the only one that matters for an init system.
#
# No KVM is required: qemu emulates in software, taking a minute or two.
#
#   tools/boot-test.sh [--build DIR] [--target multi-user.target] [--keep]
#
# Exits 0 only if the target was reached.

set -eu

BUILD=build
TARGET=multi-user.target
KEEP=0
TIMEOUT=600
EXTRA_CMDLINE=${BOOT_TEST_EXTRA_CMDLINE:-}

while [ $# -gt 0 ]; do
        case "$1" in
        --build) BUILD="${2:?}"; shift 2 ;;
        --target) TARGET="${2:?}"; shift 2 ;;
        --keep) KEEP=1; shift ;;
        --timeout) TIMEOUT="${2:?}"; shift 2 ;;
        -h|--help) sed -n '3,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "boot-test.sh: unknown option $1" >&2; exit 1 ;;
        esac
done

for t in qemu-system-x86_64 cpio objcopy; do
        command -v "$t" >/dev/null || { echo "boot-test.sh: need $t" >&2; exit 1; }
done
KERNEL=$(ls -1 /boot/vmlinuz-* 2>/dev/null | tail -1 || true)
[ -n "$KERNEL" ] || { echo "boot-test.sh: no kernel in /boot" >&2; exit 1; }
[ -x /bin/busybox ] || { echo "boot-test.sh: need busybox-static" >&2; exit 1; }
[ -f "$BUILD/build.ninja" ] || { echo "boot-test.sh: $BUILD is not configured" >&2; exit 1; }

WORK=$(mktemp -d)
[ "$KEEP" -eq 1 ] || trap 'rm -rf "$WORK"' EXIT
R="$WORK/root"

echo "==> building and staging"
ninja -C "$BUILD" >/dev/null
DESTDIR="$R" meson install -C "$BUILD" >/dev/null

stage_lib() {
        [ -e "$R$1" ] && return 0
        mkdir -p "$R${1%/*}"; cp -L "$1" "$R$1" 2>/dev/null || true
}

echo "==> staging linked libraries"
find "$R" -type f -perm -u+x -exec sh -c 'head -c4 "$1" | grep -q ELF && echo "$1"' _ {} \; > "$WORK/elves"
while read -r e; do
        LD_LIBRARY_PATH="$R/usr/lib/x86_64-linux-gnu/systemd:$R/usr/lib/x86_64-linux-gnu" \
                ldd "$e" 2>/dev/null | awk '/=> \//{print $3}'
done < "$WORK/elves" | sort -u | while read -r l; do
        case "$l" in "$R"/*) continue ;; esac
        stage_lib "$l"
done

# ldd cannot see dlopen'd libraries, and systemd dlopens most of its optional
# dependencies. They are declared in .note.dlopen, so read them from there.
echo "==> staging dlopened libraries from .note.dlopen"
while read -r e; do
        objcopy -O binary --only-section=.note.dlopen "$e" "$WORK/n" 2>/dev/null || continue
        [ -s "$WORK/n" ] || continue
        python3 -c '
import json,re,sys
for m in re.finditer(rb"\[\{.*?\}\]", open(sys.argv[1],"rb").read(), re.S):
    try:
        for e in json.loads(m.group(0).decode()):
            for s in e.get("soname", []): print(s)
    except Exception: pass' "$WORK/n"
done < "$WORK/elves" | sort -u | while read -r so; do
        p=$(ldconfig -p 2>/dev/null | awk -v s="$so" '$1==s {print $NF; exit}')
        [ -n "$p" ] && [ -e "$p" ] || continue
        stage_lib "$p"
        ldd "$p" 2>/dev/null | awk '/=> \//{print $3}' | while read -r d; do stage_lib "$d"; done
done
mkdir -p "$R/lib64"; cp -L /lib64/ld-linux-x86-64.so.2 "$R/lib64/" 2>/dev/null || true

echo "==> staging a minimal userland"
mkdir -p "$R"/{proc,sys,dev,run,tmp,root,bin,usr/bin,usr/sbin,etc/systemd/system/multi-user.target.wants,var/log}
cp /bin/busybox "$R/bin/busybox"
for a in sh ls cat ps mkdir ln sleep dmesg poweroff; do ln -sf busybox "$R/bin/$a"; done
# systemd invokes these by the absolute path it was built with
for t in mount umount; do ln -sf /bin/busybox "$R/usr/bin/$t"; done
for t in agetty sulogin; do p=$(command -v $t 2>/dev/null) && cp -L "$p" "$R/usr/sbin/$t"; done

# logind needs a system bus. Stage one if the host has it, so the test exercises
# logind rather than reporting a failure caused by the test rig.
if [ -x /usr/bin/dbus-daemon ]; then
        cp -L /usr/bin/dbus-daemon "$R/usr/bin/dbus-daemon"
        ldd /usr/bin/dbus-daemon 2>/dev/null | awk '/=> \//{print $3}' | while read -r l; do stage_lib "$l"; done
        mkdir -p "$R/usr/share/dbus-1" "$R/etc/dbus-1" "$R/var/lib/dbus" "$R/run/dbus"
        cp -r /usr/share/dbus-1/. "$R/usr/share/dbus-1/" 2>/dev/null || true
        cp -r /etc/dbus-1/. "$R/etc/dbus-1/" 2>/dev/null || true
        for u in dbus.socket dbus.service; do
                for src in /usr/lib/systemd/system/$u /lib/systemd/system/$u; do
                        [ -f "$src" ] && cp -L "$src" "$R/usr/lib/systemd/system/$u" && break
                done
        done
        mkdir -p "$R/etc/systemd/system/sockets.target.wants"
        ln -sf /usr/lib/systemd/system/dbus.socket "$R/etc/systemd/system/sockets.target.wants/dbus.socket"
fi

cat > "$R/etc/os-release" <<OSR
NAME="systemE"
ID=systeme
PRETTY_NAME="systemE boot test"
OSR
printf 'root:x:0:0:root:/root:/bin/sh\n' > "$R/etc/passwd"
printf 'root:x:0:\n' > "$R/etc/group"
printf 'messagebus:x:101:101:messagebus:/nonexistent:/bin/false\n' >> "$R/etc/passwd"
printf 'messagebus:x:101:\n' >> "$R/etc/group"
printf 'passwd: files\ngroup: files\nshadow: files\nhosts: files\n' > "$R/etc/nsswitch.conf"
printf 'systeme\n' > "$R/etc/hostname"
: > "$R/etc/fstab"
ln -sf /usr/lib/systemd/systemd "$R/init"

cat > "$R/etc/systemd/system/boot-verdict.service" <<UNIT
[Unit]
Description=systemE boot verdict
After=$TARGET
[Service]
Type=oneshot
StandardOutput=journal+console
ExecStart=/bin/sh -c 'echo "BOOT-TEST-STATE: \$(/usr/bin/systemctl is-system-running)"; /usr/bin/systemctl --no-pager --no-legend --failed || true; echo BOOT-TEST-END'
ExecStopPost=/bin/sh -c '/usr/bin/systemctl poweroff || /usr/bin/systemctl --force poweroff || /bin/busybox poweroff -f'
[Install]
WantedBy=$TARGET
UNIT
ln -sf ../boot-verdict.service "$R/etc/systemd/system/multi-user.target.wants/boot-verdict.service"

echo "==> packing initramfs"
( cd "$R" && find . | cpio -o -H newc --quiet | gzip -1 ) > "$WORK/initramfs.cpio.gz"

echo "==> booting"
timeout "$TIMEOUT" qemu-system-x86_64 \
        -kernel "$KERNEL" -initrd "$WORK/initramfs.cpio.gz" \
        -append "console=ttyS0 rw systemd.firstboot=no systemd.log_target=console systemd.show_status=yes systemd.unit=$TARGET $EXTRA_CMDLINE" \
        -m 1024 -smp 2 -nographic -no-reboot > "$WORK/boot.log" 2>&1 || true

sed -e 's/\x1b\[[0-9;:]*[a-zA-Z]//g' -e 's/\x1b\][^\x07]*\x07//g' "$WORK/boot.log" > "$WORK/boot.txt"
# Count systemE's markers in whichever rendering the console got: the UTF-8 glyphs,
# or the ASCII fallback used when the console cannot do UTF-8.
count_marker() { # count_marker <utf8-glyph> <ascii-char>
        a=$(grep -cF "[\$$1]" "$WORK/boot.txt" || true)
        b=$(grep -cF "[\$$2]" "$WORK/boot.txt" || true)
        echo $((a + b))
}
ok=$(count_marker '▮' '+')
failed_lines=$( { grep -F "[\$✗]" "$WORK/boot.txt" || true; grep -F '[$x]' "$WORK/boot.txt" || true; } | sed 's/^ *//' | sort -u )
failed=$(printf '%s' "$failed_lines" | grep -c . || true)

echo
echo "  units started : $ok"
echo "  units failed  : $failed"
printf '%s\n' "$failed_lines" | sed '/^$/d;s/^/    /'
sed -n '/BOOT-TEST-STATE/,/BOOT-TEST-END/p' "$WORK/boot.txt" | sed 's/^ *//;s/^\[ *[0-9.]*\] *//' | sed 's/^/  /'
[ "$KEEP" -eq 1 ] && echo "  console log   : $WORK/boot.txt"

# A boot with no done markers means job results are not reaching the console,
# which is a systemE bug even when the target is reached.
if [ "$ok" -eq 0 ]; then
        echo
        echo "systemE printed no [\$▮] lines: job-done status is broken." >&2
        exit 1
fi
if grep -q "Reached target .*$TARGET" "$WORK/boot.txt"; then
        echo
        echo "systemE reached $TARGET."
        exit 0
fi
echo
echo "systemE did NOT reach $TARGET." >&2
exit 1
