#!/usr/bin/env python3
"""
Render the profile README's cards as animated SVGs into cards/.

Design: "Three Worlds", matched to avivashishta.com (paper, ink, and one colour per
world: BUILD blue, BRAND red, LEARN yellow; Instrument Serif, Geist, Geist Mono).

Every card is a standalone SVG shown through <img>, so it can only use what GitHub
allows there: inline CSS animations, SMIL and fonts embedded as data URIs (no JS,
no external requests). Fonts are subset WOFFs in fonts/ (SIL OFL).

Live numbers come from data/contributions.json (fetch_contributions.py). The
brand and blog numbers are set by hand below; they come from data/stats.json in
the avivashishta.com repo.

Run by .github/workflows/update-profile-art.yml after fetch_contributions.py.
"""
import base64
import datetime
import json
import os
import re
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data", "contributions.json")
OUT = os.path.join(ROOT, "cards")
FONTS = os.path.join(ROOT, "fonts")
ICONS = os.path.join(ROOT, "icons")
PORTRAIT = os.path.join(ROOT, "subh-ascii.svg")

# ---- hand-set numbers (update from avivashishta.com data/stats.json) --------
REEL_VIEWS = "12.7M"
BLOG_READERS = "27.5K"

# ---- brand tokens -----------------------------------------------------------
PAPER = "#f3f3f1"
PAPER_DEEP = "#e2e2de"
INK = "#111111"
INK_SOFT = "#3a3a3c"
MUTED = "#6e6e73"
RULE = "#dcdcd7"
TECH = "#2f55ff"
STUDIO = "#ef3b2d"
LEARN = "#ffc81a"
W = 880  # full card width, GitHub's README column at 100%

SERIF = "'Instrument Serif', Georgia, serif"
SANS = "Geist, system-ui, -apple-system, sans-serif"
MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

FONT_FILES = {
    "serif": ("Instrument Serif", "normal", 400, "serif-400.woff"),
    "serif-i": ("Instrument Serif", "italic", 400, "serif-italic.woff"),
    "sans": ("Geist", "normal", 400, "geist-400.woff"),
    "sans-b": ("Geist", "normal", 600, "geist-600.woff"),
    "mono": ("Geist Mono", "normal", 400, "geistmono-400.woff"),
}

BASE_CSS = """
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.3)}70%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes nudge{0%,100%{transform:none}50%{transform:translateX(4px)}}
@keyframes nudgeup{0%,100%{transform:none}50%{transform:translate(3px,-3px)}}
.r{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.f{opacity:0;animation:fade .9s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .4s ease-out both}
.live{animation:pulse 1.6s ease-in-out infinite}
.n{transform-box:fill-box;animation:nudge 1.8s ease-in-out infinite}
.nu{transform-box:fill-box;animation:nudgeup 1.8s ease-in-out infinite}
@keyframes tilein{0%{opacity:0;transform:translateY(90px) scale(.6) rotate(-9deg)}55%{opacity:1;transform:translateY(-10px) scale(1.05) rotate(2deg)}75%{transform:translateY(3px) scale(.98) rotate(-.8deg)}90%{transform:translateY(-1px) scale(1.01) rotate(.2deg)}100%{opacity:1;transform:none}}
@keyframes slidein{from{opacity:0;transform:translateX(-26px)}to{opacity:1;transform:none}}
@keyframes arrowin{0%{opacity:0;transform:translateX(-30px)}60%{opacity:1;transform:translateX(6px)}100%{opacity:1;transform:none}}
@keyframes roll{from{transform:translateY(60px)}to{transform:none}}
@keyframes sheen{0%{transform:translateX(-260px) skewX(-20deg)}22%,100%{transform:translateX(420px) skewX(-20deg)}}
@keyframes ring{0%{opacity:.7;transform:scale(.2)}100%{opacity:0;transform:scale(2.4)}}
.ti{opacity:0;transform-box:fill-box;transform-origin:50% 60%;animation:tilein 1.1s cubic-bezier(.2,.8,.2,1) both}
.sl{opacity:0;transform-box:fill-box;animation:slidein .6s cubic-bezier(.2,.7,.2,1) both}
.ai{opacity:0;transform-box:fill-box;animation:arrowin .7s cubic-bezier(.2,.7,.2,1) both}
.ro{transform-box:fill-box;animation:roll .8s cubic-bezier(.15,.8,.2,1) both}
.sh{animation:sheen 5s ease-in-out infinite}
.rg{opacity:0;transform-box:fill-box;transform-origin:center;animation:ring 1s ease-out both}
@media (prefers-reduced-motion: reduce){.r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro,.rg{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg{display:none}}
"""


