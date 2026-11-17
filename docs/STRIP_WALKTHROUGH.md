---
title: systemE Component Decisions
category: Contributing
layout: default
SPDX-License-Identifier: LGPL-2.1-or-later
---

# systemE — Per-component decision brief

Companion to `STRIP_PLAN.md`. Settled: **disable → one upstream sync → delete.**
Keep-set is fixed (PID 1, udev, logind, journald, tmpfiles/sysusers, hostnamed/localed/timedated,
cryptsetup, nss-systemd, basic/shared/libsystemd). Below are the 8 open calls, each verified
against the tree rather than from memory.

---

## 1. networkd + libsystemd-network — 112,923 LOC — **rec: DROP**

Biggest single win available.

**Verified safe:** I chased the one scary-looking coupling. `src/udev/udev-event.c` mentions
networkd — it's a *comment*. The real question was udev's interface naming (`.link` files,
`net_setup_link` builtin): `src/udev/net/link-config.c` includes `sd-netlink.h`,
`netlink-util.h`, `network-util.h`, `ethtool-util.h` — all of which live in
`src/libsystemd/` and `src/shared/`, **not** in `src/network/` or `src/libsystemd-network/`.
So predictable interface naming survives the cut. That was the one thing that could have killed
this option and it holds.

**Note:** `sd-network` (the *client* API for querying link state) is part of libsystemd's frozen
ABI, so it stays and simply reports no data. API kept, daemon gone. Clean.

**Cost:** systemE needs NetworkManager, ifupdown, or connman. The people who lose out are cloud
and container images that chose networkd specifically *because* NM is heavy.

**Drop if** you target desktop/server. **Keep if** you target cloud/immutable images.

## 2. resolved — 59,176 LOC — **rec: DROP**

Takes `nss-resolve`, `resolvectl`, and the DNSSEC/DoT/mDNS/LLMNR stack with it. unbound, dnsmasq
and a plain `resolv.conf` all predate it and work fine.

**Bonus:** evicts `dns-rr.c` + `dns-packet.c` + `dns-type.c` — **9,144 LOC** — from
`libsystemd-shared`. Real delamination progress for free.

**Cost:** you own the resolver choice and the `/etc/resolv.conf` management policy from then on.

## 3. sd-boot / bootctl / ukify — 34,057 LOC — **rec: KEEP (I'm reversing my earlier lean)**

In `STRIP_PLAN.md` I sold this as a clean win that deletes the SBAT headache. Then I checked what
`ENABLE_BOOTLOADER` actually gates, and it's a **hub**, not a leaf:

- `src/bless-boot` (720) — automatic boot assessment / boot counting / auto-rollback
- `src/factory-reset` (509)
- `src/pcrextend` (620) — TPM PCR measurement
- `src/tpm2-setup` (1,286)

Only 3,135 LOC, but functionally that's **the entire measured-boot and auto-rollback story**, plus
UKI support. The LOC number badly understates the blast radius. `src/kernel-install` (1,782)
survives but loses its `60-ukify` and `90-loaderentry` plugins.

Also: dropping this does **not** evict `tpm2-util.c` (13,093 LOC) from `libsystemd-shared` —
`src/cryptsetup/` needs it for LUKS2 TPM2 tokens, and cryptsetup is keep-set. That's a W2
delamination target, not something stripping can reach.

So the real trade is: save 34k LOC and the SBAT process, lose UKIs, measured boot, boot assessment
and factory reset, and opt out of where the ecosystem is heading. **I'd keep it and just do the
SBAT work properly** (it's ~2 hours, per `FORK_STRATEGY.md` §6 phase 4).

## 4. machined + nspawn — 27,037 LOC — **rec: drop machined, keep nspawn**

`src/nspawn/nspawn.c` talks to `org.freedesktop.machine1` only for registration, and already
supports `--register=no`. So they separate cleanly.

- **machined** (11,887) + `nss-mymachines` + `machinectl`: podman/docker/LXC cover the real
  container story. Drop.
- **nspawn** (15,150): widely-used dev/test tool, and `mkosi` (our integration test rig) uses it.
  Cheap to keep.

## 5. homed — 28,439 LOC — **rec: DROP, and it takes two more with it**

Verified coupling: `homed-manager.c`, `homed-varlink.c`, `homectl.c` all depend on userdb.
`src/userdb` (2,944) and `src/nsresourced` (6,585) lose their principal consumer, so realistically
this is a **37,968 LOC** cut, not 28k. Also takes `pam_systemd_home` and portable encrypted homes.

Genuinely niche. Easy call unless you specifically want LUKS-backed portable home directories.

## 6. coredump — 5,604 LOC — **rec: KEEP (weak)**

Dropping reverts to the kernel's `core_pattern`, and you lose `coredumpctl` plus structured crash
metadata in the journal. It's cheap, it's a journald integration (keep-set), and it's one of the
things people actually like. Defensible either way; I'd keep.

## 7. timesyncd — 2,732 LOC — **rec: KEEP (bad-value cut)**

chrony is a better NTP client, no argument. But this is 2,732 LOC — 0.2% of the tree — and cutting
it means systemE ships with no time sync out of the box. Worst ratio of breakage to LOC saved on
the whole list.

## 8. repart — 13,822 LOC — **rec: DROP**

Grows/creates partitions declaratively, mostly for image-based and immutable systems, often from
the initrd. Its main in-tree consumer was sysupdate, which is already in the niche cut. Dead weight
on a conventional install.

---

## Totals by recommendation

| | LOC |
|---|---|
| Niche cut (already settled) | 109,296 |
| + networkd/libsystemd-network | 112,923 |
| + resolved (incl. 9,144 from libshared) | 68,320 |
| + machined (nspawn kept) | 11,887 |
| + homed/userdb/nsresourced *(userdb+nsresourced already counted in niche — net add)* | 28,439 |
| + repart | 13,822 |
| **Total if you take every recommendation** | **~344,687 (28.2% of src/)** |
| Kept against earlier lean: sd-boot stack, nspawn, coredump, timesyncd | 76,450 |

Net effect of following my recs: **~28% of `src/` gone**, measured boot and UKIs intact, desktops
and third-party packages still work.
