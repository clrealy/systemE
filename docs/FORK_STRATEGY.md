---
title: systemE Fork Strategy
category: Contributing
layout: default
SPDX-License-Identifier: LGPL-2.1-or-later
---

# systemE — Fork Strategy

**Status:** proposal, awaiting approval. No code changed yet.
**Base:** clrealy/systemE @ `7386493f`, a clean mirror of systemd `263~devel`. Zero fork delta today.
**Working branch:** `ccr-795d0f2e-gn8btx`

---

## 0. The one thing I need from you

Nothing below answers *why* we're forking, and that single answer changes the whole shape of the
work. Pick one:

- **A. Drop-in replacement** — systemE installs over systemd on existing systems and everything
  (packages, third-party daemons, containers, distro tooling) keeps working. Tier 2 below is frozen
  forever. This is the sane default and what the plan assumes.
- **B. Rebrand-only / vanity fork** — same code, our name on it, no behavioural divergence.
- **C. Real divergence** — we intend to delete, replace, or rewrite subsystems. Then the rename is
  the *least* interesting part and the maintenance model (§4) is the whole game.

**ANSWERED (2026-11-16): C, real divergence** — rationale is that systemd doesn't follow the Unix
philosophy. See `DIVERGENCE_PLAN.md`, which tests that claim and sets the roadmap. Net effect on
this document: Tier 2 (§2) **stays frozen**, and the rename work (§1, §6 phases 1–4) drops to low
priority — it was never the point. §3 (legal), §4 (maintenance model) and §5 (CI) all still apply,
and §4 matters *more*, because real code divergence conflicts with upstream in ways a generated
rename does not.

---

## 1. What we're actually up against (measured, not guessed)

| Thing | Count |
|---|---|
| Raw `systemd` string occurrences in tree | **48,029** |
| Files containing it | 3,380 |
| `src/` files affected | 1,294 / 3,930 |
| Man pages | 501 (526/545 files mention it) |
| Unit files | 405 |
| Installed `systemd-*` executables | ~167 |
| Exported `sd_*` ABI symbols | 907 |
| `/run/systemd` literals | 2,680 |
| `/usr/lib/systemd` literals | 984 |
| `/etc/systemd` literals | 946 |
| Unique `SYSTEMD_*` env vars | 440 |
| Unique `systemd.*` kernel cmdline options | 93 |
| `https://github.com/systemd/systemd` links | 311 |
| `systemd.io` links | 378 |
| Upstream velocity | **1,081 commits / 103 authors** in the last 12 months |

That last row is the headline. **A hand-edited 48k-occurrence diff is not rebaseable** against
~1,100 commits a year. The rename has to be *generated*, not committed by hand. See §4.

---

## 2. Three-tier classification

The whole fork hinges on sorting every occurrence of the name into one of three buckets.

### Tier 1 — RENAME (branding, zero ABI risk)

- `README.md`, `README`, `NEWS`, `TODO.md`, `CITATION.cff`, `docs/*.md` prose
- All CI badges (they currently point at *upstream's* OBS, Semaphore, Coverity project 350,
  OSS-Fuzz, Coveralls, Repology, OpenSSF Scorecard, Fedora Weblate — they'd report upstream's
  health as if it were ours, which is worse than having no badges)
- Support pointers: upstream mailing list, IRC `#systemd`, Matrix, and the **YesWeHack bug bounty**.
  These must go early — we do not want systemE users filing our bugs against upstream's bounty.
- The hotlinked logo (`brand.systemd.io/assets/page-logo.png`) — not in-tree, must be replaced not copied.
- `project('systemd', ...)` in `meson.build` → `project('systemE', ...)` **with the three caveats in Tier 3.**
- Man page prose and `<refpurpose>` text (not the `<refname>`s — those are binary names, Tier 2).

### Tier 2 — NEVER RENAME (compat surface; renaming = a different product, not a fork)

Under assumption A these are load-bearing and permanently frozen:

- **D-Bus:** `org.freedesktop.systemd1` and its ~190 `.Manager`/`.Unit` sub-interfaces. Every
  desktop environment, container runtime, and distro tool in existence calls these by name.