def font_face(keys):
    out = []
    for k in keys:
        fam, style, weight, fn = FONT_FILES[k]
        b64 = base64.b64encode(open(os.path.join(FONTS, fn), "rb").read()).decode()
        fmt = "woff2" if fn.endswith(".woff2") else "woff"
        out.append(
            f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
            f"src:url(data:font/{fmt};base64,{b64}) format('{fmt}')}}"
        )
    return "".join(out)


GAP = 12          # gap between cards, baked into the SVGs (GitHub's own spacing is uneven)
BOTTOM = 12       # bottom padding per row, matching GAP
COL = W / 3       # each card in a row of three is exactly a third of the column


def svg(w, h, body, fonts, label, extra_css="", left=0, right=0, bottom=BOTTOM):
    """Card of w x h drawn at x=left inside a transparent canvas, padded so rows tile exactly."""
    if left:
        body = f'<g transform="translate({left:.3f} 0)">{body}</g>'
    w, h = w + left + right, h + bottom
    css = font_face(fonts) + BASE_CSS + extra_css
    if os.environ.get("STATIC"):  # preview: show every animation at its end state
        css += ".r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg{display:none}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}" height="{h}" viewBox="0 0 {w:.3f} {h}" '
        f'role="img" aria-label="{escape(label)}"><title>{escape(label)}</title>'
        f"<style>{css}</style>{body}</svg>"
    )


def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        f.write(content)
    print(f"wrote cards/{name} ({len(content) // 1024} KB)")


def d(s):  # animation delay attribute
    return f'style="animation-delay:{s:.2f}s"'


def wrap(text, n):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > n:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def text_lines(x, y, lines, lh, attrs):
    return "".join(
        f'<text x="{x}" y="{y + i * lh}" {attrs}>{escape(l)}</text>' for i, l in enumerate(lines)
    )


# ---- 1 · hero -----------------------------------------------------------------
def hero():
    h = 420
    src = open(PORTRAIT).read()
    rows = re.findall(r'<text xml:space="preserve"[^>]*\by="([\d.]+)"[^>]*>(.*?)</text>', src, re.S)
    n = len(rows)
    portrait = []
    for i, (y, txt) in enumerate(rows):
        # rows "print" top to bottom like a slow terminal
        portrait.append(
            f'<text class="f" style="animation-delay:{0.25 + i * 0.018:.3f}s;animation-duration:.35s" '
            f'xml:space="preserve" x="20" y="{y}" fill="{INK}" font-size="7.2" '
            f'textLength="800" lengthAdjust="spacing">{txt}</text>'
        )
    s = 0.41
    body = f"""
<defs>
  <linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="600" y2="0">
    <stop offset="0" stop-color="{INK}"/><stop offset=".42" stop-color="{INK}"/>
    <stop offset=".5" stop-color="{TECH}"/><stop offset=".58" stop-color="{INK}"/>
    <stop offset="1" stop-color="{INK}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-600 0;600 0;600 0"
      keyTimes="0;.45;1" dur="7s" begin="1.6s" repeatCount="indefinite"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>
<g class="f" {d(0)}>
  <circle cx="52" cy="53" r="4.5" fill="#ff5f56"/>
  <circle cx="66" cy="53" r="4.5" fill="#ffbd2e"/>
  <circle cx="80" cy="53" r="4.5" fill="#27c93f"/>
  <text x="96" y="57" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">AI &amp; FULL-STACK ENGINEER</text>
</g>
<text class="r" {d(0.15)} x="44" y="185" font-family="{SERIF}" font-size="104" letter-spacing="-2.5" fill="{INK}">Subharup</text>
<text class="r" {d(0.3)} x="44" y="282" font-family="{SERIF}" font-style="italic" font-size="104" letter-spacing="-2.5" fill="url(#shine)">Nandi</text>
<g class="r" {d(0.55)}>
  {text_lines(48, 336, ["I build AI automation, RAG pipelines, and full-stack", "systems in Python, TypeScript & Rust. If it excites me, I ship it."], 27, f'font-family="{SANS}" font-size="18" fill="{INK_SOFT}"')}
</g>
<g class="f" {d(0.8)}>
  <text x="48" y="396" font-family="{MONO}" font-size="13" fill="{INK}">github.com/subhwastaken</text>
  <text class="nu" x="252" y="396" font-family="{MONO}" font-size="13" fill="{TECH}">&#8599;</text>
</g>
<g transform="translate(520 46) scale({s}) translate(-20 -37)" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">
  {''.join(portrait)}
</g>
"""
    write("hero.svg", svg(W, h, body, ["serif", "serif-i", "sans", "mono"],
                          "Subharup Nandi. AI & Full-Stack Engineer. I build AI automation, RAG pipelines, and full-stack systems in Python, TypeScript & Rust."))


