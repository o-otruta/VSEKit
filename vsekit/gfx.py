"""Pillow graphics for overlays. All functions return RGBA PIL images."""
import math
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def hex_rgba(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def shadow(img, radius=14, offset=(0, 10), opacity=0.6, pad=None):
    """Return a new image (padded) with a soft drop shadow under `img`."""
    pad = pad if pad is not None else radius * 2 + max(abs(offset[0]), abs(offset[1]))
    W, H = img.width + pad * 2, img.height + pad * 2
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    a = img.split()[3].point(lambda v: int(v * opacity))
    sh = Image.new('RGBA', img.size, (0, 0, 0, 255)); sh.putalpha(a)
    out.alpha_composite(sh, (pad + offset[0], pad + offset[1]))
    out = out.filter(ImageFilter.GaussianBlur(radius))
    out.alpha_composite(img, (pad, pad))
    return out


def glow(img, radius=18, color=None, strength=1.6):
    """Outer glow of the image's alpha (in `color` or the image's own colors)."""
    pad = radius * 3
    W, H = img.width + pad * 2, img.height + pad * 2
    base = Image.new('RGBA', (W, H), (0, 0, 0, 0)); base.alpha_composite(img, (pad, pad))
    if color:
        g = Image.new('RGBA', (W, H), color); g.putalpha(base.split()[3])
    else:
        g = base.copy()
    g = g.filter(ImageFilter.GaussianBlur(radius))
    a = g.split()[3].point(lambda v: min(255, int(v * strength))); g.putalpha(a)
    g.alpha_composite(base)
    return g


def rounded_mask(size, r):
    m = Image.new('L', size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], r, fill=255)
    return m


def cover(img, w, h, fx=0.5, fy=0.5):
    """Scale-to-cover + crop (like CSS object-fit: cover)."""
    s = max(w / img.width, h / img.height)
    nw, nh = math.ceil(img.width * s), math.ceil(img.height * s)
    im = img.resize((nw, nh), Image.LANCZOS)
    x, y = int((nw - w) * fx), int((nh - h) * fy)
    return im.crop((x, y, x + w, y + h))


def card(img, w, h, radius=28, border=6, border_color=(255, 255, 255, 255), shadow_r=18):
    im = cover(img.convert('RGBA'), w - 2 * border, h - 2 * border)
    c = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(c).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=border_color)
    inner = Image.new('RGBA', im.size, (0, 0, 0, 0))
    inner.paste(im, (0, 0), rounded_mask(im.size, max(1, radius - border)))
    c.alpha_composite(inner, (border, border))
    return shadow(c, shadow_r, (0, 14), 0.65)


def phone(img, w, radius=54, bezel=16):
    """Simple phone mockup around a portrait screenshot."""
    sw = w - 2 * bezel
    sh = int(sw * img.height / img.width)
    h = sh + 2 * bezel
    c = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=(18, 18, 24, 255), outline=(70, 70, 86, 255), width=3)
    scr = img.convert('RGBA').resize((sw, sh), Image.LANCZOS)
    c.paste(scr, (bezel, bezel), rounded_mask((sw, sh), radius - bezel))
    d.rounded_rectangle([w // 2 - 46, bezel + 10, w // 2 + 46, bezel + 34], 12, fill=(10, 10, 14, 255))
    return shadow(c, 22, (0, 18), 0.7)


def text_size(fnt, s, stroke=0):
    b = fnt.getbbox(s, stroke_width=stroke)
    return b[2] - b[0], b[3] - b[1], b


def pill(text, fnt, fg, bg, pad=(34, 18), radius=None, stroke=0, stroke_fill=None, shadow_r=10):
    tw, th, b = text_size(fnt, text, stroke)
    w, h = tw + pad[0] * 2, th + pad[1] * 2
    radius = h // 2 if radius is None else radius
    c = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=bg)
    d.text((pad[0] - b[0], pad[1] - b[1]), text, font=fnt, fill=fg, stroke_width=stroke, stroke_fill=stroke_fill)
    return shadow(c, shadow_r, (0, 8), 0.55) if shadow_r else c


def gradient(w, h, top, bottom):
    g = Image.new('RGBA', (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        g.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(4)))
    return g.resize((w, h))


def radial(w, h, center, radius, color):
    m = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(m)
    cx, cy = center
    for i in range(40, 0, -1):
        r = radius * i / 40
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(255 * (1 - i / 40) ** 1.5))
    m = m.filter(ImageFilter.GaussianBlur(radius / 10))
    c = Image.new('RGBA', (w, h), color); c.putalpha(m)
    return c


