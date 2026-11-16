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
**Status: decided. Phases A and B done and verified; C onwards not started.**

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
| **C** | **Delete** the dropped directories. 319,192 LOC gone | Build green; repo is legibly a smaller project | ~1 day |
| **D** | **W1 — closure harness.** Per-binary linked LOC, symbol count, object closure, dlopen set. Baseline the *stripped* tree. CI gate that **fails when a tool's dependency closure grows** | Gate live and failing correctly on a deliberate regression | ~1 day |
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

## Still open, deliberately

**Is the binary journal format in scope?** Strongest remaining Unix-philosophy target, most
compat-destructive change available. Worth noting it gets *easier* to answer after G: porting
`journal-file.c` to Rust means fully re-deriving the format parser anyway, and doing that port
first commits you to nothing. Decide after G's first chunks, with real data.
