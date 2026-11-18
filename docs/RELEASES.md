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

## Open question

**These are not the versions the build reports.** `meson.version` says `263~devel`, inherited
from the upstream release this forked at, and `docs/FORK_STRATEGY.md` records the scheme as
tracking upstream's major with a suffix — `263.0E`, then `263.1E`. A systemE 0.1 is a
different claim: that this versions independently of the systemd release it tracks. That is a
reasonable thing to want, and it is also the kind of thing that breaks packaging, since 0.1
sorts below 263 and a distro upgrading from systemd would read it as a downgrade and refuse
without an epoch. Pick one and the other document should change to match.
