---
title: systemE Rust Plan
category: Contributing
layout: default
SPDX-License-Identifier: LGPL-2.1-or-later
---

# systemE — Rust: the rewrite already started, and it isn't ours

Fourth doc. Decided scope is in `SCOPE_DECISION.md`.

---

## 1. The thing you need to know before deciding anything

**systemd already has Rust in-tree, with a written, enforced policy.**

- **31 `.rs` files, 6,726 LOC**
- `src/rust/systemd-shared/` — a 29-module in-tree crate: `json`, `table`, `x509`, `fileio`,
  `conf_files`, `chase`, `strv`, `cstr`, `errno`, `dlopen`, `kmod`, `keyring`, `tmpfile`,
  `program`, `prelude`, …
- One shipping production tool: **`systemd-keyring-setup`, 1,233 LOC of Rust**
- MSRV 1.85, `bindgen` for FFI, `rustfmt.toml` and `.clippy.toml` in the tree root
- Build integration at `meson.build:379-457` and `2298-2320`

The policy is `docs/CODING_STYLE.md:1046-1103`, and it is strict:

> *"Rust is only used for new leaf components, i.e. programs that nothing else in the tree depends
> on. Existing C code is not ported to Rust for now, and `libsystemd-shared`, `libsystemd`, the NSS
> and PAM modules and everything else other components depend on stay C."*

> *"Only the `core` and `libc` crates are permitted. `std`, `alloc` and any other crate are not,
> hence all Rust code is `#![no_std]`."*

Also enforced: meson only (**no cargo, no crates.io**), C linkage only, `#![no_main]` with the C
side parsing the command line and dispatching verbs, `// SAFETY:` on every `unsafe` block
(clippy-enforced), callbacks must not panic, and `test/test-cli-parity.sh` requires a Rust program
to match its C twin *byte for byte* on stdout, stderr and exit status.

This is a serious, well-designed incremental-Rust program. It is better than what we would invent
from scratch. **So the question is not "should systemE use Rust" — it's "where do we diverge from
upstream's Rust policy, and what does that cost."**

---

## 2. The full rewrite: the honest arithmetic

Post-strip, systemE is **901,333 LOC** of C.

Sustained, reviewed, tested C→Rust at systems level runs ~30–80 LOC/day. Take 50:

> 901,333 / 50 = **18,027 person-days ≈ 82 person-years.** A dedicated team of 5 → **~16 years.**

The rate is the arguable number; the order of magnitude isn't. And upstream's `no_std` constraint
makes it *slower* than normal Rust, not faster — no `Vec`, no `String`, no `Box` (`alloc` is
banned), no `serde`, no `nix`, no `clap`. Every owned type is hand-rolled in the in-tree crate.

Meanwhile upstream lands 1,081 commits/year into the C you're replacing.

**A full rewrite is not a plan, it's a way to fail slowly.** Every from-scratch Rust init has
stalled at exactly this wall. I'm not going to help you walk into it — but the targeted version
below is genuinely strong, and it's the version that gets the actual safety win.

---

## 3. Where Rust actually pays: untrusted-input parsers

Memory safety buys the most where hostile bytes meet privileged code. In the *surviving* tree:

| Target | LOC | Untrusted input | Privilege |
|---|---|---|---|
| **`sd-journal` on-disk format** (`journal-file.c` 5,035 of 21,288 total) | 21,288 | Journal files from anywhere; `journalctl` opens files it didn't write | often root |
| **`sd-json`** | 6,028 | JSON from every varlink peer | varies |
| **`dissect-image.c`** | 6,223 | GPT/LUKS/verity headers in arbitrary disk images | root |
| **`load-fragment.c`** (unit parsing) | 6,903 | Unit files, incl. user units | PID 1 |
| **`udev-rules.c`** + hwdb | 4,807 | Rules + device-supplied strings from hardware | root |
| **`boot.c`** / EFI | 3,597 | ESP contents pre-boot, no ASLR, no mitigations — *and already `no_std`-shaped, Rust's natural home* | firmware |
| **Total** | **~41,943** | | |

~42k LOC, not 901k. That's a finite, fundable program with a real security argument, and the EFI
one is live precisely because we **kept** the boot stack.

---

## 4. The catch, and it's the whole fork again

**Upstream's policy bans every single target in that table.**