# ---- 2 · world tiles ----------------------------------------------------------
TILE_W, TILE_H = 880 / 3 - 8, 210  # 285.33: two 12px gaps across the row


def count_up(num, word, x, y, attrs, begin, dur=1.1, frames=18):
    """Number counts up from 0 with SMIL <set> frames (works inside <img>), easing out."""
    clean = num.replace(",", "")
    m = re.match(r"([\d.]+)(.*)", clean)
    val, suf = float(m.group(1)), m.group(2)
    dec = len(m.group(1).split(".")[1]) if "." in m.group(1) else 0
    tail = f' <tspan font-style="italic">{escape(word)}</tspan>'
    if os.environ.get("STATIC"):
        return f'<text x="{x}" y="{y}" {attrs}>{escape(num)}{tail}</text>'
    if val == 0:
        return f'<text class="r" style="animation-delay:{begin:.2f}s" x="{x}" y="{y}" {attrs}>{escape(num)}{tail}</text>'
    out = []
    for i in range(frames + 1):
        e = 1 - (1 - i / frames) ** 3
        if i == frames:
            txt = num
        elif dec == 0:
            txt = f"{int(round(val * e)):,}{suf}"
        else:
            txt = f"{val * e:.{dec}f}{suf}"
        on = begin + dur * i / frames
        off = "" if i == frames else f'<set attributeName="opacity" to="0" begin="{begin + dur * (i + 1) / frames:.3f}s"/>'
        out.append(f'<text x="{x}" y="{y}" {attrs} opacity="0">{escape(txt)}{tail}'
                   f'<set attributeName="opacity" to="1" begin="{on:.3f}s"/>{off}</text>')
    return "".join(out)


def tile(name, label, color, on, num, word, blurb, delay, pos):
    lines = wrap(blurb, 34)
    blurb_svg = "".join(
        f'<text class="r" {d(delay + 0.75 + i * 0.1)} x="24" y="{150 + i * 20}" font-family="{SANS}" '
        f'font-size="14" fill="{on}" opacity=".92">{escape(l)}</text>'
        for i, l in enumerate(lines)
    )
    body = f"""
<defs>
  <clipPath id="card"><rect width="{TILE_W}" height="{TILE_H}" rx="14"/></clipPath>
  <clipPath id="slot"><rect x="0" y="62" width="{TILE_W}" height="62"/></clipPath>
  <linearGradient id="gl" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".5" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<g class="ti" {d(delay)}>
  <g clip-path="url(#card)">
    <rect width="{TILE_W}" height="{TILE_H}" fill="{color}"/>
    <circle class="rg" {d(delay + 0.5)} cx="{TILE_W - 40}" cy="{TILE_H - 40}" r="60" fill="none" stroke="{on}" stroke-opacity=".5" stroke-width="2"/>
    <rect class="sh" style="animation-delay:{delay + 1.4:.2f}s" x="0" y="-20" width="90" height="{TILE_H + 40}" fill="url(#gl)" transform="translate(-260 0)"/>
  </g>
  <text class="sl" {d(delay + 0.35)} x="24" y="38" font-family="{MONO}" font-size="12" letter-spacing="1.2" fill="{on}">{label}</text>
  <g class="ai" {d(delay + 0.5)}><text class="n" style="animation-delay:{delay + 1.3:.2f}s" x="250" y="38" font-family="{MONO}" font-size="14" fill="{on}">&#8594;</text></g>
  <g clip-path="url(#slot)"><g class="ro" {d(delay + 0.45)}>
    {count_up(num, word, 22, 112, f'font-family="{SERIF}" font-size="44" fill="{on}"', delay + 0.45)}
  </g></g>
  {blurb_svg}
</g>
"""
    write(f"{name}.svg", svg(TILE_W, TILE_H, body, ["serif", "serif-i", "sans", "mono"],
                             f"{label}: {num} {word}. {blurb}", left=4 * pos, right=8 - 4 * pos))


