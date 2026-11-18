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
| 0.4 | Dacquoise |  |
| 0.5 | Éclair | ⚡ |
| 0.6 | Financier | 💰 |
| 0.7 | Galette | 🥧 |
| 0.8 | Haricot | 🫘 |
| 0.9 | Isigny | 🧈 |
| 1.0 | Jalousie |  |
| 1.1 | Kouign-amann | 🧈🔥 |
| 1.2 | Lunette |  |
| 1.4 | Macaron | 🍬 |
| 1.5 | Napoléon | 👑 |
| 1.6 | Opéra | 🎭 |
| 1.7 | Palmier | 🌴 |
| 1.8 | Quiche |  |
| 1.9 | Religieuse | ⛪ |
| 2.0 | Sablé | 🍪 |
| 2.1 | Tarte Tatin | 🍎 |

Notes on the ones that need defending: Dacquoise is a nutty meringue cake. Haricot is a bean
rather than a pastry, because H is hard. Isigny is the Normandy butter. Jalousie is a real
pastry, slatted like the blinds it is named after. Kouign-amann is the butteriest thing
anyone has ever baked. Opéra is the chocolate and coffee one.

## Rules

- **No A.** It would have been 0.0, and 0.0 is not a release.
- **No x.3.** Valve rules apply.
- A skipped version costs a version number, not a letter: 0.3 and 1.3 do not exist, and the
  names carry straight on across the gap.

## Open question

**These are not the versions the build reports.** `meson.version` says `263~devel`, inherited
from the upstream release this forked at, and `docs/FORK_STRATEGY.md` records the scheme as
tracking upstream's major with a suffix — `263.0E`, then `263.1E`. A systemE 0.1 is a
different claim: that this versions independently of the systemd release it tracks. That is a
reasonable thing to want, and it is also the kind of thing that breaks packaging, since 0.1
sorts below 263 and a distro upgrading from systemd would read it as a downgrade and refuse
without an epoch. Pick one and the other document should change to match.
