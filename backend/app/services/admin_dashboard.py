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
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{_escape(title)}</title>
  <style>
    :root {{
      --bg: #0b1020;
      --panel: #121a33;
      --text: #e8ecff;
      --muted: #a7b0d6;
      --accent: #7aa2ff;
      --border: rgba(255,255,255,0.08);
      --good: #38d996;
      --warn: #ffcc66;
      --bad: #ff6b6b;
    }}
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system; background: var(--bg); color: var(--text); }}
    header {{ padding: 18px 20px; border-bottom: 1px solid var(--border); display:flex; justify-content:space-between; align-items:center; }}
    header h1 {{ margin:0; font-size: 16px; letter-spacing:0.2px; }}
    header .meta {{ color: var(--muted); font-size: 12px; }}
    main {{ padding: 18px 20px; max-width: 1200px; margin: 0 auto; }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 14px; }}
    .card h2 {{ margin:0 0 10px 0; font-size: 14px; }}
    .row {{ display:flex; justify-content:space-between; gap:12px; padding: 8px 0; border-bottom:1px solid var(--border); }}
    .row:last-child {{ border-bottom:none; }}
    .k {{ color: var(--muted); font-size: 12px; }}
    .v {{ font-size: 12px; text-align:right; overflow-wrap:anywhere; }}
    table {{ width:100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ padding: 8px; border-bottom: 1px solid var(--border); text-align:left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; }}
    .pill {{ display:inline-block; padding: 2px 8px; border-radius:999px; border:1px solid var(--border); font-size: 12px; }}
    .pill.good {{ color: var(--good); }}
    .pill.warn {{ color: var(--warn); }}
    .pill.bad {{ color: var(--bad); }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>BuyerOS Admin</h1>
    <div class=\"meta\">Recon & Bank Import</div>
  </header>
  <main>
    {body}
  </main>
</body>
</html>"""


def render_kv_card(title: str, rows: Dict[str, Any]) -> str:
    items = "\n".join(
        f"<div class=\"row\"><div class=\"k\">{_escape(k)}</div><div class=\"v mono\">{_escape(v)}</div></div>"
        for k, v in rows.items()
    )
    return f"<section class=\"card\"><h2>{_escape(title)}</h2>{items}</section>"


def render_table_card(title: str, *, headers: List[str], rows: List[List[Any]]) -> str:
    thead = "".join(f"<th>{_escape(h)}</th>" for h in headers)
    trs = []
    for r in rows:
        tds = "".join(f"<td class=\"mono\">{_escape(c)}</td>" for c in r)
        trs.append(f"<tr>{tds}</tr>")
    tbody = "\n".join(trs)
    return f"""<section class=\"card\">
<h2>{_escape(title)}</h2>
<table>
<thead><tr>{thead}</tr></thead>
<tbody>{tbody}</tbody>
</table>
</section>"""
