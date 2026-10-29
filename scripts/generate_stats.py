"""Generate the monochrome stats cards shown on the profile README.

Writes assets/stats.svg, assets/streak.svg and assets/graph.svg from the
GitHub GraphQL API. Needs GITHUB_TOKEN in the environment. Standard library only.
"""

import datetime as dt
import json
import os
import urllib.request
from pathlib import Path

LOGIN = "Omkarshinde19"
DISPLAY = "Omkar"
ASSETS = Path(__file__).resolve().parent.parent / "assets"

BG = "#0d1117"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"


def graphql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": "profile-stats",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {
      nodes { stargazerCount }
    }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
  }
}
"""

CALENDAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch():
    user = graphql(PROFILE_QUERY, {"login": LOGIN})["user"]
    created = dt.date.fromisoformat(user["createdAt"][:10])
    today = dt.datetime.now(dt.timezone.utc).date()

    days = {}
    for year in range(created.year, today.year + 1):
        start = max(dt.date(year, 1, 1), created)
        end = min(dt.date(year, 12, 31), today)
        data = graphql(CALENDAR_QUERY, {
            "login": LOGIN,
            "from": f"{start}T00:00:00Z",
            "to": f"{end}T23:59:59Z",
        })
        for week in data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                d = dt.date.fromisoformat(day["date"])
                if created <= d <= today:
                    days[d] = day["contributionCount"]

    return {
        "created": created,
        "today": today,
        "stars": sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
        "prs": user["pullRequests"]["totalCount"],
        "issues": user["issues"]["totalCount"],
        "contributed_to": user["repositoriesContributedTo"]["totalCount"],
        "days": dict(sorted(days.items())),
    }


def streaks(days, today):
    """Return (current, current_start, current_end, longest, longest_start, longest_end)."""
    longest = (0, None, None)
    run_start, run_len = None, 0
    for d, n in days.items():
        if n > 0:
            run_start = run_start or d
            run_len += 1
            if run_len > longest[0]:
                longest = (run_len, run_start, d)
        else:
            run_start, run_len = None, 0

    # A streak stays current until a full day passes with no contributions.
    cursor = today if days.get(today, 0) > 0 else today - dt.timedelta(days=1)
    current, end = 0, cursor
    while days.get(cursor, 0) > 0:
        current += 1
        cursor -= dt.timedelta(days=1)
    start = cursor + dt.timedelta(days=1)
    return current, start, end, *longest


def fmt(d, year=True):
    if d is None:
        return ""
    return d.strftime("%b %-d, %Y") if year else d.strftime("%b %-d")


def card(width, height, inner):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<style>text{{font-family:{FONT};fill:{TEXT}}} .muted{{fill:{MUTED}}}</style>'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="6" fill="{BG}" stroke="{BORDER}"/>'
        f"{inner}</svg>"
    )


ICONS = {
    "star": "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z",
    "commit": "M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z",
    "pr": "M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354Z",
    "issue": "M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z",
    "repo": "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.25.25 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z",
}


def stats_svg(s):
    year = s["today"].year
    year_total = sum(n for d, n in s["days"].items() if d.year == year)
    rows = [
        ("star", "Total Stars Earned", s["stars"]),
        ("commit", f"Contributions ({year})", year_total),
        ("pr", "Total Pull Requests", s["prs"]),
        ("issue", "Total Issues", s["issues"]),
        ("repo", "Contributed to", s["contributed_to"]),
    ]
    inner = f'<text x="25" y="35" font-size="18" font-weight="600">{DISPLAY}\'s GitHub Stats</text>'
    for i, (icon, label, value) in enumerate(rows):
        y = 70 + i * 25
        inner += (
            f'<g transform="translate(25,{y - 12})"><path d="{ICONS[icon]}" fill="{TEXT}"/></g>'
            f'<text x="50" y="{y}" font-size="14">{label}:</text>'
            f'<text x="250" y="{y}" font-size="14" font-weight="700">{value}</text>'
        )
    # Initial in a ring, in place of a grade
    inner += (
        f'<circle cx="395" cy="110" r="42" fill="none" stroke="{BORDER}" stroke-width="6"/>'
        f'<circle cx="395" cy="110" r="42" fill="none" stroke="{TEXT}" stroke-width="6" '
        f'stroke-dasharray="200 264" stroke-linecap="round" transform="rotate(-90 395 110)"/>'
        f'<text x="395" y="122" font-size="32" font-weight="700" text-anchor="middle">O</text>'
    )
    return card(495, 195, inner)


def streak_svg(s):
    total = sum(s["days"].values())
    cur, cs, ce, best, bs, be = streaks(s["days"], s["today"])
    cur_range = f"{fmt(cs, False)} to {fmt(ce, False)}" if cur else "No current streak"
    best_range = f"{fmt(bs)} to {fmt(be)}" if best else ""
    inner = (
        f'<line x1="165" y1="28" x2="165" y2="168" stroke="{BORDER}"/>'
        f'<line x1="330" y1="28" x2="330" y2="168" stroke="{BORDER}"/>'
        # Total
        f'<text x="82.5" y="88" font-size="28" font-weight="700" text-anchor="middle">{total}</text>'
        f'<text x="82.5" y="118" font-size="14" text-anchor="middle">Total Contributions</text>'
        f'<text x="82.5" y="142" font-size="11" class="muted" text-anchor="middle">{fmt(s["created"])} to Present</text>'
        # Current, with ring
        f'<circle cx="247.5" cy="71" r="40" fill="none" stroke="{TEXT}" stroke-width="5"/>'
        f'<text x="247.5" y="81" font-size="28" font-weight="700" text-anchor="middle">{cur}</text>'
        f'<text x="247.5" y="140" font-size="14" font-weight="700" text-anchor="middle">Current Streak</text>'
        f'<text x="247.5" y="160" font-size="11" class="muted" text-anchor="middle">{cur_range}</text>'
        # Longest
        f'<text x="412.5" y="88" font-size="28" font-weight="700" text-anchor="middle">{best}</text>'
        f'<text x="412.5" y="118" font-size="14" text-anchor="middle">Longest Streak</text>'
        f'<text x="412.5" y="142" font-size="11" class="muted" text-anchor="middle">{best_range}</text>'
    )
    return card(495, 195, inner)


def graph_svg(s):
    last = [(d, n) for d, n in s["days"].items()][-31:]
    w, h = 1000, 320
    left, right, top, bottom = 60, 30, 55, 50
    pw, ph = w - left - right, h - top - bottom
    peak = max([n for _, n in last] + [1])
    # Axis step of 1, 2 or 5 times a power of ten, giving at most six gridlines
    raw = max(1, -(-peak // 6))
    magnitude = 10 ** (len(str(raw)) - 1)
    step = next(m * magnitude for m in (1, 2, 5, 10) if m * magnitude >= raw)
    ticks = -(-peak // step)
    ymax = step * ticks

    def xy(i, n):
        return left + pw * i / (len(last) - 1), top + ph * (1 - n / ymax)

    pts = [xy(i, n) for i, (_, n) in enumerate(last)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{left},{top + ph} {line} {left + pw},{top + ph}"

    inner = f'<text x="{w / 2}" y="32" font-size="18" font-weight="600" text-anchor="middle">{DISPLAY}\'s Contribution Graph</text>'
    for k in range(ticks + 1):
        y = top + ph * (1 - k / ticks)
        inner += (
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + pw}" y2="{y:.1f}" stroke="{BORDER}" stroke-dasharray="3 4"/>'
            f'<text x="{left - 10}" y="{y + 4:.1f}" font-size="11" class="muted" text-anchor="end">{k * step}</text>'
        )
    inner += (
        f'<polygon points="{area}" fill="{TEXT}" fill-opacity="0.08"/>'
        f'<polyline points="{line}" fill="none" stroke="{TEXT}" stroke-width="2"/>'
    )
    for (x, y), (d, _) in zip(pts, last):
        inner += (
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{TEXT}"/>'
            f'<text x="{x:.1f}" y="{top + ph + 20}" font-size="11" class="muted" text-anchor="middle">{d.day}</text>'
        )
    inner += (
        f'<text x="{w / 2}" y="{h - 8}" font-size="12" class="muted" text-anchor="middle">Last 31 days</text>'
        f'<text x="18" y="{top + ph / 2}" font-size="12" class="muted" text-anchor="middle" '
        f'transform="rotate(-90 18 {top + ph / 2})">Contributions</text>'
    )
    return card(w, h, inner)


def main():
    s = fetch()
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "stats.svg").write_text(stats_svg(s))
    (ASSETS / "streak.svg").write_text(streak_svg(s))
    (ASSETS / "graph.svg").write_text(graph_svg(s))
    print(f"total={sum(s['days'].values())} days={len(s['days'])} stars={s['stars']}")


if __name__ == "__main__":
    main()
