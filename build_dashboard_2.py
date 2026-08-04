#!/usr/bin/env python3
"""
Builds dashboard_2.html — a balance-dynamics view — from data/history.jsonl.

Usage:
    python3 build_dashboard_2.py

Reads:  ./data/history.jsonl   (one JSON row per (date, exchange, network, coin))
Writes: ./dashboard_2.html

Self-contained single HTML file. Charts via Chart.js from CDN. No build step.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
HISTORY = DATA_DIR / "history.jsonl"
OUT = HERE / "dashboard_2.html"


def load_history():
    rows = []
    if not HISTORY.exists():
        return rows
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


HTML = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CEX Balance Dynamics</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root {
  --bg:#0b0f1a; --panel:#131929; --panel2:#1a2236; --border:#222b44;
  --text:#e7ecf3; --muted:#8a93a6; --accent:#5b8def; --good:#2dd4bf; --warn:#fbbf24;
  --bad:#f87171;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
* { box-sizing: border-box; }
html, body { margin:0; padding:0; background:var(--bg); color:var(--text);
  font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.wrap { max-width:1440px; margin:0 auto; padding:24px 32px; }
h1 { margin:0 0 4px; font-size:18px; }
.sub { color:var(--muted); font-size:12px; margin-bottom:20px; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:14px; margin-bottom:22px; }
.card { background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:16px 18px; }
.card .k { color:var(--muted); font-size:11px; text-transform:uppercase;
  letter-spacing:.08em; margin-bottom:6px; }
.card .v { font-size:22px; font-weight:600; font-variant-numeric:tabular-nums; }
.card .d { font-size:12.5px; margin-top:6px; font-variant-numeric:tabular-nums; }
.section { background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:18px 20px; margin-bottom:18px; }
.section h2 { margin:0 0 12px; font-size:13px; text-transform:uppercase;
  letter-spacing:.08em; color:var(--muted); font-weight:600;
  display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
.chart-box { position:relative; height:340px; }
.chart-box.sm { height:300px; }
.filters { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:16px; align-items:start; }
.filters .group label { display:block; font-size:11px; text-transform:uppercase;
  letter-spacing:.08em; color:var(--muted); margin-bottom:6px; }
select[multiple] { width:100%; min-height:120px; background:var(--panel2); color:var(--text);
  border:1px solid var(--border); border-radius:6px; font:inherit; padding:4px; outline:none; }
select[multiple]:focus { border-color:var(--accent); }
.daterange { display:flex; flex-direction:column; gap:8px; }
.daterange input[type=range] { width:100%; accent-color:var(--accent); }
.daterange .lbl { font-variant-numeric:tabular-nums; font-size:12.5px; color:var(--text); }
.toggle { display:inline-flex; gap:6px; }
.toggle button, .seg button { background:var(--panel2); color:var(--text);
  border:1px solid var(--border); padding:5px 12px; border-radius:6px; cursor:pointer;
  font:inherit; font-size:12px; }
.toggle button.active, .seg button.active { background:var(--accent); color:#fff;
  border-color:var(--accent); }
.seg { display:inline-flex; gap:6px; margin-left:auto; }
button.ghost { background:var(--panel2); color:var(--text); border:1px solid var(--border);
  padding:6px 12px; border-radius:6px; cursor:pointer; font:inherit; font-size:12px; }
button.ghost:hover { filter:brightness(1.15); }
table { width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }
th, td { padding:8px 10px; text-align:left; border-bottom:1px solid var(--border);
  white-space:nowrap; }
th { color:var(--muted); font-weight:500; font-size:11px; text-transform:uppercase;
  letter-spacing:.06em; cursor:pointer; user-select:none; }
th.num, td.num { text-align:right; font-family:var(--mono); }
th .arrow { color:var(--accent); }
.pos { color:var(--good); }
.neg { color:var(--bad); }
.muted { color:var(--muted); }
.empty { color:var(--muted); padding:24px; text-align:center; }
.nav { font-size:12px; margin-bottom:16px; }
.nav a { color:var(--accent); text-decoration:none; }
</style>
</head>
<body>
<div class="wrap">
  <h1>CEX Balance Dynamics</h1>
  <div class="sub" id="sub">CoinMarketCap Proof of Reserves — динамика балансов</div>
  <div class="nav"><a href="dashboard.html">← К дашборду кошельков</a></div>

  <div class="cards" id="kpis"></div>

  <div class="section">
    <h2>Суммарный баланс по дням (USD, стек по биржам)
      <span class="seg" id="area-toggle">
        <button data-mode="all" class="active">Все биржи</button>
        <button data-mode="sel">Только выбранные</button>
      </span>
    </h2>
    <div class="chart-box"><canvas id="areaChart"></canvas></div>
  </div>

  <div class="section">
    <h2>Фильтры</h2>
    <div class="filters">
      <div class="group">
        <label>Биржа</label>
        <select id="f-exchange" multiple></select>
      </div>
      <div class="group">
        <label>Сеть</label>
        <select id="f-network" multiple></select>
      </div>
      <div class="group">
        <label>Монета</label>
        <select id="f-coin" multiple></select>
      </div>
      <div class="group">
        <label>Период</label>
        <div class="daterange">
          <div class="lbl"><span id="d-from"></span> → <span id="d-to"></span></div>
          <input type="range" id="r-from" min="0" max="0" value="0">
          <input type="range" id="r-to" min="0" max="0" value="0">
          <button class="ghost" id="reset">Сбросить фильтры</button>
        </div>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>Динамика по выбору
      <span class="seg" id="metric-toggle">
        <button data-metric="usd" class="active">USD</button>
        <button data-metric="balance">Токены</button>
      </span>
    </h2>
    <div class="chart-box sm"><canvas id="detailChart"></canvas></div>
  </div>

  <div class="section">
    <h2>Изменения по (биржа · сеть · монета)
      <span class="row-count muted" id="tbl-count"></span>
      <span class="seg"><button class="ghost" id="show-all">Показать все</button></span>
    </h2>
    <div style="max-height:560px; overflow:auto;">
      <table id="delta-table">
        <thead><tr>
          <th data-sort="exchange">Биржа</th>
          <th data-sort="network">Сеть</th>
          <th data-sort="coin">Монета</th>
          <th class="num" data-sort="balance">Баланс</th>
          <th class="num" data-sort="usd">USD</th>
          <th class="num" data-sort="d1tok">Δ1d ток</th>
          <th class="num" data-sort="d1pct">Δ1d %</th>
          <th class="num" data-sort="d7tok">Δ7d ток</th>
          <th class="num" data-sort="d7usd">Δ7d USD</th>
          <th class="num" data-sort="d7pct">Δ7d %</th>
          <th class="num" data-sort="d30tok">Δ30d ток</th>
          <th class="num" data-sort="d30pct">Δ30d %</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const ROWS = __DATA_PLACEHOLDER__;

const $ = s => document.querySelector(s);
const palette = ['#5b8def','#2dd4bf','#fbbf24','#f87171','#a78bfa','#34d399',
                 '#f472b6','#60a5fa','#fb923c','#c084fc','#4ade80','#e879f9'];

const fmtUsd = n => '$' + (n||0).toLocaleString('en-US',{maximumFractionDigits:0});
const fmtUsd2 = n => '$' + (n||0).toLocaleString('en-US',{maximumFractionDigits:2});
const fmtTok = n => (n||0).toLocaleString('en-US',{maximumFractionDigits:4});
const fmtPct = n => (n>=0?'+':'') + (n||0).toFixed(2) + '%';
const fmtSignedUsd = n => (n>=0?'+':'') + fmtUsd(n);
const fmtSignedTok = n => (n>=0?'+':'') + fmtTok(n);
const uniq = a => [...new Set(a)];
const cls = n => n>0 ? 'pos' : (n<0 ? 'neg' : 'muted');

// ---- index data -------------------------------------------------------
const DATES = uniq(ROWS.map(r => r.date)).sort();
const LAST = DATES[DATES.length-1];
const EXCHANGES = uniq(ROWS.map(r => r.exchange)).sort();
const NETWORKS = uniq(ROWS.map(r => r.network)).sort();
const COINS = uniq(ROWS.map(r => r.coin)).sort();

function dayOffset(dateStr, n) {
  const d = new Date(dateStr + 'T00:00:00');
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0,10);
}
// closest available date <= target
function dateAtOrBefore(target) {
  let best = null;
  for (const d of DATES) { if (d <= target) best = d; else break; }
  return best;
}

// ---- filter state -----------------------------------------------------
function getSel(id) {
  return [...$(id).selectedOptions].map(o => o.value);
}
function filterState() {
  const ex = getSel('#f-exchange'), net = getSel('#f-network'), coin = getSel('#f-coin');
  const fromIdx = +$('#r-from').value, toIdx = +$('#r-to').value;
  const lo = Math.min(fromIdx, toIdx), hi = Math.max(fromIdx, toIdx);
  return { ex, net, coin, from: DATES[lo], to: DATES[hi] };
}
function rowPass(r, st, useDate=true) {
  if (st.ex.length && !st.ex.includes(r.exchange)) return false;
  if (st.net.length && !st.net.includes(r.network)) return false;
  if (st.coin.length && !st.coin.includes(r.coin)) return false;
  if (useDate && (r.date < st.from || r.date > st.to)) return false;
  return true;
}

// ---- KPIs (global, all exchanges) ------------------------------------
function usdByDate(rows) {
  const m = {};
  for (const r of rows) m[r.date] = (m[r.date]||0) + r.usd;
  return m;
}
function renderKpis() {
  const byDate = usdByDate(ROWS);
  const today = byDate[LAST] || 0;
  const card = (k,v,d='') => `<div class="card"><div class="k">${k}</div>
    <div class="v">${v}</div>${d?`<div class="d">${d}</div>`:''}</div>`;
  const deltaStr = n => {
    const base = byDate[dateAtOrBefore(dayOffset(LAST,n))];
    if (base === undefined || base === null) return '<span class="muted">нет данных</span>';
    const abs = today - base, pct = base ? abs/base*100 : 0;
    return `<span class="${cls(abs)}">${fmtSignedUsd(abs)} (${fmtPct(pct)})</span>`;
  };
  $('#kpis').innerHTML =
    card('Итого USD (сегодня)', fmtUsd(today), LAST) +
    card('Δ за 1 день', '', deltaStr(1)) +
    card('Δ за 7 дней', '', deltaStr(7)) +
    card('Δ за 30 дней', '', deltaStr(30));
}

// ---- stacked area chart ----------------------------------------------
let areaChart, detailChart;
let areaMode = 'all';
function renderArea() {
  const st = filterState();
  const exList = (areaMode === 'sel' && st.ex.length) ? st.ex : EXCHANGES;
  const labels = DATES.filter(d => d >= st.from && d <= st.to);
  const datasets = exList.map((ex,i) => {
    const m = {};
    for (const r of ROWS) if (r.exchange === ex) m[r.date] = (m[r.date]||0) + r.usd;
    return {
      label: ex,
      data: labels.map(d => m[d] || 0),
      backgroundColor: palette[i % palette.length] + 'cc',
      borderColor: palette[i % palette.length],
      borderWidth: 1, fill: true, pointRadius: 0, tension: 0.25,
    };
  });
  const cfg = {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#8a93a6', boxWidth: 12 } },
        tooltip: { callbacks: { label: c => c.dataset.label + ': ' + fmtUsd2(c.parsed.y) } },
      },
      scales: {
        x: { stacked: true, ticks: { color: '#8a93a6' }, grid: { color: '#222b44' } },
        y: { stacked: true, ticks: { color: '#8a93a6', callback: v => fmtUsd(v) },
             grid: { color: '#222b44' } },
      },
    },
  };
  if (areaChart) { areaChart.data = cfg.data; areaChart.update(); }
  else areaChart = new Chart($('#areaChart'), cfg);
}

// ---- detail line chart (one line per coin in scope) -------------------
let metric = 'usd';
function renderDetail() {
  const st = filterState();
  const labels = DATES.filter(d => d >= st.from && d <= st.to);
  // coins in scope (respect filters); cap to top 12 by latest value
  const scopeRows = ROWS.filter(r => rowPass(r, st));
  const coinTotals = {};
  for (const r of scopeRows) coinTotals[r.coin] = (coinTotals[r.coin]||0) + r[metric];
  const coins = Object.keys(coinTotals).sort((a,b)=>coinTotals[b]-coinTotals[a]).slice(0,12);
  const datasets = coins.map((coin,i) => {
    const m = {};
    for (const r of scopeRows) if (r.coin === coin) m[r.date] = (m[r.date]||0) + r[metric];
    return {
      label: coin,
      data: labels.map(d => m[d] ?? null),
      borderColor: palette[i % palette.length],
      backgroundColor: palette[i % palette.length],
      borderWidth: 2, pointRadius: 0, tension: 0.25, spanGaps: true, fill: false,
    };
  });
  const fmt = metric === 'usd' ? fmtUsd : fmtTok;
  const fmt2 = metric === 'usd' ? fmtUsd2 : fmtTok;
  const cfg = {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#8a93a6', boxWidth: 12 } },
        tooltip: { callbacks: { label: c => c.dataset.label + ': ' + fmt2(c.parsed.y) } },
      },
      scales: {
        x: { ticks: { color: '#8a93a6' }, grid: { color: '#222b44' } },
        y: { ticks: { color: '#8a93a6', callback: v => fmt(v) }, grid: { color: '#222b44' } },
      },
    },
  };
  if (detailChart) { detailChart.data = cfg.data; detailChart.update(); }
  else detailChart = new Chart($('#detailChart'), cfg);
}

// ---- delta table ------------------------------------------------------
let sortKey = 'd7usd', sortDir = -1, showAll = false;
function buildTableData() {
  const st = filterState();
  // group by key across full history (deltas need older dates regardless of range)
  const keyed = {};
  for (const r of ROWS) {
    if (!rowPass(r, st, false)) continue;
    const k = r.exchange + '|' + r.network + '|' + r.coin;
    (keyed[k] = keyed[k] || {}).meta = { exchange:r.exchange, network:r.network, coin:r.coin };
    (keyed[k].byDate = keyed[k].byDate || {})[r.date] = r;
  }
  const out = [];
  for (const k in keyed) {
    const { meta, byDate } = keyed[k];
    const cur = byDate[LAST];
    if (!cur) continue;
    const at = n => byDate[dateAtOrBefore(dayOffset(LAST,n))] || null;
    const b1 = at(1), b7 = at(7), b30 = at(30);
    const dtok = b => b ? cur.balance - b.balance : null;
    const dusdv = b => b ? cur.usd - b.usd : null;
    const dpct = b => (b && b.usd) ? (cur.usd - b.usd)/b.usd*100 : null;
    out.push({
      exchange: meta.exchange, network: meta.network, coin: meta.coin,
      balance: cur.balance, usd: cur.usd,
      d1tok: dtok(b1), d1pct: dpct(b1),
      d7tok: dtok(b7), d7usd: dusdv(b7), d7pct: dpct(b7),
      d30tok: dtok(b30), d30pct: dpct(b30),
    });
  }
  return out;
}
function renderTable() {
  let data = buildTableData();
  data.sort((a,b) => {
    let va = a[sortKey], vb = b[sortKey];
    if (typeof va === 'string') return sortDir * va.localeCompare(vb);
    va = (va==null) ? -Infinity : va; vb = (vb==null) ? -Infinity : vb;
    if (sortKey === 'd7usd' && sortDir === -1) { va = Math.abs(a.d7usd??0); vb = Math.abs(b.d7usd??0); }
    return sortDir * (va - vb);
  });
  const total = data.length;
  if (!showAll) data = data.slice(0, 50);
  const tbody = $('#delta-table tbody');
  const tokCell = v => v==null ? '<td class="num muted">—</td>'
    : `<td class="num ${cls(v)}">${fmtSignedTok(v)}</td>`;
  const usdCell = v => v==null ? '<td class="num muted">—</td>'
    : `<td class="num ${cls(v)}">${fmtSignedUsd(v)}</td>`;
  const pctCell = v => v==null ? '<td class="num muted">—</td>'
    : `<td class="num ${cls(v)}">${fmtPct(v)}</td>`;
  tbody.innerHTML = data.map(r => `<tr>
    <td>${r.exchange}</td><td>${r.network}</td><td>${r.coin}</td>
    <td class="num">${fmtTok(r.balance)}</td>
    <td class="num">${fmtUsd(r.usd)}</td>
    ${tokCell(r.d1tok)}${pctCell(r.d1pct)}
    ${tokCell(r.d7tok)}${usdCell(r.d7usd)}${pctCell(r.d7pct)}
    ${tokCell(r.d30tok)}${pctCell(r.d30pct)}
  </tr>`).join('') || `<tr><td colspan="12" class="empty">Нет данных под фильтр</td></tr>`;
  $('#tbl-count').textContent = showAll
    ? `(все ${total})` : `(топ ${Math.min(50,total)} из ${total})`;
  $('#show-all').textContent = showAll ? 'Показать топ-50' : 'Показать все';
  document.querySelectorAll('#delta-table th').forEach(th => {
    const base = th.textContent.replace(/ ?[▲▼]$/,'');
    th.innerHTML = base + (th.dataset.sort === sortKey
      ? ` <span class="arrow">${sortDir<0?'▼':'▲'}</span>` : '');
  });
}

// ---- wiring -----------------------------------------------------------
function fillSelect(id, items) {
  $(id).innerHTML = items.map(i => `<option value="${i}">${i}</option>`).join('');
}
function renderAll() { renderArea(); renderDetail(); renderTable(); }

document.addEventListener('DOMContentLoaded', () => {
  $('#sub').textContent = `CoinMarketCap Proof of Reserves — динамика балансов · `
    + `${DATES.length} дн., ${ROWS.length} строк, обновлено ${LAST}`;
  fillSelect('#f-exchange', EXCHANGES);
  fillSelect('#f-network', NETWORKS);
  fillSelect('#f-coin', COINS);

  const maxIdx = DATES.length - 1;
  const rf = $('#r-from'), rt = $('#r-to');
  rf.max = rt.max = maxIdx; rt.value = maxIdx;
  // default last 30 days
  let startIdx = DATES.findIndex(d => d >= dayOffset(LAST, 30));
  if (startIdx < 0) startIdx = 0;
  rf.value = startIdx;
  const lbl = () => {
    const lo = Math.min(+rf.value,+rt.value), hi = Math.max(+rf.value,+rt.value);
    $('#d-from').textContent = DATES[lo]; $('#d-to').textContent = DATES[hi];
  };
  lbl();

  renderKpis();
  renderAll();

  ['#f-exchange','#f-network','#f-coin'].forEach(s =>
    $(s).addEventListener('change', renderAll));
  [rf, rt].forEach(s => s.addEventListener('input', () => { lbl(); renderAll(); }));

  $('#reset').addEventListener('click', () => {
    ['#f-exchange','#f-network','#f-coin'].forEach(s =>
      [...$(s).options].forEach(o => o.selected = false));
    rf.value = startIdx; rt.value = maxIdx; lbl(); renderAll();
  });
  $('#area-toggle').addEventListener('click', e => {
    if (e.target.tagName !== 'BUTTON') return;
    areaMode = e.target.dataset.mode;
    $('#area-toggle').querySelectorAll('button').forEach(b =>
      b.classList.toggle('active', b === e.target));
    renderArea();
  });
  $('#metric-toggle').addEventListener('click', e => {
    if (e.target.tagName !== 'BUTTON') return;
    metric = e.target.dataset.metric;
    $('#metric-toggle').querySelectorAll('button').forEach(b =>
      b.classList.toggle('active', b === e.target));
    renderDetail();
  });
  document.querySelectorAll('#delta-table th').forEach(th => {
    th.addEventListener('click', () => {
      const k = th.dataset.sort;
      if (sortKey === k) sortDir = -sortDir;
      else { sortKey = k; sortDir = (k==='exchange'||k==='network'||k==='coin') ? 1 : -1; }
      renderTable();
    });
  });
  $('#show-all').addEventListener('click', () => { showAll = !showAll; renderTable(); });
});
</script>
</body>
</html>
"""


def main():
    rows = load_history()
    if not rows:
        # Still emit a valid page so the file always exists.
        placeholder = (
            "<!doctype html><meta charset='utf-8'>"
            "<body style='background:#0b0f1a;color:#e7ecf3;font-family:sans-serif;"
            "padding:40px'><h1>CEX Balance Dynamics</h1>"
            "<p>Нет данных истории. Запусти <code>cmc_fetch.py</code> или "
            "<code>cmc_update.py</code>, чтобы накопить "
            "<code>data/history.jsonl</code>.</p>"
            "<p><a style='color:#5b8def' href='dashboard.html'>← К дашборду кошельков</a></p>"
        )
        OUT.write_text(placeholder, encoding="utf-8")
        print(f"OK (empty): {OUT} — history.jsonl has no rows yet", file=sys.stderr)
        return
    js = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    html = HTML.replace("__DATA_PLACEHOLDER__", js)
    OUT.write_text(html, encoding="utf-8")
    dates = sorted({r["date"] for r in rows})
    print(f"OK: {OUT} ({len(html):,} chars, {len(rows)} rows, "
          f"{len(dates)} day(s) {dates[0]}..{dates[-1]})")


if __name__ == "__main__":
    main()
