---
title: systemE Scope Decision Record
category: Contributing
layout: default
SPDX-License-Identifier: LGPL-2.1-or-later
---

# systemE — Scope Decision Record

**Date:** 2026-11-16 · **Base:** systemd `263~devel` @ `7386493f` · **Branch:** `ccr-795d0f2e-gn8btx`
**Status:** decided, not yet implemented. No source file has been modified.

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

## Phase A — the disable commit (ready to apply)

All 23 option names verified present in `meson_options.txt`:

```
-Dnetworkd=false -Ddefault-network=false
-Dresolve=false -Dnss-resolve=false
-Dmachined=false -Dnss-mymachines=false
-Dhomed=false -Duserdb=false -Dnsresourced=false
-Drepart=false
-Dsysupdate=false -Dsysupdated=false
-Dimportd=false -Dvmspawn=false -Dreport=false -Dportabled=false
-Dimds=false -Dimds-network=false
-Dsysext=false -Dmountfsd=false -Dstoragetm=false -Dpstore=false
-Dremote=false
```

Phase A flips these defaults in `meson_options.txt` so a plain `meson setup build` yields a systemE
build, rather than relying on packagers passing flags.

**Work in Phase A:**
1. Flip the 23 defaults.
2. Remove units for disabled components (`units/meson.build` is already conditional — verify, don't
   assume).
3. Strip the matching integration tests from `test/` so CI goes green, not red.
4. `meson setup build && meson test -C build` must pass clean.
5. `meson test -C build --suite clang-tidy-<dir>` for any directory touched.
6. Per this repo's `AGENTS.md`: prepend the review-confirmation banner to `README.md`. That line is
   removed by a human reviewer, never by me.

**Not in Phase A:** no directory deletions, no renames, no interface changes.

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
