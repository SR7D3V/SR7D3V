"""Builds the SVG graphics for the profile README.

    python3 scripts/build.py static   # header, links, section titles, projects, stack -> assets/
    python3 scripts/build.py live     # GitHub stats + contributions -> dist/ (needs GITHUB_TOKEN)

Edit the CONTENT block below, then re-run `static`. Standard library only.
"""

import base64
import datetime as dt
import json
import math
import os
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / 'assets' / 'fonts'
USER = 'SR7D3V'

# ---------------------------------------------------------------- CONTENT

SITE = 'https://swarnimrai.vercel.app'
SITE_LABEL = 'swarnimrai.vercel.app'
NAME = ['SWARNIM', 'RAI']
TAGLINE = 'A creative technologist exploring design, game development, and digital experiences.'

# (slug, label, palette colour)
LINKS = [
    ('linkedin', 'LinkedIn', 'midnight'),
    ('github', 'GitHub', 'olive'),
    ('email', 'Email', 'merlot'),
]

# (slug, number, title, palette colour)
SECTIONS = [
    ('about', '01', 'About', 'merlot'),
    ('projects', '02', 'Featured Projects', 'olive'),
    ('stack', '03', 'Tech Stack', 'midnight'),
    ('stats', '04', 'GitHub Stats', 'tobacco'),
    ('contributions', '05', 'Contributions', 'merlot'),
]

PROJECTS = [
    {
        'slug': 'lucid',
        'kind': 'Full-stack',
        'title': 'Lucid',
        'body': 'A multi-store clothing retail platform. 3NF PostgreSQL schema, concurrency-safe '
                'checkout with row-level locks, a trigger-maintained inventory ledger and '
                'full-text search.',
        'stack': ['Next.js', 'TypeScript', 'PostgreSQL'],
        'color': 'merlot',
    },
]

# (category, items, palette colour)
STACK = [
    ('Programming Languages', ['Java', 'Python', 'C', 'Swift', 'SQL'], 'merlot'),
    ('Frontend Development', ['JavaScript', 'React', 'Next.js', 'GSAP', 'Web Animation', 'HTML', 'CSS'], 'tobacco'),
    ('Backend Development', ['MySQL', 'Oracle SQL', 'PostgreSQL', 'Schema Design', 'Query Optimization'], 'olive'),
    ('Design', ['UI/UX Design', 'Graphic Design'], 'midnight'),
    ('Game Development', ['Unreal Engine', 'Blender', 'Meta XR'], 'merlot'),
    ('Tools', ['Git', 'Jupyter', 'VS Code', 'Figma', 'Xcode', 'Swift Playgrounds'], 'tobacco'),
]

# ---------------------------------------------------------------- THEME

# Bone, Merlot, Olive, Midnight Blue, Tobacco, Graphite.
BONE, GRAPHITE = '#E6E0D6', '#121212'
PALETTE = {
    'merlot': '#4B1E23', 'olive': '#6B6F4E', 'midnight': '#1C2430',
    'tobacco': '#8A5A2B', 'graphite': GRAPHITE,
}

THEMES = {
    'light': {
        'text': GRAPHITE, 'muted': '#6f675c', 'rule': '#e2dbcf',
        'panel': BONE, 'panel_text': GRAPHITE, 'panel_muted': '#6f675c',
        'grid': 'rgba(18,18,18,0.07)', 'track': '#ece6dc',
        'colors': dict(PALETTE),
        'levels': ['#ece6dc', '#d6bb97', '#a87849', '#7a3b33', '#4B1E23'],
    },
    'dark': {
        'text': BONE, 'muted': '#a39b8e', 'rule': '#2a303a',
        'panel': '#1C2430', 'panel_text': BONE, 'panel_muted': '#a39b8e',
        'grid': 'rgba(230,224,214,0.06)', 'track': '#1d232c',
        # The same hues lifted so they read against GitHub's dark background.
        'colors': {
            'merlot': '#a5525b', 'olive': '#9a9f72', 'midnight': '#6a7a94',
            'tobacco': '#c08a52', 'graphite': BONE,
        },
        'levels': ['#1d232c', '#4a3524', '#7d532b', '#c08a52', BONE],
    },
}