- **Varlink:** the `io.systemd.*` interface family (hundreds of method/error names).
- **Library ABI:** `libsystemd.so.0` (v0.45.0), `libudev.so.1` (v1.7.15), 907 `sd_*` symbols, and
  the `libsystemd.pc` / `libudev.pc` / `systemd.pc` / `udev.pc` pkg-config names. Renaming any of
  these breaks every package that links or `pkg-config`s against systemd.
- **Filesystem layout:** `/run/systemd`, `/etc/systemd`, `/usr/lib/systemd`, `/var/lib/systemd`.
  `/run/systemd/system` in particular is how `sd_booted()` and a thousand shell scripts detect us.
- **Kernel cmdline:** all 93 `systemd.*` options (`systemd.unit=`, `systemd.debug_shell`, …) —
  these live in bootloader configs, i.e. on disks we don't control.
- **Env vars:** all 440 `SYSTEMD_*` (`$SYSTEMD_EDITOR`, `$SYSTEMD_LOG_LEVEL`, …), plus
  `$NOTIFY_SOCKET` / the `sd_notify` wire protocol.
- **Journal field names:** `_SYSTEMD_UNIT`, `_SYSTEMD_CGROUP`, `_SYSTEMD_INVOCATION_ID`, …
  Renaming these invalidates every existing log query and journal file.
- **Binary names:** `systemctl`, `journalctl`, `systemd-run`, `systemd-nspawn`, and the other ~167.
  Called by name from packaging scripts (`%systemd_post`), Dockerfiles, Ansible, and muscle memory.
- **Unit names & the 405 shipped units**, generator dirs, credential names, preset files.
- **System users/groups:** `systemd-journal`, `systemd-network`, `systemd-resolve`,
  `systemd-timesync`, `systemd-imds`. Renaming orphans file ownership across an upgrade.
- **Catalog message IDs** — 128-bit UUIDs, name-free, nothing to do.

### Tier 3 — the three traps hiding inside the "safe" meson rename

`meson.project_name()` is not cosmetic. It feeds:

1. **`SBAT_PROJECT`** (`src/boot/meson.build:112`) — the UEFI Secure Boot SBAT component name baked
   into `systemd-boot` / `systemd-stub`. A fork **must** take its own SBAT component name and
   generation number so it can be revoked independently of upstream; shipping signed binaries that
   claim to be upstream's SBAT component is actively wrong. So this one *does* get renamed —
   deliberately, with its own generation counter, not as a side effect of a string swap.
2. **`GETTEXT_PACKAGE`** (`meson.build:1140`) — the translation domain. Flip it and all 59 `po/`
   catalogs silently stop resolving. Rename the domain *and* move the catalogs in the same commit.
3. **EFI `pkgname`** (`src/boot/meson.build:133`) — install paths for the EFI payload.

Also soft-compat: `systemctl --version` prints the project name, and third-party scripts grep it.
Recommend keeping a machine-readable `systemd 263 (263~devel systemE)`-shaped string so naive
greps for `systemd` still match.

---

## 3. Legal & attribution

- Licensing is fine to fork: **LGPL-2.1-or-later** on ~4,496 files, GPL-2.0-or-later on 64,
  MIT-0 on 36, plus `GPL-2.0 WITH Linux-syscall-note` kernel headers. All permit derivative works.
- **Keep every copyright header and `LICENSES/` file byte-identical.** Do not add our own copyright
  line to files we only renamed.
- Add an explicit fork notice at the top of `README.md`: what this is, what upstream commit it
  derives from, and that it is **not endorsed by or affiliated with the systemd project**.
- "systemd" functions as the upstream project's mark. We keep using it where it's a *technical
  identifier* (Tier 2 — nominative/interop use, which is exactly what trademark law leaves room
  for) and stop using it as our *product name* (Tier 1). That split is the whole legal posture, and
  it's another reason Tier 2 must stay literal.
- Rewrite `CITATION.cff` so citations don't attribute our fork to upstream's authors.
- I am not a lawyer; if systemE gets distributed under a company, get the mark use reviewed.

---

## 4. Maintenance model — the part that decides if this fork survives

**The rebrand must be an idempotent generator, not a hand-written diff.**

- `main` stays a **pristine upstream mirror**. Never commit to it.
- Fork work lives on `systemE`, and the entire Tier 1 rebrand is produced by a committed script
  (`tools/rebrand.py`) with an explicit allow/deny list derived from §2. Re-running it after an
  upstream merge reproduces the rename; conflicts collapse from ~48k sites to the handful of files
  the script itself touches.
