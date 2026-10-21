"""Fetch missing official files; preserve the published snapshot by default."""

import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.newyorkfed.org/medialibrary/research/interactives/data/college-labor-market/"
FILES = [
    "college-labor-outcomes-by-major-data.csv",
    "college-labor-unemployment-data.csv",
    "college-labor-chart-meta.json",
]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--refresh",
    action="store_true",
    help="Replace snapshots with current releases; results may change.",
)
args = parser.parse_args()
for name in FILES:
    target = ROOT / "data/raw" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not args.refresh:
        print(f"Keeping snapshot: {name}")
        continue
    temporary = target.with_suffix(target.suffix + ".download")
    subprocess.run(
        [
            "curl",
            "--fail",
            "--location",
            "--retry",
            "3",
            BASE + name,
            "--output",
            str(temporary),
        ],
        check=True,
    )
    temporary.replace(target)
    print(f"Downloaded: {name}")