W = 880
METRICS = {int(k): v for k, v in json.loads((FONTS / 'metrics.json').read_text()).items()}


def text_width(s, size, weight=400, tracking=0.0):
    m = METRICS[weight]
    return sum(m.get(c, 0.55) for c in s) * size + tracking * size * max(len(s) - 1, 0)


def wrap(s, size, weight, max_w):
    lines, line = [], ''
    for word in s.split():
        trial = f'{line} {word}'.strip()
        if text_width(trial, size, weight) <= max_w or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def font_css(weights):
    rules = []
    for w in sorted(set(weights)):
        data = base64.b64encode((FONTS / f'outfit-{w}.woff2').read_bytes()).decode()
        rules.append(
            f"@font-face{{font-family:O;font-weight:{w};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
        )
    return ''.join(rules)


def svg(width, height, body, weights, label):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">'
        f'<style>{font_css(weights)}text{{font-family:O,Outfit,-apple-system,"Segoe UI",'
        f'Helvetica,Arial,sans-serif}}</style>{body}</svg>'
    )


def t(x, y, s, size, weight, fill, anchor='start', tracking=0.0, upper=False, opacity=None):
    s = s.upper() if upper else s
    ls = f' letter-spacing="{tracking * size:.2f}"' if tracking else ''
    op = f' fill-opacity="{opacity}"' if opacity is not None else ''
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}"{ls}{op}>{escape(s)}</text>'
    )


def rect(x, y, w, h, fill, rx=0, extra=''):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{extra}/>'


