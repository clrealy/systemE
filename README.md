
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/systemE-box-wordmark-dark-blink.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/assets/brand/systemE-box-wordmark-light-blink.svg">
  <img alt="systemE" src="docs/assets/brand/systemE-box-wordmark-dark-blink.svg" width="600">
</picture>

System and Service Manager

## Details

Most documentation is available on [systemd's website](https://systemd.io/).

Assorted, older, general information about systemd can be found in the [systemd Wiki](https://www.freedesktop.org/wiki/Software/systemd).

Information about build requirements is provided in the [README file](README).

Consult our [NEWS file](NEWS) for information about what's new in the most recent systemd versions.

To build and install, run `./install.sh`. It stages the result into `dest/` so you can see what would be installed; `sudo ./install.sh --system` (or `doas`), as root, installs over the running machine. Read the warning it prints before you do that on a system you care about.

Please see the [systemE Fork Roadmap](docs/ROADMAP.md) for the plan governing this fork, its decided scope, and what is deliberately frozen.

Please see the [Code Map](docs/ARCHITECTURE.md) for information about this repository's layout and content.

Please see the [Hacking guide](docs/HACKING.md) for information on how to hack on systemd and test your modifications.

Please see our [Contribution Guidelines](docs/CONTRIBUTING.md) for more information about filing GitHub Issues and posting GitHub Pull Requests.

When preparing patches for systemd, please follow our [Coding Style Guidelines](docs/CODING_STYLE.md).

If you are looking for support, please contact our [mailing list](https://lists.freedesktop.org/mailman/listinfo/systemd-devel), join our [IRC channel #systemd on libera.chat](https://web.libera.chat/#systemd) or [Matrix channel](https://matrix.to/#/#systemd-project:matrix.org)

Stable branches with backported patches are available in the [stable repo](https://github.com/systemd/systemd-stable).

We have a security bug bounty program sponsored by the [Sovereign Tech Fund](https://www.sovereigntechfund.de/) hosted on [YesWeHack](https://yeswehack.com/programs/systemd-bug-bounty-program)

Repositories with distribution packages built from git main are [available on OBS](https://software.opensuse.org//download.html?project=system%3Asystemd&package=systemd),
and also repositories with [packages built from the latest stable release](https://software.opensuse.org//download.html?project=system%3Asystemd%3Astable&package=systemd)
