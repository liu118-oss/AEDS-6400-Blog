"""Optional: recreate the compact public-data inputs from the two official wide CSVs.
Usage: python code/extract_inputs.py --raw-root '/path/to/Blog file'
"""

from pathlib import Path
import argparse, hashlib, json
import pandas as pd

B = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--raw-root", type=Path, required=True)
a = p.parse_args()
manifest = []
for cohort, folder, ids in [
    ("mother", "nlsy79_all_1979-2018", ["R0000100", "R0000500", "R0214800"]),
    ("child", "nlscya_all_1979-2018", ["C0000100", "C0000200", "C0005700"]),
]:
    v = pd.read_csv(B / "data" / f"{cohort}_variables.csv")
    cols = list(dict.fromkeys(ids + v.variable.tolist()))
    source = a.raw_root / folder / (folder + ".csv")
    target = B / "data" / f"{cohort}_selected.csv"
    for i, chunk in enumerate(pd.read_csv(source, usecols=cols, chunksize=256)):
        chunk[cols].to_csv(
            target, index=False, mode="w" if i == 0 else "a", header=i == 0
        )
    manifest.append(
        {
            "cohort": cohort,
            "original_filename": source.name,
            "original_bytes": source.stat().st_size,
            "selected_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "selected_columns": cols,
        }
    )
(B / "data/source_manifest.json").write_text(json.dumps(manifest, indent=2))
