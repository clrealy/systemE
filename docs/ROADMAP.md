---
title: systemE Fork Roadmap
category: Contributing
layout: default
SPDX-License-Identifier: LGPL-2.1-or-later
---

# systemE — Master Roadmap

**Single source of truth.** Supersedes the phase lists in `FORK_STRATEGY.md` §6,
`DIVERGENCE_PLAN.md` §4, `STRIP_PLAN.md` §5 and `RUST_PLAN.md` §6.
Base: systemd `263~devel` @ `7386493f`. Branch: `ccr-795d0f2e-gn8btx`.
**Status: decided. Phases A–D done and verified; E onwards not started.**

---

## The fork in one paragraph

systemE is a **scope-reduced, delaminated, selectively-Rust** systemd derivative that stays a
**drop-in replacement**. Every external interface is frozen: D-Bus names, `io.systemd.*` varlink,
907 `sd_*` symbols, filesystem paths, env vars, kernel cmdline, journal fields, unit semantics. We
change what's *inside*: 26% less of it, split along real seams, with the untrusted-input parsers
rewritten in `no_std` Rust behind the unchanged C ABI.

Three findings justify forking rather than filing bugs, and all three are direction disagreements
rather than defects:

1. `src/shared` is **190,024 LOC** — 62% larger than PID 1 — and linked into all ~167 binaries.
   Upstream's answer to that smell was a linter (`meson.build:3348`), and they ship a
   `systemd-multicall-binary` option to fuse things *further*. They're consolidating; we delaminate.
2. Upstream's Rust policy (`docs/CODING_STYLE.md:1046`) is leaf-components-only, existing C never
   ported — which bans every parser where memory safety actually pays.
3. Scope: 13 components we consider out of an init system's business.

---

## Decisions on record

| Area | Ruling |
|---|---|
| Rationale | Real divergence (Unix philosophy) |
| Thesis | Unbundle, don't rewrite. Interfaces frozen |
| Strip method | Disable → sync → delete |
| Strip scope | **319,192 LOC / 26.2% of `src/`** |
| Dropped | networkd + libsystemd-network, resolved, machined, homed (+userdb, nsresourced), repart, + 13 niche components |
| Kept against earlier leans | sd-boot stack (`ENABLE_BOOTLOADER` gates measured boot), nspawn, coredump, timesyncd |
| Rust policy | **Diverge:** port untrusted-input parsers behind the frozen C ABI |
| Rust constraints | **Keep `no_std`**, `core` + `libc` only, meson, no cargo |
| Sequencing | **W2 delamination before the Rust push** |
| Rebrand | Lowest priority. Was never the point |

---

## Phases, in order

Dependencies are real: **E blocks both F and G.** That's what the sequencing decision bought.

| Phase | Work | Gate to pass | Est. |
|---|---|---|---|
| **A** ✅ | **Disable commit.** *Done — `2363a83d`, `4a55c401`. 21 options flipped, 150 fewer installed files, 1,696 tests passed / 0 failed. See `SCOPE_DECISION.md`.* Flip 23 verified `meson_options.txt` defaults. Remove units for disabled components. Strip matching `test/` integration tests so CI stays green. Prepend the `AGENTS.md` review banner to `README.md` | `meson test -C build` clean; `--suite clang-tidy-<dir>` clean for any dir touched | ~1 day |
| **B** ✅ | **First upstream sync.** *Done — history unshallowed (94,220 commits, tags recovered; our base is `v262-2499-g7386493f3b`), upstream merged clean, 1,696 tests passed / 0 failed. See the correction below.* `git remote add upstream` + `git fetch --unshallow --tags` (clone was shallow: 17 days of history, no tags). Sync with components disabled — this is the free dry run that proves the seam before anything irreversible | Full build + test green with everything off | ~1 day |
| **C** ✅ | **Delete** the dropped directories. *Done — `5411b56af2`, `86cc5b506c`, `7596dab98a`. 1,597 files, ~355,700 lines, 33 build options; installed files 783 → 633; 1,629 tests passed / 0 failed.* | Build green; repo is legibly a smaller project | ~1 day |
| **D** ✅ | **W1 — closure harness.** *Done — `tools/closure-report.py`, `tools/closure-baseline.json`, `.github/workflows/closure-gate.yml`. See the result below.* Per-binary linked LOC, symbol count, object closure, dlopen set. Baseline the *stripped* tree. CI gate that **fails when a tool's dependency closure grows** | Gate live and failing correctly on a deliberate regression | ~1 day |
| **E** | **W2 — delaminate `libsystemd-shared`** (190,024 LOC) into tiers: `util` → `fmt` → `sys` → `crypto` → `net`. Cut lines chosen from D's data, not taste. Lower layers never call upward. One tier per topic branch | Each tier merges green independently; D's numbers move the right way | **weeks** (the bulk of the fork) |
| **F** | **W3 — `standalone-binaries` from 5 → all leaf tools.** Includes fixing `rust_executable_template` (`meson.build:2299`) so Rust programs can static-link a slim tier instead of always needing libshared | Each conversion is one reviewable PR with a measured closure delta | ~2–4 days |
| **G** | **Rust chunk program.** Order: `sd-json` → `journal-file` → `dissect-image` → `udev-rules` → EFI `boot.c`. One chunk = one file, ported `no_std` behind the unchanged C ABI, then **differential-fuzzed C vs Rust** on the existing corpora (`fuzz-json`, `fuzz-journal-file`, `fuzz-unit-file`, `fuzz-udev-rules`, `fuzz-varlink` all exist in-tree, plus OSS-Fuzz history). Disagreement = bug, pre-merge. Green merges, red reverts *the chunk* | Byte-for-byte parity under differential fuzzing | ~42k LOC, multi-quarter |
| **H** | **Rebrand.** systemE naming, **SBAT component identity + generation** (required: we kept sd-boot, so this is a real security-process task), gettext domain + `po/` move, EFI pkgname, version string | Build green; signed EFI binaries carry systemE's own SBAT identity | ~1 day |

