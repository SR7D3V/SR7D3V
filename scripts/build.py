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

LINKS = [
    ('linkedin', 'LinkedIn'),
    ('github', 'GitHub'),
    ('email', 'Email'),
]

# (slug, number, title, palette colour)
SECTIONS = [
    ('about', '01', 'About', 'merlot'),
    ('projects', '02', 'Featured Projects', 'olive'),
    ('stack', '03', 'Tech Stack', 'midnight'),
    ('stats', '04', 'GitHub Stats', 'tobacco'),
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


def glass(x, y, w, h, ink):
    """A neutral, translucent pill: buttons and chips stay colourless so the palette isn't overused."""
    return rect(x, y, w, h, ink, h / 2, f' fill-opacity="0.06" stroke="{ink}" stroke-opacity="0.24"')


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
        glass(px + 0.5, base - 30.5, pill_w - 1, 45, c['panel_text'])
        + t(px + 24, base - 2, SITE_LABEL, 15, 400, c['panel_text'])
        + arrow(px + pill_w - 34, base - 14, 9, c['panel_text'])
    )
    return svg(W, h, body, [300, 400, 900], f'Swarnim Rai: {TAGLINE} Visit {SITE_LABEL}')


def link_pill(label, c):
    size, h = 15, 44
    w = round(text_width(label, size, 400) + 64)
    body = (
        glass(0.5, 0.5, w - 1, h - 1, c['text'])
        + t(22, 27.5, label, size, 400, c['text'])
        + arrow(w - 32, 17, 9, c['text'])
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


def stack(c):
    """One row per category, marked with the category's colour; items are neutral chips."""
    item_x, size, chip_h, chip_gap, line_gap, pad_y = 250, 15, 34, 8, 10, 18
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
                body += glass(cx + 0.5, cy + 0.5, cw - 1, chip_h - 1, c['text'])
                body += t(cx + 15, cy + 22.5, item, size, 400, c['text'])
        y += row_h
        body += rect(0, y - 1, W, 1, c['rule'])
    alt = '; '.join(f'{label}: {", ".join(items)}' for label, items, _ in STACK)
    return svg(W, y, body, [400], alt)


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
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes {
        name
        stargazerCount
        primaryLanguage { name }
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
    }
  }
}
"""

ORDER = ['merlot', 'tobacco', 'olive', 'midnight', 'graphite']


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


def top_five(counts):
    top = sorted(counts.items(), key=lambda kv: -kv[1])
    if len(top) > 5:
        top = top[:4] + [('Other', sum(v for _, v in top[4:]))]
    return top


def donut_panel(x0, width, title, note, items, centre, caption, c, value_fmt):
    """A titled donut with a legend. items: [(name, value, colour)]."""
    total = sum(v for _, v, _ in items)
    cx, cy, r, sw = x0 + width / 2, 180, 70, 18
    body = (
        t(x0, 60, title, 12, 400, c['muted'], tracking=0.16, upper=True)
        + t(x0 + width, 60, note, 12, 300, c['muted'], 'end')
        + f'<circle cx="{cx:.1f}" cy="{cy}" r="{r}" fill="none" stroke="{c["track"]}" stroke-width="{sw}"/>'
    )
    circ = 2 * math.pi * r
    shown = [(n, v, col) for n, v, col in items if v]
    gap = 3 if len(shown) > 1 else 0
    offset = 0.0
    for _, v, col in shown:
        seg = circ * v / total
        body += (
            f'<circle cx="{cx:.1f}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}" '
            f'stroke-dasharray="{max(seg - gap, 0.5):.2f} {circ:.2f}" stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {cx:.1f} {cy})"/>'
        )
        offset += seg
    body += t(cx, cy + 4, centre if total else '—', 26, 500, c['text'], 'middle', -0.02)
    body += t(cx, cy + 22, caption if total else 'no data yet', 10, 400, c['muted'], 'middle', 0.08, True)
    for k, (name, v, col) in enumerate(items):
        yy = 292 + k * 27
        body += rect(x0, yy - 10, 10, 10, col, 2)
        body += t(x0 + 18, yy, name, 14, 400, c['text'])
        body += t(x0 + width, yy, value_fmt(v, total), 14, 300, c['muted'], 'end')
    return body, 292 + (len(items) - 1) * 27 + 14


def stats(u, c, today):
    cc = u['contributionsCollection']
    repos = u['repositories']['nodes']
    stars = sum(r['stargazerCount'] for r in repos)
    colours = lambda names: [c['muted'] if n == 'Other' else c['colors'][ORDER[k % 5]] for k, n in enumerate(names)]
    pct = lambda v, total: f'{100 * v / total:.1f}%' if total else '0%'
    count = lambda v, total: fmt(v)

    sizes = {}
    for r in repos:
        if r['name'] == USER:
            continue
        for e in r['languages']['edges']:
            sizes[e['node']['name']] = sizes.get(e['node']['name'], 0) + e['size']
    langs = top_five(sizes)
    lang_total = sum(v for _, v in langs)

    primary = {}
    for r in repos:
        name = (r['primaryLanguage'] or {}).get('name', 'Other')
        primary[name] = primary.get(name, 0) + 1
    by_repo = top_five(primary)

    mix = [
        ('Commits', cc['totalCommitContributions']),
        ('Pull requests', cc['totalPullRequestContributions']),
        ('Reviews', cc['totalPullRequestReviewContributions']),
        ('Issues', cc['totalIssueContributions']),
        ('New repos', cc['totalRepositoryContributions']),
    ]
    mix_total = sum(v for _, v in mix)

    gap = 44
    col = (W - gap * 2) / 3
    panels = [
        ('Languages', 'by bytes of code',
         [(n, v, k) for (n, v), k in zip(langs, colours([n for n, _ in langs]))],
         f'{100 * langs[0][1] / lang_total:.0f}%' if lang_total else '', langs[0][0] if langs else '', pct),
        ('Repos by language', 'primary language',
         [(n, v, k) for (n, v), k in zip(by_repo, colours([n for n, _ in by_repo]))],
         fmt(len(repos)), 'public repos', count),
        ('Contribution mix', 'past year',
         [(n, v, c['colors'][ORDER[k]]) for k, (n, v) in enumerate(mix)],
         fmt(mix_total), 'contributions', count),
    ]
    body = (
        t(0, 16, f'@{USER}  ·  {len(repos)} public repos  ·  {stars} stars', 13, 400, c['muted'], tracking=0.04)
        + t(W, 16, f'On GitHub since {u["createdAt"][:4]}  ·  Updated {today:%d %b %Y}', 13, 400, c['muted'], 'end', 0.04)
    )
    bottom = 0
    for k, (title, note, items, centre, caption, value_fmt) in enumerate(panels):
        part, end = donut_panel(k * (col + gap), col, title, note, items, centre, caption, c, value_fmt)
        body += part
        bottom = max(bottom, end)
    for k in (1, 2):
        body += rect(k * (col + gap) - gap / 2, 44, 1, bottom - 44, c['rule'])
    return svg(W, round(bottom), body, [300, 400, 500],
               'GitHub stats: languages, repositories by language and contribution mix')


def build_live():
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    u = fetch()
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date()
    for name, c in THEMES.items():
        (out / f'stats-{name}.svg').write_text(stats(u, c, today))
    print(f'wrote live graphics to {out}')


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'static'
    {'static': build_static, 'live': build_live}[mode]()