def arrow(x, y, size, stroke, width=1.6):
    """A drawn ↗, so it sits optically the same at every size."""
    return (
        f'<path d="M{x:.1f} {y + size:.1f} L{x + size:.1f} {y:.1f} M{x + size * 0.28:.1f} {y:.1f} '
        f'H{x + size:.1f} V{y + size * 0.72:.1f}" fill="none" stroke="{stroke}" '
        f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def palette_band(x, y, w, h, c):
    order = ['merlot', 'olive', 'tobacco', 'midnight', 'graphite']
    seg = w / len(order)
    return ''.join(rect(x + i * seg, y, seg + 0.5, h, c['colors'][k]) for i, k in enumerate(order))


# ---------------------------------------------------------------- STATIC

def header(c):
    h, pad, cell = 420, 44, 40
    grid = ''.join(f'<path d="M{x} 0V{h}"/>' for x in range(0, W + 1, cell))
    grid += ''.join(f'<path d="M0 {y}H{W}"/>' for y in range(0, h + 1, cell))
    body = (
        '<defs><clipPath id="card"><rect width="100%" height="100%" rx="22"/></clipPath>'
        '<radialGradient id="g" cx="0.75" cy="0.35" r="0.7">'
        '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
        '</radialGradient><mask id="m"><rect width="100%" height="100%" fill="url(#g)"/></mask></defs>'
        '<g clip-path="url(#card)">'
        + rect(0, 0, W, h, c['panel'])
        + f'<g mask="url(#m)" stroke="{c["grid"]}" stroke-width="1">{grid}</g>'
        + palette_band(0, h - 8, W, 8, c)
        + '</g>'
        + t(pad, pad + 14, 'SR', 18, 900, c['panel_text'])
        + t(W - pad, pad + 14, 'Portfolio', 13, 400, c['panel_muted'], 'end', 0.18, True)
    )
    size = 128
    for i, word in enumerate(NAME):
        body += t(pad - 5, 168 + i * size * 0.86, word, size, 900, c['panel_text'], tracking=-0.03)
    base = h - pad - 14
    lines = wrap(TAGLINE, 17, 300, 400)
    for i, line in enumerate(lines):
        body += t(pad, base - (len(lines) - 1 - i) * 24, line, 17, 300, c['panel_muted'])
    pill_w = text_width(SITE_LABEL, 15, 400) + 70
    px = W - pad - pill_w
    body += (
        rect(px, base - 31, pill_w, 46, PALETTE['merlot'], 23)
        + t(px + 24, base - 2, SITE_LABEL, 15, 400, BONE)
        + arrow(px + pill_w - 34, base - 14, 9, BONE)
    )
    return svg(W, h, body, [300, 400, 900], f'Swarnim Rai: {TAGLINE} Visit {SITE_LABEL}')


def link_pill(label, color, c, dark):
    size, h = 15, 44
    w = round(text_width(label, size, 400) + 64)
    border = f' stroke="{BONE}" stroke-opacity="0.18"' if dark else ''
    body = (
        rect(0.5, 0.5, w - 1, h - 1, PALETTE[color], h / 2, border)
        + t(22, 27.5, label, size, 400, BONE)
        + arrow(w - 32, 17, 9, BONE)
    )
    return svg(w, h, body, [400], label)


def section_title(num, title, color, c):
    h = 86
    accent = c['colors'][color]
    body = (
        t(0, 22, num, 13, 500, accent, tracking=0.18)
        + t(0, 64, title, 36, 500, c['text'], tracking=-0.02)
        + rect(0, h - 1, W, 1, c['rule'])
        + rect(0, h - 3, 56, 3, accent)
    )
    return svg(W, h, body, [400, 500], f'{num} {title}')


CARD_PAD = 34
# A lone featured project spans the full width; otherwise cards sit two per row.
CARD_W = W if len(PROJECTS) == 1 else 430


def card_height():
    body_lines = max(len(wrap(p['body'], 16, 300, CARD_W - CARD_PAD * 2)) for p in PROJECTS)
    return 156 + body_lines * 25 + 74


def project_card(i, p, c):
    w, h, pad = CARD_W, card_height(), CARD_PAD
    fill = PALETTE[p.get('color', 'merlot')]
    body = (
        '<defs><clipPath id="card"><rect width="100%" height="100%" rx="20"/></clipPath></defs>'
        f'<g clip-path="url(#card)">{rect(0, 0, w, h, fill)}</g>'
        + t(pad, pad + 14, f'{i:02d}', 13, 400, BONE, tracking=0.18, opacity=0.6)
        + t(pad + 34, pad + 14, p['kind'], 13, 500, BONE, tracking=0.18, upper=True, opacity=0.85)
        + arrow(w - pad - 13, pad + 1, 13, BONE, 1.8)
        + t(pad, pad + 92, p['title'], 40, 500, BONE, tracking=-0.02)
    )
    for j, line in enumerate(wrap(p['body'], 16, 300, w - pad * 2)):
        body += t(pad, pad + 132 + j * 25, line, 16, 300, BONE, opacity=0.78)
    x = pad
    for item in p['stack']:
        cw = text_width(item.upper(), 12, 500, 0.14) + 28
        body += rect(x, h - pad - 30, cw, 30, 'none', 15, f' stroke="{BONE}" stroke-opacity="0.4"')
        body += t(x + 14, h - pad - 10.5, item, 12, 500, BONE, tracking=0.14, upper=True)
        x += cw + 8
    return svg(w, h, body, [300, 400, 500], f'{p["title"]}: {p["body"]}')


def stack(c, dark):
    """One row per category; each item is a chip tinted with the category's colour."""
    item_x, size, chip_h, chip_gap, line_gap, pad_y = 250, 15, 34, 8, 10, 18
    tint = 0.24 if dark else 0.12
    body, y = '', 0
    for label, items, color in STACK:
        accent = c['colors'][color]
        lines, line, x = [], [], item_x
        for item in items:
            cw = text_width(item, size, 400) + 30
            if line and x + cw > W:
                lines.append(line)
                line, x = [], item_x
            line.append((x, cw, item))
            x += cw + chip_gap
        lines.append(line)
        row_h = pad_y * 2 + len(lines) * chip_h + (len(lines) - 1) * line_gap
        body += rect(0, y + pad_y + 12, 10, 10, accent, 2)
        label_lines = wrap(label.upper(), 12, 400, 200)
        for k, ll in enumerate(label_lines):
            body += t(20, y + pad_y + 21.5 + k * 17, ll, 12, 400, c['muted'], tracking=0.16)
        for k, ln in enumerate(lines):
            cy = y + pad_y + k * (chip_h + line_gap)
            for cx, cw, item in ln:
                body += rect(cx, cy, cw, chip_h, accent, chip_h / 2,
                             f' fill-opacity="{tint}" stroke="{accent}" stroke-opacity="0.45"')
                body += t(cx + 15, cy + 22.5, item, size, 400, c['text'])
        y += row_h
        body += rect(0, y - 1, W, 1, c['rule'])
    alt = '; '.join(f'{label}: {", ".join(items)}' for label, items, _ in STACK)
    return svg(W, y, body, [400], alt)


def build_static():
    out = ROOT / 'assets'
    out.mkdir(exist_ok=True)
    for name, c in THEMES.items():
        dark = name == 'dark'
        files = {
            f'header-{name}.svg': header(c),
            f'stack-{name}.svg': stack(c, dark),
        }
        for slug, label, color in LINKS:
            files[f'link-{slug}-{name}.svg'] = link_pill(label, color, c, dark)
        for slug, num, title, color in SECTIONS:
            files[f'section-{slug}-{name}.svg'] = section_title(num, title, color, c)
        for i, p in enumerate(PROJECTS, 1):
            files[f'project-{p["slug"]}-{name}.svg'] = project_card(i, p, c)
        for fname, content in files.items():
            (out / fname).write_text(content)
    print(f'wrote static graphics to {out}')


# ---------------------------------------------------------------- LIVE

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    pullRequests { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes {
        name
        stargazerCount
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      totalRepositoryContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""

LEVELS = ['NONE', 'FIRST_QUARTILE', 'SECOND_QUARTILE', 'THIRD_QUARTILE', 'FOURTH_QUARTILE']
LANGUAGE_ORDER = ['merlot', 'tobacco', 'olive', 'midnight', 'graphite']


def fetch():
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        sys.exit('GITHUB_TOKEN is not set')
    req = urllib.request.Request(
        'https://api.github.com/graphql',
        data=json.dumps({'query': QUERY, 'variables': {'login': USER}}).encode(),
        headers={'Authorization': f'bearer {token}', 'User-Agent': USER},
    )
    with urllib.request.urlopen(req) as res:
        payload = json.load(res)
    if payload.get('errors'):
        sys.exit(json.dumps(payload['errors'], indent=2))
    return payload['data']['user']


def fmt(n):
    return f'{n:,}'


def label(x, y, s, c, anchor='start'):
    return t(x, y, s, 12, 400, c['muted'], anchor, 0.16, True)


def monthly(days, today):
    counts = {}
    for d in days:
        counts[d['date'][:7]] = counts.get(d['date'][:7], 0) + d['contributionCount']
    months, y, m = [], today.year, today.month
    for _ in range(12):
        months.append(dt.date(y, m, 1))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return [(d, counts.get(f'{d:%Y-%m}', 0)) for d in reversed(months)]


def languages(repos):
    sizes = {}
    for r in repos['nodes']:
        if r['name'] == USER:
            continue
        for e in r['languages']['edges']:
            sizes[e['node']['name']] = sizes.get(e['node']['name'], 0) + e['size']
    top = sorted(sizes.items(), key=lambda kv: -kv[1])
    if len(top) > 5:
        top = top[:4] + [('Other', sum(v for _, v in top[4:]))]
    return top, sum(sizes.values())


def stats(u, c, today):
    cc = u['contributionsCollection']
    repos = u['repositories']
    days = [d for w in cc['contributionCalendar']['weeks'] for d in w['contributionDays']]
    stars = sum(r['stargazerCount'] for r in repos['nodes'])
    body = (
        t(0, 16, f'@{USER}  ·  {repos["totalCount"]} public repos  ·  {stars} stars', 13, 400, c['muted'], tracking=0.04)
        + t(W, 16, f'On GitHub since {u["createdAt"][:4]}  ·  Updated {today:%d %b %Y}', 13, 400, c['muted'], 'end', 0.04)
    )

    # Monthly activity: one bar per month for the last year.
    ax, aw, top_y, chart_h = 0, 520, 112, 150
    data = monthly(days, today)
    peak = max(v for _, v in data) or 1
    slot = aw / len(data)
    bar_w = slot * 0.56
    body += label(ax, 60, 'Monthly activity', c) + t(aw, 60, 'last 12 months', 12, 300, c['muted'], 'end')
    for k, (month, v) in enumerate(data):
        bx = ax + k * slot + (slot - bar_w) / 2
        bh = max(chart_h * v / peak, 0) if v else 0
        body += rect(bx, top_y, bar_w, chart_h, c['track'], 4)
        if v:
            fill = c['colors']['merlot'] if v == peak else c['colors']['tobacco']
            body += rect(bx, top_y + chart_h - bh, bar_w, bh, fill, 4)
            body += t(bx + bar_w / 2, top_y + chart_h - bh - 8, str(v), 12, 500, c['text'], 'middle')
        body += t(bx + bar_w / 2, top_y + chart_h + 20, f'{month:%b}', 11, 400, c['muted'], 'middle')

    # Languages: a donut with a legend.
    body += rect(560, 44, 1, 240, c['rule'])
    lx = 600
    top, total = languages(repos)
    body += label(lx, 60, 'Languages', c)
    cx, cy, r, sw = lx + 66, top_y + 72, 54, 18
    circ = 2 * math.pi * r
    body += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c["track"]}" stroke-width="{sw}"/>'
    offset, gap = 0.0, 2.5 if len(top) > 1 else 0
    colors = [c['muted'] if n == 'Other' else c['colors'][LANGUAGE_ORDER[k % 5]] for k, (n, _) in enumerate(top)]
    for (name, size), fill in zip(top, colors):
        seg = circ * size / total if total else 0
        dash = max(seg - gap, 0.5)
        body += (
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{fill}" stroke-width="{sw}" '
            f'stroke-dasharray="{dash:.2f} {circ:.2f}" stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += seg
    if top:
        body += t(cx, cy + 6, f'{100 * top[0][1] / total:.0f}%', 20, 500, c['text'], 'middle')
    for k, ((name, size), fill) in enumerate(zip(top, colors)):
        yy = top_y + 10 + k * 28
        body += rect(lx + 150, yy, 10, 10, fill, 2)
        body += t(lx + 168, yy + 10, name, 14, 400, c['text'])
        body += t(W, yy + 10, f'{100 * size / total:.1f}%', 14, 300, c['muted'], 'end')

    # Contribution mix: what the year's activity was made of.
    mix = [
        ('Commits', cc['totalCommitContributions'], 'merlot'),
        ('Pull requests', cc['totalPullRequestContributions'], 'tobacco'),
        ('Reviews', cc['totalPullRequestReviewContributions'], 'olive'),
        ('Issues', cc['totalIssueContributions'], 'midnight'),
        ('New repos', cc['totalRepositoryContributions'], 'graphite'),
    ]
    my = 330
    mix_total = sum(v for _, v, _ in mix)
    body += rect(0, my - 26, W, 1, c['rule'])
    body += label(0, my, 'Contribution mix', c) + t(W, my, 'past year', 12, 300, c['muted'], 'end')
    # Segments are clipped to one rounded track so only the outer ends are rounded.
    body += f'<defs><clipPath id="mix">{rect(0, my + 18, W, 14, "#000", 7)}</clipPath></defs>'
    body += rect(0, my + 18, W, 14, c['track'], 7) + '<g clip-path="url(#mix)">'
    x = 0.0
    for name, v, key in mix:
        if v:
            seg = W * v / mix_total
            body += rect(x, my + 18, seg - (2 if x + seg < W - 1 else 0), 14, c['colors'][key])
            x += seg
    body += '</g>'
    lx = 0.0
    for name, v, key in mix:
        body += rect(lx, my + 52, 10, 10, c['colors'][key], 2)
        body += t(lx + 18, my + 62, name, 14, 400, c['text'])
        nx = lx + 18 + text_width(name, 14, 400) + 7
        body += t(nx, my + 62, fmt(v), 14, 500, c['colors'][key])
        lx = nx + text_width(fmt(v), 14, 500) + 34
    h = my + 76
    return svg(W, h, body, [300, 400, 500], 'GitHub stats: monthly activity, languages and contribution mix')


def streaks(days, today):
    counts = [(d['date'], d['contributionCount']) for d in days if d['date'] <= today.isoformat()]
    longest = run = 0
    for _, n in counts:
        run = run + 1 if n else 0
        longest = max(longest, run)
    current = 0
    tail = counts[:-1] if counts and counts[-1][1] == 0 else counts
    for _, n in reversed(tail):
        if not n:
            break
        current += 1
    return current, longest


def contributions(u, c, today):
    cal = u['contributionsCollection']['contributionCalendar']
    weeks = cal['weeks']
    days = [d for w in weeks for d in w['contributionDays']]
    current, longest = streaks(days, today)
    active = sum(1 for d in days if d['contributionCount'])
    plural = lambda n, word: f'{n} {word}' + ('' if n == 1 else 's')

    left, top, gap = 34, 92, 3
    cell = (W - left - gap * (len(weeks) - 1)) / len(weeks)
    total = fmt(cal['totalContributions'])
    body = (
        t(0, 40, total, 40, 500, c['colors']['merlot'], tracking=-0.03)
        + t(text_width(total, 40, 500, -0.03) + 12, 40, 'contributions in the last year', 15, 300, c['muted'])
        + label(W, 22, 'Current streak', c, 'end')
        + t(W, 42, plural(current, 'day'), 16, 500, c['colors']['tobacco'], 'end')
        + label(W - 150, 22, 'Longest streak', c, 'end')
        + t(W - 150, 42, plural(longest, 'day'), 16, 500, c['colors']['tobacco'], 'end')
        + label(W - 300, 22, 'Active days', c, 'end')
        + t(W - 300, 42, str(active), 16, 500, c['colors']['olive'], 'end')
    )
    last_month = None
    for i, w in enumerate(weeks):
        first = dt.date.fromisoformat(w['contributionDays'][0]['date'])
        if first.month != last_month and i < len(weeks) - 2:
            if last_month is not None or first.day <= 7:
                body += t(left + i * (cell + gap), top - 12, f'{first:%b}', 12, 400, c['muted'])
            last_month = first.month
        for d in w['contributionDays']:
            lvl = LEVELS.index(d['contributionLevel'])
            body += rect(left + i * (cell + gap), top + d['weekday'] * (cell + gap), cell, cell, c['levels'][lvl], 2.5)
    for wd, name in ((1, 'Mon'), (3, 'Wed'), (5, 'Fri')):
        body += t(0, top + wd * (cell + gap) + cell - 2.5, name, 11, 400, c['muted'])
    ly = top + 7 * (cell + gap) + 22
    lx = W - 5 * (cell + gap) - 40
    body += t(lx - 8, ly + cell - 2.5, 'Less', 11, 400, c['muted'], 'end')
    for k, fill in enumerate(c['levels']):
        body += rect(lx + k * (cell + gap), ly, cell, cell, fill, 2.5)
    body += t(W, ly + cell - 2.5, 'More', 11, 400, c['muted'], 'end')
    h = ly + cell + 4
    alt = (f'{cal["totalContributions"]} contributions in the last year. '
           f'Current streak {current} days, longest {longest} days.')
    return svg(W, round(h), body, [300, 400, 500], alt)


def build_live():
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    u = fetch()
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date()
    for name, c in THEMES.items():
        (out / f'stats-{name}.svg').write_text(stats(u, c, today))
        (out / f'contributions-{name}.svg').write_text(contributions(u, c, today))
    print(f'wrote live graphics to {out}')


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'static'
    {'static': build_static, 'live': build_live}[mode]()
