"""SVG chart builders for R01 (Delhi air). Pure functions: data in, SVG string out.

Colours are never literal here. Every mark carries a class, and the page that embeds the SVG
supplies the colours through CSS tokens (report page: light + dark themes; carousel: dark).
Classes: grid, ax, axs, ref, reflbl, bar, bar-hi, bar-amb, lbl, lbls, rng, dot, dot-hi.
"""
from html import escape


def _t(x, y, s, cls, anchor="start", extra=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}"{extra}>{escape(str(s))}</text>'


def _bar(x, y, w, h, cls, tip=""):
    # 4px rounded data end anchored to baseline: path with rounded top corners only
    r = min(4, w / 2, h) if h > 0 else 0
    if h <= 0:
        return ""
    d = (f"M{x:.1f},{y+h:.1f} L{x:.1f},{y+r:.1f} Q{x:.1f},{y:.1f} {x+r:.1f},{y:.1f} "
         f"L{x+w-r:.1f},{y:.1f} Q{x+w:.1f},{y:.1f} {x+w:.1f},{y+r:.1f} L{x+w:.1f},{y+h:.1f} Z")
    t = f' data-tip="{escape(tip)}" tabindex="0"' if tip else ""
    return f'<path d="{d}" class="{cls}"{t}/>'


def _svg(w, h, body, label):
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{escape(label)}" '
            f'xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">{body}</svg>')


def season_bars(years, vals, *, w=960, h=520, highlight=(), label_years=(), refs=(), ymax=None,
                fmt=lambda v: f"{v:.0f}", tipfmt=None, label="", scale=1.0, xticks=None):
    """Vertical bars by year. highlight -> accent; others context. refs = [(value, text)]."""
    s = scale
    padl, padr, padt, padb = 64 * s, 16 * s, 28 * s, 52 * s
    ymax = ymax or max(vals) * 1.12
    pw, ph = w - padl - padr, h - padt - padb
    n = len(years)
    gap = 2 * s
    slot = pw / n
    bw = slot * 0.72
    Y = lambda v: padt + ph - (v / ymax) * ph
    g = []
    for v, txt in refs:
        y = Y(v)
        g.append(f'<line x1="{padl:.1f}" x2="{w-padr:.1f}" y1="{y:.1f}" y2="{y:.1f}" class="ref"/>')
        g.append(_t(padl - 10 * s, y + 6 * s, txt, "axs", "end"))
    g.append(f'<line x1="{padl:.1f}" x2="{w-padr:.1f}" y1="{padt+ph:.1f}" y2="{padt+ph:.1f}" class="grid"/>')
    for i, (yr, v) in enumerate(zip(years, vals)):
        x = padl + i * slot + (slot - bw) / 2
        cls = "bar-hi" if yr in highlight else "bar"
        tip = (tipfmt(yr, v) if tipfmt else f"{yr}: {fmt(v)}")
        g.append(_bar(x, Y(v), bw, padt + ph - Y(v), cls, tip))
        if yr in label_years:
            g.append(_t(x + bw / 2, Y(v) - 10 * s, fmt(v), "lbl", "middle"))
        if xticks is None or yr in xticks:
            g.append(_t(x + bw / 2, padt + ph + 30 * s, str(yr), "ax", "middle"))
    return _svg(w, h, "".join(g), label)


