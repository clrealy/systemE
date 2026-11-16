---
title: systemE Scope Decision Record
category: Contributing
layout: default
SPDX-License-Identifier: LGPL-2.1-or-later
---

# systemE — Scope Decision Record

**Date:** 2026-11-16 · **Base:** systemd `263~devel` @ `7386493f` · **Branch:** `ccr-795d0f2e-gn8btx`
**Status:** decided. Phase A implemented and verified.

Supersedes the open questions in `FORK_STRATEGY.md`, `DIVERGENCE_PLAN.md` and `STRIP_PLAN.md`.

---

## Decisions

| # | Question | Ruling |
|---|---|---|
| 1 | Fork rationale | **Real divergence** — systemd doesn't follow the Unix philosophy |
| 2 | Thesis | **Unbundle, don't rewrite.** External interfaces stay frozen |
| 3 | Strip method | **Disable → one upstream sync → delete** |
| 4 | networkd + libsystemd-network | **DROP** |
| 5 | resolved | **DROP** |
| 6 | sd-boot / bootctl / ukify | **KEEP** (reversal — `ENABLE_BOOTLOADER` gates measured boot) |
| 7 | machined / nspawn | **DROP machined, KEEP nspawn** |
| 8 | homed (+ userdb, nsresourced) | **DROP** |
| 9 | coredump | **KEEP** |
| 10 | timesyncd | **KEEP** |
| 11 | repart | **DROP** |

---

## Final scope

| | LOC |
|---|---|
| Total `src/` at base | 1,220,525 |
| **Cut** | **319,192** |
| Remaining | 901,333 |
| **Reduction** | **26.2%** |

Breakdown of the cut: niche set 109,296 · networkd + libsystemd-network 112,923 ·
resolved 59,176 + 9,144 (`dns-*.c` evicted from `libsystemd-shared`) · machined 11,887 ·
repart 13,822 · userdb 2,944.

Deliberately kept despite earlier leans (60,678 LOC): boot stack + satellites, nspawn, coredump,
timesyncd.

**Frozen, non-negotiable:** PID 1, udev, logind + `pam_systemd`, journald, tmpfiles, sysusers,
hostnamed, localed, timedated, cryptsetup, `nss-systemd`, `basic`/`shared`/`libsystemd`.
Plus the whole Tier 2 interface surface from `FORK_STRATEGY.md` §2 — D-Bus names, `io.systemd.*`
varlink, 907 `sd_*` symbols, paths, env vars, kernel cmdline, journal fields, unit semantics.

---

## Phase A — the disable commit (done)

**Implemented** in commit `2363a83d`. 21 options, not the 23 first listed: bare booleans default
to `true` and bare features to `auto`, so each needs an explicit value.

```
value : false       networkd, resolve, machined, userdb, nsresourced,
                    portabled, sysext, mountfsd, storagetm, pstore
value : 'disabled'  nss-resolve, nss-mymachines, homed, repart, sysupdate,
                    importd, vmspawn, report, imds, remote, sysupdated
```

Two entries from the original list are deliberately untouched: `default-network` is already `false`
upstream, and `imds-network` is a **combo** selecting the IMDS network mode (`unlocked`/`locked`),
not an on/off switch — disabling `imds` covers it. Listing it here was an error.

The defaults are flipped in `meson_options.txt` itself, so a plain `meson setup build` yields a
systemE build rather than relying on packagers to pass flags.

**Work in Phase A:**
1. Flip the defaults (21 options; see above).
2. Remove units for disabled components (`units/meson.build` is already conditional — verify, don't
   assume).
3. Strip the matching integration tests from `test/` so CI goes green, not red.
4. `meson setup build && meson test -C build` must pass clean.
5. `meson test -C build --suite clang-tidy-<dir>` for any directory touched.
6. Per this repo's `AGENTS.md`: prepend the review-confirmation banner to `README.md`. That line is
   removed by a human reviewer, never by me.

**Not in Phase A:** no directory deletions, no renames, no interface changes.

### Phase A result (verified)

Measured against a baseline configured from the unmodified options file, so the delta isolates this
change rather than this container's missing dependencies:

| | |
|---|---|
| Components moved to disabled | 20 / 20 |
| Installed files | 783 → 633 (**150 removed**) |
| Breakdown | 64 units, 34 executables, 36 network examples/configs, 7 polkit policies, 5 shell completions, 4 NSS modules |
| Build | clean (2,312 targets) |
| Tests | **1,696 passed, 0 failed, 32 skipped** |
| clang-tidy | not applicable — no C changed |

Items 2 and 3 above needed no work: upstream's `meson.build` files already `subdir_done()` on the
component's own `ENABLE_*` key, so units and tests for disabled components drop out on their own.

**One latent bug found and fixed** (`4a55c401`): `tmpfiles.d/systemd-nspawn.conf` was gated on
`ENABLE_MACHINED` alone, but `/var/lib/machines` is where nspawn resolves `--machine=NAME`
(`src/nspawn/nspawn.c:3058`) and the `--ephemeral` snapshot cleanup is nspawn's alone. Keeping
nspawn while dropping machined is a combination upstream does not contemplate, so the directory
and its cleanup silently vanished. Now gated on either component. This is the "silent keep-set
dependency" risk from `STRIP_PLAN.md` §6.2, and a scan of every other install gate in
`tmpfiles.d`, `sysusers.d`, `rules.d`, `presets` and `sysctl.d` found it to be the only one — all
other gated files pair with their own component.

---

## Roadmap after Phase A

| Phase | Work |
|---|---|
| **A** | Disable commit (above) |
| **B** | One full upstream sync with components off — proves the seam before anything irreversible. First step: `git fetch --unshallow --tags upstream` (the clone is shallow, 1,081 commits, no tags) |
| **C** | Delete the dropped directories. Priced at ~1.4 straddling merge commits/week |
| **D** | W1 — closure measurement harness + CI gate that fails when a tool's dependency closure grows. Baselines the *stripped* tree |
| **E** | W3 — extend `standalone-binaries` from 5 tools to every leaf tool |
| **F** | W2 — delaminate `libsystemd-shared` (190,024 LOC) into layers, one tier per topic branch |
| **G** | Rebrand, SBAT component identity, gettext domain. Low priority; it was never the point |

Still open, deliberately deferred: **is the binary journal in scope?** Strongest remaining
Unix-philosophy target, most compat-destructive. Revisit after D, with closure data in hand.
