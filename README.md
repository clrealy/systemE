> [!IMPORTANT]
> Remove this line to confirm you've reviewed this PR before submitting.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/systemE-box-wordmark-dark-blink.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/assets/brand/systemE-box-wordmark-light-blink.svg">
  <img alt="systemE" src="docs/assets/brand/systemE-box-wordmark-dark-blink.svg" width="600">
</picture>

System and Service Manager

systemE is a fork of [systemd](https://systemd.io/), branched at `v262-2499-g7386493f3b`
(263~devel). It is **not endorsed by or affiliated with the systemd project**, and bugs in it
are not theirs to answer.

It ships a reduced set of components, keeps every external interface identical so it remains
a drop-in replacement, and is working towards splitting the internal shared library so a
program links what it uses. What is in scope, what is deliberately frozen, and why, are all
in the [Fork Roadmap](docs/ROADMAP.md).

## Details

Most documentation still describes systemd and applies to systemE unchanged: see
[systemd.io](https://systemd.io/) and the older
[systemd Wiki](https://www.freedesktop.org/wiki/Software/systemd). Where systemE differs,
this repository's own documentation says so.

Information about build requirements is provided in the [README file](README).

To build and install, run `./install.sh`. It stages the result into `dest/` so you can see
what would be installed; `sudo ./install.sh --system` (or `doas`), as root, installs over the
running machine. Read the warning it prints before you do that on a system you care about.

Consult the [NEWS file](NEWS) for what changed in each systemd release this fork has taken.

Please see the [Fork Roadmap](docs/ROADMAP.md) for the plan governing systemE, and the
[Code Map](docs/ARCHITECTURE.md) for this repository's layout and content.

Please see the [Hacking guide](docs/HACKING.md) for how to build systemE and test your
modifications, and the [Contribution Guidelines](docs/CONTRIBUTING.md) for filing issues and
posting pull requests.

When preparing patches, please follow the [Coding Style Guidelines](docs/CODING_STYLE.md).

For support, or to report a security issue, open an issue on this repository. Do not take
systemE problems to systemd's mailing list, IRC or Matrix channels, and do not report them to
systemd's bug bounty programme: those are upstream's, and systemE is not their work.
