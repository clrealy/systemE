---
title: systemE Strip Plan
category: Contributing
layout: default
SPDX-License-Identifier: LGPL-2.1-or-later
---

# systemE — Strip Plan (W0: scope reduction)

Third doc. `FORK_STRATEGY.md` = mechanics, `DIVERGENCE_PLAN.md` = thesis, this = **what we cut.**

Stripping is a different axe from delamination: `DIVERGENCE_PLAN.md` W2 reshapes *how* the code is
coupled; this reduces *how much there is*. They compose, and stripping is **much cheaper**, so it
should go first.

---

## 1. Why this is the best-value move in the whole fork

Three reasons, all measured:

1. **The build system already supports it.** 289 meson options, with per-component feature flags
   for essentially every candidate below. Stripping is largely `-Dnetworkd=false -Dresolve=false …`
   — not a patch.
2. **We walk away from the quieter part of the tree.** **2,062 of 9,345** commits (22%) in the last
   12 months touch a strip candidate, against **4,102** (44%) touching the keep-set. Disabling costs
   nothing at all; deleting costs what §5 prices.
3. **The seam is already clean.** I checked for cross-includes from the keep-set into the
   candidates: **zero**. Nothing in `core`, `udev`, `login`, `journal` or `shared` includes
   `libsystemd-network`, resolved internals, or any candidate's headers. The cut lines exist
   already; we're not carving them.

---

## 2. What it's worth, by cut line

Total `src/` is **1,220,525 LOC**.

| Cut line | LOC removed | % of src |
|---|---|---|
| **Niche only** — homed, sysupdate, importd, vmspawn, report, portabled, nsresourced, imds, sysext, mountfsd, storagetm, pstore, journal-remote | 109,296 | **9.0%** |
| **+ network stack** — networkd (78,792), libsystemd-network (34,131), resolved (59,176), plus the 9,144 LOC of `dns-*.c` that leaves `libsystemd-shared` with it | 290,539 | **23.8%** |
| **+ boot stack** — sd-boot, sd-stub, bootctl, ukify | 324,596 | **26.6%** |
| **+ containers** — machined, nspawn | 351,633 | **28.8%** |

So the realistic ceiling is **~29% of the source tree gone** without touching a single interface
in the Tier 2 freeze.

Two freebies worth calling out:

- Dropping resolved evicts `dns-rr.c` / `dns-packet.c` / `dns-type.c` — **9,144 LOC** — out of
  `libsystemd-shared`. Stripping does W2's job for free on that slice.
- Dropping the boot stack **deletes the SBAT problem entirely** (`FORK_STRATEGY.md` §2 Tier 3).
  No signed EFI binaries, no Secure Boot component identity, no revocation generation to manage.
  That was the single nastiest item in the whole fork and scope reduction makes it vanish.

---

## 3. KEEP — load-bearing for the world outside systemE

Dropping any of these means systemE is not a drop-in replacement, i.e. nobody can run it.

| Component | LOC | Why it cannot go |
|---|---|---|
| `src/core` | 117,607 | It's PID 1. |
| `src/udev` | 28,660 | Device management; every distro, every initrd, every GUI depends on it. |
| `src/login` (logind + `pam_systemd`) | 23,654 | GNOME, KDE, polkit, PipeWire, Wayland compositors and seatd all talk to logind; **86** `sd-login` API entry points. This is the #1 thing people wrongly assume is optional. |
| `src/journal` (journald) | 14,702 | Every existing `journalctl` archive and log query. Replacing the format is a separate, later fight. |
| `src/tmpfiles` + `src/sysusers` | 8,131 | **Third-party packages ship `.conf` snippets** and call these from install scripts. Dropping them breaks other people's packages at install time, not ours at build time. |
| `src/hostname` + `locale` + `timedate` | 8,768 | GNOME Settings and NetworkManager call these over D-Bus. Tiny; not worth the breakage. |
| `src/cryptsetup` | 5,671 | Encrypted root does not boot without it. |
| `nss-systemd` | — | Resolves `DynamicUser=` identities. Drop it and dynamic users become unresolvable UIDs. |
| `src/basic`, `src/shared`, `src/libsystemd` | 386,878 | The thing W2 delaminates, not something to delete. |

