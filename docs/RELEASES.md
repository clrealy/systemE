---
title: systemE Release Codenames
category: Contributing
layout: default
SPDX-License-Identifier: LGPL-2.1-or-later
---

# systemE Release Codenames

French pastries, in alphabetical order.

| version | codename | |
|---|---|---|
| 0.1 | Baguette | 🥖 |
| 0.2 | Dacquoise |  |
| 0.4 | Éclair | ⚡ |
| 0.5 | Financier | 💰 |
| 0.6 | Galette | 🥧 |
| 0.7 | Haricot | 🫘 |
| 0.8 | Isigny | 🧈 |
| 0.9 | Jalousie |  |
| 1.0 | Kouign-amann | 🧈🔥 |
| 1.1 | Lunette |  |
| 1.2 | Macaron | 🍬 |
| 1.4 | Napoléon | 👑 |
| 1.5 | Opéra | 🎭 |
| 1.6 | Palmier | 🌴 |
| 1.7 | Quiche |  |
| 1.8 | Religieuse | ⛪ |
| 1.9 | Sablé | 🍪 |
| 2.0 | Tarte Tatin | 🍎 |

## Rules

- **No version ends in .3.** Valve rules apply.
- **No codename starts with C**, the third letter. The same rule, applied to the other axis.
- **No A.** It would have belonged to 0.0, and 0.0 is not a release.
- Every release takes the next allowed letter. A banned version number does not burn a
  letter and a banned letter does not burn a version number; the two sequences skip
  independently and meet again on the next line.

Eighteen releases, 0.1 to 2.0, B to T.

Notes on the ones that need defending: Dacquoise is a nutty meringue cake. Haricot is a bean
rather than a pastry, because H is hard. Isigny is the Normandy butter. Jalousie is a real
pastry, slatted like the blinds it is named after. Kouign-amann is the butteriest thing
anyone has ever baked, which is the right way to mark a 1.0. Opéra is the chocolate and
coffee one. Croissant was the obvious C and is forbidden, which is the cost of the rule.

## Versions

The codename names a **release**. It is not the number the binary reports, and it cannot be:

- `meson.version` feeds `PROJECT_VERSION`, which is what `ConditionVersion=systemd >= N` in a
  unit file compares against. A systemE reporting `0` would make every third-party unit
  carrying that condition silently fail its check and not start.
- The minor component is passed to `tools/elf2efi.py --version-minor`, which is `type=int`.
  A version like `263.0E` fails the build of `systemd-bootx64.efi` outright:
  `invalid int value: '0E'`.

So the build version is `<upstream major>.<serial>`, all digits, and the release has a name:

| release | build version | reports as |
|---|---|---|
| 0.1 Baguette | `263.1` | `systemd 263 (263.1)` |
| 0.2 Dacquoise | assigned at release, from whichever systemd it tracks then | |

`263.1` sorts above systemd's own `263`, so a distro upgrading from systemd sees an upgrade and
no packaging epoch is needed. `docs/FORK_STRATEGY.md` carries the same rule.

The tree is `263~devel` until 0.1 is cut.
