#!/usr/bin/env python3
"""Regenerate the repository map on the org profile from the live org, not from memory.

The map is the MANIFESTO's filing order made visible: a repo walks research -> teaching -> products
-> people -> identity -> ops and stops at the first room it belongs to. Everything here is derived
from the GitHub API at run time, so a repo created ten minutes ago is in the map an hour later and
nobody has to remember to edit a table.

profile/README.md is PUBLIC. In the default `--names public` mode a private repo therefore never
appears by name or description: it is counted, and nothing else. `--names all` exists because the
MANIFESTO's own hand-written map already lists private repo names publicly; use it only if that is
the intent for this file too. `check_no_private_leak` is the enforcement, and it runs in both modes:
in `public` it raises rather than emit a private name, so the failure is a red workflow, not a quiet
disclosure.

    GITHUB_TOKEN=... python3 scripts/build_repo_map.py --org aura-lab-wm --write profile/README.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
START = "<!-- REPO-MAP:START -->"
END = "<!-- REPO-MAP:END -->"

# The MANIFESTO's rooms, in its walk-in order: first match wins.
ROOMS = [
    ("people", "people", lambda n: n.startswith(("student-aura-", "student-grad-", "student-undergrad-"))),
    ("research", "research", lambda n: n.startswith("research-")),
    ("teaching", "teaching", lambda n: n.startswith("teaching-")),
    ("products", "products", lambda n: n.startswith("project-")),
    ("identity", "identity", lambda n: n.startswith(("web-", "design-")) or n == ".github"),
    ("ops", "ops", lambda n: n.startswith("ops-") or n == "skills"),
]
# A repo that matches no room is not a failure of the map: it is the map doing its job, showing a
# name the MANIFESTO's naming table does not cover yet.
UNFILED = "unfiled"


def fetch_repos(org: str, token: str) -> list[dict]:
    out, page = [], 1
    while True:
        req = urllib.request.Request(
            f"{API}/orgs/{org}/repos?per_page=100&page={page}&type=all&sort=full_name",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "aura-repo-map",
                     **({"Authorization": f"Bearer {token}"} if token else {})})
        with urllib.request.urlopen(req, timeout=30) as r:
            batch = json.load(r)
        out.extend(batch)
        if len(batch) < 100:
            return out
        page += 1


def room_of(name: str) -> str:
    for key, _, match in ROOMS:
        if match(name):
            return key
    return UNFILED


def group(repos: list[dict]) -> dict[str, list[dict]]:
    rooms: dict[str, list[dict]] = {key: [] for key, _, _ in ROOMS}
    rooms[UNFILED] = []
    for r in repos:
        rooms[room_of(r["name"])].append(r)
    for v in rooms.values():
        v.sort(key=lambda r: r["name"])
    return rooms


def _link(org: str, r: dict) -> str:
    return f"[`{r['name']}`](https://github.com/{org}/{r['name']})"


def _private_note(n: int) -> str:
    return "" if not n else f"{n} private"


def render(org: str, repos: list[dict], names: str, now: str) -> str:
    rooms = group(repos)
    public = [r for r in repos if not r["private"]]
    show_private_names = names == "all"

    lines = [START, ""]
    lines.append(f'<p align="center"><sub>REPOSITORY MAP · {len(repos)} repos · {len(public)} public · '
                 f'generated {now} · <a href="MANIFESTO.md">filing rules</a></sub></p>')
    lines.append("")

    # Mermaid: the walk-in order left to right, each room carrying its own counts. Private repos are
    # a number here in `public` mode, never a name.
    # Labels stay plain text plus <br/>: GitHub's Mermaid does not reliably render other HTML in a
    # node label, and a literal "<b>" on the org's front page is worse than an unbolded word.
    lines += ["```mermaid", "flowchart LR",
              f'  ORG["{org}<br/>{len(repos)} repos"]']
    for key, label, _ in ROOMS + [(UNFILED, UNFILED, None)]:
        rs = rooms.get(key, [])
        if not rs:
            continue
        pub = sum(1 for r in rs if not r["private"])
        priv = len(rs) - pub
        bits = [f"{len(rs)} repo" + ("s" if len(rs) != 1 else "")]
        if pub:
            bits.append(f"{pub} public")
        if priv:
            bits.append(f"{priv} private")
        node = key.upper()
        lines.append(f'  ORG --> {node}["{label}<br/>{" · ".join(bits)}"]')
        named = [r for r in rs if (not r["private"] or show_private_names)]
        for i, r in enumerate(named[:6]):
            # A positional id, not hash(): PYTHONHASHSEED is randomised per process, so hashed ids
            # would differ on every run and the hourly job would commit a diff that is not a change.
            lines.append(f'  {node} --> {node}_{i}["{r["name"]}"]')
        if len(named) > 6:
            lines.append(f'  {node} --> {node}_more["+{len(named) - 6} more"]')
    lines += ["```", ""]

    # The table carries what a diagram cannot: who is public, and when the room last moved.
    lines += ["| Room | Repos | Public | Private | Last push |", "|---|---:|---|---:|---|"]
    for key, label, _ in ROOMS + [(UNFILED, UNFILED, None)]:
        rs = rooms.get(key, [])
        if not rs:
            continue
        pub = [r for r in rs if not r["private"]]
        priv = [r for r in rs if r["private"]]
        shown = sorted(pub, key=lambda r: r["name"]) if not show_private_names else sorted(rs, key=lambda r: r["name"])
        cell = ", ".join(_link(org, r) for r in shown) or "—"
        last = max((r["pushed_at"] or "") for r in rs)[:10] or "—"
        lines.append(f"| **{label}** | {len(rs)} | {cell} | {len(priv)} | {last} |")
    lines.append("")
    if rooms.get(UNFILED):
        lines.append(f"<sub><b>unfiled</b> names match no rule in the naming table — file them or extend the table.</sub>")
        lines.append("")
    lines.append(f"<sub>Regenerated hourly by <code>.github/workflows/repo-map.yml</code>. "
                 f"Private repositories are counted, never named.</sub>" if not show_private_names else
                 f"<sub>Regenerated hourly by <code>.github/workflows/repo-map.yml</code>.</sub>")
    lines += ["", END]
    return "\n".join(lines)


def check_no_private_leak(block: str, repos: list[dict]) -> None:
    """A private name or description in a public block is the one failure mode that matters."""
    leaked = []
    for r in repos:
        if not r["private"]:
            continue
        if r["name"] in block:
            leaked.append(r["name"])
        desc = (r["description"] or "").strip()
        if len(desc) > 12 and desc in block:
            leaked.append(f"{r['name']} (description)")
    if leaked:
        raise SystemExit("refusing to write: private repositories would be named in a public file: "
                         + ", ".join(sorted(set(leaked))))


def splice(doc: str, block: str) -> str:
    if START in doc and END in doc:
        head, rest = doc.split(START, 1)
        _, tail = rest.split(END, 1)
        return head + block + tail
    sep = "" if doc.endswith("\n\n") else ("\n" if doc.endswith("\n") else "\n\n")
    return doc + sep + block + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--org", default="aura-lab-wm")
    ap.add_argument("--write", metavar="FILE", help="splice the block into this file (default: print)")
    ap.add_argument("--names", choices=("public", "all"), default="public",
                    help="'public' (default) names only public repos; 'all' also names private ones")
    ap.add_argument("--now", default=None, help="timestamp override, for tests")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        repos = fetch_repos(args.org, token)
    except urllib.error.HTTPError as e:
        print(f"GitHub API {e.code}: {e.reason}", file=sys.stderr)
        return 1
    repos = [r for r in repos if not r.get("archived")]
    if not repos:
        print("no repositories returned — refusing to write an empty map", file=sys.stderr)
        return 1

    # The public map can only say "1 unfiled"; the names belong in the job log, which only org
    # members can read, so the drift is actionable without being published.
    unfiled = sorted(r["name"] for r in repos if room_of(r["name"]) == UNFILED)
    if unfiled:
        print(f"unfiled ({len(unfiled)}), not named in the public map: {', '.join(unfiled)}",
              file=sys.stderr)

    now = args.now or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    block = render(args.org, repos, args.names, now)
    if args.names == "public":
        check_no_private_leak(block, repos)

    if not args.write:
        print(block)
        return 0
    with open(args.write, encoding="utf-8") as f:
        doc = f.read()
    new = splice(doc, block)
    if new == doc:
        print("map unchanged")
        return 0
    with open(args.write, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"map written to {args.write} ({len(repos)} repos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
