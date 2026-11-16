# SPDX-License-Identifier: LGPL-2.1-or-later

bashcompletiondir = get_option('bashcompletiondir')
if bashcompletiondir == 'no'
        subdir_done()
elif bashcompletiondir == ''
        bash_completion = dependency('bash-completion', required : false)
        if bash_completion.found()
                bashcompletiondir = bash_completion.get_variable(pkgconfig : 'completionsdir')
        else
                bashcompletiondir = datadir / 'bash-completion/completions'
        endif
endif

custom_target(
        input : 'systemctl.in',
        output : 'systemctl',
        command : [jinja2_cmdline, '@INPUT@', '@OUTPUT@'],
        install : true,
        install_dir : bashcompletiondir)

if want_ukify
        custom_target(
                'ukify-bash-completion',
                input : ukify,
                output : 'ukify',
                command : [python, '@INPUT@', 'completion', 'bash'],
                capture : true,
                install : true,
                install_dir : bashcompletiondir)
endif

foreach item : [
        ['bootctl',             ''],
        ['busctl',              ''],
        ['coredumpctl',         'ENABLE_COREDUMP'],
        ['hostnamectl',         'ENABLE_HOSTNAMED'],
        ['journalctl',          ''],
        ['kernel-install',      'ENABLE_KERNEL_INSTALL'],
        ['localectl',           'ENABLE_LOCALED'],
        ['loginctl',            'ENABLE_LOGIND'],
        ['oomctl',              'ENABLE_OOMD'],
        ['ptyctl',              ''],
        ['run0',                ''],
        ['storagectl',          'ENABLE_STORAGE'],
        ['systemd-analyze',     ''],
        ['systemd-cat',         ''],
        ['systemd-cgls',        ''],
        ['systemd-cgtop',       ''],
        ['systemd-creds',       ''],
        ['systemd-cryptenroll', 'HAVE_LIBCRYPTSETUP'],
        ['systemd-delta',       ''],
        ['systemd-detect-virt', ''],
        ['systemd-dissect',     'HAVE_BLKID'],
        ['systemd-hwdb',        'ENABLE_HWDB'],
        ['systemd-id128',       ''],
        ['systemd-manifest',    ''],
        ['systemd-notify',      ''],
        ['systemd-nspawn',      'ENABLE_NSPAWN'],
        ['systemd-path',        ''],
        ['systemd-pty-forward', ''],
        ['systemd-run',         ''],
        ['systemd-sysinstall',  'ENABLE_SYSINSTALL'],
        ['systemd-vpick',       ''],
        ['timedatectl',         'ENABLE_TIMEDATED'],
        ['udevadm',             ''],
        ['varlinkctl',          ''],
]

        if item[1] == '' or conf.get(item[1]) == 1
                install_data(item[0],
                             install_dir : bashcompletiondir)
        endif
endforeach