def voxel_scatter(w, h, n, colors, size=(8, 34), seed=3, alpha=(30, 110)):
    rnd = random.Random(seed)
    c = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    for _ in range(n):
        s = rnd.randint(*size); x = rnd.randint(-s, w); y = rnd.randint(-s, h)
        col = rnd.choice(colors)
        d.rectangle([x, y, x + s, y + s], fill=col[:3] + (rnd.randint(*alpha),))
    return c.filter(ImageFilter.GaussianBlur(0.6))


# ------------------------------------------------------------------ captions
def chunk_words(words, max_words=3, max_chars=18):
    """words: [{'text','start','end'}] -> list of chunks (lists of word dicts)."""
    chunks, cur = [], []
    for wd in words:
        cur.append(wd)
        txt = ' '.join(x['text'] for x in cur)
        if len(cur) >= max_words or len(txt) >= max_chars or wd['text'][-1:] in '.,!?':
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    return chunks


def caption_image(words, active, fnt, width=1000, color=(255, 255, 255, 255), hi=(255, 214, 10, 255),
                  stroke=9, upper=True, line_gap=8, active_scale=1.12, font_path=None):
    """Render one caption state: all `words`, with index `active` highlighted (bigger, yellow).
    Returns an RGBA image of fixed width, centred text, wrapping if needed."""
    toks = [w.upper() if upper else w for w in words]
    big = font(font_path, int(fnt.size * active_scale)) if font_path else fnt
    space = fnt.getlength(' ')
    sizes = []
    for i, t in enumerate(toks):
        f = big if i == active else fnt
        sizes.append((f.getlength(t) + stroke * 2, f))
    # wrap
    lines, cur, cw = [], [], 0
    for i, (w, f) in enumerate(sizes):
        add = w + (space if cur else 0)
        if cur and cw + add > width - 40:
            lines.append(cur); cur, cw = [], 0; add = w
        cur.append(i); cw += add
    lines.append(cur)
    asc, desc = big.getmetrics()
    lh = asc + desc + line_gap
    H = lh * len(lines) + stroke * 2 + 20
    img = Image.new('RGBA', (width, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 10 + stroke
    for ln in lines:
        lw = sum(sizes[i][0] for i in ln) + space * (len(ln) - 1)
        x = (width - lw) / 2
        for i in ln:
            w, f = sizes[i]
            fa, _ = f.getmetrics()
            yy = y + (asc - fa)
            d.text((x + stroke, yy), toks[i], font=f, fill=hi if i == active else color,
                   stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
            x += w + space
        y += lh
    return shadow(img, 8, (0, 6), 0.55, pad=24)


# ------------------------------------------------------------------ counters / lower thirds
def lower_third(number_text, label, f_num, f_lab, accent=(255, 214, 10, 255), w=760, h=190):
    c = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 30, fill=(12, 12, 22, 215))
    d.rounded_rectangle([0, 0, 18, h - 1], 9, fill=accent)
    nb = f_num.getbbox(number_text)
    d.text((48 - nb[0], (h - (nb[3] - nb[1])) / 2 - nb[1]), number_text, font=f_num, fill=accent)
    lb = f_lab.getbbox(label)
    x = 48 + max(f_num.getlength('88'), nb[2] - nb[0]) + 28
    d.text((x - lb[0], (h - (lb[3] - lb[1])) / 2 - lb[1]), label, font=f_lab, fill=(255, 255, 255, 255))
    return shadow(c, 14, (0, 10), 0.6)


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


# ------------------------------------------------------------------ misc shapes
def divider(height=1920, width=160, handle_y=None, color=(255, 255, 255, 255)):
    handle_y = height // 2 if handle_y is None else handle_y
    c = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    cx = width // 2
    d.rectangle([cx - 4, 0, cx + 3, height], fill=color)
    r = 50
    d.ellipse([cx - r, handle_y - r, cx + r, handle_y + r], fill=color)
    for sgn in (-1, 1):
        x0 = cx + sgn * 12
        d.polygon([(x0, handle_y - 16), (x0, handle_y + 16), (x0 + sgn * 20, handle_y)], fill=(20, 20, 30, 255))
    return glow(c, 12, (255, 255, 255, 255), 0.9)
