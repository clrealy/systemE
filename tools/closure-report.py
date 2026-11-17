#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Report what each installed program actually drags in, and fail when that grows.

systemE's premise is that a tool should link what it uses and no more. That is only
enforceable if it is measured, so this walks the real link graph for every installed
executable and records, per program:

  own_loc        lines of the program's own sources
  libs           the libraries it links
  closure_objs   object files in its link closure
  closure_loc    lines of source behind those objects
  dlopens        features its closure may dlopen at runtime
  size           size of the built binary in bytes

The link edges come from ninja, which is the build's own account of what links what,
rather than from reading meson.build files. Source lists come from meson introspection.

Usage:
  closure-report.py BUILDDIR --write-baseline FILE   record the current state
  closure-report.py BUILDDIR --baseline FILE         compare, exit 1 if anything grew
  closure-report.py BUILDDIR [--top N]               human-readable summary
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout


def loc(path, cache={}):
    if path not in cache:
        try:
            with open(path, 'rb') as f:
                cache[path] = f.read().count(b'\n')
        except OSError:
            cache[path] = 0
    return cache[path]


def introspect_targets(build):
    targets = json.loads(run(['meson', 'introspect', '--targets', build]))
    by_output = {}
    for t in targets:
        srcs = []
        for ts in t.get('target_sources', []):
            srcs += [s for s in ts.get('sources', []) if s.endswith(('.c', '.h', '.rs'))]
        info = {
            'name': t['name'],
            'type': t['type'],
            'install': bool(t.get('installed')),
            'sources': sorted(set(srcs)),
        }
        for fn in t.get('filename', []):
            by_output[os.path.relpath(fn, build)] = info
    return by_output


QUERY_LIB = re.compile(r'\.(a|so)(\.[0-9.]+)?$')

# Options that only move files around do not change what gets linked, so they are left out
# of the fingerprint: otherwise a different --prefix would look like a closure regression.
PATH_OPTION = re.compile(r'(dir|dirs|path|prefix|root)$')


def config_fingerprint(build):
    """The build options that decide what is compiled and linked.

    A closure baseline is only comparable against the same configuration. With tpm2 or
    libfdisk available a program legitimately links more, and without this the gate would
    report that as a regression.
    """
    opts = json.loads(run(['meson', 'introspect', '--buildoptions', build]))
    fp = {}
    for o in opts:
        name = o['name']
        if PATH_OPTION.search(name) or o.get('section') == 'directory':
            continue
        fp[name] = o['value']
    return fp


def query_inputs(build, target):
    """Direct inputs of a ninja target: (objects, library outputs)."""
    try:
        out = run(['ninja', '-t', 'query', target], cwd=build)
    except subprocess.CalledProcessError:
        return [], []
    objs, libs = [], []
    collecting = False
    for line in out.splitlines():
        s = line.strip()
        if s.startswith('input:'):
            collecting = True
            continue
        if s.startswith(('outputs:', 'validations:')):
            collecting = False
            continue
        if not collecting or not s:
            continue
        s = s.lstrip('| ').strip()
        if s.endswith('.o'):
            objs.append(s)
        elif s.endswith('.symbols'):
            # A shared library is linked via its .symbols stamp: strip the .p directory.
            d = os.path.dirname(s)
            if d.endswith('.p'):
                libs.append(d[:-2])
        elif QUERY_LIB.search(s):
            libs.append(s)
    return objs, libs


_CLOSURE_CACHE = {}


def closure(build, entry, by_output):
    """Transitive link closure of a target, memoised.

    Every program links libsystemd-shared, so without the cache its closure would be
    recomputed once per program and the run would take a minute instead of a second.
    """
    if entry in _CLOSURE_CACHE:
        return _CLOSURE_CACHE[entry]
    # Reserve the slot first: a cyclic link graph would otherwise recurse forever.
    _CLOSURE_CACHE[entry] = (set(), [])
    objs, libs = query_inputs(build, entry)
    objs = set(objs)
    all_libs = set(libs)
    for lib in libs:
        sub_objs, sub_libs = closure(build, lib, by_output)
        objs.update(sub_objs)
        all_libs.update(sub_libs)
    result = (objs, sorted(all_libs))
    _CLOSURE_CACHE[entry] = result
    return result


_DLOPEN_CACHE = {}


def dlopens(path):
    """Features the binary or its libraries may dlopen, from .note.dlopen."""
    if path in _DLOPEN_CACHE:
        return _DLOPEN_CACHE[path]
    _DLOPEN_CACHE[path] = _dlopens_uncached(path)
    return _DLOPEN_CACHE[path]


def _dlopens_uncached(path):
    # objcopy seeks in its output, so it cannot write to a pipe: /dev/stdout yields
    # nothing at all. It needs a real file.
    with tempfile.NamedTemporaryFile(suffix='.note') as tmp:
        try:
            subprocess.run(['objcopy', '-O', 'binary', '--only-section=.note.dlopen',
                            path, tmp.name], check=True, capture_output=True)
            with open(tmp.name, 'rb') as f:
                raw = f.read()
        except (subprocess.CalledProcessError, OSError):
            return []
    found = set()
    for m in re.finditer(rb'\[\{.*?\}\]', raw, re.S):
        try:
            for entry in json.loads(m.group(0).decode('utf-8')):
                if 'feature' in entry:
                    found.add(entry['feature'])
        except (ValueError, UnicodeDecodeError):
            continue
    return sorted(found)


