#!/usr/bin/env python3
"""
CMC-fetch — download Proof-of-Reserves JSON for all supported exchanges
straight from CoinMarketCap and pipe them into cmc_update.py.

Usage:
    python3 cmc_fetch.py                   # fetch ALL supported exchanges
    python3 cmc_fetch.py binance bybit     # fetch only listed slugs

After download, the script invokes cmc_update.py on the fresh files,
which normalizes them into data/<slug>.json and rebuilds dashboard.html.
"""

import datetime
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cmc_update import EXCHANGES  # noqa: E402

DATA_DIR = HERE / "data"
SNAP_DIR = DATA_DIR / "snapshots"
SNAP_RETENTION_DAYS = 30

CMC_URL = "https://api.coinmarketcap.com/data-api/v3/exchange/reserves/wallets?id={cmc_id}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://coinmarketcap.com",
    "Referer": "https://coinmarketcap.com/",
}


def fetch_one(slug: str, out_dir: Path):
    display, cmc_id = EXCHANGES[slug]
    url = CMC_URL.format(cmc_id=cmc_id)
    print(f"[*] {display} (id={cmc_id}) → {url}")
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        print(f"  [!] HTTP {e.code}: {e.reason}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"  [!] network error: {e.reason}", file=sys.stderr)
        return None

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        print(f"  [!] response is not JSON ({len(body)} bytes) — likely blocked", file=sys.stderr)
        return None

    wallets = (
        (parsed.get("data") or {}).get("exchangeWallets")
        or (parsed.get("data") or {}).get("wallets")
        or parsed.get("exchangeWallets")
        or parsed.get("wallets")
        or []
    )
    if not wallets:
        print(f"  [!] no wallets in payload — skipping", file=sys.stderr)
        return None

    path = out_dir / f"{slug}.json"
    path.write_bytes(body)
    print(f"  ok: {len(wallets)} wallets, {len(body):,} bytes → {path.name}")
    return path


def save_snapshots(files: list[Path]):
    """Copy each freshly downloaded raw JSON into data/snapshots/<today>/<slug>.json.
    Idempotent: re-running on the same day overwrites today's snapshot."""
    today = datetime.date.today().isoformat()
    day_dir = SNAP_DIR / today
    day_dir.mkdir(parents=True, exist_ok=True)
    for p in files:
        dest = day_dir / p.name
        shutil.copyfile(p, dest)
        print(f"  snapshot → data/snapshots/{today}/{p.name}")


def prune_snapshots():
    """Drop any data/snapshots/<date>/ folder older than SNAP_RETENTION_DAYS."""
    if not SNAP_DIR.exists():
        return
    today = datetime.date.today()
    for child in SNAP_DIR.iterdir():
        if not child.is_dir():
            continue
        try:
            d = datetime.date.fromisoformat(child.name)
        except ValueError:
            continue
        if (today - d) > datetime.timedelta(days=SNAP_RETENTION_DAYS):
            shutil.rmtree(child, ignore_errors=True)
            print(f"  pruned old snapshot: {child.name}")


def main():
    requested = [s.lower() for s in sys.argv[1:]] or list(EXCHANGES.keys())
    unknown = [s for s in requested if s not in EXCHANGES]
    if unknown:
        print(f"[!] unknown slug(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"    supported: {', '.join(EXCHANGES)}", file=sys.stderr)
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="cmc_fetch_") as tmp:
        tmp_dir = Path(tmp)
        downloaded = []
        for slug in requested:
            p = fetch_one(slug, tmp_dir)
            if p:
                downloaded.append(p)

        if not downloaded:
            print("[!] nothing downloaded — aborting", file=sys.stderr)
            sys.exit(2)

        print()
        print(f"[*] Saving {len(downloaded)} raw snapshot(s) ...")
        save_snapshots(downloaded)

        print()
        print(f"[*] Handing {len(downloaded)} file(s) to cmc_update.py ...")
        cmd = [sys.executable, str(HERE / "cmc_update.py"), *map(str, downloaded)]
        subprocess.run(cmd, check=True)

    print()
    print("[*] Pruning snapshots older than "
          f"{SNAP_RETENTION_DAYS} days ...")
    prune_snapshots()


if __name__ == "__main__":
    main()
