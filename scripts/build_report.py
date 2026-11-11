"""Build 02_Report/AmlanAcharya_Capstone_Report.pdf from the Markdown source.

Figures are generated from the committed validation run; the PDF is printed by headless Chrome (puppeteer).
Usage: python scripts/build_report.py <validation.db>
"""
import html
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "02_Report" / "AmlanAcharya_Capstone_Report.md"
OUT_HTML = ROOT / "02_Report" / "_report.html"
OUT_PDF = ROOT / "02_Report" / "AmlanAcharya_Capstone_Report.pdf"
REPORT = json.loads((ROOT / "evaluation" / "validation_report.json").read_text(encoding="utf-8"))

INK, BLUE, RED, GREY, GREEN = "#0f172a", "#1d4ed8", "#dc2626", "#94a3b8", "#059669"


def fig_outcomes() -> str:
    v = REPORT["volume"]
    parts = [("Auto-resolved", v["auto_resolved"], GREEN), ("Guardrail veto", v["escalated_guardrail"], "#d97706"),
             ("Router escalation", v["escalated_router"], BLUE), ("Provider fallback", v["escalated_error"], GREY)]
    total = v["total_tickets"]
    x, w_total, y = 20, 640, 40
    out = [f'<svg viewBox="0 0 700 150" class="fig" role="img" aria-label="Outcome of 80 validation tickets">']
    for label, n, col in parts:
        w = w_total * n / total
        out.append(f'<rect x="{x}" y="{y}" width="{w:.1f}" height="40" fill="{col}"/>')
        out.append(f'<text x="{x + w / 2:.1f}" y="{y + 25}" fill="#fff" font-size="14" text-anchor="middle" font-weight="700">{n}</text>')
        out.append(f'<text x="{x:.1f}" y="{y + 62}" fill="{INK}" font-size="12">{label}</text>')
        x += w
    out.append(f'<text x="20" y="25" fill="{INK}" font-size="13" font-weight="700">80 validation tickets: where each ended up</text>')
    out.append(f'<text x="20" y="130" fill="{GREY}" font-size="11">Source: evaluation/validation_report.json (final configuration, run 3)</text>')
    out.append("</svg>")
    return "".join(out)


def fig_similarity(db: str) -> str:
    rows = sqlite3.connect(db).execute("select top_retrieval_score from decision_log").fetchall()
    vals = [r[0] for r in rows]
    nb = 20  # 0.05-wide bins
    bins = [0] * nb
    for s in vals:
        bins[min(int(max(s, 0) * nb), nb - 1)] += 1
    mx = max(bins)
    x0, y0, bw, h = 40, 170, 28, 130
    out = ['<svg viewBox="0 0 640 215" class="fig" role="img" aria-label="Retrieval similarity histogram">']
    for i, c in enumerate(bins):
        bh = h * c / mx
        col = GREEN if i >= 8 else BLUE  # bin 8 starts at 0.40
        out.append(f'<rect x="{x0 + i * bw}" y="{y0 - bh:.1f}" width="{bw - 3}" height="{bh:.1f}" fill="{col}"/>')
        if c:
            out.append(f'<text x="{x0 + i * bw + (bw - 3) / 2}" y="{y0 - bh - 4:.1f}" font-size="10" text-anchor="middle" fill="{INK}">{c}</text>')
        if i % 2 == 0:
            out.append(f'<text x="{x0 + i * bw}" y="{y0 + 14}" font-size="10" text-anchor="middle" fill="{INK}">{i / nb:.1f}</text>')
    tx = x0 + 13 * bw - 1.5
    out.append(f'<line x1="{tx}" y1="34" x2="{tx}" y2="{y0}" stroke="{RED}" stroke-width="2" stroke-dasharray="5 3"/>')
    out.append(f'<text x="{tx - 6}" y="46" font-size="12" fill="{RED}" font-weight="700" text-anchor="end">original floor 0.65</text>')
    t4 = x0 + 8 * bw - 1.5
    out.append(f'<line x1="{t4}" y1="34" x2="{t4}" y2="{y0}" stroke="{INK}" stroke-width="2"/>')
    out.append(f'<text x="{t4 + 6}" y="46" font-size="12" fill="{INK}" font-weight="700">current floor 0.40</text>')
    out.append(f'<text x="{x0}" y="22" font-size="13" font-weight="700" fill="{INK}">Top retrieval similarity per ticket (0.05 bins, lower edge)</text>')
    out.append(f'<text x="{x0}" y="205" font-size="11" fill="{GREY}">n = {len(vals)}; green bars clear the current 0.40 floor</text>')
    out.append("</svg>")
    return "".join(out)


