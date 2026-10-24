"""Builds the SVG graphics for the profile README.

    python3 scripts/build.py static   # header, links, section titles, projects, stack -> assets/
    python3 scripts/build.py live     # GitHub stats + contributions -> dist/ (needs GITHUB_TOKEN)

Edit the CONTENT block below, then re-run `static`. Standard library only.
"""

import base64
import re
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
# Lines break where the portfolio's hero breaks them.
TAGLINE_LINES = ['I like to design, develop,', 'and deliver digital experiences.']
TAGLINE = ' '.join(TAGLINE_LINES)

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
        'url': 'https://github.com/SR7D3V/Lucid',
        'kind': 'Full-stack',
        'title': 'Lucid',
        'body': 'A multi-store clothing retail platform. 3NF PostgreSQL schema, concurrency-safe '
                'checkout with row-level locks, a trigger-maintained inventory ledger and '
                'full-text search.',
        'stack': ['Next.js', 'TypeScript', 'PostgreSQL'],
        'color': 'merlot',
    },
    {
        'slug': 'tenderbridge',
        'url': 'https://github.com/harshbhushan21/TenderBridge',
        'kind': 'Agentic AI',
        'title': 'TenderBridge',
        'body': 'A bid / no-bid copilot for public IT tenders. LangGraph agents turn a tender pack '
                'into a compliance matrix, a scored recommendation and a cited draft, with a human '
                'approving each decision.',
        'stack': ['Python', 'LangGraph', 'Next.js'],
        'color': 'olive',
    },
    {
        'slug': 'hibermate',
        'url': 'https://github.com/SR7D3V/hibermate',
        'kind': 'macOS',
        'title': 'Hibermate',
        'body': 'A menu bar app that keeps a MacBook awake with the lid closed only while AI agents '
                'like Claude Code and Codex are working, then lets it sleep, with thermal and '
                'battery safety limits.',
        'stack': ['Swift', 'SwiftUI', 'Shell'],
        'color': 'tobacco',
    },
]

# (category, palette colour, [(name shown on hover, icon key, brand colour, link)])
# Brand colour None uses the category's palette colour; 'ink' keeps monochrome logos in the text colour.
MDN = 'https://developer.mozilla.org/en-US/docs/Web'
WIKI = 'https://en.wikipedia.org/wiki'
STACK = [
    ('Programming Languages', 'merlot', [
        ('Java', 'java', '#E76F00', 'https://dev.java'),
        ('Python', 'python', '#3776AB', 'https://www.python.org'),
        ('C', 'c', '#A8B9CC', 'https://en.cppreference.com/w/c'),
        ('Swift', 'swift', '#F05138', 'https://www.swift.org'),
        ('SQL', 'sql', None, f'{WIKI}/SQL'),
    ]),
    ('Frontend Development', 'tobacco', [
        ('JavaScript', 'javascript', '#F7DF1E', f'{MDN}/JavaScript'),
        ('React', 'react', '#61DAFB', 'https://react.dev'),
        ('Next.js', 'nextjs', 'ink', 'https://nextjs.org'),
        ('GSAP', 'gsap', '#0AE448', 'https://gsap.com'),
        ('Web Animation', 'web-animation', None, f'{MDN}/API/Web_Animations_API'),
        ('HTML', 'html', '#E34F26', f'{MDN}/HTML'),
        ('CSS', 'css', '#663399', f'{MDN}/CSS'),
    ]),
    ('Backend Development', 'olive', [
        ('MySQL', 'mysql', '#4479A1', 'https://www.mysql.com'),
        ('Oracle SQL', 'oracle', '#F80000', 'https://www.oracle.com/database/'),
        ('PostgreSQL', 'postgresql', '#4169E1', 'https://www.postgresql.org'),
        ('Schema Design', 'schema-design', None, f'{WIKI}/Database_schema'),
        ('Query Optimization', 'query-optimization', None, f'{WIKI}/Query_optimization'),
    ]),
    ('Design', 'midnight', [
        ('UI/UX Design', 'ui-ux', None, f'{WIKI}/User_experience_design'),
        ('Graphic Design', 'graphic-design', None, f'{WIKI}/Graphic_design'),
    ]),
    ('Game Development', 'merlot', [
        ('Unreal Engine', 'unreal-engine', 'ink', 'https://www.unrealengine.com'),
        ('Blender', 'blender', '#E87D0D', 'https://www.blender.org'),
        ('Meta XR', 'meta', '#0081FB', 'https://developers.meta.com/horizon/'),
    ]),
    ('Tools', 'tobacco', [
        ('Git', 'git', '#F05032', 'https://git-scm.com'),
        ('Jupyter', 'jupyter', '#F37626', 'https://jupyter.org'),
        ('VS Code', 'vscode', '#007ACC', 'https://code.visualstudio.com'),
        ('Figma', 'figma', '#F24E1E', 'https://www.figma.com'),
        ('Xcode', 'xcode', '#147EFB', 'https://developer.apple.com/xcode/'),
        ('Swift Playgrounds', 'swift+play', '#F05138', 'https://www.apple.com/swift/playgrounds/'),
    ]),
]

