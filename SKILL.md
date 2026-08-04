---
name: cmc-parser
description: Parse uploaded CoinMarketCap exchange Proof-of-Reserves JSON dumps, or auto-fetch them from CMC, and update a wallets dashboard. Use when the user uploads a JSON file with CMC structure (data.exchangeWallets array), wants to refresh all exchanges in one shot (triggers like "обнови дашборд", "пересобери дашборд", "качни свежие данные с cmc", "refresh dashboard", "fetch all exchanges"), or pastes CMC reserves JSON. Also triggers on phrases like "новый CMC json", "добавь биржу в дашборд", "распарсь cmc", "cmc parser", or when an attached file is named binance*.json, okx*.json, bybit*.json, bitget*.json, mexc*.json, gate*.json. Auto-detects exchange by filename, normalizes records, writes data per exchange, regenerates dashboard.html.
---

# CMC-parser

Folds CoinMarketCap Proof-of-Reserves JSON (raw from `https://api.coinmarketcap.com/data-api/v3/exchange/reserves/wallets?id={ID}`) into the wallets dashboard.

## How Claude should use this skill

### Mode A — user uploads JSON files

1. Identify the file(s) in the user's uploads directory.
2. For each file, run:
   ```bash
   python3 {skill_dir}/cmc_update.py path/to/uploaded.json [more.json ...]
   ```
3. The script auto-detects the exchange from the filename (must contain one of: `binance`, `okx`, `bybit`, `bitget`, `mexc`, `gate`).
4. After all files are processed, the dashboard is automatically rebuilt at `{skill_dir}/dashboard.html`.
5. Present `dashboard.html` to the user with `mcp__cowork__present_files`.

### Mode B — auto-fetch from CMC (no uploads needed)

Use this when the user asks to refresh / pull / fetch all exchanges, or didn't attach files:

```bash
python3 {skill_dir}/cmc_fetch.py                # all 6 exchanges
python3 {skill_dir}/cmc_fetch.py binance bybit  # a subset
```

`cmc_fetch.py` downloads the raw CMC JSON for each requested slug (using a browser-like User-Agent), drops them in a temp dir, then hands them off to `cmc_update.py` which normalizes and rebuilds the dashboard. If CMC blocks a request (403, non-JSON HTML) the script logs it and skips that exchange — fall back to Mode A and ask the user to paste/save that one manually.

## Supported exchanges (CMC slug → CMC id)

| slug | display | id |
|---|---|---|
| binance | Binance | 270 |
| okx | OKX | 294 |
| bybit | Bybit | 521 |
| bitget | Bitget | 513 |
| mexc | MEXC | 544 |
| gate | Gate | 302 |

To add another exchange, edit the `EXCHANGES` dict at the top of `cmc_update.py`.

## How the user feeds new data

1. Open `https://api.coinmarketcap.com/data-api/v3/exchange/reserves/wallets?id={id}` in a browser.
2. Cmd+S → save the JSON. Filename should contain the exchange slug (e.g. `binance.json`, `okx_dump.json`).
3. Drag the file into chat. Claude finds it in uploads, runs `cmc_update.py`, rebuilds dashboard.

## Dashboard 2 — balance dynamics

Alongside the snapshot dashboard, the skill tracks **daily balance dynamics** and
renders them in a second page, `dashboard_2.html`.

Every time `cmc_update.py` (or `cmc_fetch.py`, which calls it) runs, the flow is:

1. `data/<slug>.json` files are refreshed (normalization).
2. `history_append.append_today()` aggregates all `data/*.json` by
   `(exchange, network, coin)` and appends one row per key for today into
   `data/history.jsonl` (JSON-Lines). Re-running on the same day overwrites
   today's rows — no duplicates. History is forward-only; it grows by one
   day per run.
3. `build_dashboard.py` rebuilds `dashboard.html` (snapshot view, unchanged).
4. `build_dashboard_2.py` rebuilds `dashboard_2.html` (dynamics view).

`dashboard_2.html` is a single self-contained file (Chart.js from CDN) showing:

- **Header KPIs** — total USD today + Δ vs 1d / 7d / 30d (absolute + %).
- **Stacked area chart** — total USD per day, stacked by exchange
  (toggle: all exchanges / only filter-selected).
- **Filter bar** — multi-select exchange / network / coin + a date-range slider
  (default last 30 days, max = full history).
- **Detail line chart** — aggregated USD or token balance over time for the
  current selection; one line per coin (radio: USD / tokens).
- **Delta table** — per `(exchange, network, coin)`: today's balance, USD,
  Δ1d / Δ7d / Δ30d (token amount + USD %, red/green). Sortable, default sort by
  |Δ7d USD| desc, top 50 with a "show all" toggle.

Deltas use the closest snapshot **≤ N days ago** (missing days handled gracefully).
Charts stay flat until 2+ days of history accumulate — that's expected.

Each script is independently runnable:

```bash
python3 history_append.py        # append today's rows to data/history.jsonl
python3 build_dashboard_2.py     # rebuild dashboard_2.html from history.jsonl
```

Present `dashboard_2.html` to the user with `mcp__cowork__present_files` (alongside
`dashboard.html`) when they ask about balance dynamics / history.

## Raw snapshot retention

`cmc_fetch.py` also archives each freshly downloaded raw JSON into
`data/snapshots/YYYY-MM-DD/<slug>.json` (local date, idempotent per day) and prunes
any snapshot folder older than 30 days at the end of the run. Uploads via
`cmc_update.py` do not produce raw snapshots (no raw payload to keep), but they
still append to `data/history.jsonl`.

## Files in this skill

- `SKILL.md` — this file
- `cmc_fetch.py` — downloads raw CMC JSON for all 6 exchanges, archives raw
  snapshots, prunes old ones, then runs `cmc_update.py`
- `cmc_update.py` — parser; appends history, rebuilds both dashboards (entrypoint for uploads)
- `history_append.py` — appends today's per-coin rows to `data/history.jsonl`
- `build_dashboard.py` — snapshot dashboard HTML generator (called by `cmc_update.py`)
- `build_dashboard_2.py` — dynamics dashboard HTML generator (called by `cmc_update.py`)
- `data/` — normalized per-exchange JSONs (persisted across runs)
- `data/history.jsonl` — append-only daily balance history (per coin)
- `data/snapshots/<date>/` — raw CMC JSON archive, 30-day rolling retention
- `dashboard.html` — snapshot dashboard, regenerated on every run
- `dashboard_2.html` — balance-dynamics dashboard, regenerated on every run
