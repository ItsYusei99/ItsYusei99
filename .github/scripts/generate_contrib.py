#!/usr/bin/env python3
"""Generate progressive contribution-grid animation (light + dark SVGs).

Cada celda aparece poco a poco (fade-in secuencial de viejo -> nuevo),
sin serpientes ni juegos. Se regenera via GitHub Actions.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime

USER = os.environ.get("GITHUB_USER", "ItsYusei99")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_DIR = os.environ.get("OUT_DIR", "dist")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
DARK = ["#21262d", "#0e4429", "#006d32", "#26a641", "#39d353"]
TEXT_LIGHT = "#24292f"
TEXT_DARK = "#e6edf3"
MUTED_LIGHT = "#57606a"
MUTED_DARK = "#7d8590"

CELL = 10
STEP = 13
PAD_X = 12
PAD_TOP = 34
PAD_BOTTOM = 28
DELAY_STEP = 0.018

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def level(count: int) -> int:
    if count == 0:
        return 0
    if count <= 3:
        return 1
    if count <= 6:
        return 2
    if count <= 9:
        return 3
    return 4


def fetch_calendar():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "contrib-animation"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def build_svg(cal, palette, text_color, muted):
    weeks = cal["weeks"]
    total = cal["totalContributions"]
    w = len(weeks) * STEP + PAD_X * 2
    h = 7 * STEP + PAD_TOP + PAD_BOTTOM

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">']
    parts.append('<style>.cell{opacity:0;animation:fade .45s ease forwards}@keyframes fade{to{opacity:1}}.fade-end{opacity:0;animation:fade .8s ease forwards}</style>')
    parts.append(f'<text x="{PAD_X}" y="18" font-size="13" font-weight="600" fill="{text_color}">{total} contributions in the last year</text>')

    last_month = None
    for wi, week in enumerate(weeks):
        if not week["contributionDays"]:
            continue
        dt = datetime.strptime(week["contributionDays"][0]["date"], "%Y-%m-%d")
        if last_month is None:
            last_month = dt.month
        elif dt.month != last_month and wi > 0:
            x = PAD_X + wi * STEP
            parts.append(f'<text x="{x}" y="{PAD_TOP - 10}" font-size="9" fill="{muted}">{MONTHS[dt.month - 1]}</text>')
            last_month = dt.month

    idx = 0
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week["contributionDays"]):
            x = PAD_X + wi * STEP
            y = PAD_TOP + di * STEP
            lv = level(day["contributionCount"])
            delay = idx * DELAY_STEP
            tip = f'{day["date"]}: {day["contributionCount"]} contributions'
            parts.append(
                f'<rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{palette[lv]}" style="animation-delay:{delay:.2f}s"><title>{tip}</title></rect>')
            idx += 1

    total_dur = idx * DELAY_STEP + 0.5
    lx = w - PAD_X - 5 * (CELL + 3) - 78
    ly = h - 16
    parts.append(f'<g class="fade-end" style="animation-delay:{total_dur:.2f}s">')
    parts.append(f'<text x="{lx}" y="{ly + 9}" font-size="9" fill="{muted}">Less</text>')
    for i, c in enumerate(palette):
        parts.append(f'<rect x="{lx + 32 + i * (CELL + 3)}" y="{ly}" width="{CELL}" height="{CELL}" rx="2.5" fill="{c}"/>')
    parts.append(f'<text x="{lx + 32 + 5 * (CELL + 3) + 4}" y="{ly + 9}" font-size="9" fill="{muted}">More</text>')
    parts.append('</g>')
    parts.append('</svg>')
    return "\n".join(parts), total_dur


def main():
    cal = fetch_calendar()
    os.makedirs(OUT_DIR, exist_ok=True)
    light_svg, dur = build_svg(cal, LIGHT, TEXT_LIGHT, MUTED_LIGHT)
    dark_svg, _ = build_svg(cal, DARK, TEXT_DARK, MUTED_DARK)
    with open(os.path.join(OUT_DIR, "contrib-light.svg"), "w") as f:
        f.write(light_svg)
    with open(os.path.join(OUT_DIR, "contrib-dark.svg"), "w") as f:
        f.write(dark_svg)
    print(f"total={cal['totalContributions']} weeks={len(cal['weeks'])} duration={dur:.1f}s -> {OUT_DIR}/contrib-*.svg")


if __name__ == "__main__":
    sys.exit(main())
