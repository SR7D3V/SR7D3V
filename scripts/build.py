"""Builds the SVG graphics for the profile README.

    python3 scripts/build.py static   # header, links, section titles, projects, stack -> assets/
    python3 scripts/build.py live     # GitHub stats + contributions -> dist/ (needs GITHUB_TOKEN)

Edit the CONTENT block below, then re-run `static`. Standard library only.
"""

import base64
import datetime as dt
import json
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

LINKS = [
    ('linkedin', 'LinkedIn'),
    ('github', 'GitHub'),
    ('email', 'Email'),
]

SECTIONS = [
    ('about', '01', 'About'),
    ('projects', '02', 'Featured Projects'),
    ('stack', '03', 'Tech Stack'),
    ('stats', '04', 'GitHub Stats'),
    ('contributions', '05', 'Contributions'),
]

PROJECTS = [
    {
        'slug': 'portfolio',
        'kind': 'Web',
        'title': 'Portfolio Website',
        'body': 'A monochrome, scroll-driven portfolio. A custom SR preloader zooms through the '
                'wordmark to reveal the page, with smooth scrolling, a pinned horizontal gallery '
                'and reduced-motion support.',
        'stack': ['React', 'Vite', 'GSAP'],
    },
    {
        'slug': 'lucid',
        'kind': 'Full-stack',
        'title': 'Lucid',
        'body': 'A multi-store clothing retail platform. 3NF PostgreSQL schema, concurrency-safe '
                'checkout with row-level locks, a trigger-maintained inventory ledger and '
                'full-text search.',
        'stack': ['Next.js', 'TypeScript', 'PostgreSQL'],
    },
    {
        'slug': 'infinite-rodeo',
        'kind': 'Game',
        'title': 'Infinite Rodeo',
        'body': 'A fast-paced arcade endless runner. Dodge dynamic obstacles, gather collectibles '
                'and survive levels that keep getting harder while chasing the high score.',
        'stack': ['Unreal Engine'],
    },
    {
        'slug': 'horizons',
        'kind': 'Environment Art',
        'title': 'Featured Horizons',
        'body': 'Environment studies in procedural foliage, desert terrain sculpting and landscape '
                'composition, built through lighting, scale and material blending.',
        'stack': ['Unreal Engine'],
    },
]

STACK = [
    ('Languages', ['TypeScript', 'JavaScript', 'SQL', 'HTML', 'CSS']),
    ('Frontend', ['React', 'Next.js', 'GSAP', 'Vite']),
    ('Backend & Data', ['Node.js', 'Express', 'PostgreSQL', 'Zod']),
    ('Game Development', ['Unreal Engine']),
    ('Tooling', ['Git', 'Docker', 'Vitest', 'Vercel']),
]

# ---------------------------------------------------------------- THEME

THEMES = {
    'light': {
        'text': '#111111', 'muted': '#696969', 'faint': '#a3a3a0',
        'rule': '#e3e3e0', 'surface': '#f3f3f1', 'grid': 'rgba(0,0,0,0.09)',
        'levels': ['#ececea', '#c4c4c1', '#8f8f8c', '#555553', '#111111'],
    },
    'dark': {
        'text': '#f0f0ee', 'muted': '#9a9a97', 'faint': '#5f5f5c',
        'rule': '#2a2d31', 'surface': '#161a1f', 'grid': 'rgba(255,255,255,0.07)',
        'levels': ['#1b1f24', '#3b3e42', '#6d6f71', '#a9aaa9', '#f0f0ee'],
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


def t(x, y, s, size, weight, fill, anchor='start', tracking=0.0, upper=False):
    s = s.upper() if upper else s
    ls = f' letter-spacing="{tracking * size:.2f}"' if tracking else ''
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}"{ls}>{escape(s)}</text>'
    )