**Never:** PID 1 in Rust (all `unsafe` FFI anyway — smallest win, total blast radius). Big-bang
rewrite (~82 person-years, see `RUST_PLAN.md` §2). Any change to the frozen interface surface.

---

## Maintenance invariants

- `main` stays a pristine upstream mirror. Never commit to it.
- Merge, never rebase, a pushed `systemE`.
- Sync to upstream majors **before** starting a new W2 tier, never mid-tier.
- Prefer moving files whole over editing in place — git's rename detection survives upstream churn
  far better than scattered hunks.
- D's closure gate runs on every sync, so an upstream merge that silently re-couples something
  fails loudly instead of rotting.
- Budget: strip touches **22%** of upstream's churn (2,062 of 9,345 commits/yr). Rust ports land in
  the hot **44%** (4,102 commits/yr). Deletion costs ~12 straddling merge commits/week.

---

## Correction recorded in Phase B

The figures in the first five documents were computed on the **shallow clone**, which held only
**17 days** of history (2026-10-30 to 2026-11-16) while `git log --since="12 months ago"` silently
reported all of it. Unshallowing in Phase B gave the real numbers:

| | First stated | Actual |
|---|---|---|
| Upstream commits / 12 months | 1,081 | **9,345** |
| Distinct authors / 12 months | 103 | **613** |
| Commits touching dropped code | 176 (16%) | **2,062 (22%)** |
| — of those, drop-only | 102 | **1,440** |
| — of those, straddling | 74 (~1.4/week) | **622 (~12/week)** |
| Commits touching the keep-set | 533 | **4,102 (44%)** |
| Release cadence | ~2/year | **~4/year** (v261→v262: 94 days, 1,894 commits) |
| DNS code evictable from libshared | 9,144 | **7,764** (`dns-domain.c` must stay: `conf-parser.c` and `user-record.c` use it) |

**Every conclusion survives, and two get stronger.** The argument that a hand-edited rename is
unrebaseable, and that W2 must land tier by tier, both rest on upstream velocity being high — it is
8.6× higher than stated. "Rust ports land in the hot 44%" happened to be exactly right.

**One decision input genuinely changed:** Phase C deletion was priced at ~1.4 straddling merges per
week and called "about an hour a week." It is **~12 a week**. That is a standing part-time cost, not
a rounding error. Phase C still stands — most straddling commits are not true conflicts, since git
only conflicts when the same file is touched on both sides and deletions resolve one way — but it
should be budgeted as a job.

**Phase B also exposed a measurement lesson worth keeping:** never quote a rate from a shallow
clone. `--since` cannot tell you it ran out of history.

## Phase C result (verified)

Landed as three commits, each green on its own:

| | |
|---|---|
| Source directories deleted | 21 (862 files) |
| Satellites deleted | 209 files (95 units, 171 man pages, 22 completions, 14 test fragments, 8 confs) |
| Build options removed | 33 (289 → 256) |
| Installed files | 783 → **633** |
| Build | clean |
| Tests | **1,629 passed, 0 failed, 32 skipped** |
| Man pages | 1,130 build with `-Dman=enabled`; dist suite 253 passed, 0 failed |

**Four more cross-gating bugs of the nspawn class**, where a file is gated on a component other
than the one that owns it:

1. `systemd-network-generator.service` had **no condition at all**, though its binary was built
   only as part of the networkd stack.
2. The four `systemd-sysupdate-notify-*` units are gated on `ENABLE_BOOTLOADER`, because bootctl
   handles the notification, while sysupdate is what connects to the socket.
