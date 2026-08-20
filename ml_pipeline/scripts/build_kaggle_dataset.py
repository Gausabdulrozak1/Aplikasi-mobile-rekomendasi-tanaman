from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from ml_pipeline.src.dataset.kaggle_package import (  # noqa: E402
    audit_source_truth,
    build_kaggle_staging,
    finalize_kaggle_package,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the validated TaniAdaptif Kaggle dataset")
    parser.add_argument("command", choices=("audit", "build-staging", "finalize"))
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--staging-root", type=Path)
    parser.add_argument("--imagefolder-report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository_root = args.repository_root.resolve()
    if args.command == "audit":
        result = audit_source_truth(repository_root)
    elif args.command == "build-staging":
        result = build_kaggle_staging(repository_root, args.staging_root)
    else:
        if args.imagefolder_report is None:
            raise SystemExit("--imagefolder-report is required for finalize")
        result = finalize_kaggle_package(
            repository_root,
            args.imagefolder_report.resolve(),
            args.staging_root,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
