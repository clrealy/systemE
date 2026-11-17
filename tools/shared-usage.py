#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Work out which parts of the internal libraries each program actually needs.

closure-report.py measures what a program links: today that is the whole of
libsystemd-shared, for every program. This answers the different question that the
delamination work needs answered first - what would a program link if it linked only
what it uses - by resolving undefined symbols against the library's object files and
closing over the result, which is what a static link would select.

The output is the evidence for where to cut. An object that nearly every program needs
belongs in the bottom tier; one that a handful need belongs in a tier above it.

Usage:
  shared-usage.py BUILDDIR [--json FILE] [--tiers]
"""

import argparse
import collections
import glob
import json
import os
import re
import subprocess
import sys

# Symbol types that count as a definition another object could rely on.
DEFINED = set('TDBRWVSGti')


def nm(path, args):
    try:
        out = subprocess.run(['nm'] + args + [path], check=True,
                             capture_output=True, text=True).stdout
    except subprocess.CalledProcessError:
        return []
    return out.splitlines()


_DEF_CACHE = {}
_UNDEF_CACHE = {}


def defined_symbols(obj):
    if obj in _DEF_CACHE:
        return _DEF_CACHE[obj]
    syms = set()
    for line in nm(obj, ['-g', '--defined-only']):
        parts = line.split()
        if len(parts) >= 3 and parts[-2] in DEFINED:
            syms.add(parts[-1])
    _DEF_CACHE[obj] = syms
    return syms


def undefined_symbols(obj):
    # Called once per root per object without this; with 580 roots that dominated the run.
    if obj in _UNDEF_CACHE:
        return _UNDEF_CACHE[obj]
    syms = set()
    for line in nm(obj, ['-u']):
        parts = line.split()
        if parts and parts[0] == 'U' and len(parts) >= 2:
            syms.add(parts[1])
        elif len(parts) >= 2 and parts[-2] == 'U':
            syms.add(parts[-1])
    _UNDEF_CACHE[obj] = syms
    return syms


def loc(path, cache={}):
    if path not in cache:
        try:
            with open(path, 'rb') as f:
                cache[path] = f.read().count(b'\n')
        except OSError:
            cache[path] = 0
    return cache[path]


# Each internal library, and the source directory its objects came from.
GROUPS = [
    ('shared', 'src/shared/libsystemd-shared-*.a.p', 'src/shared'),
    ('basic', 'src/basic/libbasic.a.p', 'src/basic'),
    ('libsystemd', 'src/libsystemd/libsystemd_static.a.p', 'src/libsystemd'),
]


def index_library(build, srcroot):
    """symbol -> object, object -> (group, source, defined, undefined)."""
    provider = {}
    objects = {}
    for group, pattern, srcdir in GROUPS:
        for d in glob.glob(os.path.join(build, pattern)):
            for obj in sorted(glob.glob(os.path.join(d, '*.o'))):
                base = os.path.basename(obj)
                # acl-util.c.o -> acl-util.c; nested sources keep their flattened name.
                src = os.path.join(srcroot, srcdir, re.sub(r'\.o$', '', base))
                dfn = defined_symbols(obj)
                objects[obj] = {
                    'group': group,
                    'source': src,
                    'loc': loc(src),
                    'undefined': undefined_symbols(obj),
                }
                for sym in dfn:
                    provider.setdefault(sym, obj)
    return provider, objects


# Everything that links the internal libraries is a root, not just the installed programs.
# The NSS and PAM modules, PID 1's libsystemd-core and the public libsystemd/libudev are
# consumers too, and so are the test binaries: they are not installed, but code they use is
# not dead, and src/shared/tests.c exists only for them.
ROOT_TYPES = ('executable', 'shared library', 'shared module')


def _ninja_inputs(build, target):
    try:
        out = subprocess.run(['ninja', '-t', 'query', target], cwd=build,
                             check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError:
        return [], []
    objs, libs, collecting = [], [], False
    for line in out.splitlines():
        t = line.strip()
        if t.startswith('input:'):
            collecting = True
            continue
        if t.startswith(('outputs:', 'validations:')):
            collecting = False
            continue
        if not collecting or not t:
            continue
        t = t.lstrip('| ').strip()
        if t.endswith('.o'):
            objs.append(t)
        elif t.endswith('.symbols'):
            d = os.path.dirname(t)
            if d.endswith('.p'):
                libs.append(d[:-2])
        elif re.search(r'\.(a|so)(\.[0-9.]+)?$', t):
            libs.append(t)
    return objs, libs


def root_objects(build, analysed_dirs):
    """Consumer name -> (object files, is_installed).

    Two different questions need two different root sets, and conflating them gives wrong
    answers to both:

      Is this object dead?   Every build target counts, test binaries included. Code a
                             test uses is not dead, and src/shared/tests.c exists only
                             for tests.
      Which tier does it     Only the shipped consumers count. A small test binary that
      belong in?             needs twenty objects would otherwise make "needed by most
                             consumers" far stricter than it is for the programs we ship.

    A consumer's objects are not always in <output>.p: libsystemd-core-263.so is linked
    from libsystemd-core-263.a, so its .so.p directory is empty and globbing it would make
    PID 1's code look like it consumes nothing. Follow the link graph instead, and stop at
    the libraries being analysed so their objects are not counted as a consumer's own.
    """
    targets = json.loads(subprocess.run(
        ['meson', 'introspect', '--targets', build],
        check=True, capture_output=True, text=True).stdout)
    out = {}
    for t in targets:
        if t['type'] not in ROOT_TYPES:
            continue
        objs, seen = [], set()
        queue = [os.path.relpath(f, build) for f in t.get('filename', [])]
        while queue:
            cur = queue.pop()
            if cur in seen:
                continue
            seen.add(cur)
            o, libs = _ninja_inputs(build, cur)
            objs += o
            for lib in libs:
                if os.path.dirname(lib + '.p') in analysed_dirs or (lib + '.p') in analysed_dirs:
                    continue
                queue.append(lib)
        objs = [os.path.join(build, o) for o in sorted(set(objs))
                if os.path.exists(os.path.join(build, o))]
        if objs:
            out[t['name']] = (objs, bool(t.get('installed')))
    return out


def exported_abi(srcroot):
    """Symbols the public libraries promise to external callers.

    These are roots too: the objects behind them are reachable from outside the tree, so
    nothing here may be judged dead just because no program in the tree calls it.
    """
    syms = set()
    for sym_file in glob.glob(os.path.join(srcroot, 'src', '*', '*.sym')):
        with open(sym_file) as f:
            for line in f:
                line = line.strip().rstrip(';')
                if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', line) and line not in (
                        'global', 'local', 'LIBSYSTEMD', 'LIBUDEV'):
                    syms.add(line)
    return syms


def needed(objs, provider, objects, extra_symbols=frozenset()):
    """Objects a static link would pull in, starting from these objects."""
    want = set(extra_symbols)
    for o in objs:
        want |= undefined_symbols(o)
    selected = set()
    queue = list(want)
    seen = set(want)
    while queue:
        sym = queue.pop()
        owner = provider.get(sym)
        if owner is None or owner in selected:
            continue
        selected.add(owner)
        for dep in objects[owner]['undefined']:
            if dep not in seen:
                seen.add(dep)
                queue.append(dep)
    return selected


def object_key(info):
    """Stable key for an object. Basenames collide across the three libraries."""
    return '%s/%s' % (info['group'], os.path.basename(info['source']))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('build')
    p.add_argument('--json', metavar='FILE')
    p.add_argument('--tiers', action='store_true',
                   help='group objects by how many programs need them')
    args = p.parse_args()

    srcroot = os.path.dirname(os.path.abspath(__file__))
    srcroot = os.path.dirname(srcroot)

    provider, objects = index_library(args.build, srcroot)
    analysed_dirs = set()
    for _, pattern, _ in GROUPS:
        analysed_dirs.update(os.path.relpath(d, args.build)
                             for d in glob.glob(os.path.join(args.build, pattern)))
    progs = root_objects(args.build, analysed_dirs)
    if not progs:
        sys.exit('no installed consumers with objects found in %s' % args.build)
    abi = exported_abi(srcroot)

    total_loc = sum(o['loc'] for o in objects.values())
    print('indexed %d objects (%d lines) across %s'
          % (len(objects), total_loc, ', '.join(g for g, _, _ in GROUPS)))
    shipped = {k: v for k, (v, inst) in progs.items() if inst}
    print('%d consumers: %d shipped, %d build-only (tests); '
          '%d exported ABI symbols held as roots\n'
          % (len(progs), len(shipped), len(progs) - len(shipped), len(abi)))
    abi_objs = needed([], provider, objects, abi)

    users = collections.Counter()      # shipped consumers only: drives tiering
    reached = set(abi_objs)             # any target at all: drives deadness
    per_prog = {}
    for name, (objs, installed) in sorted(progs.items()):
        sel = needed(objs, provider, objects)
        reached |= sel
        if not installed:
            continue
        per_prog[name] = {
            'needed_objs': len(sel),
            'needed_loc': sum(objects[o]['loc'] for o in sel),
        }
        for o in sel:
            users[o] += 1

    rows = sorted(per_prog.items(), key=lambda kv: kv[1]['needed_loc'])
    print('%-32s %9s %9s   %s' % ('program', 'uses_objs', 'uses_loc', 'of library'))
    for name, r in rows[:10]:
        print('%-32s %9d %9d   %5.1f%%'
              % (name, r['needed_objs'], r['needed_loc'],
                 100.0 * r['needed_loc'] / total_loc))
    print('  ...')
    for name, r in rows[-3:]:
        print('%-32s %9d %9d   %5.1f%%'
              % (name, r['needed_objs'], r['needed_loc'],
                 100.0 * r['needed_loc'] / total_loc))
    mean = sum(r['needed_loc'] for _, r in rows) // len(rows)
    print('\nmean actually used: %d lines of %d (%.1f%%)'
          % (mean, total_loc, 100.0 * mean / total_loc))

    if args.tiers:
        n = len(shipped)
        buckets = [
            ('bottom tier: needed by >90% of consumers', lambda c: c > 0.9 * n),
            ('middle tier: needed by 10-90%', lambda c: 0.1 * n < c <= 0.9 * n),
            ('upper tier: needed by <10%', lambda c: 0 < c <= 0.1 * n),
        ]
        print()
        for label, pred in buckets:
            sel = [o for o in objects if pred(users[o]) and o in reached]
            lines = sum(objects[o]['loc'] for o in sel)
            print('%-42s %4d objects %8d lines  %5.1f%%'
                  % (label, len(sel), lines, 100.0 * lines / total_loc))
        testonly = [o for o in objects if users[o] == 0 and o in reached]
        print('%-42s %4d objects %8d lines  %5.1f%%'
              % ('reached only by tests or the exported ABI', len(testonly),
                 sum(objects[o]['loc'] for o in testonly),
                 100.0 * sum(objects[o]['loc'] for o in testonly) / total_loc))
        unreached = [o for o in objects if o not in reached]
        print('%-42s %4d objects %8d lines  %5.1f%%'
              % ('reached by nothing at all, tests included', len(unreached),
                 sum(objects[o]['loc'] for o in unreached),
                 100.0 * sum(objects[o]['loc'] for o in unreached) / total_loc))
        print('\nlargest objects nothing reaches:')
        unused = sorted(unreached, key=lambda o: -objects[o]['loc'])
        for o in unused[:12]:
            print('  %-44s %6d lines  (%s)'
                  % (os.path.basename(objects[o]['source']), objects[o]['loc'],
                     objects[o]['group']))

    if args.json:
        out = {
            'total_objects': len(objects),
            'total_loc': total_loc,
            'consumers': per_prog,
            'shipped_consumers': len(shipped),
            'object_users': {object_key(objects[o]): users[o] for o in objects},
            'object_reached': {object_key(objects[o]): (o in reached) for o in objects},
            'object_loc': {object_key(objects[o]): objects[o]['loc'] for o in objects},
            'object_group': {object_key(objects[o]): objects[o]['group'] for o in objects},
        }
        with open(args.json, 'w') as f:
            json.dump(out, f, indent=1, sort_keys=True)
            f.write('\n')
        print('\nwrote %s' % args.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
