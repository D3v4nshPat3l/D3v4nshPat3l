#!/usr/bin/env python3
"""Render assets/ascii-portrait.svg from the GitHub avatar.

The portrait types itself in one row at a time on every page load: each ASCII
row sits behind its own clipPath whose width animates 0 -> full with
fill="freeze" and a staggered begin, while a single cursor block sweeps along.
Nothing repeats, so a visitor always sees it build from nothing.

Usage:  python scripts/gen_ascii_portrait.py [path/to/image]
"""

import os
import sys
import urllib.request

import numpy as np
from PIL import Image

USER = os.environ.get("STATS_USER", "D3v4nshPat3l")
AVATAR = "https://avatars.githubusercontent.com/u/147400702?v=4&s=800"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "ascii-portrait.svg")

# Perceptually-spaced ramp, darkest -> brightest on a dark terminal.
RAMP = " .,:;i1tfLCG08@"

# Percentile treated as the backdrop ceiling, and the midtone curve.
BACKDROP_PCT = 66.0
GAMMA = 0.85

COLS, ROWS = 150, 92
FONT = 6.8
CELL_W = FONT * 0.6
LINE_H = FONT
ART_W = COLS * CELL_W
PAD_X = 44
ART_Y = 70
STAGGER = 0.058                      # seconds between rows
SWEEP = STAGGER                      # a row reveals over exactly one stagger
TOTAL = ROWS * STAGGER

W = int(ART_W + PAD_X * 2)
H = int(ART_Y + ROWS * LINE_H + 116)

ACID, MUTED, DIM = "#00ff9f", "#7f9aa8", "#37604f"
MONO = "ui-monospace,'SF Mono','Cascadia Code',Menlo,Consolas,monospace"


def load(path=None):
    if path:
        return Image.open(path)
    req = urllib.request.Request(AVATAR, headers={"User-Agent": USER + "-portrait"})
    with urllib.request.urlopen(req, timeout=30) as r:
        tmp = os.path.join(os.path.dirname(os.path.abspath(OUT)), ".avatar.tmp")
        with open(tmp, "wb") as fh:
            fh.write(r.read())
    im = Image.open(tmp)
    im.load()
    os.remove(tmp)
    return im


def to_ascii(im):
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        flat = Image.new("RGBA", im.size, (0, 0, 0, 255))
        im = Image.alpha_composite(flat, im)
    grey = im.convert("L")

    # A studio portrait sits on a flat but non-black backdrop. Plain
    # autocontrast leaves that backdrop one step above zero, so it renders as a
    # field of dots that swamps the subject. Clamp the black point just above
    # the backdrop plateau instead: the backdrop drops to pure space and the
    # whole ramp is spent on the face.
    full = np.asarray(grey, dtype=float)
    black = float(np.percentile(full, BACKDROP_PCT))
    white = float(np.percentile(full, 99.5))
    if white - black < 1.0:
        black, white = float(full.min()), float(full.max()) + 1.0

    small = np.asarray(grey.resize((COLS, ROWS), Image.LANCZOS), dtype=float)
    norm = np.clip((small - black) / (white - black), 0.0, 1.0) ** GAMMA

    last = len(RAMP) - 1
    rows = []
    for row in norm:
        line = "".join(RAMP[min(last, int(v * last + 0.5))] for v in row)
        rows.append(line.rstrip() or " ")
    return rows


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cursor_track():
    """One block that sweeps each row then flicks back, instead of one per row."""
    xs, ys, kt = [], [], []
    x0, x1 = PAD_X, PAD_X + ART_W
    for i in range(ROWS):
        a, b = i / ROWS, (i + 0.94) / ROWS
        xs += ["%.1f" % x0, "%.1f" % x1]
        ys += ["%.1f" % (ART_Y + i * LINE_H)] * 2
        kt += ["%.5f" % a, "%.5f" % b]
    xs.append("%.1f" % x0)
    ys.append("%.1f" % (ART_Y + (ROWS - 1) * LINE_H))
    kt.append("1")
    return ";".join(xs), ";".join(ys), ";".join(kt)


