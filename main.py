#!/usr/bin/env python3
"""Cutest Cat - a deterministic, stdlib-only PNG cat renderer.

Writes one picture of a cute cat to /output/entry.png
(or $MAKEFUN_OUTPUT_DIR/entry.png when that env var is set).

No network, no clock, no randomness, no external files.
Pure Python raster rendering + zlib/struct PNG encoding.
"""
import os
import struct
import zlib

W = 800
H = 800

# Framebuffer: list of [r, g, b] floats 0..255
FB = [[0.0, 0.0, 0.0] for _ in range(W * H)]


def clamp(v, lo=0.0, hi=255.0):
    return lo if v < lo else hi if v > hi else v


def blend(x, y, color, alpha):
    if 0 <= x < W and 0 <= y < H and alpha > 0.0:
        if alpha > 1.0:
            alpha = 1.0
        i = y * W + x
        p = FB[i]
        inv = 1.0 - alpha
        p[0] = p[0] * inv + color[0] * alpha
        p[1] = p[1] * inv + color[1] * alpha
        p[2] = p[2] * inv + color[2] * alpha


def background():
    # Soft vertical gradient: warm cream at top to soft pink at bottom,
    # with a gentle radial glow in the centre.
    top = (255.0, 243.0, 224.0)
    bot = (255.0, 205.0, 220.0)
    cx, cy = W * 0.5, H * 0.46
    for y in range(H):
        t = y / (H - 1)
        r = top[0] + (bot[0] - top[0]) * t
        g = top[1] + (bot[1] - top[1]) * t
        b = top[2] + (bot[2] - top[2]) * t
        for x in range(W):
            dx = (x - cx) / W
            dy = (y - cy) / H
            glow = max(0.0, 1.0 - (dx * dx + dy * dy) * 4.0) * 18.0
            i = y * W + x
            FB[i][0] = clamp(r + glow)
            FB[i][1] = clamp(g + glow)
            FB[i][2] = clamp(b + glow * 0.6)
    # Deterministic polka dots
    dots = [(90, 110), (700, 100), (120, 660), (690, 650), (55, 380),
            (745, 370), (210, 55), (590, 710), (360, 725), (640, 520)]
    for (dx_, dy_) in dots:
        ellipse(dx_, dy_, 16, 16, (255, 255, 255), alpha=0.35)
        ellipse(dx_, dy_, 9, 9, (255, 255, 255), alpha=0.35)


def ellipse(cx, cy, rx, ry, color, alpha=1.0):
    x0 = max(0, int(cx - rx - 2)); x1 = min(W - 1, int(cx + rx + 2))
    y0 = max(0, int(cy - ry - 2)); y1 = min(H - 1, int(cy + ry + 2))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d < 1.15:
                # smooth edge over roughly 1.5 px
                edge = (1.0 - d) * min(rx, ry) * 0.9
                a = max(0.0, min(1.0, edge)) * alpha
                if a > 0:
                    blend(x, y, color, a)


def polygon(points, color, alpha=1.0):
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    x0 = max(0, int(min(xs) - 2)); x1 = min(W - 1, int(max(xs) + 2))
    y0 = max(0, int(min(ys) - 2)); y1 = min(H - 1, int(max(ys) + 2))
    n = len(points)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            # distance to nearest edge
            dmin = 1e9
            inside = False
            j = n - 1
            for i in range(n):
                xi, yi = points[i]; xj, yj = points[j]
                # point-segment distance
                vx, vy = xj - xi, yj - yi
                wx, wy = x - xi, y - yi
                seg2 = vx * vx + vy * vy
                t = 0.0 if seg2 == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / seg2))
                px, py = xi + t * vx, yi + t * vy
                dd = (x - px) ** 2 + (y - py) ** 2
                if dd < dmin:
                    dmin = dd
                if ((yi > y) != (yj > y)):
                    xin = (xj - xi) * (y - yi) / (yj - yi) + xi
                    if x < xin:
                        inside = not inside
                j = i
            d = dmin ** 0.5
            if inside:
                a = max(0.0, min(1.0, d + 0.5)) * alpha
                blend(x, y, color, a)
            elif d < 1.5:
                blend(x, y, color, (1.5 - d) / 1.5 * alpha)


def line(x1, y1, x2, y2, width, color, alpha=1.0):
    x0 = max(0, int(min(x1, x2) - width - 2)); x1b = min(W - 1, int(max(x1, x2) + width + 2))
    y0 = max(0, int(min(y1, y2) - width - 2)); y1b = min(H - 1, int(max(y1, y2) + width + 2))
    vx, vy = x2 - x1, y2 - y1
    seg2 = vx * vx + vy * vy
    half = width / 2.0
    for y in range(y0, y1b + 1):
        for x in range(x0, x1b + 1):
            t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((x - x1) * vx + (y - y1) * vy) / seg2))
            px, py = x1 + t * vx, y1 + t * vy
            d = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
            if d < half + 1.0:
                a = max(0.0, min(1.0, half + 0.5 - d)) * alpha
                if a > 0:
                    blend(x, y, color, a)