---

## 4. Judgment calls — your call, not mine

| Component | LOC | The trade |
|---|---|---|
| **networkd + libsystemd-network** | 112,923 | Biggest single win in the fork. But cloud images, container hosts and most minimal/immutable distros use it specifically *because* NetworkManager is heavy. Dropping it means systemE boxes need NM, ifupdown or connman. |
| **resolved** | 59,176 | unbound/dnsmasq/stub-resolv all exist and predate it. Dropping also costs `nss-resolve` and takes the DNSSEC/DoT story with it. |
| **sd-boot + bootctl + ukify** | 34,057 | GRUB and systemd-boot are genuinely interchangeable, and this kills the SBAT headache. Counterpoint: UKIs + measured boot are where the ecosystem is heading, and we'd be opting out. |
| **machined + nspawn** | 27,037 | Podman talks to machined for some integration; nspawn is a widely-used dev tool. Docker/LXC/podman cover the container case regardless. |
| **homed** | 28,439 | Genuinely niche. Easy cut unless you care about portable encrypted home dirs. |
| **coredump** | 5,604 | Dropping reverts to the kernel's `core_pattern`. Defensible either way. |
| **timesyncd** | 2,732 | chrony is better. Only 2.7k LOC though, so the cut buys little. |
| **repart** | 13,822 | Useful for image-based/immutable systems. Dead weight on a normal install. |

---

## 5. The decision that actually matters: **disable or delete?**

These are not the same move and the difference is the whole maintenance story.

**Option A — disable** (flip existing meson defaults to `false`)
- Effort: ~1 day. Zero merge conflicts, ever. Fully reversible.
- systemE *ships* smaller — users get 29% less surface.
- But the code stays in-tree, so we still carry upstream's churn and the repo still *looks* like
  systemd. Doesn't satisfy "strip it down" in spirit.

**Option B — delete the directories**
- 29% of `src/` actually gone. Repo becomes legibly a different, smaller project.
- Priced it against real churn. Of the 176 candidate-touching commits in 12 months:
  - **1,440 touch only deleted code** → resolved as "stay deleted"; mechanical, and automatable
    with `git rerere` or a merge driver.
  - **622 straddle** deleted and kept code → need a human look. That's **~12/week.**
- Note a straddling commit is not automatically a *conflict*: git only conflicts when the same
  file is touched on both sides, and deletions surface as delete/modify, which resolve one way.
  Most of the 622 will be trivial. But the honest headline is **~12 straddling commits a week, not
  the ~1.4 first estimated** — a standing part-time maintenance cost rather than an hour a week.
  **Still affordable, but budget it as a job, not a rounding error.**

**My recommendation: A then B.** Disable in one day, run one full upstream sync with the components
off, confirm nothing in the keep-set quietly needed them, *then* delete. The disable phase is a
free dry run for the delete, and if the seam turns out to be dirtier than the include analysis
suggests, we find out before it's irreversible.

Sequencing against `DIVERGENCE_PLAN.md`: this becomes **W0**, before W1's measurement harness —
no point baselining dependency closures for 167 binaries when a third of them are about to not
exist. W1 then baselines the stripped tree, which is the one we actually maintain.

---

## 6. Risk

1. **logind.** The one component people assume is optional and absolutely isn't. If a desktop has
   to run on systemE, this is frozen. Flagging it because "strip it down" conversations kill
   logind more often than anything else.
2. **Silent keep-set dependencies.** Include analysis says the seam is clean, but build-time
   generated sources and unit-file `Wants=` can couple things invisibly. Option A's dry run is
   the mitigation.
3. **Distro viability.** Past ~24% (dropping networkd + resolved) systemE stops being packageable
   as a systemd replacement for a general-purpose distro and becomes a specialist init for a
   specific kind of system. That's a legitimate choice — but it should be a *chosen* one, not a
   consequence we notice later.
4. **Test suite.** `test/` is 2,077 files; integration tests for stripped components must be
   removed in the same commit or CI goes red and stays red.
