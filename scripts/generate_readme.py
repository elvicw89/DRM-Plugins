#!/usr/bin/env python3
"""Regenerate README.md from the latest GitHub release of each plugin in plugins.json.

Uses only the standard library. Set GITHUB_TOKEN to avoid API rate limits.
"""
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSET_EXTS = (".zip", ".msi", ".exe", ".dmg", ".pkg")


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com/{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "drm-plugins-readme"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def human_size(n):
    return f"{n / 1024 / 1024:.1f} MB"


def plugin_section(p):
    repo = p["repo"]
    lines = [f"## {p['name']}", "", p["tagline"], ""]
    shot = f"https://raw.githubusercontent.com/{repo}/{p['branch']}/{p['screenshot']}"
    lines += [f'<img src="{shot}" alt="{p["name"]}" width="640">', ""]
    try:
        rel = api(f"repos/{repo}/releases/latest")
    except Exception:
        lines += [f"No published release yet. See the [repository](https://github.com/{repo}).", ""]
        return "\n".join(lines)

    tag = rel["tag_name"]
    date = rel["published_at"][:10]
    lines.append(f"**Latest: [{tag}]({rel['html_url']})** (released {date})")
    lines.append("")
    assets = [a for a in rel["assets"] if a["name"].lower().endswith(ASSET_EXTS)]
    if assets:
        lines += ["| Download | Size |", "| --- | --- |"]
        for a in assets:
            lines.append(f"| [{a['name']}]({a['browser_download_url']}) | {human_size(a['size'])} |")
        lines.append("")
    lines.append(f"[All releases](https://github.com/{repo}/releases) · [Source](https://github.com/{repo})")
    lines.append("")
    return "\n".join(lines)


def main():
    plugins = json.loads((ROOT / "plugins.json").read_text())
    out = [
        "# DRM Series by yeahwaah audio",
        "",
        "Drum-focused plugins. Download the latest build of each below.",
        "",
        "> This page is generated automatically from each plugin's latest GitHub release.",
        "> Windows (64-bit) builds. Copy the `.vst3` from the zip into `C:\\Program Files\\Common Files\\VST3`.",
        "",
        "| Plugin | Latest |",
        "| --- | --- |",
    ]
    sections = []
    for p in plugins:
        try:
            rel = api(f"repos/{p['repo']}/releases/latest")
            latest = f"[{rel['tag_name']}]({rel['html_url']})"
        except Exception:
            latest = "n/a"
        out.append(f"| [{p['name']}](#{p['name'].lower()}) | {latest} |")
        sections.append(plugin_section(p))
    out += ["", "---", ""]
    out.append("\n---\n\n".join(sections))
    out += [
        "",
        "---",
        "",
        "Add a plugin by editing `plugins.json`. The README refreshes daily and on every push.",
        "",
    ]
    (ROOT / "README.md").write_text("\n".join(out))


if __name__ == "__main__":
    main()