# ---- 2b · tech stack carousel -------------------------------------------------
TECH_ROW_1 = [
    ("Python", "python.svg"),
    ("Rust", "rust.svg"),
    ("FastAPI", "fastapi.svg"),
    ("LLMs & RAG", "openai.svg"),
    ("TypeScript", "typescript.svg"),
    ("Next.js", "nextjs.svg"),
    ("React", "react.svg"),
    ("Node.js", "nodejs.svg"),
]

TECH_ROW_2 = [
    ("PostgreSQL", "postgresql.svg"),
    ("Docker", "docker.svg"),
    ("SvelteKit", "svelte.svg"),
    ("TailwindCSS", "tailwindcss.svg"),
    ("MongoDB", "mongodb.svg"),
    ("Redis", "redis.svg"),
    ("Express", "express.svg"),
    ("GitHub Actions", "githubactions.svg"),
]


def _render_tech_track(items, y, direction, dur=22):
    gap = 12
    pills = []
    x = 0
    for name, icon_fn in items:
        icon_b64 = base64.b64encode(open(os.path.join(ICONS, icon_fn), "rb").read()).decode()
        pw = int(max(138, len(name) * 9.5 + 64))
        pills.append((x, pw, name, icon_b64))
        x += pw + gap
    track_w = x

    svg_pills = []
    for copy_idx in range(2):
        ox = copy_idx * track_w
        for px, pw, name, icon_b64 in pills:
            svg_pills.append(
                f'<g transform="translate({ox + px} {y})">'
                f'<rect width="{pw}" height="44" rx="11" fill="#ffffff" stroke="{RULE}" stroke-width="1"/>'
                f'<image x="14" y="10" width="24" height="24" href="data:image/svg+xml;base64,{icon_b64}"/>'
                f'<text x="46" y="27" font-family="{SANS}" font-weight="600" font-size="15" fill="{INK}">{escape(name)}</text>'
                f'</g>'
            )

    cls_name = "marquee-l" if direction == "left" else "marquee-r"
    smil = ""
    if not os.environ.get("STATIC"):
        frm = "0 0" if direction == "left" else f"-{track_w} 0"
        to = f"-{track_w} 0" if direction == "left" else "0 0"
        smil = (
            f'<animateTransform attributeName="transform" type="translate" '
            f'from="{frm}" to="{to}" dur="{dur}s" repeatCount="indefinite"/>'
        )
    return track_w, f'<g class="{cls_name}">{smil}{"".join(svg_pills)}</g>'


def tech_carousel():
    h = 230
    w1, track1_svg = _render_tech_track(TECH_ROW_1, 108, "left", dur=22)
    w2, track2_svg = _render_tech_track(TECH_ROW_2, 162, "right", dur=22)

    extra_css = (
        f"@keyframes scrollLeft{{from{{transform:translateX(0)}}to{{transform:translateX(-{w1}px)}}}}"
        f"@keyframes scrollRight{{from{{transform:translateX(-{w2}px)}}to{{transform:translateX(0)}}}}"
        f".marquee-l{{animation:scrollLeft 22s linear infinite}}"
        f".marquee-r{{animation:scrollRight 22s linear infinite}}"
        f"@media (prefers-reduced-motion: reduce){{.marquee-l,.marquee-r{{animation:none!important;transform:none!important}}}}"
    )
    if os.environ.get("STATIC"):
        extra_css += ".marquee-l,.marquee-r{animation:none!important;transform:none!important}"

    body = f"""
<defs>
  <clipPath id="marquee-clip"><rect x="24" y="104" width="832" height="110" rx="8"/></clipPath>
  <linearGradient id="fadeL" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{PAPER}" stop-opacity="1"/>
    <stop offset="1" stop-color="{PAPER}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="fadeR" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{PAPER}" stop-opacity="0"/>
    <stop offset="1" stop-color="{PAPER}" stop-opacity="1"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>
<text class="f" {d(3.0)} x="40" y="44" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">TECH STACK &amp; TOOLKIT</text>
<text class="f" {d(3.05)} x="840" y="44" text-anchor="end" font-family="{MONO}" font-size="11" letter-spacing="0.8" fill="{MUTED}">AI · FULL-STACK · SYSTEMS</text>
<text class="r" {d(3.1)} x="38" y="86" font-family="{SERIF}" font-size="38" fill="{INK}">Tools I <tspan font-style="italic" fill="{TECH}">ship with</tspan></text>
<g class="f" {d(3.2)} clip-path="url(#marquee-clip)">
  <g transform="translate(24 0)">
    {track1_svg}
    {track2_svg}
  </g>
</g>
<rect x="24" y="104" width="48" height="110" fill="url(#fadeL)"/>
<rect x="808" y="104" width="48" height="110" fill="url(#fadeR)"/>
"""
    all_tech = ", ".join(name for name, _ in TECH_ROW_1 + TECH_ROW_2)
    write("techstack.svg", svg(W, h, body, ["serif", "serif-i", "sans-b", "mono"],
                               f"Tech Stack & Toolkit: {all_tech}", extra_css=extra_css))


