"""
benchmark_report.py - Generate a visual HTML report from benchmark results
Run: python benchmark_report.py
Opens report in your browser automatically.
"""

import json
import os
import webbrowser
from datetime import datetime

RESULTS_FILE = "data/benchmark_results.json"
REPORT_FILE  = "data/benchmark_report.html"


def load_results() -> list:
    if not os.path.exists(RESULTS_FILE):
        print("No benchmark results found. Run: python benchmark.py first.")
        return []
    with open(RESULTS_FILE) as f:
        return json.load(f)


def generate_html(results: list) -> str:
    rows_latency = ""
    rows_rag     = ""
    rows_detail  = ""

    for i, r in enumerate(results, 1):
        ts      = r.get("timestamp", "")[:19].replace("T", " ")
        latency = r.get("latency", {})
        rag     = r.get("rag", {})

        # Latency row
        if latency:
            local_avg = latency.get("local_avg_seconds", "-")
            api_avg   = latency.get("api_avg_seconds",   "-")
            faster    = latency.get("faster", "-")
            diff      = latency.get("difference_seconds", "-")

            local_style = "color:#22c55e;font-weight:bold;" if faster == "Local" else ""
            api_style   = "color:#22c55e;font-weight:bold;" if faster == "API"   else ""

            rows_latency += f"""
            <tr>
                <td>{i}</td>
                <td>{ts}</td>
                <td style="{local_style}">{local_avg}s</td>
                <td style="{api_style}">{api_avg}s</td>
                <td class="badge {'green' if faster == 'Local' else 'blue'}">{faster}</td>
                <td>{diff}s faster</td>
            </tr>"""

        # RAG row
        if rag:
            faiss_acc   = rag.get("faiss_accuracy_pct",   "-")
            kw_acc      = rag.get("keyword_accuracy_pct", "-")
            faiss_hits  = rag.get("faiss_hits",    "-")
            kw_hits     = rag.get("keyword_hits",  "-")
            total       = rag.get("total_queries", "-")
            winner      = "FAISS" if (isinstance(faiss_acc, (int,float)) and isinstance(kw_acc, (int,float)) and faiss_acc >= kw_acc) else "Keyword"

            faiss_style = "color:#22c55e;font-weight:bold;" if winner == "FAISS"   else ""
            kw_style    = "color:#22c55e;font-weight:bold;" if winner == "Keyword" else ""

            rows_rag += f"""
            <tr>
                <td>{i}</td>
                <td>{ts}</td>
                <td style="{faiss_style}">{faiss_acc}%</td>
                <td style="{kw_style}">{kw_acc}%</td>
                <td>{faiss_hits}/{total}</td>
                <td>{kw_hits}/{total}</td>
                <td class="badge {'green' if winner == 'FAISS' else 'yellow'}">{winner}</td>
            </tr>"""

            # Detail rows
            for j, d in enumerate(rag.get("details", []), 1):
                faiss_found = d.get("faiss_found", False)
                kw_found    = d.get("keyword_found", False)
                query       = d.get("query", "")[:60]
                faiss_ms    = d.get("faiss_ms", "-")
                kw_ms       = d.get("keyword_ms", "-")

                faiss_cell = '<span class="badge green">FOUND</span>'   if faiss_found else '<span class="badge red">MISSED</span>'
                kw_cell    = '<span class="badge green">FOUND</span>'   if kw_found    else '<span class="badge red">MISSED</span>'

                rows_detail += f"""
                <tr>
                    <td>{i}.{j}</td>
                    <td>{ts}</td>
                    <td style="font-size:12px">{query}...</td>
                    <td>{faiss_cell}</td>
                    <td>{faiss_ms}ms</td>
                    <td>{kw_cell}</td>
                    <td>{kw_ms}ms</td>
                </tr>"""

    # Compute overall stats
    all_latency = [r["latency"] for r in results if r.get("latency")]
    all_rag     = [r["rag"]     for r in results if r.get("rag")]

    overall_local = sum(r.get("local_avg_seconds",0) for r in all_latency) / len(all_latency) if all_latency else 0
    overall_api   = sum(r.get("api_avg_seconds",0)   for r in all_latency) / len(all_latency) if all_latency else 0
    overall_faiss = sum(r.get("faiss_accuracy_pct",0) for r in all_rag)    / len(all_rag)     if all_rag     else 0
    overall_kw    = sum(r.get("keyword_accuracy_pct",0) for r in all_rag)  / len(all_rag)     if all_rag     else 0

    generated_at = datetime.now().strftime("%B %d, %Y %I:%M %p")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orchestrix AI Benchmark Report</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; padding: 32px; }}
  h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 4px; color: #f8fafc; }}
  .subtitle {{ color: #94a3b8; font-size: 14px; margin-bottom: 32px; }}
  h2 {{ font-size: 18px; font-weight: 600; margin: 32px 0 12px; color: #cbd5e1; border-left: 4px solid #6366f1; padding-left: 12px; }}
  h3 {{ font-size: 15px; font-weight: 600; margin: 24px 0 8px; color: #94a3b8; }}

  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 32px; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px 24px; min-width: 180px; flex: 1; }}
  .card .label {{ font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }}
  .card .value {{ font-size: 28px; font-weight: 700; }}
  .card .value.green {{ color: #22c55e; }}
  .card .value.blue  {{ color: #60a5fa; }}
  .card .value.purple{{ color: #a78bfa; }}
  .card .value.yellow{{ color: #facc15; }}

  table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; margin-bottom: 32px; }}
  th {{ background: #0f172a; color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; padding: 12px 16px; text-align: left; }}
  td {{ padding: 12px 16px; border-top: 1px solid #334155; font-size: 14px; vertical-align: middle; }}
  tr:hover td {{ background: #263147; }}

  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
  .badge.green  {{ background: #14532d; color: #22c55e; }}
  .badge.blue   {{ background: #1e3a5f; color: #60a5fa; }}
  .badge.yellow {{ background: #422006; color: #facc15; }}
  .badge.red    {{ background: #450a0a; color: #f87171; }}
  .badge.purple {{ background: #2e1065; color: #a78bfa; }}

  .footer {{ margin-top: 48px; color: #475569; font-size: 12px; text-align: center; }}
  .section {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
</style>
</head>
<body>

<h1>Orchestrix AI — Benchmark Report</h1>
<p class="subtitle">Generated: {generated_at} &nbsp;|&nbsp; Total benchmark runs: {len(results)}</p>

<!-- Summary Cards -->
<div class="cards">
  <div class="card">
    <div class="label">Local (Llama3) Avg</div>
    <div class="value {'green' if overall_local < overall_api else 'yellow'}">{overall_local:.2f}s</div>
  </div>
  <div class="card">
    <div class="label">API (Gemini) Avg</div>
    <div class="value {'green' if overall_api < overall_local else 'yellow'}">{overall_api:.2f}s</div>
  </div>
  <div class="card">
    <div class="label">Speed Winner</div>
    <div class="value purple">{'Local' if overall_local < overall_api else 'API'}</div>
  </div>
  <div class="card">
    <div class="label">FAISS Accuracy</div>
    <div class="value green">{overall_faiss:.0f}%</div>
  </div>
  <div class="card">
    <div class="label">Keyword Accuracy</div>
    <div class="value blue">{overall_kw:.0f}%</div>
  </div>
  <div class="card">
    <div class="label">RAG Winner</div>
    <div class="value purple">{'FAISS' if overall_faiss >= overall_kw else 'Keyword'}</div>
  </div>
</div>

<!-- Latency Table -->
<h2>Latency Benchmark — Local vs API</h2>
<table>
  <thead>
    <tr>
      <th>#</th>
      <th>Timestamp</th>
      <th>Local (Llama3)</th>
      <th>API (Gemini)</th>
      <th>Winner</th>
      <th>Difference</th>
    </tr>
  </thead>
  <tbody>
    {rows_latency if rows_latency else '<tr><td colspan="6" style="text-align:center;color:#475569">No latency data yet. Run: python benchmark.py --latency</td></tr>'}
  </tbody>
</table>

<!-- RAG Summary Table -->
<h2>RAG Accuracy Benchmark — FAISS vs Keyword Search</h2>
<table>
  <thead>
    <tr>
      <th>#</th>
      <th>Timestamp</th>
      <th>FAISS Accuracy</th>
      <th>Keyword Accuracy</th>
      <th>FAISS Hits</th>
      <th>Keyword Hits</th>
      <th>Winner</th>
    </tr>
  </thead>
  <tbody>
    {rows_rag if rows_rag else '<tr><td colspan="7" style="text-align:center;color:#475569">No RAG data yet. Run: python benchmark.py --rag --pdf yourfile.pdf</td></tr>'}
  </tbody>
</table>

<!-- Query Detail Table -->
<h2>RAG Query Detail — Per Query Results</h2>
<table>
  <thead>
    <tr>
      <th>#</th>
      <th>Run</th>
      <th>Query</th>
      <th>FAISS</th>
      <th>FAISS Time</th>
      <th>Keyword</th>
      <th>Keyword Time</th>
    </tr>
  </thead>
  <tbody>
    {rows_detail if rows_detail else '<tr><td colspan="7" style="text-align:center;color:#475569">No query detail data yet.</td></tr>'}
  </tbody>
</table>

<div class="footer">
  Orchestrix AI Benchmark Tool &nbsp;|&nbsp; Results from data/benchmark_results.json
</div>

</body>
</html>"""

    return html


def main():
    results = load_results()
    if not results:
        return

    html = generate_html(results)

    os.makedirs("data", exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    abs_path = os.path.abspath(REPORT_FILE)
    print(f"Report saved to: {abs_path}")
    webbrowser.open(f"file:///{abs_path}")  
    print("Opened in browser.")


if __name__ == "__main__":
    main()