CSS = """
@page { size: A4; margin: 24mm 22mm 24mm 22mm; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; color: #111827; }
h1 { font-size: 24pt; margin: 0 0 4pt; line-height: 1.15; }
h2 { font-size: 17pt; margin-top: 26pt; border-bottom: 1.5px solid #1d4ed8; padding-bottom: 3pt; page-break-after: avoid; }
h2 + h3, h3 { font-size: 13pt; margin-top: 16pt; page-break-after: avoid; }
p { margin: 0 0 9pt; text-align: justify; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: 8pt 0 14pt; page-break-inside: auto; }
th, td { border: 1px solid #cbd5e1; padding: 4pt 6pt; vertical-align: top; text-align: left; }
th { background: #eff6ff; }
tr { page-break-inside: avoid; }
code { font-family: Consolas, monospace; font-size: 9.5pt; background: #f1f5f9; padding: 0 2pt; }
pre { background: #f8fafc; border: 1px solid #e2e8f0; padding: 8pt; font-size: 8.6pt; line-height: 1.3; overflow-x: auto; page-break-inside: avoid; white-space: pre-wrap; }
pre code { background: none; padding: 0; }
.fig { width: 100%; max-width: 640px; display: block; margin: 8pt auto 14pt; font-family: Arial, sans-serif; }
strong em, p > strong:only-child { }
hr { border: none; border-top: 1px solid #e5e7eb; margin: 14pt 0; }
"""


def main() -> None:
    db = sys.argv[1]
    text = SRC.read_text(encoding="utf-8")
    text = text.replace("{{FIG2}}", fig_outcomes()).replace("{{FIG3}}", fig_similarity(db))
    # protect math from the markdown parser
    math: list[str] = []

    def stash(m):
        math.append(m.group(0))
        return f"@@MATH{len(math) - 1}@@"

    text = re.sub(r"\$\$.+?\$\$|\$[^$\n]+?\$", stash, text, flags=re.S)
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    body = body.replace('<pre><code class="language-mermaid">', '<pre class="mermaid">').replace("</code></pre>", "</code></pre>")
    body = re.sub(r'(<pre class="mermaid">)(.*?)</code></pre>', lambda m: m.group(1) + m.group(2) + "</pre>", body, flags=re.S)
    for i, m in enumerate(math):
        body = body.replace(f"@@MATH{i}@@", html.escape(m, quote=False))
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>CloudServe Support Orchestrator - Capstone Report</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<style>{CSS}pre.mermaid {{ background: #fff; border: none; text-align: center; padding: 0; break-inside: avoid; }} p:has(+ pre.mermaid) {{ break-after: avoid; }} pre.mermaid svg {{ max-height: 215mm; width: auto; }}</style></head><body>{body}
<script>document.addEventListener('DOMContentLoaded',async()=>{{mermaid.initialize({{startOnLoad:false,theme:'neutral',flowchart:{{htmlLabels:true}}}});await mermaid.run({{querySelector:'pre.mermaid'}});renderMathInElement(document.body,{{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}}],throwOnError:false}});document.body.dataset.ready='1';}});</script>
</body></html>"""
    OUT_HTML.write_text(page, encoding="utf-8")
    subprocess.run(["node", str(ROOT / "scripts" / "html_to_pdf.js"), str(OUT_HTML), str(OUT_PDF)], check=True)
    import os
    if not os.environ.get("KEEP_HTML"):
        OUT_HTML.unlink()
    print("wrote", OUT_PDF)


if __name__ == "__main__":
    main()
