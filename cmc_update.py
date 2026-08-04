#!/usr/bin/env python3
"""
CMC-parser — normalize CoinMarketCap exchange Proof-of-Reserves JSON dumps
and rebuild the wallets dashboard.

Usage:
    python3 cmc_update.py <raw.json> [<raw2.json> ...]

Filenames must contain the exchange slug, e.g. "binance.json", "okx_dump.json".
Supported slugs: binance, okx, bybit, bitget, mexc, gate.

Writes:
    <skill_dir>/data/<slug>.json     — normalized records
    <skill_dir>/dashboard.html       — regenerated dashboard
"""

import json
import re
import subprocess
import sys
from pathlib import Path

EXCHANGES = {
    "binance": ("Binance", 270),
    "okx":     ("OKX",     294),
    "bybit":   ("Bybit",   521),
    "bitget":  ("Bitget",  513),
    "mexc":    ("MEXC",    544),
    "gate":    ("Gate",    302),
}

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
DATA_DIR.mkdir(exist_ok=True)


def detect_slug(filename: str):
    name = filename.lower()
    # longest slug first, so "gate" doesn't accidentally match "gateway" etc.
    for slug in sorted(EXCHANGES, key=len, reverse=True):
        if re.search(rf"(^|[^a-z]){slug}([^a-z]|$)", name):
            return slug
    return None


def normalize(raw: dict) -> list[dict]:
    """Extract wallets from CMC raw response. Accepts:
       - {"data": {"exchangeWallets": [...]}}
       - {"exchangeWallets": [...]}
       - {"wallets": [...]} (already-normalized)
    """
    if "data" in raw and isinstance(raw["data"], dict):
        ws = raw["data"].get("exchangeWallets") or raw["data"].get("wallets") or []
    else:
        ws = raw.get("exchangeWallets") or raw.get("wallets") or []
    out = []
    for w in ws:
        out.append({
            "walletAddress": w["walletAddress"],
            "network":       w["network"],
            "name":          w["name"],
            "balance":       float(w["balance"]),
            "priceUsd":      float(w["priceUsd"]),
            "updateTime":    w.get("updateTime", ""),
        })
    return out


def write_exchange(slug: str, records: list[dict]):
    display, cmc_id = EXCHANGES[slug]
    out_path = DATA_DIR / f"{slug}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f'{{"exchange":"{display}","cmcId":{cmc_id},"wallets":[\n')
        for i, r in enumerate(records):
            comma = "," if i < len(records) - 1 else ""
            f.write(json.dumps(r, ensure_ascii=False) + comma + "\n")
        f.write("]}\n")
    print(f"  → data/{out_path.name} ({len(records)} wallets)")


def main():
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        sys.exit(1)

    any_ok = False
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        if not path.exists():
            print(f"[!] not found: {path}", file=sys.stderr)
            continue
        slug = detect_slug(path.name)
        if not slug:
            print(f"[!] cannot detect exchange from filename: {path.name}", file=sys.stderr)
            print(f"    expected one of: {', '.join(EXCHANGES)}", file=sys.stderr)
            continue
        print(f"[*] {path.name} → {EXCHANGES[slug][0]}")
        try:
            raw = json.load(open(path, encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  [!] not valid JSON: {e}", file=sys.stderr)
            continue
        records = normalize(raw)
        if not records:
            print(f"  [!] no wallets found in JSON (looked for data.exchangeWallets)", file=sys.stderr)
            continue
        write_exchange(slug, records)
        any_ok = True

    if not any_ok:
        sys.exit(2)

    # Append today's per-coin balance snapshot to data/history.jsonl.
    print()
    print("[*] Appending daily balance history ...")
    try:
        from history_append import append_today
        append_today(HERE)
    except Exception as e:  # noqa: BLE001 — history must never break the main flow
        print(f"  [!] history append failed: {e}", file=sys.stderr)

    # Rebuild the snapshot dashboard.
    builder = HERE / "build_dashboard.py"
    if not builder.exists():
        print(f"[!] build_dashboard.py not found next to cmc_update.py", file=sys.stderr)
        sys.exit(3)
    print()
    print("[*] Rebuilding dashboard.html ...")
    subprocess.run([sys.executable, str(builder)], check=True)

    # Rebuild the balance-dynamics dashboard.
    builder2 = HERE / "build_dashboard_2.py"
    if builder2.exists():
        print()
        print("[*] Rebuilding dashboard_2.html ...")
        subprocess.run([sys.executable, str(builder2)], check=True)
    else:
        print("[!] build_dashboard_2.py not found — skipping dynamics dashboard",
              file=sys.stderr)


if __name__ == "__main__":
    main()
