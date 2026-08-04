#!/usr/bin/env python3
"""
Builds a single self-contained HTML dashboard from data/*.json files.

Usage:
    python build_dashboard.py

Reads:  ./data/*.json   (each file = one exchange, schema: {exchange, cmcId, wallets: [...]})
Writes: ./dashboard.html
"""

import json
import glob
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
OUT = HERE / "dashboard.html"


def load_data():
    payload = []
    for path in sorted(glob.glob(str(DATA_DIR / "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        payload.append(obj)
        print(f"  loaded {os.path.basename(path)}: "
              f"{obj.get('exchange')} ({len(obj.get('wallets', []))} wallets)",
              file=sys.stderr)
    return payload


HTML = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>CEX Wallets Dashboard</title>
<style>
:root {
  --bg:#0b0f1a; --panel:#131929; --panel2:#1a2236; --border:#222b44;
  --text:#e7ecf3; --muted:#8a93a6; --accent:#5b8def; --good:#2dd4bf; --warn:#fbbf24;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
* { box-sizing: border-box; }
html, body { margin:0; padding:0; background:var(--bg); color:var(--text);
  font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.app { display:grid; grid-template-columns:320px 1fr; min-height:100vh; }
.sidebar { background:var(--panel); border-right:1px solid var(--border); padding:20px; }
.sidebar h1 { margin:0 0 6px; font-size:16px; }
.sidebar .sub { color:var(--muted); font-size:12px; margin-bottom:18px; }
.group { margin-bottom:14px; }
.group label { display:block; font-size:11px; text-transform:uppercase;
  letter-spacing:.08em; color:var(--muted); margin-bottom:6px; }
.group select, .group input {
  width:100%; padding:9px 10px; background:var(--panel2); color:var(--text);
  border:1px solid var(--border); border-radius:6px; font:inherit; outline:none;
}
.group select:focus, .group input:focus { border-color:var(--accent); }
.main { padding:24px 32px; overflow-x:hidden; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:14px; margin-bottom:24px; }
.card { background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:16px 18px; }
.card .k { color:var(--muted); font-size:11px; text-transform:uppercase;
  letter-spacing:.08em; margin-bottom:6px; }
.card .v { font-size:22px; font-weight:600; font-variant-numeric:tabular-nums; }
.card .v.sm { font-size:14px; }
.section { background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:18px 20px; margin-bottom:18px; }
.section h2 { margin:0 0 12px; font-size:14px; text-transform:uppercase;
  letter-spacing:.08em; color:var(--muted); font-weight:600; }
.actions { display:flex; gap:8px; margin-bottom:10px; flex-wrap:wrap; }
button { background:var(--accent); color:#fff; border:none; padding:8px 14px;
  border-radius:6px; cursor:pointer; font:inherit; font-weight:500; }
button:hover { filter:brightness(1.1); }
button.ghost { background:var(--panel2); color:var(--text); border:1px solid var(--border); }
.addr-list { background:#0a0f1c; border:1px solid var(--border); border-radius:6px;
  padding:10px 12px; font-family:var(--mono); font-size:12.5px; white-space:pre;
  max-height:480px; overflow:auto; }
table { width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }
th, td { padding:8px 10px; text-align:left; border-bottom:1px solid var(--border); }
th { color:var(--muted); font-weight:500; font-size:11px; text-transform:uppercase;
  letter-spacing:.06em; }
td.addr { font-family:var(--mono); font-size:12px; word-break:break-all; }
td.num { text-align:right; font-family:var(--mono); }
.empty { color:var(--muted); padding:18px; text-align:center; }
.copied { color:var(--good); font-size:12px; margin-left:8px; }
.dim { color:var(--muted); }
.row-count { color:var(--muted); margin-left:8px; font-weight:normal; font-size:12px; }
</style>
</head>
<body>
<div class="app">
  <div class="sidebar">
    <h1>CEX Wallets</h1>
    <div class="sub">CoinMarketCap Proof of Reserves</div>

    <div class="group">
      <label>Биржа</label>
      <select id="f-exchange"></select>
    </div>

    <div class="group">
      <label>Блокчейн</label>
      <select id="f-network"></select>
    </div>

    <div class="group">
      <label>Монета (name)</label>
      <select id="f-token"></select>
    </div>

    <div class="group">
      <label>Поиск по адресу</label>
      <input id="f-search" type="search" placeholder="часть адреса...">
    </div>

    <div class="group" style="margin-top:24px;">
      <button class="ghost" id="reset" style="width:100%">Сбросить фильтры</button>
    </div>

    <div class="group" style="margin-top:24px; font-size:11px; color:var(--muted);">
      <div id="meta"></div>
    </div>
  </div>

  <div class="main">
    <div class="cards">
      <div class="card"><div class="k">Итого, USD</div><div class="v" id="kpi-usd">$0</div></div>
      <div class="card"><div class="k">Сумма balance (нативный)</div><div class="v" id="kpi-bal">0</div></div>
      <div class="card"><div class="k">Уникальных кошельков</div><div class="v" id="kpi-wallets">0</div></div>
      <div class="card"><div class="k">Записей</div><div class="v" id="kpi-rows">0</div></div>
    </div>

    <div class="section">
      <h2>Список кошельков <span class="row-count" id="addr-count"></span></h2>
      <div class="actions">
        <button id="copy-all">Скопировать все адреса</button>
        <button class="ghost" id="copy-uniq">Только уникальные</button>
        <button class="ghost" id="dl-csv">Скачать CSV</button>
        <span class="copied" id="copied-msg"></span>
      </div>
      <pre class="addr-list" id="addr-list"></pre>
    </div>

    <div class="section">
      <h2>Детали по записям</h2>
      <div style="max-height:420px; overflow:auto;">
        <table id="rows-table">
          <thead><tr>
            <th>Адрес</th><th>Network</th><th>Token</th>
            <th class="num">Balance</th><th class="num">Price USD</th><th class="num">Value USD</th>
          </tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<script>
const DATA = __DATA_PLACEHOLDER__;

const $ = sel => document.querySelector(sel);
const fmtUsd = n => '$' + (n||0).toLocaleString('en-US',{maximumFractionDigits:2});
const fmtNum = (n,d=4) => (n||0).toLocaleString('en-US',{maximumFractionDigits:d});

function unique(arr) { return [...new Set(arr)]; }

function populate(sel, items, allLabel) {
  sel.innerHTML = '';
  const opt0 = document.createElement('option');
  opt0.value = '__ALL__'; opt0.textContent = allLabel;
  sel.appendChild(opt0);
  for (const it of items) {
    const o = document.createElement('option');
    o.value = it; o.textContent = it;
    sel.appendChild(o);
  }
}

function buildExchanges() {
  populate($('#f-exchange'), DATA.map(d => d.exchange), 'Все биржи');
}

function selectedRows() {
  const ex  = $('#f-exchange').value;
  const net = $('#f-network').value;
  const tok = $('#f-token').value;
  const q   = ($('#f-search').value || '').trim().toLowerCase();
  let rows = [];
  for (const d of DATA) {
    if (ex !== '__ALL__' && d.exchange !== ex) continue;
    for (const w of d.wallets) {
      if (net !== '__ALL__' && w.network !== net) continue;
      if (tok !== '__ALL__' && w.name    !== tok) continue;
      if (q && !w.walletAddress.toLowerCase().includes(q)) continue;
      rows.push({...w, exchange: d.exchange});
    }
  }
  return rows;
}

function refreshSubFilters() {
  // фильтры подстраиваются под выбранную биржу
  const ex = $('#f-exchange').value;
  const pool = DATA.filter(d => ex === '__ALL__' || d.exchange === ex)
                  .flatMap(d => d.wallets);
  const networks = unique(pool.map(w => w.network)).sort();
  const tokens   = unique(pool.map(w => w.name)).sort();
  const prevNet = $('#f-network').value;
  const prevTok = $('#f-token').value;
  populate($('#f-network'), networks, 'Все сети');
  populate($('#f-token'),   tokens,   'Все токены');
  if (networks.includes(prevNet)) $('#f-network').value = prevNet;
  if (tokens.includes(prevTok))   $('#f-token').value   = prevTok;
}

function render() {
  const rows = selectedRows();
  const totalUsd  = rows.reduce((s,r)=>s + r.balance * r.priceUsd, 0);
  const totalBal  = rows.reduce((s,r)=>s + r.balance, 0);
  const addresses = rows.map(r => r.walletAddress);
  const uniqAddrs = unique(addresses);

  $('#kpi-usd').textContent     = fmtUsd(totalUsd);
  $('#kpi-bal').textContent     = fmtNum(totalBal, 2);
  $('#kpi-wallets').textContent = uniqAddrs.length;
  $('#kpi-rows').textContent    = rows.length;

  // зависит от тогла uniq
  const mode = window.__uniqMode ? uniqAddrs : addresses;
  $('#addr-list').textContent = mode.join('\n');
  $('#addr-count').textContent = `(${mode.length})`;

  // таблица
  const tbody = $('#rows-table tbody');
  tbody.innerHTML = '';
  for (const r of rows.slice(0, 1000)) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="addr">${r.walletAddress}</td>
      <td>${r.network}</td>
      <td>${r.name}</td>
      <td class="num">${fmtNum(r.balance,4)}</td>
      <td class="num">${fmtUsd(r.priceUsd)}</td>
      <td class="num">${fmtUsd(r.balance * r.priceUsd)}</td>`;
    tbody.appendChild(tr);
  }
  if (rows.length > 1000) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td colspan="6" class="empty dim">... +${rows.length-1000} записей не показано (фильтруй точнее)</td>`;
    tbody.appendChild(tr);
  }
  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty">Ничего не найдено</td></tr>`;
  }
}

function copyText(t, btn) {
  navigator.clipboard.writeText(t).then(()=>{
    const m = $('#copied-msg');
    m.textContent = '✓ скопировано (' + t.split('\n').length + ' строк)';
    setTimeout(()=>m.textContent='', 2500);
  });
}

function downloadCsv() {
  const rows = selectedRows();
  const head = ['exchange','walletAddress','network','name','balance','priceUsd','valueUsd','updateTime'];
  const lines = [head.join(',')];
  for (const r of rows) {
    lines.push([r.exchange, r.walletAddress, r.network, r.name,
                r.balance, r.priceUsd, (r.balance*r.priceUsd).toFixed(2),
                r.updateTime || ''].join(','));
  }
  const blob = new Blob([lines.join('\n')], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  const ex = $('#f-exchange').value, net = $('#f-network').value, tok = $('#f-token').value;
  a.download = `wallets_${ex}_${net}_${tok}.csv`.replaceAll('__ALL__','all');
  a.click();
}

document.addEventListener('DOMContentLoaded', () => {
  buildExchanges();
  refreshSubFilters();
  render();

  // meta info
  const total = DATA.reduce((s,d)=>s+d.wallets.length, 0);
  $('#meta').textContent = `${DATA.length} биржа(и), ${total} записей всего`;

  $('#f-exchange').addEventListener('change', ()=>{ refreshSubFilters(); render(); });
  $('#f-network').addEventListener('change', render);
  $('#f-token').addEventListener('change', render);
  $('#f-search').addEventListener('input', render);
  $('#reset').addEventListener('click', ()=>{
    $('#f-exchange').value = '__ALL__';
    refreshSubFilters();
    $('#f-network').value = '__ALL__';
    $('#f-token').value   = '__ALL__';
    $('#f-search').value  = '';
    render();
  });
  $('#copy-all').addEventListener('click', e => {
    window.__uniqMode = false; render();
    copyText($('#addr-list').textContent, e.target);
  });
  $('#copy-uniq').addEventListener('click', e => {
    window.__uniqMode = true; render();
    copyText($('#addr-list').textContent, e.target);
  });
  $('#dl-csv').addEventListener('click', downloadCsv);
});
</script>
</body>
</html>
"""


def main():
    data = load_data()
    if not data:
        print("No JSON files in data/. Aborting.", file=sys.stderr)
        sys.exit(1)
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = HTML.replace("__DATA_PLACEHOLDER__", js)
    OUT.write_text(html, encoding="utf-8")
    total = sum(len(d["wallets"]) for d in data)
    print(f"OK: {OUT} ({len(html):,} chars, {len(data)} exchange(s), {total} wallets)")


if __name__ == "__main__":
    main()
