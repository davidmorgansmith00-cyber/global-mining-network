"""
HTML report generator for load test results.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_REPORT_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>GMN Load Test Report</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 2em; }}
  h1 {{ color: #333; }}
  .summary {{ background: #f5f5f5; padding: 1em; border-radius: 4px; margin-bottom: 1em; }}
  .metric {{ display: inline-block; margin: 0.5em 1em; }}
  .metric .value {{ font-size: 2em; font-weight: bold; color: {sla_color}; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: right; }}
  th {{ background: #333; color: white; text-align: center; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  .ok {{ color: green; }} .warn {{ color: orange; }} .fail {{ color: red; }}
</style>
</head>
<body>
<h1>GMN Load Test Report</h1>
<div class="summary">
  <div class="metric"><div class="value">{throughput_rps}</div><div>req/s</div></div>
  <div class="metric"><div class="value">{error_rate_pct}%</div><div>Error Rate</div></div>
  <div class="metric"><div class="value">{total_requests}</div><div>Total Requests</div></div>
  <div class="metric"><div class="value">{elapsed_s}s</div><div>Duration</div></div>
  <div class="metric"><div class="value">{sla_status}</div><div>SLA</div></div>
</div>
<h2>Per-Endpoint Breakdown</h2>
<table>
<tr>
  <th>Endpoint</th><th>Total</th><th>Passed</th><th>Failed</th>
  <th>P50 ms</th><th>P95 ms</th><th>P99 ms</th><th>Error Rate</th>
</tr>
{endpoint_rows}
</table>
</body>
</html>
"""

_ROW_TEMPLATE = """\
<tr>
  <td style="text-align:left">{endpoint}</td>
  <td>{total}</td><td>{passed}</td><td class="{fail_class}">{failed}</td>
  <td>{p50}</td><td>{p95}</td><td class="{p99_class}">{p99}</td>
  <td class="{err_class}">{error_rate}%</td>
</tr>"""


def generate_html_report(summary: dict[str, Any], output_path: str) -> None:
    error_rate = summary.get("error_rate", 0)
    throughput = summary.get("throughput_rps", 0)
    total = summary.get("total_requests", 0)
    elapsed = summary.get("elapsed_seconds", 0)

    # SLA: p99 < 1000ms and error_rate < 1%
    sla_ok = error_rate < 0.01
    if sla_ok:
        for ep in summary.get("endpoints", []):
            if ep.get("latency_p99_ms", 0) > 1000:
                sla_ok = False
                break

    sla_color = "#27ae60" if sla_ok else "#e74c3c"
    sla_status = "PASS" if sla_ok else "FAIL"

    rows = []
    for ep in summary.get("endpoints", []):
        ep_total = ep.get("total", 0)
        ep_failed = ep.get("failed", 0)
        ep_rate = ep_failed / ep_total if ep_total else 0
        p99 = ep.get("latency_p99_ms", 0)
        rows.append(
            _ROW_TEMPLATE.format(
                endpoint=ep["endpoint"],
                total=ep_total,
                passed=ep.get("passed", 0),
                failed=ep_failed,
                fail_class="fail" if ep_failed > 0 else "ok",
                p50=ep.get("latency_p50_ms", 0),
                p95=ep.get("latency_p95_ms", 0),
                p99=p99,
                p99_class="fail" if p99 > 1000 else "ok",
                error_rate=f"{ep_rate:.1%}".replace("%", ""),
                err_class="fail" if ep_rate > 0.01 else "ok",
            )
        )

    html = _REPORT_TEMPLATE.format(
        throughput_rps=round(throughput, 1),
        error_rate_pct=round(error_rate * 100, 2),
        total_requests=total,
        elapsed_s=round(elapsed, 1),
        sla_status=sla_status,
        sla_color=sla_color,
        endpoint_rows="\n".join(rows),
    )
    Path(output_path).write_text(html)