def draw_cat():
    ginger = (247, 168, 92)
    ginger_dark = (224, 128, 58)
    cream = (255, 236, 205)
    pink = (255, 150, 175)
    pink_soft = (255, 183, 197)

    # Tail (behind body, curling to the right)
    for i in range(28):
        t = i / 27.0
        x = 560 + 130 * t
        y = 690 - 90 * (t ** 1.6)
        ellipse(x, y, 30, 30, ginger)
    ellipse(688, 602, 30, 30, cream)

    # Body
    ellipse(400, 655, 185, 125, ginger)
    ellipse(400, 680, 120, 88, cream)

    # Paws
    ellipse(295, 760, 62, 30, ginger)
    ellipse(505, 760, 62, 30, ginger)
    ellipse(295, 758, 40, 20, cream)
    ellipse(505, 758, 40, 20, cream)
    for px in (278, 295, 312):
        line(px, 748, px, 762, 3, ginger_dark, alpha=0.7)
    for px in (488, 505, 522):
        line(px, 748, px, 762, 3, ginger_dark, alpha=0.7)

    # Ears
    polygon([(238, 305), (268, 118), (392, 228)], ginger)
    polygon([(562, 305), (532, 118), (408, 228)], ginger)
    polygon([(262, 275), (280, 165), (352, 228)], pink_soft)
    polygon([(538, 275), (520, 165), (448, 228)], pink_soft)

    # Head - big and round for maximum cute
    ellipse(400, 400, 235, 205, ginger)
    # Forehead stripes
    for sx, ln in ((360, 44), (400, 54), (440, 44)):
        line(sx, 208, sx, 208 + ln, 13, ginger_dark, alpha=0.55)
    # Cheek stripes
    for sy in (400, 435):
        line(180, sy, 228, sy + 8, 10, ginger_dark, alpha=0.45)
        line(620, sy, 572, sy + 8, 10, ginger_dark, alpha=0.45)
    # Muzzle / chin cream patch
    ellipse(400, 478, 138, 92, cream)

    # Blush
    ellipse(242, 462, 48, 27, pink, alpha=0.75)
    ellipse(558, 462, 48, 27, pink, alpha=0.75)
    for bx, by in ((222, 452), (242, 442), (262, 452), (538, 452), (558, 442), (578, 452)):
        line(bx - 7, by, bx + 7, by - 6, 3, (244, 110, 145), alpha=0.6)

    # Eyes - huge, glossy, with double highlights
    for ex in (305, 495):
        ellipse(ex, 395, 46, 58, (43, 30, 26))
        ellipse(ex, 410, 38, 42, (84, 48, 32))
        ellipse(ex, 428, 26, 24, (43, 30, 26))
        ellipse(ex - 14, 372, 15, 15, (255, 255, 255))
        ellipse(ex + 13, 408, 8, 8, (255, 255, 255), alpha=0.95)
    # Happy closed-eye sparkle brows are skipped; eyes stay open and shiny.

    # Nose - small pink heart-ish triangle
    polygon([(382, 462), (418, 462), (400, 484)], (244, 110, 145))
    ellipse(400, 462, 18, 8, (244, 110, 145))

    # Mouth: two small arcs (w shape) drawn as short thick strokes
    line(400, 484, 382, 500, 6, (120, 66, 44))
    line(382, 500, 366, 490, 6, (120, 66, 44))
    line(400, 484, 418, 500, 6, (120, 66, 44))
    line(418, 500, 434, 490, 6, (120, 66, 44))
    # Tiny tongue peeking out
    ellipse(400, 512, 16, 12, pink_soft)
    line(400, 504, 400, 516, 3, (244, 110, 145), alpha=0.7)

    # Whiskers
    wc = (120, 90, 70)
    for (x1, y1, x2, y2) in [
        (250, 470, 108, 442), (252, 492, 112, 492), (256, 514, 122, 540),
        (550, 470, 692, 442), (548, 492, 688, 492), (544, 514, 678, 540),
    ]:
        line(x1, y1, x2, y2, 5, wc, alpha=0.8)

    # Bow on the right ear - red-pink, with knot
    polygon([(545, 205), (610, 160), (622, 232)], (239, 83, 108))
    polygon([(545, 205), (478, 162), (468, 234)], (239, 83, 108))
    ellipse(545, 200, 24, 24, (214, 52, 88))
    ellipse(537, 192, 8, 8, (255, 170, 190), alpha=0.9)

    # Little heart floating by the head
    heart(648, 268, 26, (244, 110, 145))
    heart(128, 250, 18, (255, 150, 175))


def heart(cx, cy, s, color):
    ellipse(cx - s * 0.5, cy - s * 0.25, s * 0.55, s * 0.55, color)
    ellipse(cx + s * 0.5, cy - s * 0.25, s * 0.55, s * 0.55, color)
    polygon([(cx - s * 1.02, cy), (cx + s * 1.02, cy), (cx, cy + s * 1.25)], color)


def encode_png():
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        base = y * W
        for x in range(W):
            p = FB[base + x]
            raw.append(int(clamp(p[0] + 0.5)))
            raw.append(int(clamp(p[1] + 0.5)))
            raw.append(int(clamp(p[2] + 0.5)))

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)  # 8-bit RGB
    idat = zlib.compress(bytes(raw), level=9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def main():
    background()
    draw_cat()
    data = encode_png()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
