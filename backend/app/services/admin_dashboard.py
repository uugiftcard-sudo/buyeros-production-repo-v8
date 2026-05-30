"""Admin dashboard (server-rendered HTML).

Minimal admin UI for recon + bank import observability.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _escape(s: Any) -> str:
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def render_admin_page(*, title: str, blocks: List[str]) -> str:
    body = "\n".join(blocks)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape(title)}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    :root {{
      --bg: #0a0f1e;
      --surface: #111827;
      --panel: #1a2236;
      --panel-alt: #1e2840;
      --text: #e2e8f0;
      --muted: #64748b;
      --accent: #60a5fa;
      --accent-dim: rgba(96,165,250,0.15);
      --border: rgba(255,255,255,0.07);
      --good: #34d399;
      --good-dim: rgba(52,211,153,0.12);
      --warn: #fbbf24;
      --warn-dim: rgba(251,191,36,0.12);
      --bad: #f87171;
      --bad-dim: rgba(248,113,113,0.12);
      --radius: 10px;
      --shadow: 0 1px 3px rgba(0,0,0,0.3), 0 4px 16px rgba(0,0,0,0.2);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: 'Inter', ui-sans-serif, system-ui, -apple-system; background: var(--bg); color: var(--text); line-height: 1.5; font-size: 13px; }}
    header {{
      background: linear-gradient(135deg, #111827 0%, #1a2236 100%);
      border-bottom: 1px solid var(--border);
      padding: 16px 24px;
      display: flex; justify-content: space-between; align-items: center;
    }}
    header h1 {{ margin: 0; font-size: 15px; font-weight: 700; letter-spacing: -0.2px; color: #fff; }}
    header .meta {{ color: var(--muted); font-size: 11px; letter-spacing: 0.5px; text-transform: uppercase; }}
    main {{ padding: 20px 24px; max-width: 1280px; margin: 0 auto; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .grid-full {{ grid-column: 1 / -1; }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      box-shadow: var(--shadow);
    }}
    .card-header {{
      display: flex; align-items: center; gap: 8px;
      margin-bottom: 14px;
    }}
    .card-header h2 {{ margin: 0; font-size: 11px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; }}
    .dot {{
      width: 7px; height: 7px; border-radius: 50%;
      display: inline-block; flex-shrink: 0;
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}
    .dot.good {{ background: var(--good); box-shadow: 0 0 6px var(--good); }}
    .dot.warn {{ background: var(--warn); box-shadow: 0 0 6px var(--warn); }}
    .dot.bad {{ background: var(--bad); box-shadow: 0 0 6px var(--bad); }}
    .dot.neutral {{ background: var(--muted); animation: none; }}
    .kv {{ display: flex; flex-direction: column; gap: 0; }}
    .kv-row {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 9px 0; border-bottom: 1px solid var(--border); }}
    .kv-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
    .kv-row:first-child {{ padding-top: 0; }}
    .kv .k {{ color: var(--muted); font-size: 12px; min-width: 100px; }}
    .kv .v {{ font-size: 12px; text-align: right; font-weight: 500; overflow-wrap: anywhere; color: var(--text); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    thead tr {{ border-bottom: 1px solid var(--border); }}
    th {{ padding: 6px 10px 8px 0; color: var(--muted); font-weight: 600; font-size: 11px; text-align: left; text-transform: uppercase; letter-spacing: 0.5px; }}
    th:first-child {{ padding-left: 0; }}
    td {{ padding: 9px 10px 9px 0; border-bottom: 1px solid var(--border); vertical-align: top; }}
    td:first-child {{ padding-left: 0; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: rgba(255,255,255,0.02); }}
    tr td:first-child a {{ color: var(--accent); }}
    .pill {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; letter-spacing: 0.3px; }}
    .pill.good {{ color: var(--good); background: var(--good-dim); }}
    .pill.warn {{ color: var(--warn); background: var(--warn-dim); }}
    .pill.bad {{ color: var(--bad); background: var(--bad-dim); }}
    .pill.neutral {{ color: var(--muted); background: rgba(255,255,255,0.05); }}
    .pill.accent {{ color: var(--accent); background: var(--accent-dim); }}
    .mono {{ font-family: 'SF Mono', ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px; }}
    .empty {{ color: var(--muted); font-size: 12px; text-align: center; padding: 16px 0; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .link-btn {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; background: var(--panel-alt); border: 1px solid var(--border); border-radius: 6px; color: var(--accent); font-size: 12px; text-decoration: none; }}
    .link-btn:hover {{ background: var(--accent-dim); text-decoration: none; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>BuyerOS Admin</h1>
    <div class="meta">Recon &amp; Bank Import</div>
  </header>
  <main>
    {body}
  </main>
</body>
</html>"""


def render_kv_card(title: str, rows: Dict[str, Any]) -> str:
    items = "\n".join(
        f"<div class=\"kv-row\"><div class=\"k\">{_escape(k)}</div><div class=\"v mono\">{_escape(v)}</div></div>"
        for k, v in rows.items()
    )
    return f"<section class=\"card\"><div class=\"card-header\"><h2>{_escape(title)}</h2></div><div class=\"kv\">{items}</div></section>"


def render_table_card(title: str, *, headers: List[str], rows: List[List[Any]]) -> str:
    thead = "".join(f"<th>{_escape(h)}</th>" for h in headers)
    if not rows:
        trs = ""
        empty_row = f'<tr><td colspan="{len(headers)}" class="empty">No data</td></tr>'
    else:
        trs = []
        for r in rows:
            tds = "".join(f"<td class=\"mono\">{_escape(c)}</td>" for c in r)
            trs.append(f"<tr>{tds}</tr>")
        empty_row = ""
    tbody = "\n".join(trs) if trs else empty_row
    return f"""<section class="card">
<div class="card-header"><h2>{_escape(title)}</h2></div>
<table>
<thead><tr>{thead}</tr></thead>
<tbody>{tbody}</tbody>
</table>
</section>"""
