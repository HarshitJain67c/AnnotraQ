from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any, Mapping


def _score_class(score: float) -> str:
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 60:
        return "warning"
    return "poor"


def render_html(report: Mapping[str, Any], title: str = "AnnotraQ benchmark") -> str:
    summary = report["summary"]
    dimensions = summary["dimensions"]
    dimension_cards = "".join(
        f"""
        <article class="metric">
          <div class="metric-label">{escape(name.replace('_', ' ').title())}</div>
          <div class="metric-value">{value:.1f}</div>
          <div class="bar"><span style="width:{max(0, min(100, value)):.1f}%"></span></div>
        </article>
        """
        for name, value in dimensions.items()
    )
    slice_rows = "".join(
        f"<tr><td>{escape(name.replace('_', ' ').title())}</td><td>{values['count']}</td>"
        f"<td>{values['overall_score']:.2f}</td><td><span class='grade {_score_class(values['overall_score'])}'>{values['grade']}</span></td></tr>"
        for name, values in report["slices"].items()
    )
    item_rows = "".join(
        f"""
        <tr>
          <td><code>{escape(str(item['id']))}</code></td>
          <td>{escape(item['task'].replace('_', ' ').title())}</td>
          <td class="number">{item['overall_score']:.2f}</td>
          <td><span class="grade {_score_class(item['overall_score'])}">{item['grade']}</span></td>
          <td class="number">{item['scores']['accuracy']:.1f}</td>
          <td class="number">{item['scores']['completeness']:.1f}</td>
          <td class="number">{item['scores']['consistency']:.1f}</td>
          <td class="number">{item['scores']['format_validity']:.1f}</td>
          <td>{escape('; '.join(item['errors']) or '—')}</td>
        </tr>
        """
        for item in report["items"]
    )
    weights = ", ".join(f"{name.replace('_', ' ')} {value:.0%}" for name, value in report["weights"].items())
    low, high = summary["confidence_interval_95"]
    safe_title = escape(title)
    metadata = escape(json.dumps({"schema_version": report["schema_version"], "generated_at": report["generated_at"]}))
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="AnnotraQ annotation quality benchmark report">
  <title>{safe_title}</title>
  <style>
    :root {{ --ink:#151625; --muted:#666a7c; --paper:#f6f7fb; --card:#fff; --line:#e5e7f0; --brand:#6757e7; --brand2:#31b7a4; --danger:#d84b63; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; color:var(--ink); background:var(--paper); font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    .wrap {{ width:min(1180px,calc(100% - 32px)); margin:0 auto; }}
    header {{ color:#fff; background:linear-gradient(125deg,#1f174b,#4936c7 58%,#179b91); padding:58px 0 72px; }}
    .eyebrow {{ margin:0 0 10px; color:#cfc9ff; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }}
    h1 {{ margin:0; font-size:clamp(32px,6vw,58px); line-height:1; letter-spacing:-.04em; }}
    header p {{ max-width:680px; margin:18px 0 0; color:#ebeaff; font-size:17px; }}
    main {{ margin-top:-38px; padding-bottom:48px; }}
    .hero-card,.panel,.metric {{ background:var(--card); border:1px solid var(--line); border-radius:18px; box-shadow:0 10px 35px rgba(27,24,68,.07); }}
    .hero-card {{ display:grid; grid-template-columns:190px 1fr; gap:28px; align-items:center; padding:26px; }}
    .score {{ display:grid; place-items:center; width:150px; height:150px; border-radius:50%; background:conic-gradient(var(--brand) {summary['overall_score']:.1f}%,#e9e8f4 0); position:relative; }}
    .score::after {{ content:""; position:absolute; inset:13px; background:#fff; border-radius:50%; }}
    .score strong {{ z-index:1; font-size:35px; letter-spacing:-.05em; }}
    .score small {{ z-index:1; margin-top:-48px; color:var(--muted); }}
    .summary h2 {{ margin:0 0 4px; font-size:30px; }}
    .summary p {{ margin:5px 0; color:var(--muted); }}
    .grade {{ display:inline-grid; min-width:30px; place-items:center; border-radius:999px; padding:3px 9px; font-weight:800; }}
    .excellent {{ color:#116d60; background:#ddf7f0; }} .good {{ color:#3d319e; background:#ebe8ff; }}
    .warning {{ color:#8e5d00; background:#fff1cb; }} .poor {{ color:#9f243a; background:#ffe1e7; }}
    .metrics {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:22px 0; }}
    .metric {{ padding:18px; box-shadow:none; }} .metric-label {{ color:var(--muted); font-size:13px; }}
    .metric-value {{ margin:4px 0 10px; font-size:28px; font-weight:800; }}
    .bar {{ height:7px; overflow:hidden; background:#ececf4; border-radius:99px; }} .bar span {{ display:block; height:100%; background:linear-gradient(90deg,var(--brand),var(--brand2)); }}
    .panel {{ margin-top:18px; padding:22px; overflow:hidden; box-shadow:none; }}
    h3 {{ margin:0 0 14px; font-size:20px; }} .table-wrap {{ overflow:auto; }}
    table {{ width:100%; border-collapse:collapse; white-space:nowrap; }}
    th,td {{ padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ color:var(--muted); font-size:12px; letter-spacing:.05em; text-transform:uppercase; }}
    td:last-child {{ max-width:360px; white-space:normal; }} .number {{ font-variant-numeric:tabular-nums; }}
    code {{ color:#4032a7; background:#f0eefe; border-radius:5px; padding:2px 5px; }}
    footer {{ padding:4px 0 36px; color:var(--muted); font-size:13px; }}
    @media (max-width:760px) {{ .hero-card {{ grid-template-columns:1fr; }} .score {{ margin:auto; }} .metrics {{ grid-template-columns:repeat(2,1fr); }} }}
    @media (max-width:430px) {{ .metrics {{ grid-template-columns:1fr; }} .wrap {{ width:min(100% - 20px,1180px); }} }}
  </style>
</head>
<body>
  <header><div class="wrap"><p class="eyebrow">Annotation quality intelligence</p><h1>AnnotraQ</h1><p>{safe_title}</p></div></header>
  <main class="wrap">
    <section class="hero-card">
      <div class="score"><strong>{summary['overall_score']:.1f}</strong><small>/ 100</small></div>
      <div class="summary">
        <h2>Grade <span class="grade {_score_class(summary['overall_score'])}">{summary['grade']}</span></h2>
        <p>{summary['item_count']} annotations · 95% bootstrap interval {low:.2f}–{high:.2f}</p>
        <p>Weights: {escape(weights)}</p>
      </div>
    </section>
    <section class="metrics">{dimension_cards}</section>
    <section class="panel"><h3>Performance by task</h3><div class="table-wrap"><table><thead><tr><th>Task</th><th>Items</th><th>Score</th><th>Grade</th></tr></thead><tbody>{slice_rows}</tbody></table></div></section>
    <section class="panel"><h3>Item-level audit</h3><div class="table-wrap"><table><thead><tr><th>ID</th><th>Task</th><th>Score</th><th>Grade</th><th>Accuracy</th><th>Complete</th><th>Consistent</th><th>Format</th><th>Issues</th></tr></thead><tbody>{item_rows}</tbody></table></div></section>
  </main>
  <footer class="wrap">Generated by AnnotraQ · {metadata}</footer>
</body>
</html>
"""
    return "\n".join(line.rstrip() for line in document.splitlines()) + "\n"


def write_html(path: str | Path, report: Mapping[str, Any], title: str = "AnnotraQ benchmark") -> None:
    Path(path).write_text(render_html(report, title), encoding="utf-8")
