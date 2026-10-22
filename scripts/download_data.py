"""Download the FlyWire v783 connectome files used by the Shiu et al. (2024) model.

Files come from github.com/philshiu/Drosophila_brain_model, pinned to one commit so that
everyone gets byte-identical data. Existing files whose checksum matches are skipped.

Usage:
    uv run python scripts/download_data.py
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

SHIU_COMMIT = "91bdd1e7dcf193f3e7ca5a8933497fcef63b7960"
BASE_URL = f"https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/{SHIU_COMMIT}"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# filename -> expected SHA-256
FILES = {
    "Completeness_783.csv": "bbb847a4cc2caaa7a16349722d220c087317b946d148d4d592d94d250617a311",
    "Connectivity_783.parquet": "efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(name: str, expected: str) -> bool:
    dest = DATA_DIR / name
    if dest.exists() and sha256(dest) == expected:
        print(f"{name}: already present, checksum OK")
        return True

    print(f"{name}: downloading...")
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(f"{BASE_URL}/{name}", tmp)
    actual = sha256(tmp)
    if actual != expected:
        tmp.unlink()
        print(f"{name}: CHECKSUM MISMATCH (expected {expected}, got {actual})")
        return False

    tmp.replace(dest)
    print(f"{name}: done ({dest.stat().st_size / 1e6:.1f} MB)")
    return True


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)
    ok = all(download(name, expected) for name, expected in FILES.items())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
