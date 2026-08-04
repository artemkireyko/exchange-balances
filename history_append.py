#!/usr/bin/env python3
"""
history_append — append a per-coin daily balance snapshot to data/history.jsonl.

Reads every data/<slug>.json (normalized records), aggregates wallets by
(exchange, network, coin), and writes one JSON-Lines row per key for today.
Re-runs on the same day overwrite that day's rows (no duplicates).

Usage (standalone):
    python3 history_append.py

Or import and call:
    from history_append import append_today
    append_today(skill_dir)
"""

import datetime
import json
import sys
from pathlib import Path


def append_today(skill_dir: Path) -> None:
    skill_dir = Path(skill_dir)
    data_dir = skill_dir / "data"
    history = data_dir / "history.jsonl"
    today = datetime.date.today().isoformat()

    # Aggregate today's wallets across all per-exchange files.
    agg: dict[tuple[str, str, str], dict] = {}
    for path in sorted(data_dir.glob("*.json")):
        try:
            obj = json.load(open(path, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print(f"  [!] skipping unreadable {path.name}", file=sys.stderr)
            continue
        exchange = obj.get("exchange") or path.stem
        for w in obj.get("wallets", []):
            try:
                bal = float(w["balance"])
                price = float(w["priceUsd"])
            except (KeyError, TypeError, ValueError):
                continue
            key = (exchange, w.get("network", ""), w.get("name", ""))
            e = agg.setdefault(key, {"balance": 0.0, "usd": 0.0,
                                     "wallets": 0, "priceUsd": 0.0})
            e["balance"] += bal
            e["usd"] += bal * price
            e["wallets"] += 1
            e["priceUsd"] = max(e["priceUsd"], price)

    # Read existing history, dropping any rows already stored for today.
    kept: list[str] = []
    if history.exists():
        for line in history.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("date") == today:
                continue
            kept.append(json.dumps(row, ensure_ascii=False))

    # Build today's rows.
    new_rows: list[str] = []
    for (exchange, network, coin), v in sorted(agg.items()):
        row = {
            "date": today,
            "exchange": exchange,
            "network": network,
            "coin": coin,
            "balance": round(v["balance"], 8),
            "usd": round(v["usd"], 2),
            "wallets": v["wallets"],
            "priceUsd": v["priceUsd"],
        }
        new_rows.append(json.dumps(row, ensure_ascii=False))

    history.parent.mkdir(parents=True, exist_ok=True)
    with open(history, "w", encoding="utf-8") as f:
        for line in kept:
            f.write(line + "\n")
        for line in new_rows:
            f.write(line + "\n")

    print(f"  → data/history.jsonl (+{len(new_rows)} rows for {today}, "
          f"{len(kept)} prior rows kept)")


if __name__ == "__main__":
    append_today(Path(__file__).resolve().parent)