def collect(build):
    by_output = introspect_targets(build)
    report = {'__config__': config_fingerprint(build)}
    for out, info in sorted(by_output.items()):
        if info['type'] != 'executable' or not info['install']:
            continue
        objs, libs = closure(build, out, by_output)
        srcs = set(info['sources'])
        for lib in libs:
            if lib in by_output:
                srcs.update(by_output[lib]['sources'])
        binpath = os.path.join(build, out)
        dl = set(dlopens(binpath))
        for lib in libs:
            dl.update(dlopens(os.path.join(build, lib)))
        report[info['name']] = {
            'own_loc': sum(loc(s) for s in info['sources']),
            'libs': [os.path.basename(l) for l in libs],
            'closure_objs': len(objs),
            'closure_loc': sum(loc(s) for s in srcs),
            'dlopens': sorted(dl),
            'size': os.path.getsize(binpath) if os.path.exists(binpath) else 0,
        }
    return report


# Growth in these is what the gate exists to prevent.
GUARDED = ('closure_loc', 'closure_objs')


def compare(baseline, current):
    regressions, notes = [], []
    base_cfg = baseline.get('__config__')
    cur_cfg = current.get('__config__')
    if base_cfg is not None and base_cfg != cur_cfg:
        differing = sorted(k for k in set(base_cfg) | set(cur_cfg)
                           if base_cfg.get(k) != cur_cfg.get(k))
        return None, ['%s: %r -> %r' % (k, base_cfg.get(k), cur_cfg.get(k))
                      for k in differing]
    for name, cur in sorted(current.items()):
        if name == '__config__':
            continue
        base = baseline.get(name)
        if base is None:
            notes.append('new program %s (closure %d lines, %d objects)'
                         % (name, cur['closure_loc'], cur['closure_objs']))
            continue
        for key in GUARDED:
            if cur[key] > base[key]:
                regressions.append('%s: %s grew %d -> %d (+%d)'
                                   % (name, key, base[key], cur[key], cur[key] - base[key]))
        gained = set(cur['libs']) - set(base['libs'])
        if gained:
            regressions.append('%s: now links %s' % (name, ', '.join(sorted(gained))))
        gained_dl = set(cur['dlopens']) - set(base['dlopens'])
        if gained_dl:
            regressions.append('%s: may now dlopen %s' % (name, ', '.join(sorted(gained_dl))))
    for name in sorted(set(baseline) - set(current) - {'__config__'}):
        notes.append('program %s is gone' % name)
    return regressions, notes


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('build', help='configured build directory')
    p.add_argument('--write-baseline', metavar='FILE')
    p.add_argument('--baseline', metavar='FILE')
    p.add_argument('--top', type=int, default=15)
    args = p.parse_args()

    if not os.path.exists(os.path.join(args.build, 'build.ninja')):
        sys.exit('%s is not a configured build directory' % args.build)

    current = collect(args.build)
    if not current:
        sys.exit('no installed executables found in %s' % args.build)

    if args.write_baseline:
        with open(args.write_baseline, 'w') as f:
            json.dump(current, f, indent=1, sort_keys=True)
            f.write('\n')
        print('wrote baseline for %d programs to %s'
              % (len(current) - 1, args.write_baseline))
        return 0

    if args.baseline:
        with open(args.baseline) as f:
            baseline = json.load(f)
        regressions, notes = compare(baseline, current)
        if regressions is None:
            print('The baseline was recorded for a different build configuration, so the\n'
                  'closures are not comparable. These options differ:\n', file=sys.stderr)
            for n in notes:
                print('  %s' % n, file=sys.stderr)
            print('\nConfigure the same way, or re-record with --write-baseline.',
                  file=sys.stderr)
            return 1
        for n in notes:
            print('note: %s' % n)
        if regressions:
            print('\nDependency closures grew:\n', file=sys.stderr)
            for r in regressions:
                print('  %s' % r, file=sys.stderr)
            print('\nsystemE only shrinks. Either link less, or update the baseline\n'
                  'deliberately with --write-baseline and say why in the commit.',
                  file=sys.stderr)
            return 1
        print('%d programs checked, no closure grew.' % (len(current) - 1))
        return 0

    rows = sorted(((k, v) for k, v in current.items() if k != '__config__'),
                  key=lambda kv: -kv[1]['closure_loc'])
    print('%-34s %>9s %9s %7s %9s' .replace('>', '') % ('program', 'own_loc', 'clos_loc', 'objs', 'size'))
    for name, r in rows[:args.top]:
        print('%-34s %9d %9d %7d %9d'
              % (name, r['own_loc'], r['closure_loc'], r['closure_objs'], r['size']))
    tot = sum(r['closure_loc'] for _, r in rows)
    print('\n%d installed programs, mean closure %d lines'
          % (len(rows), tot // len(rows)))
    worst = max(rows, key=lambda kv: kv[1]['closure_loc'] - kv[1]['own_loc'])
    print('widest gap: %s carries %d lines of closure for %d lines of its own'
          % (worst[0], worst[1]['closure_loc'], worst[1]['own_loc']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
