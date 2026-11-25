#!/usr/bin/env python3
"""Sync the latest release of each plugin in plugins.json into this repo, then rebuild README.md.

For every plugin it downloads the newest .zip release asset into downloads/<name>/ and the
screenshot into screenshots/<name>.png. Release info is kept in data/releases.json so the README
still renders (and old files stay) when a source repo can't be reached, e.g. after it goes private.

Needs the GitHub CLI (`gh`). Set GH_TOKEN. Private source repos need a token that can read them
(the SOURCE_TOKEN secret in the workflow).
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "releases.json"
HUB = "elvicw/DRM-Plugins"
BRANCH = "main"
ASSET_EXTS = (".zip",)


def gh(*args, binary=False):
    res = subprocess.run(["gh", *args], capture_output=True, check=True)
    return res.stdout if binary else res.stdout.decode()


def hub_url(rel_path):
    return f"https://github.com/{HUB}/raw/{BRANCH}/{rel_path.replace(' ', '%20')}"


def human_size(n):
    return f"{n / 1024 / 1024:.1f} MB"


def sync_plugin(p, state):
    name, repo = p["name"], p["repo"]
    rel = json.loads(gh("api", f"repos/{repo}/releases/latest"))
    assets = [a for a in rel["assets"] if a["name"].lower().endswith(ASSET_EXTS)]
    target = ROOT / "downloads" / name
    entry = {"tag": rel["tag_name"], "date": rel["published_at"][:10], "assets": []}

    if state.get(name, {}).get("tag") != rel["tag_name"] or not target.exists():
        with tempfile.TemporaryDirectory() as tmp:
            for a in assets:
                gh("release", "download", rel["tag_name"], "-R", repo, "-p", a["name"], "-D", tmp)
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True)
            for f in Path(tmp).iterdir():
                shutil.move(str(f), target / f.name)
    for a in assets:
        entry["assets"].append({"name": a["name"], "size": a["size"]})

    shot = gh("api", f"repos/{repo}/contents/{p['screenshot']}?ref={p['branch']}",
              "-H", "Accept: application/vnd.github.raw", binary=True)
    (ROOT / "screenshots").mkdir(exist_ok=True)
    (ROOT / "screenshots" / f"{name}.png").write_bytes(shot)
    state[name] = entry


def section(p, entry):
    name = p["name"]
    lines = [f"## {name}", "", p["tagline"], "",
             f'<img src="{hub_url(f"screenshots/{name}.png")}" alt="{name}" width="640">', ""]
    if not entry:
        return "\n".join(lines + ["No release yet.", ""])
    lines += [f"**Latest: {entry['tag']}** (released {entry['date']})", "",
              "| Download | Size |", "| --- | --- |"]
    for a in entry["assets"]:
        url = hub_url(f"downloads/{name}/{a['name']}")
        lines.append(f"| [{a['name']}]({url}) | {human_size(a['size'])} |")
    lines.append("")
    return "\n".join(lines)


def main():
    plugins = json.loads((ROOT / "plugins.json").read_text())
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    for p in plugins:
        try:
            sync_plugin(p, state)
        except Exception as e:
            print(f"warning: could not sync {p['name']}, keeping existing files: {e}")
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + "\n")

    out = [
        "# DRM Series by yeahwaah audio",
        "",
        "Drum-focused plugins. Download the latest build of each below.",
        "",
        "> Windows (64-bit) builds. Copy the `.vst3` from the zip into `C:\\Program Files\\Common Files\\VST3`.",
        "",
        "---",
        "",
        "\n---\n\n".join(section(p, state.get(p["name"])) for p in plugins),
        "",
        "---",
        "",
    ]
    (ROOT / "README.md").write_text("\n".join(out))


if __name__ == "__main__":
    main()
