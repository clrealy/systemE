---
title: systemE Divergence Plan
category: Contributing
layout: default
SPDX-License-Identifier: LGPL-2.1-or-later
---

# systemE — Divergence Plan: the Unix-philosophy thesis, tested

Companion to `FORK_STRATEGY.md`. Answers §0 of that doc: **option C, real divergence.**
Stated rationale: *systemd doesn't follow the Unix philosophy.*

Before planning around that, I measured it. Part of it does not survive contact with the tree, and
part of it survives very well. Building on the wrong half would sink the fork, so:

---

## 1. The version of the critique that is NO LONGER TRUE

**"systemd is a monolith / one giant process."** Structurally false:

- ~**167** separate installed executables.
- **289** build options, including per-component feature flags for `networkd`, `resolved`, `homed`,
  `logind`, `machined`, `timesyncd`, `oomd`, `portabled`, `sysupdate`, `importd`, `nspawn`,
  `coredump`, `hwdb`, `tmpfiles`, `sysusers`, and ~40 more. You can already build a systemd with
  almost all of it switched off.
- PID 1 (`src/core`, 117k LOC) is overwhelmingly unit-type state machines:
  `unit.c` 7.3k, `exec-invoke.c` 7.3k, `load-fragment.c` 6.9k, `service.c` 6.8k, `manager.c` 5.7k.
  That is work *any* supervising init must do somewhere. There is no 50k-LOC lump in there to
  delete.

**"Every systemd tool drags in a pile of libraries."** Also largely false *at runtime* — and this
is the one I expected to confirm and couldn't. `libsystemd-shared` names **30** external deps
(openssl, cryptsetup, fido2, tpm2, libarchive, curl, microhttpd, qrencode, pwquality, pcre2,
seccomp, selinux, apparmor, audit, blkid, fdisk, kmod, mount, pam, p11kit, xenctrl, …) — but
upstream **dlopens essentially all of them** (`dlopen_libcrypto`, `dlopen_libfido2`,
`dlopen_cryptsetup`, `dlopen_microhttpd`, `dlopen_libseccomp`, … ~30 helpers). So
`systemd-tmpfiles` does not actually pull libqrencode into memory. The bloat-at-runtime argument
has been quietly engineered away over the last few releases.

**If the fork's goal were "fewer deps, smaller processes," there is much less to win here than the
discourse suggests, and we'd spend months to land near where upstream already is.** I'd be doing
you a disservice not to say that up front.

---

## 2. The version of the critique that IS TRUE, and is fork-worthy

The coupling is not in processes or runtime deps. It's in **code, build, and release**.

### 2.1 `libsystemd-shared.so` — the actual monolith

| | LOC |
|---|---|
| `src/shared/` | **190,024** |
| `src/core/` (PID 1) | 117,607 |
| `src/basic/` | 73,979 |
| `src/libsystemd/` | 122,875 |

`src/shared` is **62% larger than PID 1 itself**, and `meson.build:2269` sets
`'link_with' : [libshared]` in the **global `executable_template`** — so every one of the ~167
binaries links the whole thing. `systemd-tmpfiles` is a two-file tool that creates directories; it
links the same object that contains `tpm2-util.c` (13,093 LOC), `dns-packet.c` (3,203),
`dissect-image.c` (6,223), `seccomp-util.c` (2,779) and `format-table.c` (3,308).

Upstream knows: there is a `libshared-unused-symbols` check at `meson.build:3348`. The response to
the smell was a linter, not a seam.

**Consequences that are real, and that dlopen does not fix:**
- No component can be built, tested, versioned, audited, or released independently.
- There are **no stable internal interfaces** — `src/shared` is a free-for-all, so any change can
  touch everything, which is exactly why 9,345 commits/year land as one undividable stream.
- One shared security/CVE surface across 167 binaries.
- You cannot replace one component with an alternative implementation, because the seam doesn't
  exist to replace it at.

### 2.2 Upstream is moving the other way

`meson_options.txt` ships `systemd-multicall-binary`: *"link systemd+systemd-executor as a single
binary."* There are also `link-executor-shared`, `link-systemctl-shared`, `link-networkd-shared`,
`link-timesyncd-shared`, `link-journalctl-shared`, `link-boot-shared`, `link-portabled-shared` —
knobs for how tightly to fuse tools to the shared blob.