def arrow(x, y, size, stroke, width=1.6):
    """A drawn ↗, so it sits optically the same at every size."""
    return (
        f'<path d="M{x:.1f} {y + size:.1f} L{x + size:.1f} {y:.1f} M{x + size * 0.28:.1f} {y:.1f} '
        f'H{x + size:.1f} V{y + size * 0.72:.1f}" fill="none" stroke="{stroke}" '
        f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


# ---------------------------------------------------------------- STATIC

def header(c):
    h = 380
    cell = 40
    grid = ''.join(f'<path d="M{x} 0V{h}"/>' for x in range(0, W + 1, cell))
    grid += ''.join(f'<path d="M0 {y}H{W}"/>' for y in range(0, h + 1, cell))
    body = (
        '<defs><radialGradient id="g" cx="0.72" cy="0.38" r="0.75">'
        '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
        '</radialGradient><mask id="m"><rect width="100%" height="100%" fill="url(#g)"/></mask></defs>'
        f'<g mask="url(#m)" stroke="{c["grid"]}" stroke-width="1">{grid}</g>'
        + t(0, 34, 'SR', 18, 900, c['text'])
        + t(W, 34, 'Portfolio', 13, 400, c['muted'], 'end', 0.18, True)
    )
    size = 132
    for i, word in enumerate(NAME):
        body += t(-6, 150 + i * size * 0.86, word, size, 900, c['text'], tracking=-0.03)
    base = 340
    lines = wrap(TAGLINE, 17, 300, 420)
    for i, line in enumerate(lines):
        body += t(0, base - (len(lines) - 1 - i) * 24, line, 17, 300, c['muted'])
    label_w = text_width(SITE_LABEL, 15, 400)
    pill_w = label_w + 70
    px = W - pill_w
    body += (
        f'<rect x="{px + 0.5}" y="{base - 30.5}" width="{pill_w - 1}" height="44" rx="22" '
        f'fill="none" stroke="{c["text"]}"/>'
        + t(px + 24, base - 3, SITE_LABEL, 15, 400, c['text'])
        + arrow(px + pill_w - 34, base - 15, 9, c['text'])
    )
    return svg(W, h, body, [300, 400, 900], f'Swarnim Rai: {TAGLINE} Visit {SITE_LABEL}')


def link_pill(label, c):
    size = 15
    w = round(text_width(label, size, 400) + 64)
    h = 44
    body = (
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{h / 2}" '
        f'fill="none" stroke="{c["text"]}"/>'
        + t(22, 27.5, label, size, 400, c['text'])
        + arrow(w - 32, 17, 9, c['text'])
    )
    return svg(w, h, body, [400], label)


def section_title(num, title, c):
    h = 84
    body = (
        t(0, 22, num, 13, 400, c['muted'], tracking=0.18)
        + t(0, 64, title, 36, 500, c['text'], tracking=-0.02)
        + f'<rect x="0" y="{h - 1}" width="{W}" height="1" fill="{c["rule"]}"/>'
    )
    return svg(W, h, body, [400, 500], f'{num} {title}')


CARD_W, CARD_PAD = 430, 30


def card_height():
    body_lines = max(len(wrap(p['body'], 15, 300, CARD_W - CARD_PAD * 2)) for p in PROJECTS)
    return 150 + body_lines * 23 + 64


def project_card(i, p, c):
    w, h, pad = CARD_W, card_height(), CARD_PAD
    body = (
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="18" fill="{c["surface"]}" '
        f'stroke="{c["rule"]}"/>'
        + t(pad, pad + 14, f'{i:02d}', 13, 400, c['muted'], tracking=0.18)
        + t(pad + 34, pad + 14, p['kind'], 13, 400, c['muted'], tracking=0.18, upper=True)
        + arrow(w - pad - 12, pad + 1, 12, c['text'], 1.8)
        + t(pad, pad + 86, p['title'], 30, 500, c['text'], tracking=-0.02)
    )
    for j, line in enumerate(wrap(p['body'], 15, 300, w - pad * 2)):
        body += t(pad, pad + 124 + j * 23, line, 15, 300, c['muted'])
    body += f'<rect x="{pad}" y="{h - pad - 30}" width="{w - pad * 2}" height="1" fill="{c["rule"]}"/>'
    body += t(pad, h - pad, '   ·   '.join(p['stack']), 12, 400, c['text'], tracking=0.16, upper=True)
    return svg(w, h, body, [300, 400, 500], f'{p["title"]}: {p["body"]}')


def stack(c):
    row = 64
    h = row * len(STACK)
    body = ''
    for i, (label, items) in enumerate(STACK):
        y = i * row
        body += t(0, y + 38, label, 12, 400, c['muted'], tracking=0.18, upper=True)
        x = 250
        for item in items:
            body += t(x, y + 39, item, 19, 400, c['text'])
            x += text_width(item, 19, 400) + 34
        body += f'<rect x="0" y="{y + row - 1}" width="{W}" height="1" fill="{c["rule"]}"/>'
    alt = '; '.join(f'{label}: {", ".join(items)}' for label, items in STACK)
    return svg(W, h, body, [400], alt)


def build_static():
    out = ROOT / 'assets'
    out.mkdir(exist_ok=True)
    for name, c in THEMES.items():
        files = {
            f'header-{name}.svg': header(c),
            f'stack-{name}.svg': stack(c),
        }
        for slug, label in LINKS:
            files[f'link-{slug}-{name}.svg'] = link_pill(label, c)
        for slug, num, title in SECTIONS:
            files[f'section-{slug}-{name}.svg'] = section_title(num, title, c)
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
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
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


def stats(u, c, today):
    cc = u['contributionsCollection']
    repos = u['repositories']
    metrics = [
        (cc['contributionCalendar']['totalContributions'], 'Contributions', 'past year'),
        (cc['totalCommitContributions'], 'Commits', 'past year'),
        (u['pullRequests']['totalCount'], 'Pull requests', 'all time'),
        (repos['totalCount'], 'Public repos', 'owned'),
        (sum(r['stargazerCount'] for r in repos['nodes']), 'Stars', 'earned'),
    ]
    since = u['createdAt'][:4]
    body = (
        t(0, 16, f'@{USER}', 13, 400, c['muted'], tracking=0.12)
        + t(W, 16, f'On GitHub since {since}  ·  Updated {today:%d %b %Y}', 13, 400, c['muted'], 'end', 0.04)
    )
    col = W / len(metrics)
    for i, (value, label, note) in enumerate(metrics):
        x = i * col
        if i:
            body += f'<rect x="{x - 0.5:.1f}" y="44" width="1" height="94" fill="{c["rule"]}"/>'
        px = x + (0 if i == 0 else 24)
        body += t(px, 104, fmt(value), 52, 500, c['text'], tracking=-0.03)
        body += t(px, 132, label, 12, 400, c['text'], tracking=0.16, upper=True)
        body += t(px + text_width(label.upper(), 12, 400, 0.16) + 8, 132, note, 12, 300, c['muted'])

    sizes = {}
    for r in repos['nodes']:
        if r['name'] == USER:
            continue
        for e in r['languages']['edges']:
            sizes[e['node']['name']] = sizes.get(e['node']['name'], 0) + e['size']
    total = sum(sizes.values())
    top = sorted(sizes.items(), key=lambda kv: -kv[1])
    if len(top) > 5:
        top = top[:4] + [('Other', sum(v for _, v in top[4:]))]
    shades = c['levels'][::-1][:len(top)]
    y = 186
    body += f'<rect x="0" y="{y - 22}" width="{W}" height="1" fill="{c["rule"]}"/>'
    body += t(0, y + 8, 'Languages', 12, 400, c['muted'], tracking=0.18, upper=True)
    body += t(W, y + 8, 'by bytes of code in public repos', 12, 300, c['muted'], 'end')
    bar_y, x, gap = y + 28, 0.0, 3
    usable = W - gap * (len(top) - 1)
    for (name, size), fill in zip(top, shades):
        seg = usable * size / total if total else 0
        body += f'<rect x="{x:.1f}" y="{bar_y}" width="{max(seg, 2):.1f}" height="10" rx="2" fill="{fill}"/>'
        x += seg + gap
    lx = 0.0
    for (name, size), fill in zip(top, shades):
        pct = f'{100 * size / total:.1f}%' if total else '-'
        body += f'<rect x="{lx:.1f}" y="{bar_y + 34}" width="10" height="10" rx="2" fill="{fill}"/>'
        body += t(lx + 18, bar_y + 44, name, 14, 400, c['text'])
        nx = lx + 18 + text_width(name, 14, 400) + 7
        body += t(nx, bar_y + 44, pct, 14, 300, c['muted'])
        lx = nx + text_width(pct, 14, 300) + 30
    h = bar_y + 56
    alt = ', '.join(f'{v} {l.lower()}' for v, l, _ in metrics)
    return svg(W, h, body, [300, 400, 500], f'GitHub stats: {alt}')


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
    body = (
        t(0, 40, fmt(cal['totalContributions']), 40, 500, c['text'], tracking=-0.03)
        + t(text_width(fmt(cal['totalContributions']), 40, 500, -0.03) + 12, 40,
            'contributions in the last year', 15, 300, c['muted'])
        + t(W, 22, 'Current streak', 12, 400, c['muted'], 'end', 0.16, True)
        + t(W, 42, plural(current, 'day'), 16, 400, c['text'], 'end')
        + t(W - 150, 22, 'Longest streak', 12, 400, c['muted'], 'end', 0.16, True)
        + t(W - 150, 42, plural(longest, 'day'), 16, 400, c['text'], 'end')
        + t(W - 300, 22, 'Active days', 12, 400, c['muted'], 'end', 0.16, True)
        + t(W - 300, 42, str(active), 16, 400, c['text'], 'end')
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
            body += (
                f'<rect x="{left + i * (cell + gap):.2f}" y="{top + d["weekday"] * (cell + gap):.2f}" '
                f'width="{cell:.2f}" height="{cell:.2f}" rx="2.5" fill="{c["levels"][lvl]}"/>'
            )
    for wd, label in ((1, 'Mon'), (3, 'Wed'), (5, 'Fri')):
        body += t(0, top + wd * (cell + gap) + cell - 2.5, label, 11, 400, c['muted'])
    ly = top + 7 * (cell + gap) + 22
    lx = W - 5 * (cell + gap) - 40
    body += t(lx - 8, ly + cell - 2.5, 'Less', 11, 400, c['muted'], 'end')
    for k, fill in enumerate(c['levels']):
        body += f'<rect x="{lx + k * (cell + gap):.2f}" y="{ly:.2f}" width="{cell:.2f}" height="{cell:.2f}" rx="2.5" fill="{fill}"/>'
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
