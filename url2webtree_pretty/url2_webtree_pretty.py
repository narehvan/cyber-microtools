#!/usr/bin/env python3
"""
url2_webtree_pretty.py - turn a flat list of discovered URLs into an indented tree.

Accepts (auto-detected, mix freely):
    - a plain list of URLs, one per line        (e.g. feroxbuster --silent)
    - feroxbuster JSON lines                     (--json; keeps status codes)
    - feroxbuster / gobuster default text output (best-effort status + redirect)
    - your own hand-written list

Usage:
    feroxbuster -u http://10.0.0.5/ -w big.txt --silent | python3 url2_webtree_pretty.py
    feroxbuster -u http://10.0.0.5/ -w big.txt --json    | python3 url2_webtree_pretty.py
    python3 url2_webtree_pretty.py results.txt                 # one or more files
    python3 url2_webtree_pretty.py *.txt > tree.txt            # stitch several gobuster runs
    python3 url2_webtree_pretty.py --full results.txt          # print full URLs, not just names
    python3 url2_webtree_pretty.py --no-annotate results.txt   # hide [status, redirect] tags

Example:
    http://10.10.10.5/dashboard.php
    http://10.10.10.5/static/style.css
    http://10.10.10.5/static/myscripts.js
    http://10.10.10.5/ourteam.php
    http://10.10.10.5/
    http://10.10.10.5/backup
    http://10.10.10.5/backup/README.txt

    becomes

    http://10.10.10.5/
    ├── backup/
    │   └── README.txt
    ├── static/  [implied]
    │   ├── myscripts.js
    │   └── style.css
    ├── dashboard.php
    └── ourteam.php

"""

from __future__ import annotations

import sys
import re
import json
import argparse
import os
from urllib.parse import urlsplit

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
URL_RE = re.compile(r"https?://[^\s'\"]+")
STATUS_LEADING_RE = re.compile(r"^\s*(\d{3})\b")          # feroxbuster text
STATUS_LABELED_RE = re.compile(r"Status:\s*(\d{3})")       # gobuster text
REDIRECT_RE = re.compile(r"(?:=>|-->)\s*([^\s\]\)\"',]+)")  # ferox "=>", gobuster "-->"

SHOW_ANNOTATIONS = True

__version__ = "0.0.1"   # version of this script
current_script_name = os.path.basename(__file__)  # shown in usage, help and error messages

class Node:
    __slots__ = ("name", "children", "is_dir", "status", "redirect", "is_discovered")

    name: str
    children: dict[str, "Node"]
    is_dir: bool
    status: int | None
    redirect: str | None
    is_discovered: bool

    def __init__(self, name):
        self.name = name
        self.children = {}
        self.is_dir = False
        self.status = None
        self.redirect = None
        self.is_discovered = False  # True if this exact path was a found entry


def parse_line(line):
    """Return (url, status, redirect) for one input line, or None to skip it."""
    line = ANSI_ESCAPE_RE.sub("", line).strip()
    if not line or line.startswith("#"):
        return None

    # "feroxbuster --json" emits one JSON object per line
    if line[0] == "{":
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return None
        if record.get("type") not in (None, "response"):
            return None  # skip config/statistics records
        url = record.get("url")
        if not url:
            return None
        return url, record.get("status"), record.get("location") or None

    # Otherwise: find a URL anywhere on the line, plus optional status/redirect
    url_match = URL_RE.search(line)
    if not url_match:
        return None
    url = url_match.group(0).rstrip(",")

    status = None
    status_match = STATUS_LEADING_RE.search(line) or STATUS_LABELED_RE.search(line)
    if status_match:
        status = int(status_match.group(1))

    redirect = None
    redirect_match = REDIRECT_RE.search(line)
    if redirect_match and redirect_match.group(1) != url:
        redirect = redirect_match.group(1)

    return url, status, redirect


def normalize_redirect(redirect, host):
    """Trim a redirect target to a path when it points at the same host."""
    if redirect.startswith("http"):
        parsed_redirect = urlsplit(redirect)
        redirect_tail = parsed_redirect.path or "/"
        if parsed_redirect.query:
            redirect_tail += "?" + parsed_redirect.query
        if f"{parsed_redirect.scheme}://{parsed_redirect.netloc}" == host:
            return redirect_tail
    return redirect


