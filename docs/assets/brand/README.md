# systemE brand assets

Replaces the systemd logo, which systemE must not use: the fork is not endorsed by or
affiliated with the systemd project. See `docs/FORK_STRATEGY.md` §3.

## The box set

The current marks. `-dark` sits on `#0e0c14`, `-light` on white, so a pair of them
switches with the reader's theme.

| file | what it is |
|---|---|
| `systemE-box-wordmark-dark.svg` / `-light.svg` | mark and name, 1507x500. The README banner |
| `systemE-box-wordmark-*-blink.svg` | the same, with the box blinking like a cursor |
| `systemE-box-dark.svg` / `-light.svg` | the box on its own, 1200x1200. For the GitHub avatar |
| `systemE-box-*-blink.svg` | the same, blinking |
| `*.png` | 1507x500 and 1200x1200 exports of the four static marks |

The blink is SMIL: `<animate>` on opacity, a 1.06s cycle. It animates in a browser that
renders the file directly. Whether it animates inside a README depends on how the host
serves repository SVGs, so the static pair is what the banner uses.

Setting the GitHub avatar is not something the repository can do: upload
`systemE-box-dark.png` by hand under the account or organisation's profile settings.

## The earlier gear set

Kept because the docs site header still uses it, and it is the fuller lockup.

| file | what it is |
|---|---|
| `systemE-logo.svg` / `.png` | the mark on its own, 1200x1200 |
| `systemE-wordmark.svg` / `.png` | mark and name together, 1800x500. Used in `README.md` and the docs site header |
| `systemE-typed.svg` / `.png` / `.gif` | terminal-styled wordmark, dark background. The GIF animates |
| `systemE-typed-light.svg` / `.png` | the same on a light background |
| `systemE-prompt.svg` / `.png` | prompt-styled mark, 1200x1200, with a `-dark` variant |
| `systemE-prompt-blink.svg` | as above, with an animated cursor. A `-dark` variant too |
| `systemE-prompt-wordmark.svg` / `.png` | prompt-styled mark and name together |

Palette: `#0e0c14` background, `#f5f0e8` text, `#ff7a2e` accent on the lockup, `#1ee81e`
on the terminal-styled variants.

The SVGs are self-contained: no scripts, no external references, no embedded raster images.
Prefer them over the PNGs, which are exports for contexts that cannot render SVG. Note
`systemE-logo.png` is 742K and the SVG supersedes it everywhere that can take one.