# ---- 3 · activity (monthly bars) ------------------------------------------------
def activity(data):
    h = 340
    monthly = data["monthly"][-12:]
    best = max(monthly[:-1] or monthly, key=lambda m: m["total"])
    top = max(1, best["total"])
    x0, x1, base, maxh, gap = 40, 600, 292, 140, 10
    bw = (x1 - x0 - gap * (len(monthly) - 1)) / len(monthly)
    bars = []
    for i, m in enumerate(monthly):
        partial = i == len(monthly) - 1
        is_best = m is best
        bh = max(4, round(m["total"] / top * maxh))
        x = x0 + i * (bw + gap)
        fill = TECH if is_best else ("#c9c9c4" if partial else INK)
        label = datetime.date.fromisoformat(m["month"] + "-01").strftime("%b")
        bars.append(
            f'<rect class="g" style="animation-delay:{2.2 + i * 0.07:.2f}s" x="{x:.1f}" y="{base - bh}" '
            f'width="{bw:.1f}" height="{bh}" rx="4" fill="{fill}"><title>{label}: {m["total"]:,}</title></rect>'
            f'<text class="f" style="animation-delay:{2.2 + i * 0.07:.2f}s" x="{x + bw / 2:.1f}" y="{base + 22}" '
            f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{MUTED}">{label}</text>'
        )
        if is_best:
            bars.append(
                f'<text class="p" style="animation-delay:3.2s" x="{x + bw / 2:.1f}" y="{base - bh - 10}" '
                f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{TECH}">{m["total"]:,}</text>'
            )
    cs = data["current_streak"]["length"]
    ls = data["longest_streak"]["length"]
    streak_note = "current streak, and the longest" if cs >= ls else f"current streak, longest {ls}"
    total_days = len(data["days"])
    stats = [
        (f'{cs} <tspan font-style="italic">days</tspan>', streak_note),
        (f'{data["active_days"]}<tspan fill="#8e8e93"> / {total_days}</tspan>', "days with a commit"),
        (f'{data["best_day"]["count"]}', "on the busiest day"),
    ]
    side = []
    for i, (big, small) in enumerate(stats):
        y = 104 + i * 92
        side.append(
            f'<g class="r" {d(2.6 + i * 0.15)}>'
            f'<text x="650" y="{y}" font-family="{SERIF}" font-size="40" fill="{INK}">{big}</text>'
            f'<text x="650" y="{y + 24}" font-family="{SANS}" font-size="13" fill="{MUTED}">{small}</text></g>'
        )
        if i < 2:
            side.append(f'<rect class="f" {d(2.6)} x="650" y="{y + 44}" width="190" height="1" fill="{RULE}"/>')
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>
<text class="f" {d(1.9)} x="40" y="58" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">THE LAST 12 MONTHS ON GITHUB</text>
<text class="r" {d(2.0)} x="38" y="114" font-family="{SERIF}" font-size="52" fill="{INK}">{data["total_contributions"]:,} <tspan font-style="italic">contributions</tspan></text>
{''.join(bars)}
{''.join(side)}
"""
    write("activity.svg", svg(W, h, body, ["serif", "serif-i", "sans", "mono"],
                              f'{data["total_contributions"]:,} contributions in the last year, {cs}-day streak'))


# ---- 4 · Ship It! Endless Runner + profile views -----------------------------
GAME_W, GAME_H = W * 2 / 3 - 4, 240  # 582.667 + right=4 => 586.667 (2/3 of 880)
VIEWS_W, VIEWS_H = W / 3 - 8, 240      # 285.333 + left=8  => 293.333 (1/3 of 880)


def runner_card():
    static = bool(os.environ.get("STATIC"))

    # Seamless ground dashes (period 76px, divides 8.0s into 10 exact 0.8s cycles)
    ground_dashes = "".join(
        f'<rect x="{30 + i * 38}" y="196" width="{14 if i % 2 == 0 else 8}" height="2" rx="1" fill="{MUTED}" opacity="0.45"/>'
        for i in range(18)
    )
    ground_anim = ""
    if not static:
        ground_anim = '<animateTransform attributeName="transform" type="translate" from="0 0" to="-76 0" dur="0.8s" repeatCount="indefinite"/>'

    # Seamless parallax sky tags (duplicated over 540px, 8.0s exact loop)
    sky_tags = "".join(
        f'<g transform="translate({ox} 0)">'
        f'<text x="60" y="80">&lt;/&gt;</text>'
        f'<text x="250" y="74">v2.4</text>'
        f'<text x="410" y="88">git push</text>'
        f'</g>'
        for ox in (0, 540)
    )
    sky_anim = ""
    if not static:
        sky_anim = '<animateTransform attributeName="transform" type="translate" from="0 0" to="-540 0" dur="8.0s" repeatCount="indefinite"/>'

    # Runner character (at x=96, y=150, 36x36)
    runner_transform = ' transform="translate(0 -52)"' if static else ""
    runner_anim = ""
    if not static:
        runner_anim = (
            '<animateTransform attributeName="transform" type="translate" '
            'values="0 0;0 0;0 -54;0 -64;0 -54;0 0;0 0;0 -62;0 -72;0 -62;0 0;0 0" '
            'keyTimes="0;0.09;0.14;0.171;0.21;0.26;0.70;0.75;0.790;0.83;0.88;1" '
            'dur="8.0s" repeatCount="indefinite"/>'
        )

    # Seamless dual-copy world track (840px period, 8.0s loop, even spacing)
    if static:
        copies = (0,)
        goomba_x, blocks_x, pipe_x = 126, 266, 432
        obs_anim = ""
        coin_anim = ""
    else:
        copies = (0, 840)
        goomba_x, blocks_x, pipe_x = 240, 490, 760
        obs_anim = '<animateTransform attributeName="transform" type="translate" from="0 0" to="-840 0" dur="8.0s" repeatCount="indefinite"/>'
        coin_anim = '<animateTransform attributeName="transform" type="translate" values="0 0;0 -9;0 0" keyTimes="0;0.5;1" dur="2.0s" repeatCount="indefinite"/>'

    track_copies = "".join(
        f"""
    <g transform="translate({ox} 0)">
      <g transform="translate({goomba_x} 154)">
        <rect width="38" height="28" rx="8" fill="{STUDIO}" stroke="{INK}" stroke-width="1.5"/>
        <rect x="6" y="27" width="8" height="5" rx="2" fill="{INK}"/>
        <rect x="24" y="27" width="8" height="5" rx="2" fill="{INK}"/>
        <text x="19" y="18" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="#ffffff">BUG</text>
      </g>
      <g transform="translate({blocks_x} 96)">
        <g transform="translate(28 -34)">
          {coin_anim}
          <circle cx="14" cy="14" r="12" fill="{LEARN}" stroke="{INK}" stroke-width="1.5"/>
          <text x="14" y="18" text-anchor="middle" font-family="{MONO}" font-size="8.5" fill="{INK}">+100</text>
        </g>
        <rect x="0" y="0" width="26" height="24" rx="4" fill="#b45309" stroke="{INK}" stroke-width="1.5"/>
        <line x1="2" y1="12" x2="24" y2="12" stroke="{INK}" stroke-width="1"/>
        <rect x="28" y="0" width="26" height="24" rx="4" fill="{LEARN}" stroke="{INK}" stroke-width="1.5"/>
        <text x="41" y="17" text-anchor="middle" font-family="{MONO}" font-size="14" fill="{INK}">?</text>
        <rect x="56" y="0" width="26" height="24" rx="4" fill="#b45309" stroke="{INK}" stroke-width="1.5"/>
        <line x1="58" y1="12" x2="80" y2="12" stroke="{INK}" stroke-width="1"/>
      </g>
      <g transform="translate({pipe_x} 144)">
        <rect x="4" y="12" width="36" height="30" fill="#16a34a" stroke="{INK}" stroke-width="1.5"/>
        <rect x="0" y="0" width="44" height="12" rx="3" fill="#15803d" stroke="{INK}" stroke-width="1.5"/>
      </g>
    </g>"""
        for ox in copies
    )
    obstacles_svg = f"<g>{obs_anim}{track_copies}</g>"
    eyebrow = "ARCADE · SHIP IT!"
    aria = "Playable Ship It! arcade game"

    body = f"""