def add_url(host_trees, url, status, redirect):
    url_parts = urlsplit(url)
    host = f"{url_parts.scheme}://{url_parts.netloc}"
    path = url_parts.path or "/"
    is_dir = path.endswith("/")
    segments = [segment for segment in path.split("/") if segment]

    host_node = host_trees.get(host)
    if host_node is None:
        host_node = Node(host)
        host_node.is_dir = True
        host_trees[host] = host_node

    node = host_node
    for index, segment in enumerate(segments):
        node = node.children.setdefault(segment, Node(segment))
        if index < len(segments) - 1:
            node.is_dir = True  # anything with something beneath it is a dir

    node.is_discovered = True
    if is_dir:
        node.is_dir = True
    if status is not None:
        node.status = status
    if redirect:
        node.redirect = normalize_redirect(redirect, host)


def annotate(node):
    if not SHOW_ANNOTATIONS:
        return ""
    annotation_parts = []
    if node.status is not None:
        annotation_parts.append(str(node.status))
    if node.redirect:
        annotation_parts.append(f"→ {node.redirect}")
    if not node.is_discovered:
        annotation_parts.append("implied")
    return "  [" + ", ".join(annotation_parts) + "]" if annotation_parts else ""


def sort_key(child_entry):
    name, child = child_entry
    is_directory = child.is_dir or bool(child.children)
    return (0 if is_directory else 1, name.lower())  # dirs first, then files


def render(node, prefix, is_last, parent_url, use_full_urls, output_lines):
    is_directory = node.is_dir or bool(node.children)
    segment = node.name + ("/" if is_directory and not node.name.endswith("/") else "")
    node_url = parent_url.rstrip("/") + "/" + segment
    connector = "└── " if is_last else "├── "
    label = node_url if use_full_urls else segment
    output_lines.append(prefix + connector + label + annotate(node))

    child_prefix = "    " if is_last else "│   "
    children = sorted(node.children.items(), key=sort_key)
    for index, (_, child) in enumerate(children):
        is_last_child = index == len(children) - 1
        render(child, prefix + child_prefix, is_last_child, node_url, use_full_urls, output_lines)


def render_host(host_node, use_full_urls):
    label = host_node.name.rstrip("/") + "/"
    output_lines = [label + annotate(host_node)]
    children = sorted(host_node.children.items(), key=sort_key)
    for index, (_, child) in enumerate(children):
        is_last_child = index == len(children) - 1
        render(child, "", is_last_child, host_node.name, use_full_urls, output_lines)
    return output_lines


def main():
    parser = argparse.ArgumentParser(description="Build an indented tree from a flat list of discovered URLs.")
    parser.add_argument("files", nargs="*", help="input files (default: read stdin)")
    parser.add_argument("--full", action="store_true", help="print full URLs instead of path segments")
    parser.add_argument("--no-annotate", action="store_true", help="hide the [status, redirect] annotations")
    parser.add_argument("-V", "--version", action="version", version=f"{current_script_name} {__version__}",help="show version information and exit")
    args = parser.parse_args()

    global SHOW_ANNOTATIONS
    SHOW_ANNOTATIONS = not args.no_annotate

    lines = []
    if args.files:
        for file_path in args.files:
            try:
                with open(file_path, encoding="utf-8", errors="replace") as file_handle:
                    lines.extend(file_handle)
            except OSError as error:
                print(f"{current_script_name}: cannot read {file_path}: {error}", file=sys.stderr)
    else:
        # read from stdin if no files are provided. used for piping output from other tools like feroxbuster or gobuster
        lines = sys.stdin.readlines()

    host_trees = {}
    entry_count = 0
    for line in lines:
        parsed_entry = parse_line(line)
        if not parsed_entry:
            continue
        add_url(host_trees, *parsed_entry)
        entry_count += 1

    if not host_trees:
        print(f"{current_script_name}: no URLs found in input.", file=sys.stderr)
        sys.exit(1)

    for index, host in enumerate(sorted(host_trees)):
        if index:
            print()
        print("\n".join(render_host(host_trees[host], args.full)))

    print(f"\n{current_script_name}: {entry_count} entries across {len(host_trees)} host(s).\n", file=sys.stderr)


if __name__ == "__main__":
    main()