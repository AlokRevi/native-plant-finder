"""Generate decorative plant illustrations as static SVG files.

All files are static SVG images used by the application. This generator is not
required to run the site; the results are included in assets/illustrations.
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets" / "illustrations"
DATA = ROOT / "data" / "plants.json"
OUT.mkdir(exist_ok=True, parents=True)

COLOR = {
    "Amelanchier laevis": ("#f6f9eb", "#e9ede1", "#fcfff6", "#b48c39"),
    "Cornus alternifolia": ("#edf5e2", "#d9e8d3", "#fffff3", "#aab76c"),
    "Asclepias tuberosa": ("#e6f0d7", "#c5dfc6", "#e97d34", "#f5b75a"),
    "Aquilegia canadensis": ("#edf3e5", "#dae9cd", "#ca4852", "#f4dc6f"),
    "Pinus strobus": ("#e1ece7", "#c5dfd1", "#577b5d", "#d7e5ca"),
    "Oenothera biennis": ("#f5f0d7", "#e2e4b8", "#eccc4e", "#a76a38"),
    "Impatiens capensis": ("#e7f0de", "#d3e6d5", "#eaa047", "#a75d30"),
    "Lobelia cardinalis": ("#e5eedb", "#c4dfd2", "#d74547", "#f8a371"),
    "Monarda fistulosa": ("#e4ebdf", "#d9dfcd", "#b576b9", "#dc9ac9"),
    "Asclepias incarnata": ("#e7f0e0", "#cde0c6", "#d68aa2", "#f2beca"),
    "Iris versicolor": ("#e3e9e9", "#cfdbdd", "#7e83cc", "#eee6a8"),
    "Fragaria virginiana": ("#ecf1e1", "#d8e4bf", "#f6f5df", "#d3be63"),
}


def blossom(x, y, r, petals, colour, heart):
    elements = []
    for n in range(petals):
        angle = (360 / petals) * n
        elements.append(f'<ellipse cx="{x}" cy="{y-r*0.6:.1f}" rx="{r*0.42:.1f}" ry="{r*0.68:.1f}" fill="{colour}" transform="rotate({angle} {x} {y})" />')
    elements.append(f'<circle cx="{x}" cy="{y}" r="{r*.23:.1f}" fill="{heart}" />')
    return "".join(elements)


def leaf(x, y, angle=0, length=42, width=12):
    return (f'<ellipse cx="{x}" cy="{y}" rx="{width}" ry="{length/2}" '
            f'fill="#678e67" stroke="#537453" stroke-width="1" transform="rotate({angle} {x} {y})"/>')


def draw(plant):
    name = plant["scientific_name"]
    bg1, bg2, flower, centre = COLOR[name]
    common = html.escape(plant["common_name"])
    scientific = html.escape(name)
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="360" height="450" viewBox="0 0 360 450" role="img" aria-label="Decorative illustration of {common}">
<defs><linearGradient id="ground" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{bg1}"/><stop offset="1" stop-color="{bg2}"/></linearGradient></defs>
<rect width="360" height="450" fill="url(#ground)"/><ellipse cx="180" cy="395" rx="127" ry="15" fill="#4f7560" opacity=".11"/>
<circle cx="280" cy="66" r="80" fill="#ffffff" opacity=".25"/>
''']
    if plant["form"] == "tree" and name != "Pinus strobus":
        parts.extend(['<path d="M180 360 Q179 249 177 135 M178 233 Q124 173 89 160 M179 230 Q239 190 275 151 M177 175 Q143 142 125 98 M175 176 Q222 129 246 112" fill="none" stroke="#795f48" stroke-width="12" stroke-linecap="round"/>'])
        points = [(89,160),(125,98),(246,112),(275,151),(180,112),(140,191),(219,191),(108,133)]
        for i,(x,y) in enumerate(points):
            parts.append(leaf(x,y,i*31,57,18))
            parts.append(blossom(x+9,y-10,11,5,flower,centre))
    elif name == "Pinus strobus":
        parts.extend(['<path d="M180 382 L180 76" stroke="#695f47" stroke-width="12" stroke-linecap="round"/>'])
        for ring in range(7):
            y = 110 + ring*37
            extent = 35 + ring*15
            parts.append(f'<path d="M180 {y} L{180-extent} {y+45} M180 {y} L{180+extent} {y+45}" stroke="#4e705c" stroke-width="6" stroke-linecap="round"/>')
            for k in range(9):
                x1 = 180-extent + k*extent/4
                parts.append(f'<path d="M{x1:.1f} {y+45-(k%4)*11:.1f} l-8 -11 M{x1:.1f} {y+45-(k%4)*11:.1f} l10 -16" stroke="#83a48a" stroke-width="2"/>')
    elif name == "Cornus alternifolia":
        parts.append('<path d="M175 372 Q178 260 164 116 M177 240 L101 170 M174 220 L256 154" stroke="#7d644a" stroke-width="8" fill="none" stroke-linecap="round"/>')
        for x,y,angle in [(112,169,-35),(230,149,55),(147,129,-10),(188,205,30),(121,237,-30)]:
            parts.append(leaf(x,y,angle,75,28))
        for x,y in [(115,150),(240,127),(165,105)]:
            for i in range(9):
                theta = i*2.3999
                parts.append(blossom(round(x+math.cos(theta)*i*2),round(y+math.sin(theta)*i*2),5,5,flower,centre))
    else:
        # Wildflowers / herbs: distinct whorls and plant-specific colour palettes.
        parts.append('<path d="M180 375 Q175 295 185 189 M180 295 Q134 250 108 222 M185 261 Q225 229 259 205" fill="none" stroke="#547f54" stroke-width="7" stroke-linecap="round"/>')
        for x,y,a in [(138,309,-55),(215,283,45),(122,228,-43),(234,225,42),(162,342,-21),(206,337,25)]:
            parts.append(leaf(x,y,a,65,15 if name != "Iris versicolor" else 8))
        if name == "Iris versicolor":
            for x,y in [(180,132),(125,166),(232,162)]:
                parts.append(blossom(x,y,28,3,flower,centre))
            for x,y,a in [(122,260,-10),(185,255,7),(246,263,12)]:
                parts.append(leaf(x,y,a,150,10))
        elif name == "Aquilegia canadensis":
            for x,y in [(170,150),(113,184),(241,166)]:
                parts.append(f'<path d="M{x-16} {y-12} Q{x} {y+28} {x+18} {y-12}" stroke="{flower}" stroke-width="16" fill="none" stroke-linecap="round"/>')
                parts.append(f'<path d="M{x-6} {y+2} l6 29 l8 -29" stroke="{centre}" stroke-width="6" fill="none"/>')
        elif name in ("Asclepias tuberosa", "Asclepias incarnata", "Monarda fistulosa"):
            for x,y in [(175,136),(105,192),(247,182)]:
                for k in range(14):
                    theta = k * (2*math.pi/14)
                    px = x + math.cos(theta)*22
                    py = y + math.sin(theta)*15
                    parts.append(blossom(round(px),round(py),6,5,flower,centre))
        elif name == "Lobelia cardinalis":
            for j in range(12):
                x = 180+(-1)**j*(13+(j%3)*8)
                y = 102+j*14
                parts.append(blossom(x,y,15,5,flower,centre))
        elif name == "Fragaria virginiana":
            for x,y in [(170,155),(108,203),(233,191)]:
                parts.append(blossom(x,y,21,5,flower,centre))
            for x,y in [(144,265),(211,296)]:
                parts.append(f'<path d="M{x} {y-10} q-17 12 0 29 q18 -17 0 -29" fill="#bb4244"/>')
        else:
            for x,y,r in [(180,141,29),(112,183,23),(245,191,23),(212,105,20)]:
                parts.append(blossom(x,y,r,5,flower,centre))
    parts.extend([f'''<rect x="15" y="397" width="330" height="41" rx="10" fill="#ffffff" opacity=".88"/>
<text x="180" y="414" fill="#25513c" font-family="Georgia,serif" font-size="13" font-weight="bold" text-anchor="middle">{common}</text>
<text x="180" y="429" fill="#67806d" font-family="Arial,sans-serif" font-size="10" font-style="italic" text-anchor="middle">{scientific} · illustration</text>
</svg>'''])
    (OUT / plant["image"]).write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    for item in json.loads(DATA.read_text(encoding="utf-8")):
        draw(item)
    print(f"Generated {len(list(OUT.glob('*.svg')))} illustrations")
