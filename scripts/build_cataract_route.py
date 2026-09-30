"""
Build the cataract-focused labeling route.

Writes data/routes/cataract_focus.json: an ordered list of image keys (the
normalized paths used by LabelManager) for the "cataract_focus" route strategy.

Images are picked from two cataract signals and taken tier by tier until the
target size is reached:

  1. both signals   - AI pre-label has a cataract type AND the exam order
                      diagnosis mentions cataract / pseudophakia / aphakia
  2. AI, definite   - AI pre-label type Nuclear, Cortical, PSC, Mature-White,
                      Pseudophakia or Aphakia
  3. diagnosis only - order diagnosis mentions cataract, no AI cataract label
  4. AI, unclear    - AI pre-label type Other-Unclear

Within a tier, studies are shuffled with a fixed seed so the route is not
dominated by a handful of patients, and the photos of one study stay together
so same-study autofill keeps working. Images already saved by a human labeler
(label files present on this machine) are skipped.

Usage:
    python scripts/build_cataract_route.py [--size 10000] [--seed 42] [--force]
"""

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))

from config.config import LABELS_DIR, PATH_LIST_ROUTES, PREPROCESSED_PATH  # noqa: E402
from utils.label_manager import normalize_image_path  # noqa: E402

ROUTE_NAME = "cataract_focus"

DEFINITE_AI_TYPES = {"Nuclear", "Cortical", "PSC", "Mature-White", "Pseudophakia", "Aphakia"}
UNCLEAR_AI_TYPES = {"Other-Unclear"}

DX_NAME_PATTERN = r"catar|pseudophak|aphak|lens opac|nuclear scler|posterior capsul|\bPCO\b"
DX_CODE_PATTERN = r"H25|H26|H28|Z96\.1|Z98\.4|\b366"

TIER_NAMES = ["both signals", "AI definite", "diagnosis only", "AI unclear"]


def load_ai_cataract_types():
    """{image key: AI cataract type} for every pre-label with a real cataract type."""
    with open(LABELS_DIR / "AI_prelabel_labels.json", encoding="utf-8") as f:
        labels = json.load(f).get("labels") or {}
    types = {}
    for path, record in labels.items():
        cataract = (record.get("conditions") or {}).get("Cataract")
        if cataract and cataract.get("type") not in (None, "None"):
            types[normalize_image_path(path)] = cataract["type"]
    return types


def load_human_labeled_keys():
    """Image keys already saved by any human labeler on this machine."""
    keys = set()
    for path in LABELS_DIR.glob("*_labels.json"):
        if path.name.startswith("AI_prelabel"):
            continue
        with open(path, encoding="utf-8") as f:
            keys.update(normalize_image_path(k) for k in (json.load(f).get("labels") or {}))
    return keys


def load_dataset():
    """One row per image with its study and a cataract-diagnosis flag."""
    df = pd.read_parquet(
        PREPROCESSED_PATH,
        columns=["maskedid", "maskedid_studyid", "proc_name", "photo_name",
                 "order_diagnosis_name", "order_diagnosis"],
    )
    df["key"] = (
        "slitlamp\\" + df["maskedid"].astype(str) + "\\" + df["maskedid_studyid"].astype(str)
        + "\\" + df["proc_name"].astype(str) + "\\" + df["photo_name"].astype(str)
    ).map(normalize_image_path)
    df["has_dx"] = (
        df["order_diagnosis_name"].fillna("").str.contains(DX_NAME_PATTERN, case=False, regex=True)
        | df["order_diagnosis"].fillna("").astype(str).str.contains(DX_CODE_PATTERN, case=False, regex=True)
    )
    # The dataset repeats an image once per matched diagnosis row: keep one row,
    # flagged if any of its rows carries a cataract diagnosis.
    return (
        df.groupby("key", sort=False)
        .agg(studyid=("maskedid_studyid", "first"), photo=("photo_name", "first"), has_dx=("has_dx", "any"))
        .reset_index()
    )


def assign_tier(row, ai_types):
    ai_type = ai_types.get(row.key)
    if ai_type and row.has_dx:
        return 0
    if ai_type in DEFINITE_AI_TYPES:
        return 1
    if row.has_dx:
        return 2
    if ai_type in UNCLEAR_AI_TYPES:
        return 3
    return None


def build_route(size, seed):
    ai_types = load_ai_cataract_types()
    human_labeled = load_human_labeled_keys()
    df = load_dataset()

    df["tier"] = [assign_tier(row, ai_types) for row in df.itertuples()]
    candidates = df[df["tier"].notna() & ~df["key"].isin(human_labeled)].copy()
    candidates["tier"] = candidates["tier"].astype(int)

    rng = random.Random(seed)
    route, tier_counts = [], {}
    for tier in range(len(TIER_NAMES)):
        in_tier = candidates[candidates["tier"] == tier]
        studies = sorted(in_tier["studyid"].unique())
        rng.shuffle(studies)
        by_study = {sid: grp.sort_values("photo")["key"].tolist() for sid, grp in in_tier.groupby("studyid")}
        added = 0
        for sid in studies:
            if len(route) >= size:
                break
            # Take whole studies; only the very last one may be cut short.
            chunk = by_study[sid][: size - len(route)]
            route.extend(chunk)
            added += len(chunk)
        tier_counts[TIER_NAMES[tier]] = {"available": len(in_tier), "taken": added}

    return route, {
        "candidates_total": int(len(candidates)),
        "skipped_already_labeled": int(df["tier"].notna().sum() - len(candidates)),
        "tiers": tier_counts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--size", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true", help="overwrite an existing route file")
    args = parser.parse_args()

    out = PATH_LIST_ROUTES[ROUTE_NAME]
    if out.exists() and not args.force:
        sys.exit(f"{out} already exists. Re-running would reorder a route someone may be "
                 f"working through; pass --force if that is intended.")

    route, stats = build_route(args.size, args.seed)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "route": ROUTE_NAME,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "size": len(route),
            "seed": args.seed,
            "stats": stats,
            "image_keys": route,
        }, f, indent=1)

    print(f"Wrote {len(route):,} images to {out}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
