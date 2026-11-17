# SPDX-License-Identifier: LGPL-2.1-or-later

# The container .link files configure udev's handling of the host side of the virtual Ethernet
# links that systemd-nspawn creates for --network-veth, --network-bridge and --network-zone.
# They are udev's and nspawn's, not systemd-networkd's, so they are installed unconditionally:
# without them 99-default.link would match instead and apply MACAddressPolicy=persistent to
# container interfaces.
install_data(
        '80-container-vb.link',
        '80-container-ve.link',
        '80-container-vz.link',
        '99-default.link',
        install_dir : networkdir)

if install_sysconfdir
        install_emptydir(sysconfdir / 'systemd/network')
endif