def step_line(points, *, w=960, h=460, label="", annotations=(), ymax=None, scale=1.0, gstep=20, gfmt=lambda v: f"{v:g}", xlabels=None):
    """points: list of (fractional_year, value). Step line, 2px, with selective annotations."""
    s = scale
    padl, padr, padt, padb = 64 * s, 24 * s, 28 * s, 52 * s
    x0, x1 = points[0][0], points[-1][0]
    ymax = ymax or max(v for _, v in points) * 1.15
    pw, ph = w - padl - padr, h - padt - padb
    X = lambda t: padl + (t - x0) / (x1 - x0) * pw
    Y = lambda v: padt + ph - v / ymax * ph
    g = []
    gv = 0
    while gv <= ymax + 1e-9:
        y = Y(gv)
        g.append(f'<line x1="{padl:.1f}" x2="{w-padr:.1f}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        g.append(_t(padl - 10 * s, y + 6 * s, gfmt(gv), "axs", "end"))
        gv += gstep
    d = []
    for i, (t, v) in enumerate(points):
        if i == 0:
            d.append(f"M{X(t):.1f},{Y(v):.1f}")
        else:
            d.append(f"H{X(t):.1f} V{Y(v):.1f}")
    d.append(f"H{X(x1):.1f}")
    g.append(f'<path d="{" ".join(d)}" class="line" fill="none"/>')
    for yr in (xlabels if xlabels is not None else [y for y in range(int(x0) + 1, int(x1) + 1) if y % 2 == 0 or y == int(x1)]):
        g.append(_t(X(yr), padt + ph + 30 * s, yr, "ax", "middle"))
    for t, v, txt, anchor, dy in annotations:
        g.append(f'<circle cx="{X(t):.1f}" cy="{Y(v):.1f}" r="{5*s:.1f}" class="dot-hi" data-tip="{escape(txt)}" tabindex="0"/>')
        g.append(_t(X(t) + (10 * s if anchor == "start" else -10 * s), Y(v) + dy * s, txt, "lbl", anchor))
    return _svg(w, h, "".join(g), label)


def change_bars(rows, *, w=960, h=520, label="", scale=1.0, lim=30):
    """Horizontal diverging bars. rows: (city, pct, group, note). group 'added' -> blue, 'same' -> amber."""
    s = scale
    padl, padr, padt, padb = 190 * s, 180 * s, 20 * s, 44 * s
    pw = w - padl - padr
    n = len(rows)
    rowh = (h - padt - padb) / n
    X = lambda p: padl + (p + lim) / (2 * lim) * pw
    g = []
    for tv in (-30, -20, -10, 0, 10, 20, 30):
        if abs(tv) > lim:
            continue
        x = X(tv)
        g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{padt:.1f}" y2="{h-padb:.1f}" class="{"ref0" if tv == 0 else "grid"}"/>')
        g.append(_t(x, h - padb + 30 * s, (f"{tv:+d}%".replace("-", "−")) if tv else "0", "axs", "middle"))
    for i, (city, pct, grp, note) in enumerate(rows):
        yc = padt + i * rowh + rowh / 2
        bh = rowh * 0.52
        x0, x1 = sorted((X(0), X(pct)))
        cls = "bar-hi" if grp == "added" else "bar-amb"
        tip = f"{city}: {pct:+.1f}% · monitors {note}"
        g.append(f'<rect x="{x0:.1f}" y="{yc-bh/2:.1f}" width="{max(x1-x0,1):.1f}" height="{bh:.1f}" rx="{3*s:.1f}" class="{cls}" data-tip="{escape(tip)}" tabindex="0"/>')
        g.append(_t(padl - 16 * s, yc + 7 * s, city, "lbl", "end"))
        txt = f"{pct:+.1f}%".replace("-", "−")
        if pct < 0 and (x1 - x0) > 120 * s:   # long bar: label sits inside its far end
            g.append(_t(X(pct) + 12 * s, yc + 7 * s, txt, "lblin", "start"))
        else:
            vx = X(pct) + (-10 * s if pct < 0 else 10 * s)
            g.append(_t(vx, yc + 7 * s, txt, "lbl", "end" if pct < 0 else "start"))
        g.append(_t(w - padr + 20 * s, yc + 7 * s, f"monitors {note}", "lbls", "start"))
    return _svg(w, h, "".join(g), label)


def range_dots(years, mid, lo, hi, *, w=960, h=500, highlight=(), ymin=60, ymax=130, ref=100,
               reflabel="", label="", scale=1.0):
    s = scale
    padl, padr, padt, padb = 64 * s, 16 * s, 28 * s, 52 * s
    pw, ph = w - padl - padr, h - padt - padb
    n = len(years)
    slot = pw / n
    Y = lambda v: padt + ph - (v - ymin) / (ymax - ymin) * ph
    g = []
    for gv in range(ymin, ymax + 1, 10):
        y = Y(gv)
        g.append(f'<line x1="{padl:.1f}" x2="{w-padr:.1f}" y1="{y:.1f}" y2="{y:.1f}" class="{"ref" if gv == ref else "grid"}"/>')
        g.append(_t(padl - 10 * s, y + 6 * s, gv, "axs", "end"))
    if reflabel:
        g.append(_t(w - padr, Y(ref) - 10 * s, reflabel, "reflbl", "end"))
    for i, yr in enumerate(years):
        x = padl + i * slot + slot / 2
        hi_ = yr in highlight
        g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{Y(lo[i]):.1f}" y2="{Y(hi[i]):.1f}" class="{"rng-hi" if hi_ else "rng"}"/>')
        tip = f"{yr}: {mid[i]:.0f} (range {lo[i]:.0f}–{hi[i]:.0f})"
        g.append(f'<circle cx="{x:.1f}" cy="{Y(mid[i]):.1f}" r="{(8 if hi_ else 6)*s:.1f}" class="{"dot-hi" if hi_ else "dot"}" data-tip="{escape(tip)}" tabindex="0"/>')
        if hi_:
            g.append(_t(x, Y(lo[i]) + 26 * s, f"{mid[i]:.0f}", "lbl", "middle"))
        g.append(_t(x, padt + ph + 30 * s, yr, "ax", "middle"))
    return _svg(w, h, "".join(g), label)


def twin_panels(years, a_vals, b_vals, *, a_title, b_title, a_fmt, b_fmt, w=960, h=560, label="",
                scale=1.0, a_label_years=(), b_label_years=()):
    """Two small-multiple bar panels, side by side, sharing the year axis. Never a dual axis."""
    s = scale
    gutter = 48 * s
    pw = (w - gutter) / 2
    out = []
    for k, (vals, title, fmt, lys, cls) in enumerate(
            [(a_vals, a_title, a_fmt, a_label_years, "bar"), (b_vals, b_title, b_fmt, b_label_years, "bar-hi")]):
        ox = k * (pw + gutter)
        padl, padt, padb = 8 * s, 64 * s, 52 * s
        ph = h - padt - padb
        ymax = max(vals) * 1.18
        n = len(years)
        slot = (pw - padl) / n
        bw = slot * 0.7
        Y = lambda v: padt + ph - v / ymax * ph
        out.append(_t(ox + padl, 26 * s, title, "lbl"))
        out.append(f'<line x1="{ox+padl:.1f}" x2="{ox+pw:.1f}" y1="{padt+ph:.1f}" y2="{padt+ph:.1f}" class="grid"/>')
        for i, (yr, v) in enumerate(zip(years, vals)):
            x = ox + padl + i * slot + (slot - bw) / 2
            out.append(_bar(x, Y(v), bw, padt + ph - Y(v), cls, f"{yr}: {fmt(v)}"))
            if yr in lys:
                out.append(_t(x + bw / 2, Y(v) - 10 * s, fmt(v), "lbls", "middle"))
            out.append(_t(x + bw / 2, padt + ph + 30 * s, f"’{str(yr)[2:]}", "ax", "middle"))
    return _svg(w, h, "".join(out), label)


def hbars(rows, *, w=960, h=520, label="", scale=1.0, xmax=None, xmin=0.0, ref=None, reflabel="",
          fmt=lambda v: f"{v:.2f}", ticks=(), tickfmt=lambda v: f"{v:g}", padl=330, padr=90):
    """Horizontal bars. rows: (name, value, cls, tip). Bars run from xmin (0) toward value; supports negatives.
    ref: optional vertical reference value drawn over the bars with a label."""
    s = scale
    padl, padr, padt, padb = padl * s, padr * s, (44 if (ref is not None and reflabel) else 16) * s, 46 * s
    vals = [r[1] for r in rows]
    xmax = xmax if xmax is not None else max(vals) * 1.1
    xmin = min(xmin, min(vals) * 1.1)
    pw = w - padl - padr
    X = lambda v: padl + (v - xmin) / (xmax - xmin) * pw
    n = len(rows)
    rowh = (h - padt - padb) / n
    g = []
    for tv in ticks:
        x = X(tv)
        g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{padt:.1f}" y2="{h-padb:.1f}" class="{"ref0" if tv == 0 else "grid"}"/>')
        g.append(_t(x, h - padb + 30 * s, tickfmt(tv), "axs", "middle"))
    for i, (name, v, cls, tip) in enumerate(rows):
        yc = padt + i * rowh + rowh / 2
        bh = min(rowh * 0.58, 44 * s)
        x0, x1 = sorted((X(0), X(v)))
        g.append(f'<rect x="{x0:.1f}" y="{yc-bh/2:.1f}" width="{max(x1-x0,1.5):.1f}" height="{bh:.1f}" rx="{3*s:.1f}" class="{cls}" data-tip="{escape(tip)}" tabindex="0"/>')
        g.append(_t(padl - 16 * s, yc + 7 * s, name, "lbl", "end"))
        txt = fmt(v).replace("-", "−")
        if v < 0 and (x1 - x0) > 90 * s:
            g.append(_t(x0 + 10 * s, yc + 7 * s, txt, "lblin", "start"))
        elif v < 0:
            g.append(_t(x0 - 10 * s, yc + 7 * s, txt, "lbl", "end"))
        else:
            g.append(_t(x1 + 10 * s, yc + 7 * s, txt, "lbl", "start"))
    if ref is not None:
        x = X(ref)
        g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{padt-4*s:.1f}" y2="{h-padb:.1f}" class="refstrong"/>')
        if reflabel:
            g.append(_t(x + 8 * s, padt - 14 * s, reflabel, "reflbl2", "start"))
    return _svg(w, h, "".join(g), label)


def grouped_pairs(groups, a, b, *, a_name, b_name, w=960, h=520, label="", scale=1.0, fmt=lambda v: f"{v:+.0f}", tickfmt=None):
    """Paired vertical bars per group (e.g. this season vs next season), zero baseline, legend on top."""
    s = scale
    padl, padr, padt, padb = 64 * s, 16 * s, 70 * s, 64 * s
    lo = min(min(a), min(b), 0) * 1.2
    hi = max(max(a), max(b)) * 1.15
    pw, ph = w - padl - padr, h - padt - padb
    Y = lambda v: padt + (hi - v) / (hi - lo) * ph
    n = len(groups)
    slot = pw / n
    bw = slot * 0.32
    g = []
    for tv in range(int(lo // 10 * 10), int(hi) + 1, 10):
        y = Y(tv)
        g.append(f'<line x1="{padl:.1f}" x2="{w-padr:.1f}" y1="{y:.1f}" y2="{y:.1f}" class="{"ref0" if tv == 0 else "grid"}"/>')
        g.append(_t(padl - 10 * s, y + 6 * s, tickfmt(tv) if tickfmt else (f"{tv:+d}".replace("-", "−") if tv else "0"), "axs", "end"))
    # legend
    g.append(f'<rect x="{padl:.1f}" y="{14*s:.1f}" width="{18*s:.1f}" height="{18*s:.1f}" class="bar"/>')
    g.append(_t(padl + 28 * s, 29 * s, a_name, "lbls"))
    lx = padl + 28 * s + len(a_name) * 9.5 * s + 40 * s
    g.append(f'<rect x="{lx:.1f}" y="{14*s:.1f}" width="{18*s:.1f}" height="{18*s:.1f}" class="bar-hi"/>')
    g.append(_t(lx + 28 * s, 29 * s, b_name, "lbls"))
    for i, grp in enumerate(groups):
        cx = padl + i * slot + slot / 2
        for j, (v, cls) in enumerate(((a[i], "bar"), (b[i], "bar-hi"))):
            x = cx - bw - 1 * s if j == 0 else cx + 1 * s
            y0, y1 = sorted((Y(0), Y(v)))
            g.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{max(y1-y0,1.5):.1f}" rx="{3*s:.1f}" class="{cls}" data-tip="{escape(grp)}: {fmt(v)}" tabindex="0"/>')
            ty = (y0 - 10 * s) if v >= 0 else (y1 + 24 * s)
            g.append(_t(x + bw / 2, ty, fmt(v).replace("-", "−"), "lbls", "middle"))
        g.append(_t(cx, h - padb + 34 * s, grp, "ax", "middle"))
    return _svg(w, h, "".join(g), label)
