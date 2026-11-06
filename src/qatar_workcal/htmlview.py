"""A small self-contained HTML page with one table."""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Sequence

CSS = """
:root { --bg: #fbfbf8; --fg: #1d2327; --muted: #5f6b73; --line: #dfe3e6; --bar: #3f7d6e;
        --bad: #b3261e; --warn: #a15c00; --ok: #2e7d32; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #15191c; --fg: #e6e8ea; --muted: #9aa5ad; --line: #2c3338; --bar: #6fb5a3;
          --bad: #f2867e; --warn: #f0b35c; --ok: #81c784; }
}
body { background: var(--bg); color: var(--fg); font: 14px/1.45 system-ui, sans-serif; margin: 24px auto;
       max-width: 1100px; padding: 0 16px; }
h1 { font-size: 20px; margin-bottom: 4px; }
p { color: var(--muted); margin-top: 0; }
.wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; }
th, td { border-bottom: 1px solid var(--line); padding: 6px 8px; text-align: left; white-space: nowrap; }
th { color: var(--muted); font-weight: 600; }
.bar { background: var(--bar); height: 10px; border-radius: 2px; display: inline-block; vertical-align: middle;
       margin-right: 6px; }
.breached td:last-child { color: var(--bad); font-weight: 600; }
.at-risk td:last-child, .paused td:last-child { color: var(--warn); }
.met td:last-child { color: var(--ok); }
.ramadan { background: color-mix(in srgb, var(--bar) 10%, transparent); }
"""


def page(title: str, notes: Sequence[str], headers: Sequence[str], rows: Sequence[Sequence[object]],
         row_classes: Sequence[str] | None = None, bar_column: int | None = None) -> str:
    peak = max((float(r[bar_column]) for r in rows), default=0) if bar_column is not None else 0
    body = []
    for i, row in enumerate(rows):
        cls = row_classes[i] if row_classes else ""
        cells = []
        for j, value in enumerate(row):
            text = escape("" if value is None else str(value))
            if j == bar_column and peak:
                width = round(160 * float(value) / peak)
                text = f'<span class="bar" style="width:{width}px"></span>{text}'
            cells.append(f"<td>{text}</td>")
        body.append(f'<tr class="{escape(cls)}">{"".join(cells)}</tr>')
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    note_html = "".join(f"<p>{escape(n)}</p>" for n in notes)
    return (
        f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title><style>{CSS}</style></head><body>"
        f"<h1>{escape(title)}</h1>{note_html}"
        f'<div class="wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
        f"</body></html>\n"
    )


def write_page(path: str | Path, html: str) -> None:
    Path(path).write_text(html, encoding="utf-8")
