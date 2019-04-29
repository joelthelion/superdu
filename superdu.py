#!/usr/bin/env python3
""" A better way to inspect filesystem usage.
    Look directly in the tree where the space is being taken."""

import os
import re
from subprocess import Popen, PIPE
from argparse import ArgumentParser
from operator import itemgetter


def sizeof_fmt(num, suffix=''):
    """ Output human readable sizes. Compatible with du """
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)


def parseSize(size):
    """ Parse human readable strings. Has to be compatible with du"""
    units = {"": 1, "K": 1024, "M": 1024**2,
             "G": 1024**3, "T": 1024**4, "P": 1024**5}
    number, unit = re.match("([0-9]*)(.*)", size.strip()).groups()
    return int(float(number)*units[unit])


class RootPruneException(Exception):
    pass


def prune_from_tree(dir_, dirs):
    """ Add size back to closest parent still in tree,
        then remove node from the tree """
    value = dirs[dir_]
    to_prune = dir_
    while True:
        par = os.path.dirname(dir_)
        if par == dir_:
            # refuse to prune the root
            raise RootPruneException
        if par in dirs:
            dirs[par] += value
            break
        else:
            pass
        dir_ = par
    del dirs[to_prune]


def remove_from_parents(dir_, dirs):
    """ Remove size of leaf items from all ancestors"""
    value = dirs[dir_]
    while True:
        par = os.path.dirname(dir_)
        if par == dir_:
            # FS root
            break
        if par in dirs:
            dirs[par] -= value
        else:
            break
        dir_ = par


def compute_branches(dirs):
    """ Extract non-leaf directories """
    branches = set()
    for dir_ in dirs:
        par = os.path.dirname(dir_)
        if par in dirs and par != dir_:
            branches.add(par)
    return branches


def process_du_output(tuples, thresh):
    """ Intelligently prune and merge du output, using a threshold of
        thresh kilobytes """
    dirs = {os.path.abspath(path): int(size) for size, path in tuples}

    # populate the tree and keep only size not accounted for by children
    for dir_ in sorted(dirs, key=len, reverse=True):
        remove_from_parents(dir_, dirs)

    # keep only n largest items. Add removed size back into the parent
    processed = set()
    while True:
        unprocessed = [d for d in dirs if d not in processed]
        if not unprocessed:
            break
        branches = compute_branches(unprocessed)
        for dir_ in unprocessed:
            # exclude nodes with unprocessed children
            if dir_ in branches:
                continue
            processed.add(dir_)
            if dirs[dir_] < thresh:
                try:
                    prune_from_tree(dir_, dirs)
                except RootPruneException:
                    # Refusing to prune the root node
                    pass
    return dirs

def read_file(filename):
    """ Read du output from a file """
    tuples = [l.rstrip("\n").split("\t") for l in open(args.f)]
    return tuples

def run_du(options):
    """ Run 'du' and returned parsed results """
    output, err = Popen(["du"]+options+[args.path],
                        stdout=PIPE).communicate()
    output = output.decode("utf-8")
    tuples = [l.split("\t") for l in output.splitlines()]
    return tuples

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-x",
                        help="Skip directories on different filesystems",
                        action="store_true")
    parser.add_argument("-t",
                        type=str, default="100M",
                        help="Exclude entries smaller than size (eg. 34M)")
    parser.add_argument("-f",
                        type=str,
                        help="Use a file with du output instead of calling du")
    parser.add_argument("path", default=".", nargs="?")
    args = parser.parse_args()
    if args.f is not None:
        tuples = read_file(args.f)
    else:
        options = []
        if args.x:
            options.append("-x")
        options.extend(["-t", args.t])
        tuples = run_du(options)
    threshold = parseSize(args.t)/1024

    dirs = process_du_output(tuples, thresh=threshold)

    # Format output
    sorted_dirs = sorted(((d,s) for d, s in dirs.items() if s>=threshold),
            key=itemgetter(1))
    max_width = max(len(d) for d,s in sorted_dirs)
    width = min(max_width+5, 150)
    print(width)
    for dir_, size in sorted_dirs:
        print(("{:_<"+str(width)+"} {}").format(dir_+' ', sizeof_fmt(size*1024)))
