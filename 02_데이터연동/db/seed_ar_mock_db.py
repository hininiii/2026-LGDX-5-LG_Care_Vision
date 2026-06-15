# -*- coding: utf-8 -*-
"""Seed helper aligned to 전체 테이블 정리.md.

This script creates only the 21 persisted tables defined in
`01_정의서/최종_DB_테이블_전체정리.md`.

It intentionally does not recreate deprecated tables such as `devices`,
`care_videos`, `safety_audit_logs`, `preventive_alerts`, or provider/log tables
that were removed from the final table document.
"""

import os
from pathlib import Path
import sqlite3


BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("CARESHOT_DB_PATH", BASE / "careshot_ar_mock.db"))
SCHEMA_PATH = BASE / "schema.sql"


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    con.execute(
        'insert into "REGION" values (?,?,?,?,?,?,?,?,?,?,?)',
        (
            "IND_DELHI_NEW_DELHI",
            "India",
            "Delhi",
            "New Delhi",
            28.6139,
            77.2090,
            "Asia/Kolkata",
            "humid_subtropical",
            "hard",
            "north_monsoon",
            "Y",
        ),
    )
    con.execute(
        'insert into "USER" values (?,?,?,?,?,?,?)',
        (
            "demo@careshot.local",
            "demo_password",
            "Demo User",
            None,
            "New Delhi, India",
            "IND_DELHI_NEW_DELHI",
            "en",
        ),
    )
    con.execute(
        'insert into "PRODUCT" values (?,?,?,?,?,?,?,?,?,?)',
        (
            "AS-Q24ENXE",
            "LG Wall Mounted AC",
            "AS-Q24ENXE",
            "air_conditioner",
            "wall_mounted_ac",
            None,
            None,
            "Y",
            "demo_seed",
            "https://www.lg.com/in/search/?search=AS-Q24ENXE&tab=support",
        ),
    )
    con.execute(
        'insert into "USER_PRODUCT" (user_email, product_code, display_name) values (?,?,?)',
        ("demo@careshot.local", "AS-Q24ENXE", "Living Room AC"),
    )

    con.commit()
    con.close()


if __name__ == "__main__":
    main()
