#!/usr/bin/env python3
"""Generate a single-file GitHub activity dashboard SVG (stdlib only).

Usage:
  GH_TOKEN=... python scripts/generate_activity.py --user Daniel059 --out dist/activity-dashboard.svg
  python scripts/generate_activity.py --demo --out preview.svg      # fake data, no token needed
"""
import argparse, json, os, random, urllib.request
from datetime import date, datetime, timedelta, timezone

# ---------- theme ----------
BG, CARD, BORDER = "#0d1117", "#161b22", "#30363d"
TEXT, MUTED, ACCENT = "#e6edf3", "#8b949e", "#39FF14"
LEVELS = ["#161b22", "#0b4a1a", "#128a24", "#22c53a", "#39FF14"]
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
W = 900
PAD = 28

QUERY = """
query($login:String!){
  user(login:$login){
    repositories(privacy:PUBLIC, ownerAffiliations:OWNER){ totalCount }
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount } }
      }
    }
  }
}"""


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "activity-dashboard"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    u = data["data"]["user"]
    days = {}
    for wk in u["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for d in wk["contributionDays"]:
            days[date.fromisoformat(d["date"])] = d["contributionCount"]
    return days, u["repositories"]["totalCount"]


def demo():
    random.seed(7)
    today = date.today()
    days = {}
    for i in range(371):
        d = today - timedelta(days=i)
        days[d] = random.choice([0, 0, 0, 1, 2, 3, 5, 8]) if random.random() > 0.45 else 0
    return days, 58


def smooth_path(pts):
    """Catmull-Rom -> cubic bezier path through points."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def nice_max(v):
    for m in (3, 6, 9, 12, 15, 30, 60, 120, 240):
        if v <= m:
            return m
    return int(v) + 10


def streak(days, today):
    n, d = 0, today
    if days.get(d, 0) == 0:  # today may not have activity yet
        d -= timedelta(days=1)
    while days.get(d, 0) > 0:
        n += 1
        d -= timedelta(days=1)
    return n


def build(days, repos, user):
    today = max(days)
    last30 = [today - timedelta(days=29 - i) for i in range(30)]
    c30 = [days.get(d, 0) for d in last30]
    total30, active30 = sum(c30), sum(1 for c in c30 if c)
    total365 = sum(days.values())
    cur = streak(days, today)
    best = max(c30)

    # 7-day trailing average for trend line
    avg = []
    for d in last30:
        win = [days.get(d - timedelta(days=k), 0) for k in range(7)]
        avg.append(sum(win) / 7)

    out = []
    a = out.append
    H = 600
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
      f'aria-label="GitHub activity dashboard for {user}">')
    a(f"""<defs>
<filter id="glow" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/>
<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{ACCENT}"/><stop offset="1" stop-color="#0b4a1a"/></linearGradient>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#0a1a10"/></linearGradient>
</defs>
<style>
text{{font-family:{FONT};}}
.t{{fill:{TEXT};}} .m{{fill:{MUTED};}} .a{{fill:{ACCENT};}}
.bar{{transform-box:fill-box;transform-origin:50% 100%;animation:grow .7s ease-out both;}}
@keyframes grow{{from{{transform:scaleY(0);}}to{{transform:scaleY(1);}}}}
.line{{stroke-dasharray:2000;stroke-dashoffset:2000;animation:draw 1.6s .3s ease-out forwards;}}
@keyframes draw{{to{{stroke-dashoffset:0;}}}}
</style>""")
    a(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="url(#bg)" stroke="{BORDER}"/>')

    # header
    a(f'<text x="{PAD}" y="46" font-size="20" font-weight="700" class="t">GitHub activity</text>')
    a(f'<text x="{PAD}" y="66" font-size="12" class="m">@{user} · updated {datetime.now(timezone.utc):%d %b %Y}</text>')
    a(f'<circle cx="{W-PAD-6}" cy="40" r="5" fill="{ACCENT}" filter="url(#glow)"/>')

    # stat tiles
    tiles = [("Contributions", f"{total30}", "last 30 days"),
             ("Active days", f"{active30}/30", "days with activity"),
             ("Current streak", f"{cur}", "days in a row"),
             ("Public repos", f"{repos}", f"{total365} contributions / year")]
    gap = 14
    tw = (W - 2 * PAD - 3 * gap) / 4
    for i, (label, val, sub) in enumerate(tiles):
        x = PAD + i * (tw + gap)
        a(f'<rect x="{x:.1f}" y="84" width="{tw:.1f}" height="84" rx="12" fill="{CARD}" stroke="{BORDER}"/>')
        a(f'<rect x="{x:.1f}" y="96" width="3" height="60" rx="1.5" fill="{ACCENT}"/>')
        a(f'<text x="{x+18:.1f}" y="110" font-size="11" class="m" letter-spacing="0.6">{label.upper()}</text>')
        a(f'<text x="{x+18:.1f}" y="141" font-size="30" font-weight="700" class="a" filter="url(#glow)">{val}</text>')
        a(f'<text x="{x+18:.1f}" y="159" font-size="11" class="m">{sub}</text>')

    # chart
    cx0, cx1, cy0, cy1 = PAD + 30, W - PAD, 220, 340  # plot box
    a(f'<text x="{PAD}" y="196" font-size="14" font-weight="600" class="t">Activity over time</text>')
    a(f'<text x="{W-PAD}" y="196" font-size="11" text-anchor="end" class="m">last 30 days · line = 7-day average</text>')
    ymax = nice_max(max(c30 + [1]))
    for g in range(4):
        gy = cy1 - (cy1 - cy0) * g / 3
        a(f'<line x1="{cx0}" y1="{gy:.1f}" x2="{cx1}" y2="{gy:.1f}" stroke="{BORDER}" stroke-dasharray="3 5" opacity="0.7"/>')
        a(f'<text x="{cx0-8}" y="{gy+4:.1f}" font-size="10" text-anchor="end" class="m">{round(ymax*g/3)}</text>')
    step = (cx1 - cx0) / 30
    bw = step * 0.5
    pts = []
    for i, c in enumerate(c30):
        x = cx0 + step * i + (step - bw) / 2
        h = (cy1 - cy0) * c / ymax
        if c:
            a(f'<rect class="bar" style="animation-delay:{i*0.02:.2f}s" x="{x:.1f}" y="{cy1-h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" fill="url(#bar)" opacity="0.9"/>')
        else:
            a(f'<rect x="{x:.1f}" y="{cy1-2}" width="{bw:.1f}" height="2" rx="1" fill="{BORDER}"/>')
        pts.append((cx0 + step * i + step / 2, cy1 - (cy1 - cy0) * min(avg[i], ymax) / ymax))
    a(f'<path class="line" d="{smooth_path(pts)}" fill="none" stroke="{ACCENT}" stroke-width="2.5" stroke-linecap="round" filter="url(#glow)"/>')
    for i in (0, 7, 14, 21):
        a(f'<text x="{cx0+step*i+step/2:.1f}" y="{cy1+20}" font-size="10" text-anchor="middle" class="m">{last30[i]:%b} {last30[i].day}</text>')
    a(f'<text x="{cx1-step/2:.1f}" y="{cy1+20}" font-size="10" text-anchor="end" class="a">Today</text>')

    # calendar heatmap (last 53 weeks, Sun-start)
    a(f'<text x="{PAD}" y="402" font-size="14" font-weight="600" class="t">Contribution calendar</text>')
    a(f'<text x="{W-PAD}" y="402" font-size="11" text-anchor="end" class="m">{total365} contributions in the last year</text>')
    cell, cg = 12, 3
    start = today - timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)  # most recent Sunday
    start -= timedelta(weeks=52)
    gx0 = PAD + 30
    gy0 = 438
    mx = max(max(days.values()), 1)

    def level(c):
        if c == 0: return 0
        r = c / mx
        return 1 if r <= .25 else 2 if r <= .5 else 3 if r <= .75 else 4

    last_month = None
    for w in range(53):
        for dow in range(7):
            d = start + timedelta(weeks=w, days=dow)
            if d > today:
                continue
            c = days.get(d, 0)
            x = gx0 + w * (cell + cg); y = gy0 + dow * (cell + cg)
            a(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{LEVELS[level(c)]}"><title>{d:%d %b %Y}: {c} contributions</title></rect>')
        wd = start + timedelta(weeks=w)
        if wd.month != last_month and wd.day <= 7:
            a(f'<text x="{gx0 + w*(cell+cg)}" y="{gy0-8}" font-size="10" class="m">{wd:%b}</text>')
            last_month = wd.month
    for dow, lab in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        a(f'<text x="{gx0-8}" y="{gy0 + dow*(cell+cg) + 10}" font-size="9" text-anchor="end" class="m">{lab}</text>')
    # legend
    lx = W - PAD - 5 * (cell + 3) - 70
    ly = gy0 + 7 * (cell + cg) + 14
    a(f'<text x="{lx}" y="{ly+10}" font-size="10" class="m">Less</text>')
    for i, col in enumerate(LEVELS):
        a(f'<rect x="{lx+30+i*(cell+3)}" y="{ly}" width="{cell}" height="{cell}" rx="3" fill="{col}"/>')
    a(f'<text x="{lx+34+5*(cell+3)}" y="{ly+10}" font-size="10" class="m">More</text>')
    a(f'<text x="{PAD}" y="{ly+10}" font-size="10" class="m">Best day (30d): {best} · auto-updated by GitHub Actions</text>')
    a("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="Daniel059")
    ap.add_argument("--out", default="dist/activity-dashboard.svg")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        days, repos = demo()
    else:
        tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not tok:
            raise SystemExit("Set GH_TOKEN (or GITHUB_TOKEN)")
        days, repos = fetch(args.user, tok)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(build(days, repos, args.user))
    print("wrote", args.out)