<defs>
  <clipPath id="runner-clip"><rect x="24" y="52" width="534.667" height="166" rx="10"/></clipPath>
</defs>
<rect width="{GAME_W:.3f}" height="{GAME_H}" rx="14" fill="{PAPER}"/>
<g class="f" {d(3.3)}>
  <circle cx="32" cy="30" r="4" fill="{STUDIO}">{"" if static else '<animate attributeName="opacity" values="1;0.25;1" dur="1.6s" repeatCount="indefinite"/>'}</circle>
  <text x="44" y="34" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">{eyebrow}</text>
  <text x="540" y="34" text-anchor="end" font-family="{MONO}" font-size="12" fill="{TECH}">PLAY GAME</text>
  <text class="nu" x="546" y="34" font-family="{MONO}" font-size="12" fill="{TECH}">&#8599;</text>
</g>
<g class="r" {d(3.45)} clip-path="url(#runner-clip)">
  <rect x="24" y="52" width="534.667" height="166" rx="10" fill="#e6e6e1" stroke="{RULE}" stroke-width="1"/>
  <g fill="#b5b5ad" font-family="{MONO}" font-size="11">
    {sky_anim}
    {sky_tags}
  </g>
  <line x1="24" y1="186" x2="559" y2="186" stroke="{INK}" stroke-width="2"/>
  <g>{ground_anim}{ground_dashes}</g>
  {obstacles_svg}
  <g{runner_transform}>
    {runner_anim}
    <rect x="96" y="150" width="36" height="30" rx="8" fill="{TECH}"/>
    <rect x="111" y="157" width="16" height="8" rx="3" fill="#ffffff"/>
    <circle cx="122" cy="161" r="2" fill="{INK}"/>
    <rect x="102" y="180" width="7" height="6" rx="2" fill="{INK}"/>
    <rect x="119" y="180" width="7" height="6" rx="2" fill="{INK}"/>
  </g>