3. zsh installed `_userdbctl` unconditionally where bash gated it on `ENABLE_USERDB`.
4. `network/80-container-{vb,ve,vz}.link` are gated on networkd but configure **udev's** handling
   of the veth links **nspawn** creates. Both of those stay, so the files now install
   unconditionally — otherwise `99-default.link` matches instead and applies
   `MACAddressPolicy=persistent` to container interfaces.

`99-default.link`, which sets default interface naming for every NIC, is installed outside the
networkd gate upstream, so naming was never at risk. Checked rather than assumed.

**Deferred to Phase E:** `src/shared/dns-*.c` and the `resolve-*` helpers in `src/shared`. Evicting
them touches the shared library the kept components link, which is delamination work, not deletion.

**Known follow-ups:** `mkosi/` still carries drop-ins for components we no longer ship (deliberately
untouched — `mkosi.repart/` is consumed by the *host's* repart to build test images); the restored
`system-or-user-ns-mountfsd*.xml` man fragments still describe mountfsd and want a prose pass; and
`po/POTFILES.skip` has pre-existing upstream staleness (`src/boot/efi/*`).

## Phase D result (verified)

`tools/closure-report.py` walks the real link graph — link edges from `ninja -t query`, source
lists from meson introspection — and records per installed program: own lines, the libraries it
links, objects and lines in its link closure, the features its closure may `dlopen` (read out of
`.note.dlopen`), and binary size.

Run it:

```
meson setup build --auto-features=disabled && ninja -C build
tools/closure-report.py build                                    # summary
tools/closure-report.py build --baseline tools/closure-baseline.json   # the gate
tools/closure-report.py build --write-baseline tools/closure-baseline.json
```

**What it measured**, over the 90 programs of the gate configuration:

| | |
|---|---|
| Mean closure | **322,238 lines** per program |
| `systemd-analyze` | 9,516 own lines, **423,116** of closure |
| `journalctl` | 3,796 own lines, **321,566** of closure |
| `systemd-coredump` | 3,539 own lines, **321,309** of closure |

Every program links `libsystemd-shared` and `libsystemd` in full. This is the number E has to move,
and it is now recorded rather than asserted.

**The gate** fails when, for any program, `closure_loc` or `closure_objs` grows, or it gains a
library, or it gains a `dlopen` feature. New and removed programs are reported but do not fail.
Verified both ways: clean tree passes, and a deliberately tampered baseline produced all four
regression kinds and exit 1.

Two things that make it trustworthy rather than decorative:

- **It is memoised.** Every program links libsystemd-shared, so the naive version recomputed that
  closure 113 times and took 58s. It now takes 7.
- **The baseline carries a build-configuration fingerprint.** What a program links depends on which
  optional libraries are present, so a baseline recorded with tpm2 or libfdisk available is not
  comparable to one without. On a mismatch the gate names the differing options and refuses to
  compare instead of reporting phantom regressions. The gate configures with
  `--auto-features=disabled` for exactly this reason, which also makes the baseline reproducible on
  any machine — confirmed across separate build directories.

**Not verified:** the workflow itself has never run. GitHub Actions cannot be executed here, so
while every command in it was run by hand in this container, the YAML is unproven until a PR
triggers it.

## Does it boot

Yes. `tools/boot-test.sh` boots systemE as PID 1 in qemu and exits non-zero unless the default
target is reached. No KVM is needed; software emulation takes a couple of minutes.

Most recent run, against a build configured with `--auto-features=enabled`:

```
  units started : 87
  units failed  : 1
    [FAILED] Failed to start ldconfig.service.
systemE reached multi-user.target.
```

journald, logind, udevd, oomd, timesyncd, getty and serial-getty all start. The one failure is
the test rig, not systemE: an initramfs has no linker cache for `ldconfig` to rebuild.

Three things the rig had to get right, each of which produced a convincing wrong answer first:

- **`ldd` is not enough.** systemd `dlopen`s most of its optional dependencies, so the libraries
  it needs at runtime are invisible to the linker. Without them PID 1 dies at
  `Failed to mount early API filesystems`, because `mount_option_mangle()` reaches libmount
  through `dlopen`. The rig reads `.note.dlopen` instead, the same ELF notes
  `closure-report.py` uses.
- **Absolute paths.** systemd invokes `/usr/bin/mount` by the path it was built with, so a
  busybox `mount` on `PATH` is not enough and seven mount units fail.
- **`systemd.firstboot=no`.** Otherwise the boot reaches first-boot setup and waits for someone
  to type a timezone, which looks exactly like a hang.

## Still open, deliberately

**Is the binary journal format in scope?** Strongest remaining Unix-philosophy target, most
compat-destructive change available. Worth noting it gets *easier* to answer after G: porting
`journal-file.c` to Rust means fully re-deriving the format parser anyway, and doing that port
first commits you to nothing. Decide after G's first chunks, with real data.