# Bump when graphics change so GitHub's image cache fetches the new files.
VERSION = 9

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
        'bg': '#ffffff', 'panel': BONE, 'panel_text': GRAPHITE, 'panel_muted': '#6f675c',
        'grid': 'rgba(18,18,18,0.07)', 'track': '#ece6dc',
        'colors': dict(PALETTE),
    },
    'dark': {
        'text': BONE, 'muted': '#a39b8e', 'rule': '#2a303a',
        'bg': '#0d1117', 'panel': '#1C2430', 'panel_text': BONE, 'panel_muted': '#a39b8e',
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


def glass(x, y, w, h, ink, rx=None):
    """A neutral, translucent pill: buttons and chips stay colourless so the palette isn't overused."""
    return rect(x, y, w, h, ink, h / 2 if rx is None else rx,
                f' fill-opacity="0.06" stroke="{ink}" stroke-opacity="0.24"')


def palette_band(x, y, w, h, c):
    order = ['merlot', 'olive', 'tobacco', 'midnight', 'graphite']
    seg = w / len(order)
    return ''.join(rect(x + i * seg, y, seg + 0.5, h, c['colors'][k]) for i, k in enumerate(order))


# ---------------------------------------------------------------- STATIC

# The header mirrors the portfolio's footer: a black card, an ASCII rose
# growing out of the bottom-left corner (scripts/rose.py builds it) and the
# name stacked on the right. Same card in light and dark themes.
FOOTER_BG, FOOTER_INK, FOOTER_MUTED = '#0b0b0b', '#f0f0ee', '#8f897f'
ROSE = json.loads((ROOT / 'assets' / 'rose-ascii.json').read_text())


def rose_ascii(x0, y0, width):
    """The rose's characters, one <text> per row and colour, each glyph on its cell."""
    cols, rows = ROSE['cols'], ROSE['rows']
    cell = width / cols
    runs = {}
    for col, row, char, color in ROSE['cells']:
        runs.setdefault((row, color), []).append((col, char))
    out = [f'<g font-family="ui-monospace,Menlo,Consolas,monospace" font-size="{cell * 0.9:.2f}" '
           f'text-anchor="middle">']
    for (row, color), glyphs in sorted(runs.items()):
        xs = ' '.join(f'{x0 + (col + 0.5) * cell:.1f}' for col, _ in glyphs)
        text = escape(''.join(ch for _, ch in glyphs))
        out.append(f'<text x="{xs}" y="{y0 + row * cell + cell * 0.8:.1f}" fill="{color}" '
                   f'xml:space="preserve">{text}</text>')
    out.append('</g>')
    return ''.join(out), rows * cell


def header(c):
    h, pad = 420, 44
    rose_w = 370
    _, rose_h = rose_ascii(0, 0, rose_w)
    # Pushed past the corner so the stem runs off the edge, as on the site.
    rose_svg, _ = rose_ascii(-rose_w * 0.14, h - rose_h + rose_w * 0.2, rose_w)

    body = (
        '<defs><clipPath id="card"><rect width="100%" height="100%" rx="22"/></clipPath></defs>'
        '<g clip-path="url(#card)">'
        + rect(0, 0, W, h, FOOTER_BG)
        + rose_svg
        + '</g>'
        + t(W - pad, pad + 14, 'Portfolio', 13, 400, FOOTER_MUTED, 'end', 0.18, True)
    )

    # Tagline, small, top left (where the footer keeps its contact line).
    for i, line in enumerate(TAGLINE_LINES):
        body += t(pad, pad + 14 + i * 22, line, 15, 300, FOOTER_MUTED)

    # SWARNIM over RAI, right-aligned like the footer.
    size = 112
    right = W - pad + size * 0.03
    for i, word in enumerate(NAME):
        body += t(right, 210 + i * size * 0.85, word, size, 900, FOOTER_INK, 'end', tracking=-0.03)

    base = h - pad + 4
    pill_w = text_width(SITE_LABEL, 15, 400) + 70
    px = W - pad - pill_w
    body += (
        glass(px + 0.5, base - 30.5, pill_w - 1, 45, FOOTER_INK)
        + t(px + 24, base - 2, SITE_LABEL, 15, 400, FOOTER_INK)
        + arrow(px + pill_w - 34, base - 14, 9, FOOTER_INK)
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


CARD_W, CARD_PAD = 300, 26


def card_chips(stack):
    """Lay the stack chips out left to right, wrapping when a row is full."""
    rows, row, x = [], [], 0.0
    for item in stack:
        cw = text_width(item.upper(), 10, 500, 0.12) + 20
        if row and x + cw > CARD_W - CARD_PAD * 2:
            rows.append(row)
            row, x = [], 0.0
        row.append((x, cw, item))
        x += cw + 6
    return rows + [row]


def card_height():
    """Square cards, growing only if a description needs more room. All cards share one height."""
    need = max(
        118 + len(wrap(p['body'], 13.5, 300, CARD_W - CARD_PAD * 2)) * 20 + 18
        + len(card_chips(p['stack'])) * 30 + CARD_PAD
        for p in PROJECTS
    )
    return max(CARD_W, round(need))


def project_card(i, p, c):
    w, h, pad = CARD_W, card_height(), CARD_PAD
    fill = PALETTE[p.get('color', 'merlot')]
    body = (
        '<defs><clipPath id="card"><rect width="100%" height="100%" rx="18"/></clipPath></defs>'
        f'<g clip-path="url(#card)">{rect(0, 0, w, h, fill)}</g>'
        + t(pad, pad + 10, f'{i:02d}', 11, 400, BONE, tracking=0.16, opacity=0.6)
        + t(pad + 26, pad + 10, p['kind'], 11, 500, BONE, tracking=0.16, upper=True, opacity=0.85)
        + arrow(w - pad - 11, pad, 11, BONE, 1.6)
        + t(pad, pad + 70, p['title'], 32, 500, BONE, tracking=-0.02)
    )
    for j, line in enumerate(wrap(p['body'], 13.5, 300, w - pad * 2)):
        body += t(pad, pad + 100 + j * 20, line, 13.5, 300, BONE, opacity=0.78)
    rows = card_chips(p['stack'])
    for k, row in enumerate(reversed(rows)):
        cy = h - pad - 24 - k * 30
        for x, cw, item in row:
            body += rect(pad + x, cy, cw, 24, 'none', 12, f' stroke="{BONE}" stroke-opacity="0.4"')
            body += t(pad + x + 10, cy + 16, item, 10, 500, BONE, tracking=0.12, upper=True)
    return svg(w, h, body, [300, 400, 500], f'{p["title"]}: {p["body"]}')


ICONS = json.loads((ROOT / 'scripts' / 'icons.json').read_text())
# Oracle's wordmark is a thin strip; at tile size only its O mark stays legible, so crop to that.
ICONS['oracle']['viewBox'] = '-0.6 50.1 27.8 27.8'
TILE, GLYPH = 56, 26


def glyph(key, x, y, size, ink):
    icon = ICONS[key]
    shapes = ''.join(
        f'<{tag} ' + ' '.join(f'{k}="{escape(v)}"' for k, v in attrs.items()) + '/>'
        for tag, attrs in icon['shapes']
    )
    if icon['mode'] == 'stroke':
        paint = f'fill="none" stroke="{ink}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
    else:
        paint = f'fill="{ink}"'
    return (f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="{icon["viewBox"]}">'
            f'<g {paint}>{shapes}</g></svg>')


def _rgb(hex_):
    return [int(hex_[i:i + 2], 16) for i in (1, 3, 5)]


def _hex(rgb):
    return '#' + ''.join(f'{round(v):02x}' for v in rgb)


def _mix(a, b, k):
    return _hex([x + (y - x) * k for x, y in zip(_rgb(a), _rgb(b))])


def _contrast(a, b):
    def lum(h):
        v = [x / 255 for x in _rgb(h)]
        v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def readable(color, c):
    """Nudge a brand colour toward the text colour until it stands out from the page."""
    # Thin-line logos need more contrast on the dark background to read at tile size.
    minimum = 5.5 if c['bg'] == '#0d1117' else 3.4
    k = 0.0
    while _contrast(_mix(color, c['text'], k), c['bg']) < minimum and k < 1:
        k += 0.05
    return _mix(color, c['text'], min(k, 1))


def icon_tile(key, name, brand, category, c):
    base, _, badge = key.partition('+')
    if brand == 'ink':
        ink, tint = c['text'], c['text']
    else:
        ink = readable(brand or c['colors'][category], c)
        tint = ink
    o = (TILE - GLYPH) / 2
    body = rect(0.5, 0.5, TILE - 1, TILE - 1, tint, 16,
                f' fill-opacity="{0.06 if brand == "ink" else 0.1}" stroke="{tint}" stroke-opacity="0.32"')
    body += glyph(base, o, o, GLYPH, ink)
    if badge == 'play':
        # Swift Playgrounds: the Swift mark with a small play badge.
        bx, by = TILE - 17, TILE - 17
        body += (f'<circle cx="{bx}" cy="{by}" r="8" fill="{ink}"/>'
                 f'<path d="M{bx - 2.5} {by - 4}L{bx + 4} {by}L{bx - 2.5} {by + 4}Z" fill="{c["bg"]}"/>')
    return svg(TILE, TILE, body, [], name)


def stack_label(label, color, c):
    w = 230
    body = rect(0, TILE / 2 - 5, 10, 10, c['colors'][color], 2)
    lines = wrap(label.upper(), 12, 400, w - 30)
    top = TILE / 2 + 4.5 - (len(lines) - 1) * 8.5
    for k, line in enumerate(lines):
        body += t(20, top + k * 17, line, 12, 400, c['muted'], tracking=0.16)
    return svg(w, TILE, body, [400], label)


def rule(c):
    return svg(W, 1, rect(0, 0, W, 1, c['rule']), [], '')


def slugify(s):
    return ''.join(ch if ch.isalnum() else '-' for ch in s.lower()).strip('-')


RAW = f'https://raw.githubusercontent.com/{USER}/{USER}/main/assets'


def picture(name, alt, width=None, title=None):
    w = f' width="{width}"' if width else ''
    tt = f' title="{escape(title)}"' if title else ''
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{RAW}/{name}-dark.svg?v={VERSION}" />'
            f'<img src="{RAW}/{name}-light.svg?v={VERSION}" alt="{escape(alt)}"{tt}{w} /></picture>')


def readme_projects():
    cards = [f'<a href="{p["url"]}">{picture("project-" + p["slug"], p["title"] + ": " + p["body"], "32%")}</a>'
             for p in PROJECTS]
    rows = ['<p>\n' + '\n'.join(cards[k:k + 3]) + '\n</p>' for k in range(0, len(cards), 3)]
    return '\n'.join(rows)


def readme_stack():
    rows = []
    for label, _, items in STACK:
        # The link's title gives a hover label over the whole tile, and clicking opens the tool's site.
        tiles = [f'<a href="{url}" title="{escape(name)}">{picture(f"icon-{slugify(name)}", name, title=name)}</a>'
                 for name, _, _, url in items]
        rows.append('<p>\n' + picture(f'stack-{slugify(label)}', label) + '\n' + '\n'.join(tiles) + '\n</p>')
    return f'\n{picture("rule", "", "100%")}\n'.join(rows)


def fill_readme():
    path = ROOT / 'README.md'
    text = path.read_text()
    for key, block in (('projects', readme_projects()), ('stack', readme_stack())):
        start, end = f'<!-- {key}:start -->', f'<!-- {key}:end -->'
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        text = f'{before}{start}\n{block}\n{end}{after}'
    # Every image link carries the version, so GitHub's image cache refetches
    # them all when the graphics change (hand-written links included).
    text = re.sub(r'(\.svg)\?v=\d+', rf'\1?v={VERSION}', text)
    path.write_text(text)


def build_static():
    out = ROOT / 'assets'
    out.mkdir(exist_ok=True)
    for name, c in THEMES.items():
        files = {
            f'header-{name}.svg': header(c),
            f'rule-{name}.svg': rule(c),
        }
        for slug, label in LINKS:
            files[f'link-{slug}-{name}.svg'] = link_pill(label, c)
        for slug, num, title, color in SECTIONS:
            files[f'section-{slug}-{name}.svg'] = section_title(num, title, color, c)
        for i, p in enumerate(PROJECTS, 1):
            files[f'project-{p["slug"]}-{name}.svg'] = project_card(i, p, c)
        for label, color, items in STACK:
            files[f'stack-{slugify(label)}-{name}.svg'] = stack_label(label, color, c)
            for item, key, brand, _ in items:
                files[f'icon-{slugify(item)}-{name}.svg'] = icon_tile(key, item, brand, color, c)
        for fname, content in files.items():
            (out / fname).write_text(content)
    fill_readme()
    print(f'wrote static graphics to {out} and updated README.md')


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