</g>
"""
    write("game.svg", svg(GAME_W, GAME_H, body, ["sans", "mono"], aria, left=0, right=4))


def views_card(data):
    views_count = int(data.get("profile_views", 0))
    views_str = f"{views_count / 1000:.1f}K" if views_count >= 1000 else f"{views_count:,}"
    word = "view" if views_count == 1 else "views"

    monthly_totals = [m["total"] for m in data.get("monthly", [])[-12:]]
    if not monthly_totals:
        monthly_totals = [0] * 12
    max_t = max(monthly_totals) or 1
    spark_heights = [max(6, round(t / max_t * 38)) for t in monthly_totals]
    bars = "".join(
        f'<rect class="g" style="animation-delay:{3.9 + i * 0.04:.2f}s" '
        f'x="{24 + i * 19.8:.1f}" y="{158 - h}" width="13" height="{h}" rx="3" '
        f'fill="#ffffff" opacity="{0.22 + (i / len(spark_heights)) * 0.55:.2f}"/>'
        for i, h in enumerate(spark_heights)
    )
    body = f"""
<defs>
  <clipPath id="views-card"><rect width="{VIEWS_W:.3f}" height="{VIEWS_H}" rx="14"/></clipPath>
  <clipPath id="views-slot"><rect x="0" y="54" width="{VIEWS_W:.3f}" height="62"/></clipPath>
  <linearGradient id="views-gl" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".5" stop-color="#fff" stop-opacity=".16"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<g class="ti" {d(3.55)}>
  <g clip-path="url(#views-card)">
    <rect width="{VIEWS_W:.3f}" height="{VIEWS_H}" fill="{TECH}"/>
    <circle class="rg" {d(4.05)} cx="{VIEWS_W - 40:.2f}" cy="{VIEWS_H - 40}" r="60" fill="none" stroke="#ffffff" stroke-opacity=".35" stroke-width="2"/>
    <rect class="sh" style="animation-delay:4.95s" x="0" y="-20" width="90" height="{VIEWS_H + 40}" fill="url(#views-gl)" transform="translate(-260 0)"/>
  </g>
  <text class="sl" {d(3.9)} x="24" y="38" font-family="{MONO}" font-size="12" letter-spacing="1.2" fill="#ffffff">PROFILE VIEWS</text>
  <g class="ai" {d(4.05)}><text class="n" style="animation-delay:4.85s" x="250" y="38" font-family="{MONO}" font-size="14" fill="#ffffff">&#8594;</text></g>
  <g clip-path="url(#views-slot)"><g class="ro" {d(4.0)}>
    {count_up(views_str, word, 22, 102, f'font-family="{SERIF}" font-size="44" fill="#ffffff"', 4.0)}
  </g></g>
  {bars}
  <text class="r" {d(4.3)} x="24" y="186" font-family="{SANS}" font-size="13.5" fill="#ffffff" opacity=".88">Live counter synced daily</text>
  <text class="r" {d(4.4)} x="24" y="206" font-family="{SANS}" font-size="13.5" fill="#ffffff" opacity=".88">for @subhwastaken on GitHub.</text>
