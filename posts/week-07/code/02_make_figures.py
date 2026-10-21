"""Rebuild both Plotly figures and article numbers from the saved official data."""

import csv
from datetime import datetime
import json
from pathlib import Path

import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = ROOT / "results"
CLEAN = ROOT / "data/processed"
OUT.mkdir(exist_ok=True)
CLEAN.mkdir(exist_ok=True)


def read_csv(name):
    with (RAW / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def save_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


# Keep the published Overall observation separate from the 73 major observations.
original = read_csv("college-labor-outcomes-by-major-data.csv")
rows = []
for row in original:
    rows.append(
        {
            "major": row["Major"],
            "unemployment": float(row["Unemployment Rate"]),
            "underemployment": float(row["Underemployment Rate"]),
            "wage": float(row["Median Wage Early Career"]),
        }
    )
assert all(all(v == v for k, v in row.items() if k != "major") for row in rows)
overall = next(row for row in rows if row["major"] == "Overall")
majors = sorted(
    [row for row in rows if row["major"] != "Overall"], key=lambda row: row["major"]
)
assert len({row["major"] for row in majors}) == len(majors)


def memberships(row):
    high_pay = row["wage"] > overall["wage"]
    low_unemployment = row["unemployment"] < overall["unemployment"]
    return [
        True,
        high_pay,
        high_pay and low_unemployment,
        low_unemployment and row["underemployment"] > overall["underemployment"],
    ]


for row in majors:
    row["filters"] = memberships(row)
save_csv(
    CLEAN / "majors.csv",
    [{k: v for k, v in row.items() if k != "filters"} for row in majors],
)
counts = [sum(row["filters"][i] for row in majors) for i in range(4)]
save_csv(
    OUT / "filter_counts.csv",
    [
        {"filter": label, "count": count}
        for label, count in zip(
            [
                "All majors",
                "Higher pay",
                "Higher pay and lower unemployment",
                "Lower unemployment and higher underemployment",
            ],
            counts,
        )
    ],
)

# Parse dates explicitly: the original file uses month/day/year.
trend = read_csv("college-labor-unemployment-data.csv")
for row in trend:
    row["Date"] = datetime.strptime(row["Date"], "%m/%d/%Y").date().isoformat()
    for key in [
        "Young workers",
        "All workers",
        "Recent graduates",
        "College graduates",
    ]:
        row[key] = float(row[key])
trend.sort(key=lambda row: row["Date"])
save_csv(CLEAN / "unemployment.csv", trend)
latest = trend[-1]
first = trend[0]
metrics = {
    "all": counts[0],
    "higher_pay": counts[1],
    "higher_pay_low_unemployment": counts[2],
    "contrast": counts[3],
    "all_three": sum(
        row["filters"][2] and row["underemployment"] < overall["underemployment"]
        for row in majors
    ),
    "recent_latest": latest["Recent graduates"],
    "young_latest": latest["Young workers"],
    "all_latest": latest["All workers"],
    "recent_first": first["Recent graduates"],
    "all_first": first["All workers"],
    "overall_wage": overall["wage"],
    "overall_unemployment": overall["unemployment"],
    "overall_underemployment": overall["underemployment"],
}
for name, prefix in [
    ("Computer Science", "cs"),
    ("Computer Engineering", "ce"),
    ("Nursing", "nursing"),
    ("Agriculture", "ag"),
    ("Criminal Justice", "cj"),
]:
    row = next(row for row in majors if row["major"] == name)
    for key in ["wage", "unemployment", "underemployment"]:
        metrics[f"{prefix}_{key}"] = row[key]
save_csv(OUT / "metrics.csv", [{"metric": k, "value": v} for k, v in metrics.items()])
(OUT / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")

STYLE = """<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;font:15px system-ui;color:#243547}label{display:block;font-weight:600;margin-bottom:5px}select{width:100%;padding:9px;font:inherit;border:1px solid #a8b8c4;border-radius:5px;background:white} .controls{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:8px}#status{margin:10px;min-height:42px;font-size:14px} @media(max-width:520px){.controls{grid-template-columns:1fr}}</style>"""
CONFIG = {"responsive": True, "displaylogo": False, "displayModeBar": False}


def save_html(figure, name, identifier, controls="", script=None):
    html = figure.to_html(
        include_plotlyjs="plotly.min.js",
        full_html=True,
        div_id=identifier,
        config=CONFIG,
        post_script=script,
    )
    html = html.replace("<head>", "<head>" + STYLE).replace(
        "<body>", "<body>" + controls
    )
    (OUT / name).write_text(html, encoding="utf-8")


# The fixed date window allows recent changes to be compared before zooming out.
fig = go.Figure()
for key, label, color in [
    ("Recent graduates", "Recent graduates (22–27)", "#126c82"),
    ("Young workers", "No bachelor's degree (22–27)", "#c47635"),
    ("All workers", "All workers (16–65)", "#6e7181"),
]:
    fig.add_trace(
        go.Scatter(
            x=[r["Date"] for r in trend],
            y=[r[key] for r in trend],
            name=label,
            mode="lines",
            line={"color": color, "width": 2.5},
            hovertemplate="%{x|%b %Y}: %{y:.1f}%<extra>%{fullData.name}</extra>",
        )
    )
fig.update_layout(
    template="plotly_white",
    height=500,
    margin={"l": 55, "r": 15, "t": 95, "b": 35},
    font={"family": "Arial", "size": 12},
    hovermode="x unified",
    legend={"orientation": "h", "y": 1.30, "x": 0},
    yaxis={"title": "Unemployment (%)", "rangemode": "tozero"},
    xaxis={
        "range": ["2016-01-01", latest["Date"]],
        "rangeslider": {"visible": True, "thickness": 0.12},
    },
)
controls = '<div style="margin:8px"><label for="period">Time range</label><select id="period"><option value="2016-01-01">Since 2016</option><option value="1990-01-01">Full history</option><option value="2020-01-01">Since 2020</option></select></div>'
script = (
    'document.getElementById("period").addEventListener("change", function(){Plotly.relayout("trend", {"xaxis.range":[this.value,'
    + json.dumps(latest["Date"])
    + "]});});"
)
save_html(fig, "01_trend.html", "trend", controls, script)

# A single state update reads both selectors, so changing either preserves the other.
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=[r["unemployment"] for r in majors],
        y=[r["wage"] for r in majors],
        mode="markers",
        customdata=[[r["major"], r["underemployment"]] for r in majors],
        marker={
            "size": 11,
            "color": [r["underemployment"] for r in majors],
            "colorscale": "Viridis",
            "cmin": 0,
            "cmax": 80,
            "showscale": True,
            "colorbar": {
                "orientation": "h",
                "title": {
                    "text": "Underemployment (%)",
                    "side": "top",
                    "font": {"size": 12},
                },
                "x": 0.5,
                "xanchor": "center",
                "y": -0.30,
                "yanchor": "top",
                "len": 0.95,
                "thickness": 12,
                "tickvals": [0, 20, 40, 60, 80],
                "tickangle": 0,
            },
        },
        hovertemplate="<b>%{customdata[0]}</b><br>Unemployment: %{x:.1f}%<br>Early-career wage: $%{y:,.0f}<br>Underemployment: %{customdata[1]:.1f}%<extra></extra>",
        showlegend=False,
    )
)
fig.add_trace(
    go.Scatter(
        x=[],
        y=[],
        mode="markers",
        marker={
            "size": 19,
            "color": "#bb3e03",
            "symbol": "circle-open",
            "line": {"width": 3},
        },
        hoverinfo="skip",
        showlegend=False,
    )
)
fig.add_vline(x=overall["unemployment"], line_dash="dot", line_color="#aab4be")
fig.add_hline(y=overall["wage"], line_dash="dot", line_color="#aab4be")
fig.update_layout(
    template="plotly_white",
    height=510,
    margin={"l": 65, "r": 20, "t": 15, "b": 125},
    font={"family": "Arial", "size": 12},
    xaxis={"title": "Unemployment (%)", "range": [0, 10]},
    yaxis={
        "title": "Early-career annual wage ($)",
        "range": [25000, 100000],
        "tickformat": ",.0f",
    },
)
controls = '<div class="controls"><div><label for="preset">Compare conditions</label><select id="preset"><option value="0">All majors</option><option value="1">Higher pay</option><option value="2">Higher pay + lower unemployment</option><option value="3">Lower unemployment + higher underemployment</option></select></div><div><label for="major">Highlight a major</label><select id="major"><option value="">None</option>'
controls += "".join(
    f'<option value="{i}">{r["major"]}</option>' for i, r in enumerate(majors)
)
controls += '</select></div></div><p id="status" aria-live="polite"></p>'
script = (
    "const majors = "
    + json.dumps(majors)
    + ";"
    + """
function updateMajors(){
    const preset = Number(document.getElementById('preset').value);
    const selected = document.getElementById('major').value;
    const shown = majors.filter(r => r.filters[preset]);
    const chosen = selected === '' ? null : majors[Number(selected)];
    Plotly.restyle('majors', {x:[shown.map(r=>r.unemployment)], y:[shown.map(r=>r.wage)],
        customdata:[shown.map(r=>[r.major,r.underemployment])],
        'marker.color':[shown.map(r=>r.underemployment)]}, [0]);
    const inside = chosen && chosen.filters[preset];
    Plotly.restyle('majors', {x:[inside ? [chosen.unemployment] : []],
        y:[inside ? [chosen.wage] : []]}, [1]);
    let message = shown.length + ' of ' + majors.length + ' majors meet this condition.';
    if(chosen) message += inside ? ' Highlighted: ' + chosen.major + '.' : ' ' + chosen.major + ' is outside this filter; choose All majors to see it.';
    document.getElementById('status').textContent = message;
}
document.getElementById('preset').addEventListener('change', updateMajors);
document.getElementById('major').addEventListener('change', updateMajors);
updateMajors();
"""
)
save_html(fig, "02_majors.html", "majors", controls, script)
print("Filter counts:", counts)
print("Latest month:", latest["Date"])
