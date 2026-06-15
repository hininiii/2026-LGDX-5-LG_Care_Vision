from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import CareShotBackendService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CareShot intent/risk evaluation set.")
    parser.add_argument("--product-type", default=None, help="Optional product_type filter.")
    parser.add_argument("--limit", type=int, default=None, help="Optional case limit for smoke checks.")
    parser.add_argument("--run-id", default=None, help="Optional deterministic run_id.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service = CareShotBackendService()
    result = service.run_intent_risk_evaluation(
        {
            "product_type": args.product_type,
            "limit": args.limit,
            "run_id": args.run_id,
        }
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
