"""Fail a release if any version declared in the repo disagrees with the tag.

server.json is the reason this exists. mcpb/ is rewritten from the tag by
release.yml before the bundle is packed, so a missed bump there self-heals, but
nothing regenerates server.json -- a missed bump used to ship silently and left
the MCP Registry advertising a stale version for several releases.

Run locally before tagging:

    python3 .github/scripts/check_versions.py 0.1.5

Kept to the stdlib and to plain regex for the TOML files so it runs on every
Python the package supports; tomllib is 3.11+.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Top-level `version = "..."` in a [project] table. These files are a handful of
# lines each, so anchoring to the start of a line is unambiguous.
_TOML_VERSION = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)
_PIN = re.compile(r'zendesk-mcp\s*==\s*([^"\'\s,\]]+)')


def _toml_version(path: Path) -> str:
    match = _TOML_VERSION.search(path.read_text())
    if not match:
        raise SystemExit(f"no top-level version found in {path}")
    return match.group(1)


def declared_versions() -> "dict[str, str]":
    """Every version string that has to track the release tag, by location."""
    found = {}

    found["pyproject.toml -> version"] = _toml_version(REPO_ROOT / "pyproject.toml")

    bundle_path = REPO_ROOT / "mcpb" / "pyproject.toml"
    found["mcpb/pyproject.toml -> version"] = _toml_version(bundle_path)
    pin = _PIN.search(bundle_path.read_text())
    if not pin:
        raise SystemExit(f"no zendesk-mcp== pin found in {bundle_path}")
    found["mcpb/pyproject.toml -> zendesk-mcp pin"] = pin.group(1)

    manifest = json.loads((REPO_ROOT / "mcpb" / "manifest.json").read_text())
    found["mcpb/manifest.json -> version"] = manifest["version"]

    server = json.loads((REPO_ROOT / "server.json").read_text())
    found["server.json -> version"] = server["version"]
    for i, package in enumerate(server.get("packages", [])):
        found["server.json -> packages[%d].version" % i] = package["version"]

    return found


def main(expected: str) -> int:
    found = declared_versions()
    width = max(len(label) for label in found)

    mismatched = []
    for label, value in found.items():
        matches = value == expected
        print("%s  %-*s  %s" % ("ok  " if matches else "FAIL", width, label, value))
        if not matches:
            mismatched.append(label)

    if mismatched:
        print("\nTag says %s, but %d declared version(s) disagree:" % (expected, len(mismatched)))
        for label in mismatched:
            print("  - %s = %s" % (label, found[label]))
        print("\nBump them to match, then move the tag.")
        return 1

    print("\nAll %d declared versions match the tag (%s)." % (len(found), expected))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1]:
        print("usage: check_versions.py <version>   (no leading 'v')", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