- Real divergence (behaviour changes) lives in **small topic branches** that merge into `systemE`,
  kept separate from the rebrand so each can be rebased independently.
- **Merge, never rebase** `systemE` once it's pushed.
- The clone is currently **shallow** (1,081 commits, no tags). First action of any execution phase:
  `git remote add upstream https://github.com/systemd/systemd && git fetch --unshallow --tags upstream`.
  Without tags we can't even name our base release properly.
- Version scheme: track upstream's major and append ours — `263.0E`, next `263.1E`, bumping the
  major when we sync to 264. Keeps `meson.version` sortable and makes "which upstream are we on"
  answerable by anyone.
- Sync cadence: upstream ships ~2 majors a year. Budget a sync sprint per major, plus cherry-picks
  for CVEs. At 1,081 commits/yr from 103 authors, skipping two majors in a row is how forks die.

---

## 5. CI / infra

23 workflow files under `.github/workflows/`. Several will either break or phone home to upstream:

- `coverity.yml`, `cflite-pr.yml`, `cifuzz.yml`, `coverage.yml`, `scorecards.yml` — all bound to
  upstream project IDs/tokens. Disable or re-register; do not leave them failing red.
- `mkosi.yml` + `mkosi/` (85 files) — the integration test rig; needs our own image config.
- `make-release.yml`, `development-freeze.yml` — upstream's release process, not ours.
- `labeler.yml`, `issue-labeler.yml`, `gather-pr-metadata.yml`, `claude-review.yml` — harmless,
  keep.
- Build/test (`build-test.yml`, `unit-tests.yml`, `linter.yml`, `semcode.yml`,
  `differential-shellcheck.yml`) — keep, these are the ones that actually protect us.

---

## 6. Phased execution

| Phase | Work | Est. |
|---|---|---|
| **0** | `fetch --unshallow --tags`, pin + record the exact upstream base, add `upstream` remote | ~15 min |
| **1** | Fork notice + README/NEWS/CITATION rewrite, strip upstream badges & support channels, kill the hotlinked logo | ~1 h |
| **2** | Write `tools/rebrand.py` + the Tier 1/Tier 2 allow-deny lists, dry-run it, review the diff *stats* before the diff | ~3–4 h |
| **3** | Apply Tier 1. Verify: `meson setup build && meson test -C build` clean, `--suite clang-tidy-*` for anything in `src/` | ~2 h + build time |
| **4** | Tier 3 done deliberately: SBAT component + generation, gettext domain + `po/` move, EFI pkgname, version string | ~2 h |
| **5** | CI triage per §5 | ~1–2 h |
| **6** | Document the sync procedure in `docs/FORK_MAINTENANCE.md` so a human can do a 264 bump without me | ~1 h |

Phases 1–6 are a day or two of real work, not a week — *provided* we hold the Tier 2 line.
Hard-forking Tier 2 instead is a multi-week project with a permanently broken compat story, which
is why I'd push back on it.

---

## 7. Risks

1. **Over-eager sed.** A blind `s/systemd/systemE/g` silently breaks D-Bus, the gettext domain,
   journal fields, and `sd_booted()`. Mitigation: deny-list first, generator script, `meson test`
   gate, and reviewing diff *statistics* per directory before reading the diff itself.
2. **Rebase debt.** Covered in §4; the generator is the mitigation.
3. **Upstream confusion.** systemE users filing bugs upstream, or against their bug bounty.
   Mitigated in Phase 1, which is why support-channel removal is early and not cosmetic.
4. **Secure Boot.** Signed `systemd-boot`/`stub` carrying upstream's SBAT identity is a real
   security-process bug, not a branding nit. Phase 4.
5. **Translations.** 59 `po/` catalogs silently no-op if the domain moves without the files.
6. **Test suite length.** `test/` is 2,077 files, 613 mentioning the name. Integration tests need
   mkosi; expect the long pole here, not in `src/`.

---

## 8. What I will NOT do without you saying so explicitly

- Touch anything in Tier 2.
- Create a pull request.
- Push to `main`.
- Remove the review-confirmation banner that this repo's `AGENTS.md` requires on `README.md` once
  source files are modified — that line is yours to remove, by hand, as your review sign-off.