</g>
"""
    write("views.svg", svg(VIEWS_W, VIEWS_H, body, ["serif", "serif-i", "sans", "mono"],
                         f"Profile Views: {views_str} {word} on @subhwastaken",
                         left=8, right=0))


# ---- 5 · blue contribution graph -----------------------------------------------
BLUE = [PAPER_DEEP, "#c8d3ff", "#94a8ff", "#6280ff", TECH, "#1a3be0"]


def level_for(c):
    return 0 if c == 0 else 1 if c <= 5 else 2 if c <= 15 else 3 if c <= 30 else 4 if c <= 50 else 5


def heatmap(data):
    days = data["days"]
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7  # sunday = 0
    cell, step, gx, gy = 12, 15, 44, 96
    cells, months, seen = [], [], set()
    for i, day in enumerate(days):
        k = i + lead
        col, row = divmod(k, 7)
        date = datetime.date.fromisoformat(day["date"])
        if date.day <= 7 and (date.year, date.month) not in seen and row == 0:
            seen.add((date.year, date.month))
            months.append((col, date.strftime("%b")))
        c = day["count"]
        delay = 1.0 + col * 0.03 + row * 0.02
        cells.append(
            f'<rect class="p" style="animation-delay:{delay:.2f}s" x="{gx + col * step}" y="{gy + row * step}" '
            f'width="{cell}" height="{cell}" rx="3" fill="{BLUE[level_for(c)]}">'
            f'<title>{day["date"]}: {c} contribution{"s" if c != 1 else ""}</title></rect>'
        )
    ncols = (len(days) + lead + 6) // 7
    right = gx + ncols * step - 3
    labels = "".join(
        f'<text x="{gx + col * step}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{MUTED}">{m}</text>'
        for col, m in months if col < ncols - 12
    )
    legend_x = right - len(BLUE) * 14
    legend = "".join(
        f'<rect x="{legend_x + i * 14}" y="{gy + 7 * step + 6}" width="11" height="11" rx="2.5" fill="{c}"/>'
        for i, c in enumerate(BLUE)
    )
    h = gy + 7 * step + 44
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>
<text class="r" {d(0.8)} x="42" y="62" font-family="{SERIF}" font-size="34" fill="{INK}">Every day, <tspan font-style="italic" fill="{TECH}">in blue</tspan></text>
<text class="f" {d(0.8)} x="{right}" y="60" text-anchor="end" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">REFRESHED DAILY</text>
{''.join(cells)}
<g class="f" {d(2.4)}>{labels}
<text x="{legend_x - 8}" y="{gy + 7 * step + 16}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">less</text>
{legend}
<text x="{legend_x + len(BLUE) * 14 + 2}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{MUTED}">more</text></g>
"""
    write("heatmap.svg", svg(W, h, body, ["serif", "serif-i", "mono"],
                             f'Contribution graph: {data["total_contributions"]:,} contributions in the last year'))


if __name__ == "__main__":
    data = json.load(open(DATA))
    hero()
    tech_carousel()
    activity(data)
    runner_card()
    views_card(data)
    heatmap(data)