This is the real justification for forking rather than filing issues: **it's a direction
disagreement, not a defect.** Upstream is consolidating; we want to delaminate. Nobody is wrong,
and nobody is going to merge the other's patch.

### 2.3 The lever upstream already built for us

`standalone-binaries` — *"comma-separated list of patterns specifying binaries to install as
.standalone"* — currently covers **5** tools (`repart`, `report`, `shutdown`, `sysusers`,
`tmpfiles`). That mechanism is precisely "this tool stands alone, no libshared, no PID 1
coupling." It exists, it works, it's tested, and it's applied to 5 of ~167.

**Extending that from 5 to every leaf tool is the single highest-leverage thing systemE can do**,
and it starts from working upstream code instead of a rewrite.

---

## 3. Proposed thesis for systemE

> **Unbundle, don't rewrite.** Keep every external interface byte-identical; split the internals
> along seams that let each tool be built, versioned, and replaced on its own.

Concretely: the Tier 2 freeze from `FORK_STRATEGY.md` **stays**. D-Bus names, varlink interfaces,
`sd_*` ABI, paths, env vars, unit semantics — untouched. "Do one thing well" is a claim about
binaries and dependency graphs, not a license to break every client on the system. A systemE that
can't run GNOME is a tech demo, not a fork.

This also means the rename work drops to near-zero priority. It was never the point.

---

## 4. Workstreams

### W1 — Measurement harness + CI gate *(do this first)*
"Doesn't follow the Unix philosophy" is an aesthetic claim; a fork needs a **done condition**.
Build a script that emits, per installed binary: linked-in LOC, symbol count, object closure,
dlopen set. Snapshot it at the upstream base. Then a CI gate that **fails when a tool's closure
grows**. Without this, systemE is just vibes with extra steps, and in 18 months it re-accretes.
*Est. 1 day.* Deliverable: `tools/closure-report.py` + baseline JSON + CI job.

### W2 — Delaminate `src/shared` into layers
Split the 190k LOC by actual usage (the W1 data decides the cut lines, not taste). Expected tiers:
`util` (string/fd/path/alloc) → `fmt` (table/json/output) → `sys` (mount/cgroup/image) →
`crypto` (tpm2/openssl/fido2) → `net` (dns/dhcp). Hard rule: **lower layers never call upward.**
Each tool links only the tiers it uses.
*Est. the bulk of the fork — several weeks, incremental, one tier at a time, green tests between.*

### W3 — `standalone-binaries` from 5 → all leaf tools
Mechanical, high-value, low-risk, independently shippable. Each conversion is one small reviewable
PR with a measurable closure delta from W1.
*Est. 2–4 days for the first wave.*

### W4 — Interface contracts between components
Where components now talk through shared C functions, move them to the varlink/D-Bus interfaces
upstream *already defines* (`io.systemd.*` is an existing, documented, versioned IPC surface — we
don't invent a thing). This is what makes "replace one component" real.
*Est. per-component; scope after W1.*

### W5 — Explicitly NOT doing
- **No PID 1 rewrite.** That's how every previous systemd fork died. §1 shows there's no fat to cut.
- **No journal format replacement** (yet). Defensible Unix-philosophy target — binary logs — but it
  breaks `journalctl` compat and every existing archive. Revisit after W1–W3, with data.
- **No Tier 2 interface changes.** Non-negotiable if systemE is to run real systems.

---

## 5. Sequencing against upstream

`FORK_STRATEGY.md` §4 holds, with one amendment: W2 produces **real conflicts** with 9,345
upstream commits/year, unlike a generated rename. So:

- Each tier of W2 lands as its own topic branch and merges to `systemE` separately.
- Sync to upstream majors **before** starting a new tier, never mid-tier.
- Prefer moving files whole over editing in place — `git`'s rename detection survives upstream
  churn far better than scattered hunk edits.
- W1's gate runs on every sync, so an upstream merge that re-couples something fails loudly.

---

## 6. What I need from you

1. **Sign off on "unbundle, don't rewrite"** — or tell me you do want Tier 2 broken, in which case
   the plan changes completely and I'll say so plainly rather than pretend it's the same project.
2. **W1 first, or straight to W3?** W1 is a day with nothing user-visible, and it's what keeps the
   fork honest. W3 ships visible wins immediately but blind. I'd do W1.
3. **Is the journal in scope?** It's the strongest remaining Unix-philosophy target and the most
   compat-destructive. Answer changes the roadmap's back half.