`sd-journal` and `sd-json` are in `libsystemd`. `dissect-image.c` is in `libsystemd-shared`.
`load-fragment.c` is PID 1. `udev-rules.c` is depended on. Upstream says: *leaf components only,
existing C is not ported, libsystemd and libsystemd-shared stay C.*

So this is the same shape as every other finding in this fork: **a direction disagreement, not a
defect.** Upstream's policy is defensible — it keeps the core bootstrappable, cargo-free and
reviewable by its existing C maintainers. We just want something else.

**But the cost profile is the inverse of the strip, and this matters:**

| | Strip (W0) | Rust ports |
|---|---|---|
| Upstream commits/yr touching it | **176** (16%) | **533** (44%, the keep-set) |
| Conflict shape | mostly "stay deleted" | permanent, in the hottest files in the tree |
| Reversible | yes | not really |

The strip walks away from the quiet part of the tree. Rust ports plant a flag in the busiest part.
Same fork, opposite risk. Go in knowing that.

---

## 5. A conflict inside our own roadmap

`meson.build:2299` on `rust_executable_template`:

> *"No `.standalone` variants, they always link `libsystemd-shared` dynamically."*

Our `DIVERGENCE_PLAN.md` **W3** is "extend `standalone-binaries` from 5 tools to every leaf tool" —
i.e. tools that *don't* link libshared. **Rust tools, as designed, cannot be standalone.**

So W3 and a Rust push are in direct architectural tension. Three ways out:
1. Fix the template so Rust programs can static-link the crate + a slim libshared tier *(the right
   answer, and it's really a W2/delamination task)*.
2. Keep Rust tools non-standalone and accept two classes of leaf tool.
3. Drop W3.

I'd take (1), but it means **W2 delamination has to land before a serious Rust push** — which
reorders the roadmap. Better to find this now than after writing 10k LOC of Rust.

---

## 6. How to chunk it (you asked for chunks — here's the mechanism)

The safety net already exists in-tree. There are fuzzers for **exactly** the prime targets:
`fuzz-json`, `fuzz-journal-file`, `fuzz-unit-file`, `fuzz-udev-rules`, `fuzz-varlink`,
`fuzz-udev-database`, `fuzz-hwdb`, plus live OSS-Fuzz integration with years of accumulated corpora.

**One chunk = one file.**
1. Port the file to `no_std` Rust behind the *unchanged* C ABI (the frozen 907 `sd_*` symbols never
   move — callers can't tell).
2. Build both implementations.
3. **Differential-fuzz C vs Rust on the same corpus.** Any input where they disagree on output or
   error is a bug in the port, found before merge. This is the whole reason the targeted approach is
   safe and the big-bang rewrite isn't.
4. Extend `test-cli-parity.sh`'s philosophy from CLI parity to **format parity**.
5. Green → merge the chunk. Red → revert the chunk, not the program.

Each chunk is independently shippable, independently revertable, and merges on its own branch. This
is also what keeps the upstream conflict cost survivable: a chunk that becomes too painful to rebase
gets dropped without taking the rest with it.

Suggested order (cheapest proof first): **`sd-json` → `journal-file` → `dissect-image` →
`udev-rules` → EFI**. `load-fragment.c`/PID 1 last, or never.

---

## 7. What I'd refuse to do

- **PID 1 in Rust.** `src/core` is syscall orchestration — fork/exec, signals, cgroups,
  namespaces. All of it is `unsafe` FFI anyway, so the safety win is *smallest* exactly there,
  while the blast radius is total. It's the glamour target and the worst value in the tree.
- **A big-bang rewrite.** §2.
- **Allowing `std` + crates.io without you explicitly accepting the costs** — supply chain in a
  package that must build during distro bootstrap, vendoring pain for packagers, initrd binary
  size, and losing code-sharing with upstream's `systemd_shared` crate. It'd be ~2–3× faster to
  write. It's a real trade, not a free win, and it's yours to make.

---

## 8. Three decisions

1. **Policy:** follow upstream's (leaf-only, no ports), or allow porting untrusted-input parsers
   behind the frozen C ABI?
2. **`no_std` + `core`/`libc` only, or `std` + vetted crates?**
3. **Sequencing:** W2 delamination before the Rust push (resolves §5 cleanly), or Rust first and
   accept two classes of leaf tool?
