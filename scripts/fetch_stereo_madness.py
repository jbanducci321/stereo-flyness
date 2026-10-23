"""Fetch and decode the official Stereo Madness layout into data/gd/ (never committed).

The level design belongs to RobTop Games (D9), so only this script is committed. Each person
runs it to build their own local copy.

Source: the official main-level data shipped in Open-GD/OpenGD (`Content/Custom/mainLevels.json`),
pinned to one commit and checked against a SHA-256. Main-level strings are stored without the
usual gzip header, so we put it back and decode with the standard library (no extra
dependencies). `--cross-check` compares the result with the archived server copy of the level
(ID 77236587, a GD 2.1 upload), fetched directly from the Geometry Dash server.

Outputs (in data/gd/):
    stereo_madness_level.txt     the decoded level string
    stereo_madness_objects.csv   one row per object, level coordinates (see docs/game_physics.md §10)

Usage:
    uv run python scripts/fetch_stereo_madness.py [--cross-check]
"""

import argparse
import base64
import csv
import hashlib
import json
import sys
import urllib.parse
import urllib.request
import zlib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "gd"

OPENGD_COMMIT = "2a0e307"
MAIN_LEVELS_URL = f"https://raw.githubusercontent.com/Open-GD/OpenGD/{OPENGD_COMMIT}/Content/Custom/mainLevels.json"
MAIN_LEVELS_SHA256 = "b0e5dc6c6b500d023316343f72de04e3decd54bdac6de3c14ded0b24e304079e"
STEREO_MADNESS_KEY = "1"  # main level number

SERVER_URL = "http://www.boomlings.com/database/downloadGJLevel22.php"
SERVER_SECRET = "Wmfd2893gb7"  # public, community-documented request constant
CROSS_CHECK_LEVEL_ID = "77236587"

GZIP_B64_HEADER = "H4sIAAAAAAAAA"  # stripped from main-level strings

# Object ID -> category, for every ID that appears in Stereo Madness (docs/game_physics.md §10).
# Object types follow OpenGD's object table; triggers and coins aren't in it and are
# classified from community knowledge.
CATEGORY = {
    **{i: "solid" for i in ("1", "2", "3", "4", "6", "7", "40", "62", "65")},
    **{i: "hazard" for i in ("8", "9", "39", "103")},
    "12": "cube_portal",
    "13": "ship_portal",
    **{i: "decoration" for i in ("5", "15", "16", "17", "18", "19", "20", "21", "41", "54")},
    **{i: "trigger" for i in ("22", "23", "27", "29", "30")},
    **{i: "collectible" for i in ("142", "1329")},  # secret coin (2.0 / 2.1 IDs)
}
GAMEPLAY = {"solid", "hazard", "cube_portal", "ship_portal"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(level_string: str) -> str:
    raw = base64.urlsafe_b64decode(level_string + "=" * (-len(level_string) % 4))
    return zlib.decompress(raw, 47).decode()  # 47: auto-detect gzip/zlib header


def parse_objects(level: str) -> list[dict]:
    """Split a decoded level into objects. Each object is 'key,value,key,value,...'."""
    _settings, *objects = level.split(";")
    out = []
    for obj in objects:
        if obj:
            fields = obj.split(",")
            out.append(dict(zip(fields[0::2], fields[1::2])))
    return out


def fetch_official() -> str:
    cache = OUT_DIR / "mainLevels.json"
    if not (cache.exists() and sha256(cache) == MAIN_LEVELS_SHA256):
        print(f"Downloading official main-level data (OpenGD {OPENGD_COMMIT}, ~1 MB)...")
        urllib.request.urlretrieve(MAIN_LEVELS_URL, cache)
        if sha256(cache) != MAIN_LEVELS_SHA256:
            cache.unlink()
            raise SystemExit("mainLevels.json checksum mismatch. Stopping.")
    stored = json.loads(cache.read_text(encoding="utf-8"))[STEREO_MADNESS_KEY]
    return decode(GZIP_B64_HEADER + stored)


def fetch_server_copy(level_id: str) -> str:
    body = urllib.parse.urlencode({"levelID": level_id, "secret": SERVER_SECRET}).encode()
    req = urllib.request.Request(SERVER_URL, data=body, headers={"User-Agent": ""})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode()
    fields = text.split("#")[0].split(":")
    return decode(dict(zip(fields[0::2], fields[1::2]))["4"])


def gameplay_key(o: dict) -> tuple:
    return (o["1"], float(o["2"]), float(o["3"]), o.get("6", "0"), o.get("4", "0"), o.get("5", "0"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cross-check", action="store_true",
                        help=f"compare with server copy {CROSS_CHECK_LEVEL_ID} (one request to the GD server)")
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    level = fetch_official()
    objects = parse_objects(level)
    (OUT_DIR / "stereo_madness_level.txt").write_text(level, encoding="utf-8")

    unknown = sorted({o["1"] for o in objects} - CATEGORY.keys(), key=int)
    if unknown:
        print(f"WARNING: unclassified object IDs {unknown}. Add them to CATEGORY before using the level.")

    with open(OUT_DIR / "stereo_madness_objects.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "category", "x", "y", "rotation", "flip_x", "flip_y"])
        for o in sorted(objects, key=lambda o: (float(o["2"]), float(o["3"]))):
            w.writerow([o["1"], CATEGORY.get(o["1"], "unknown"), o["2"], o["3"],
                        o.get("6", "0"), o.get("4", "0"), o.get("5", "0")])

    cats = Counter(CATEGORY.get(o["1"], "unknown") for o in objects)
    end_x = max(float(o["2"]) for o in objects)
    print(f"Stereo Madness: {len(objects)} objects, level end x = {end_x:.0f} (~{end_x / 311.58:.1f} s at normal speed)")
    print("By category:", dict(cats.most_common()))
    print("Portals:")
    for o in sorted(objects, key=lambda o: float(o["2"])):
        if CATEGORY.get(o["1"], "").endswith("portal"):
            print(f"  {CATEGORY[o['1']]:<12} x={o['2']:>7} y={o['3']:>4}  (~{float(o['2']) / 311.58:.1f} s)")

    if args.cross_check:
        other = parse_objects(fetch_server_copy(CROSS_CHECK_LEVEL_ID))
        mine = {gameplay_key(o) for o in objects if CATEGORY.get(o["1"]) in GAMEPLAY}
        theirs = {gameplay_key(o) for o in other if CATEGORY.get(o["1"]) in GAMEPLAY}
        print(f"\nCross-check vs server level {CROSS_CHECK_LEVEL_ID}: gameplay objects "
              f"identical: {mine == theirs} ({len(mine & theirs)} shared, "
              f"{len(mine - theirs)} only official, {len(theirs - mine)} only server copy)")

    print(f"\nWrote {OUT_DIR.relative_to(ROOT)}/stereo_madness_level.txt and stereo_madness_objects.csv (git-ignored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
