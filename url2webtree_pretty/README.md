# url2_webtree_pretty.py

Turns a flat list of discovered URLs into an indented tree. Works standalone on any tool's output.

Here is an example of the output generated:
```
Input file:
    http://10.10.10.5/dashboard.php
    http://10.10.10.5/static/style.css
    http://10.10.10.5/static/myscripts.js
    http://10.10.10.5/ourteam.php
    http://10.10.10.5/
    http://10.10.10.5/backup
    http://10.10.10.5/backup/README.txt

becomes:

    http://10.10.10.5/
    ├── backup/
    │   └── README.txt
    ├── static/  [implied]
    │   ├── myscripts.js
    │   └── style.css
    ├── dashboard.php
    └── ourteam.php

```

## Usage

### Using directly as the outout of another app
```bash
feroxbuster -u http://10.0.0.5/ -w WORDLIST_FILE --silent  | python3 url2_webtree_pretty.py
feroxbuster -u http://10.0.0.5/ -w WORDLIST_FILE --json    | python3 url2_webtree_pretty.py
```

### Providing an input file
```bash
feroxbuster -u http://10.0.0.5/ WORDLIST_FILE -d 2 -o results.txt

python3 url2_webtree_pretty.py results.txt                             # one or more files
python3 url2_webtree_pretty.py *.txt > tree.txt                        # stitch several gobuster runs
python3 url2_webtree_pretty.py run1.txt run2.txt > tree.txt            # stitch several gobuster runs
python3 url2_webtree_pretty.py --full results.txt                      # print full URLs, not just names
python3 url2_webtree_pretty.py --no-annotate results.txt               # hide [status, redirect] tags
```

### Accepted input (auto-detected)
- a plain list of URLs, one per line (e.g. `feroxbuster --silent`)
- feroxbuster `--json` lines (keeps status codes + redirects)
- feroxbuster / gobuster default text output (best-effort status + redirect)
- your own hand-written list

### Options
| Flag | Effect |
| --- | --- |
| *(none)* | print path segments with `[status, redirect]` annotations |
| `--full` | print full URLs instead of just the path segment |
| `--no-annotate` | hide the `[status, redirect]` tags — plain tree |
| `-h, --help` | prints usage |
| `-V, --version` | prints script version |

### Reading the annotations
- `[200]` — the response status code.
- `[301, → /login]` — status plus where it redirects.
- `[implied]` — a directory that wasn't a result itself but must exist because something beneath it was found.

