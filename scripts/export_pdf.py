#!/usr/bin/env python3
"""Export ASX screener HTML report to PDF using Playwright/Chromium."""

import sys
import os
import asyncio
from pathlib import Path

SRC = Path("/Users/secondmind/claudecodetest/reports/asx_screener_report.html")
DST = Path("/Users/secondmind/claudecodetest/data/asx_screener_report_product.pdf")
DST.parent.mkdir(parents=True, exist_ok=True)

DISCLAIMER_TEXT = (
    "General information only. Not financial advice. "
    "Not to be relied upon for investment decisions."
)

PRINT_CSS = f"""
<style>
  @page {{
    size: A4;
    margin: 14mm 14mm 26mm 14mm;
  }}

  /* Force backgrounds to print */
  * {{
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}

  /* Page footer disclaimer injected as fixed element */
  body::after {{
    content: none;
  }}

  /* Avoid page breaks inside cards and table rows */
  .card, .stat-card, tr {{
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  /* Prevent sticky thead from floating off-page */
  thead {{ position: static !important; }}

  /* Ensure full-width on A4 */
  main {{ max-width: 100%; padding: 20px 24px; }}
  header {{ padding: 24px 24px 20px; }}
  footer {{ padding: 12px 24px; }}
  .cards {{ grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); }}
  .criteria-bar {{ flex-wrap: wrap; }}
  .criterion {{ min-width: 160px; }}

  /* Hide scrollbar styles */
  ::-webkit-scrollbar {{ display: none; }}
</style>

<!-- PDF disclaimer footer bar -->
<style>
  .pdf-footer-bar {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #161b22;
    border-top: 1px solid #30363d;
    padding: 6px 48px;
    font-size: 10px;
    color: #8b949e;
    text-align: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    z-index: 9999;
  }}
  .pdf-footer-bar b {{ color: #f0883e; }}
</style>
"""

FOOTER_HTML = f"""
<div class="pdf-footer-bar">
  <b>DISCLAIMER:</b> {DISCLAIMER_TEXT}
</div>
"""

html = SRC.read_text(encoding="utf-8")

# Inject print CSS before </head>
html = html.replace("</head>", PRINT_CSS + "\n</head>")

# Inject footer before </body>
html = html.replace("</body>", FOOTER_HTML + "\n</body>")

# Write modified HTML to a temp file
tmp_html = DST.parent / "_tmp_report_print.html"
tmp_html.write_text(html, encoding="utf-8")

async def generate_pdf():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file://{tmp_html}", wait_until="networkidle")
        await page.pdf(
            path=str(DST),
            format="A4",
            print_background=True,
            margin={
                "top": "14mm",
                "right": "14mm",
                "bottom": "26mm",
                "left": "14mm",
            },
            display_header_footer=True,
            footer_template=f"""
                <div style="width:100%; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
                            font-size:8px; color:#8b949e; text-align:center;
                            border-top:1px solid #30363d; padding-top:3px; margin:0 14mm;">
                    <b style="color:#f0883e;">DISCLAIMER:</b> {DISCLAIMER_TEXT}
                    &nbsp;&nbsp;&nbsp; Page <span class="pageNumber"></span> of <span class="totalPages"></span>
                </div>
            """,
            header_template="<span></span>",
        )
        await browser.close()

print(f"Converting: {SRC.name} → {DST.name}")
asyncio.run(generate_pdf())

# Clean up temp file
tmp_html.unlink(missing_ok=True)

size = DST.stat().st_size
size_kb = size / 1024
size_mb = size / (1024 * 1024)
print(f"PDF written: {DST}")
print(f"File size: {size_kb:.1f} KB ({size:,} bytes)")

# Count pages via pdfinfo or strings grep
import subprocess
result = subprocess.run(["pdfinfo", str(DST)], capture_output=True, text=True)
if result.returncode == 0:
    for line in result.stdout.splitlines():
        if "Pages" in line:
            print(f"Page count: {line.strip()}")
else:
    # Rough estimate: typical A4 HTML doc ~2-6 pages
    print("Page count: open in Preview to verify (pdfinfo not installed)")

print("Done.")
