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
| 0.2 | Croissant | 🥐 |
| 0.4 | Éclair | ⚡ |
| 0.5 | Financier | 💰 |
| 0.6 | Galette | 🥧 |
| 0.7 | Haricot | 🫘 |
| 0.8 | Isigny | 🧈 |
| 0.9 | Jalousie | |
| 1.0 | Kouign-amann | 🧈🔥 |
| 1.1 | Lunette | |
| 1.2 | Macaron | 🍬 |
| 1.4 | Napoléon | 👑 |
| 1.5 | Opéra | 🎭 |
| 1.6 | Palmier | 🌴 |
| 1.7 | Quiche | |
| 1.8 | Religieuse | ⛪ |
| 1.9 | Sablé | 🍪 |
| 2.0 | Tarte Tatin | 🍎 |

Notes on the ones that need defending: Haricot is a bean rather than a pastry, because H is
hard. Isigny is the Normandy butter. Jalousie is a real pastry, slatted like the blinds it is
named after. Kouign-amann is the butteriest thing anyone has ever baked, which is the right
way to mark a 1.0. Opéra is the chocolate and coffee one.

## Rules

- **No A.** It would have been 0.0, and 0.0 is not a release.
- **No x.3.** Valve rules apply.

## Open questions

Two things to settle before this is load-bearing.

**D.** The letters run B, C, E — D is skipped along with 0.3. But at the other end they run
M, N, O for 1.2, 1.4, 1.5, so 1.3 costs a version and no letter. One of the two is wrong:
either a skipped version burns its letter, in which case 1.4 is Opéra and everything after
shifts up one, or it does not, in which case 0.4 is Déclinaison-of-your-choice and D comes
back. As written the list ends at T either way, so this only changes which name lands on
which number.

**These are not the versions the build reports.** `meson.version` says `263~devel`, inherited
from the upstream release this forked at, and `docs/FORK_STRATEGY.md` records the scheme as
tracking upstream's major with a suffix — `263.0E`, then `263.1E`. A systemE 0.1 is a
different claim: that this versions independently of the systemd release it tracks. That is a
reasonable thing to want, and it is also the kind of thing that breaks packaging if it moves
backwards, since 0.1 sorts below 263. Pick one and the other document should change to match.