def render(rows):
    clips, texts = [], []
    for i, line in enumerate(rows):
        y = ART_Y + i * LINE_H
        begin = i * STAGGER
        clips.append(
            '<clipPath id="p%d"><rect x="%d" y="%.1f" width="0" height="%.2f">'
            '<animate attributeName="width" from="0" to="%.1f" begin="%.3fs" '
            'dur="%.3fs" fill="freeze"/></rect></clipPath>'
            % (i, PAD_X, y, LINE_H, ART_W, begin, SWEEP)
        )
        # textLength must match THIS row's character count, not the canvas
        # width: rows are right-stripped, so a short row pinned to the full
        # width would be stretched across the whole portrait.
        tl = max(len(line), 1) * CELL_W
        texts.append(
            '<text xml:space="preserve" x="%d" y="%.1f" textLength="%.2f" '
            'lengthAdjust="spacingAndGlyphs" clip-path="url(#p%d)">%s</text>'
            % (PAD_X, y + LINE_H * 0.82, tl, i, esc(line))
        )

    cx, cy, ckt = cursor_track()
    plate_y = ART_Y + ROWS * LINE_H + 16
    end = TOTAL

    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="ASCII-art portrait of {USER} rendering itself line by line in a terminal">
<title>{USER} &#183; ./portrait.sh</title>
<defs>
  <linearGradient id="pf-bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#070d14"/><stop offset="1" stop-color="#03070c"/>
  </linearGradient>
  <linearGradient id="pf-bar" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0d1622"/><stop offset="1" stop-color="#080f18"/>
  </linearGradient>
  <linearGradient id="pf-ink" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#8dffd2"/>
    <stop offset="0.42" stop-color="{ACID}"/>
    <stop offset="0.78" stop-color="#19c9a0"/>
    <stop offset="1" stop-color="#1ba3b8"/>
  </linearGradient>
  <radialGradient id="pf-glow" cx="50%" cy="46%" r="58%">
    <stop offset="0" stop-color="{ACID}" stop-opacity="0.10"/>
    <stop offset="1" stop-color="#000" stop-opacity="0"/>
  </radialGradient>
  <pattern id="pf-crt" width="3" height="3" patternUnits="userSpaceOnUse">
    <rect width="3" height="1" fill="#9dfbdb" opacity="0.030"/>
  </pattern>
  <filter id="pf-soft" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur stdDeviation="3.2" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
{CLIPS}
  <style>
    .m{{font-family:{MONO}}}
    .a{{font-family:{MONO};font-size:{FONT}px;fill:url(#pf-ink);white-space:pre}}
  </style>
</defs>

<rect x="1" y="1" width="{WI}" height="{HI}" rx="11" fill="url(#pf-bg)" stroke="#17293a"/>
<rect x="1" y="1" width="{WI}" height="{HI}" rx="11" fill="url(#pf-glow)"/>
<path d="M1 12 a11 11 0 0 1 11 -11 h{BARW} a11 11 0 0 1 11 11 v22 h-{WI} z" fill="url(#pf-bar)"/>
<path d="M1 34 H{WM}" stroke="#17293a"/>
<circle cx="24" cy="18" r="5" fill="#ff2e5b" opacity="0.85"/>
<circle cx="42" cy="18" r="5" fill="#ffb020" opacity="0.85"/>
<circle cx="60" cy="18" r="5" fill="{ACID}" opacity="0.85"/>
<text class="m" x="{CX}" y="22" font-size="11" fill="#4d7a8f" text-anchor="middle">{USER}@byteshell: ~/portrait</text>

<text class="m" x="{PAD}" y="56" font-size="11.5">
  <tspan fill="{ACID}">$</tspan><tspan fill="#c3d7e4"> ./portrait.sh --render --ascii</tspan>
</text>

<g class="a">
{TEXTS}
</g>

<rect x="{PAD}" y="{ART_Y}" width="4" height="{LH:.2f}" fill="{ACID}" opacity="0.9">
  <animate attributeName="x" values="{CURX}" keyTimes="{CKT}" dur="{TOTAL:.2f}s" fill="freeze"/>
  <animate attributeName="y" values="{CURY}" keyTimes="{CKT}" dur="{TOTAL:.2f}s" calcMode="discrete" fill="freeze"/>
  <set attributeName="opacity" to="0" begin="{END:.2f}s"/>
</rect>

<g opacity="0">
  <set attributeName="opacity" to="1" begin="{END:.2f}s"/>
  <animate attributeName="opacity" from="0" to="1" begin="{END:.2f}s" dur="0.9s" fill="freeze"/>
  <path d="M{PLX} {PY} L{PLX2} {PY} L{PLX3} {PYM} L{PLX2} {PYB} L{PLX} {PYB} L{PLXA} {PYM} Z"
        fill="#06120f" stroke="{ACID}" stroke-opacity="0.55"/>
  <text class="m" x="{CX}" y="{PYT}" font-size="25" font-weight="700" letter-spacing="7"
        fill="#eafff6" text-anchor="middle" filter="url(#pf-soft)">{USER}</text>
  <text class="m" x="{CX}" y="{PYS}" font-size="9.5" letter-spacing="4.2"
        fill="{ACID}" text-anchor="middle">BUILD &#183; BREAK &#183; DOCUMENT &#183; HARDEN</text>
</g>

<g class="m" opacity="0" font-size="11.5">
  <animate attributeName="opacity" from="0" to="1" begin="{END2:.2f}s" dur="0.6s" fill="freeze"/>
  <text x="{PAD}" y="{WHO}">
    <tspan fill="{ACID}">$</tspan><tspan fill="#c3d7e4"> whoami</tspan><tspan fill="#4d7a8f">  &#8594;  </tspan><tspan fill="#ffb020">Devansh Patel</tspan>
  </text>
  <rect x="{CURB}" y="{WHOB}" width="7" height="13" fill="{ACID}">
    <animate attributeName="opacity" values="1;1;0;0" dur="1.1s" repeatCount="indefinite"/>
  </rect>
</g>

<rect x="1" y="1" width="{WI}" height="{HI}" rx="11" fill="url(#pf-crt)"/>
</svg>
""".format(
        W=W, H=H, WI=W - 2, HI=H - 2, WM=W - 1, BARW=W - 24, CX=W // 2, PAD=PAD_X,
        USER=USER, ACID=ACID, MONO=MONO, FONT=FONT, LH=LINE_H, ART_Y=ART_Y,
        CLIPS="\n".join("  " + c for c in clips),
        TEXTS="\n".join("  " + t for t in texts),
        CURX=cx, CURY=cy, CKT=ckt, TOTAL=TOTAL, END=end, END2=end + 0.7,
        PLX=PAD_X + 54, PLXA=PAD_X + 38, PLX2=W - PAD_X - 54, PLX3=W - PAD_X - 38,
        PY=plate_y, PYB=plate_y + 52, PYM=plate_y + 26,
        PYT=plate_y + 26, PYS=plate_y + 44,
        WHO=plate_y + 86, WHOB=plate_y + 75, CURB=PAD_X + 196,
    )


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    rows = to_ascii(load(src))
    path = os.path.abspath(OUT)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render(rows))
    ink = sum(1 for r in rows for c in r if c != " ")
    print("wrote %s" % path)
    print("  %d rows x %d cols, %d inked glyphs, %.1fs build-in, %.0f KB"
          % (ROWS, COLS, ink, TOTAL, os.path.getsize(path) / 1024))


if __name__ == "__main__":
    main()
