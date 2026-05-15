#!/usr/bin/env python3
"""
YT-PDFCleaner Icon Generator (v2 — fixed compositing bug)

Generates a multi-resolution ICO file and dialog-use PNG icons with
YT brand identity (teal #0E7C7B, dark #282828).

Outputs to /opt/workspace/yt-pdf-cleaner/gui/:
  - icon.ico  (16, 24, 32, 48, 64, 128, 256)
  - icon_about.png  (64x64)
  - icon_dialog_check.png  (32x32)
  - icon_dialog_warn.png  (32x32)
"""

import os
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Brand colors ────────────────────────────────────────────────────────────
YT_TEAL = (14, 124, 123)     # #0E7C7B — Pro 版深青
DARK   = (40, 40, 40)        # #282828 — slightly lightened for better visibility
DARK_BG = (34, 34, 34)       # slightly darker inner area
WHITE  = (255, 255, 255)
NEAR_BLACK = (30, 30, 30)

OUT_DIR = "/opt/workspace/yt-pdf-cleaner/gui"

# ── Sizes ────────────────────────────────────────────────────────────────────
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
ABOUT_SIZE = 64
DIALOG_SIZE = 32

# ── Font discovery ──────────────────────────────────────────────────────────
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
]


def find_font(size, bold=True):
    """Find a font file, return None if none found."""
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return None


def rounded_rect(draw, xy, radius, fill):
    """Draw a filled rounded rectangle."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def make_base_icon(size, with_pdf=True):
    """
    Create the YT-PDFCleaner base icon at the given size.
    Returns an RGBA Image.

    IMPORTANT: always get a fresh ImageDraw.Draw after Image.alpha_composite!
    """
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # ── Geometry ───────────────────────────────────────────────────────────
    pad = max(1, size // 20)
    r = max(2, size // 6)
    x1, y1 = pad, pad
    x2, y2 = size - pad - 1, size - pad - 1

    # ── Drop shadow (only for sizes >= 48) ─────────────────────────────────
    if size >= 48:
        shadow_offset = max(1, size // 48)
        shadow_alpha = 50
        shadow_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow_img)
        sd.rounded_rectangle(
            (x1 + shadow_offset, y1 + shadow_offset,
             x2 + shadow_offset, y2 + shadow_offset),
            radius=r, fill=(0, 0, 0, shadow_alpha)
        )
        blur_r = max(1, size // 64)
        shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=blur_r))
        canvas = Image.alpha_composite(canvas, shadow_img)
        # ⚠️ canvas changed — need a new ImageDraw!

    # ── Background rounded rect ────────────────────────────────────────────
    draw = ImageDraw.Draw(canvas)
    rounded_rect(draw, (x1, y1, x2, y2), r, fill=DARK + (255,))

    # Slightly darker inner glow / subtle border
    if size >= 32:
        # Inner subtle highlight (top-left edge)
        highlight_color = (55, 55, 55, 120)
        draw.rounded_rectangle((x1, y1, x2, y2), radius=r, outline=highlight_color, width=1)

    # ── Draw "YT" letters ──────────────────────────────────────────────────
    yt_text = "YT"
    font_size = int(size * 0.48)

    font = find_font(font_size, bold=True)
    if font is None:
        font = ImageFont.load_default()

    try:
        bbox = draw.textbbox((0, 0), yt_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except Exception:
        tw, th = font_size * 0.6 * len(yt_text), font_size

    cx = size // 2
    cy = size // 2

    # YT text position - biased slightly up if PDF badge is below
    y_center_offset = -int(size * 0.04) if (with_pdf and size >= 24) else 0

    tx = cx - tw // 2
    ty = cy - th // 2 + y_center_offset

    # Draw YT text in YT_TEAL
    draw.text((tx, ty), yt_text, fill=YT_TEAL + (255,), font=font)

    # ── Draw "PDF" badge ──────────────────────────────────────────────────
    if with_pdf and size >= 24:
        pdf_text = "PDF"
        pdf_font_size = int(size * 0.15)
        pdf_font = find_font(pdf_font_size, bold=True)
        if pdf_font is None:
            pdf_font = ImageFont.load_default()

        try:
            pdf_bbox = draw.textbbox((0, 0), pdf_text, font=pdf_font)
            ptw = pdf_bbox[2] - pdf_bbox[0]
            pth = pdf_bbox[3] - pdf_bbox[1]
        except Exception:
            ptw, pth = pdf_font_size * 0.6 * len(pdf_text), pdf_font_size

        # Badge below YT
        badge_pad_x = max(2, int(size * 0.03))
        badge_pad_y = max(1, int(size * 0.02))
        badge_r = max(1, int(size * 0.03))

        badge_y = ty + th + int(size * 0.03)
        badge_x1 = cx - ptw // 2 - badge_pad_x
        badge_y1 = badge_y - badge_pad_y
        badge_x2 = cx + ptw // 2 + badge_pad_x
        badge_y2 = badge_y + pth + badge_pad_y

        # Clip to icon bounds
        badge_x1 = max(x1 + 2, badge_x1)
        badge_x2 = min(x2 - 2, badge_x2)
        badge_y2 = min(y2 - 2, badge_y2)

        if badge_x2 > badge_x1 and badge_y2 > badge_y1:
            # Badge background - dark teal-tinted
            badge_bg = (11, 62, 62, 230)
            rounded_rect(draw, (badge_x1, badge_y1, badge_x2, badge_y2), badge_r, fill=badge_bg)

            # Badge border - thin teal
            if size >= 32:
                draw.rounded_rectangle(
                    (badge_x1, badge_y1, badge_x2, badge_y2),
                    radius=badge_r, outline=YT_TEAL + (160,), width=max(1, size // 64)
                )

            # Badge text - white
            pdf_tx = cx - ptw // 2
            pdf_ty = badge_y
            draw.text((pdf_tx, pdf_ty), pdf_text, fill=WHITE + (255,), font=pdf_font)

    return canvas


def make_dialog_icon(size, variant):
    """
    Create a dialog icon with YT branding and status indicator.
    variant: 'check' for success, 'warn' for warning
    """
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Small rounded square background
    pad = max(1, size // 10)
    r = max(2, size // 5)
    x1, y1 = pad, pad
    x2, y2 = size - pad - 1, size - pad - 1

    # Background
    rounded_rect(draw, (x1, y1, x2, y2), r, fill=DARK + (255,))

    # Subtle border
    border_color = (60, 60, 60, 200)
    draw.rounded_rectangle((x1, y1, x2, y2), radius=r, outline=border_color, width=1)

    # ── Draw miniature "YT" text ──────────────────────────────────────────
    yt_font_size = int(size * 0.38)
    font = find_font(yt_font_size, bold=True)
    if font is None:
        font = ImageFont.load_default()

    try:
        bbox = draw.textbbox((0, 0), "YT", font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except Exception:
        tw, th = yt_font_size * 0.6 * 2, yt_font_size

    cx = size // 2
    cy = size // 2
    tx = cx - tw // 2
    ty = cy - th // 2 - int(size * 0.02)

    draw.text((tx, ty), "YT", fill=YT_TEAL + (255,), font=font)

    # ── Status indicator ────────────────────────────────────────────────────
    ind_size = int(size * 0.38)
    ind_x = size - ind_size - int(size * 0.04)
    ind_y = size - ind_size - int(size * 0.04)

    if variant == "check":
        # Green checkmark circle
        draw.ellipse(
            (ind_x, ind_y, ind_x + ind_size, ind_y + ind_size),
            fill=(46, 204, 113, 255),
            outline=WHITE + (200,),
            width=max(1, int(size * 0.04))
        )

        # Checkmark
        cm = ind_size * 0.5
        cx_c = ind_x + ind_size // 2
        cy_c = ind_y + ind_size // 2
        check_points = [
            (cx_c - cm * 0.35, cy_c),
            (cx_c - cm * 0.1, cy_c + cm * 0.3),
            (cx_c + cm * 0.4, cy_c - cm * 0.25),
        ]
        draw.line(check_points, fill=WHITE, width=max(1, int(size * 0.06)))

    elif variant == "warn":
        # Amber warning triangle
        cx_tri = ind_x + ind_size // 2
        by = ind_y + ind_size
        ty_tri = ind_y + int(ind_size * 0.1)
        hw = ind_size * 0.5

        triangle = [
            (cx_tri, ty_tri),
            (cx_tri - hw, by),
            (cx_tri + hw, by),
        ]
        draw.polygon(triangle, fill=(243, 156, 18, 255))

        # Exclamation mark
        ex_w = max(1, int(ind_size * 0.12))
        ex_h = int(ind_size * 0.3)
        ex_x = cx_tri - ex_w // 2
        ex_top = ty_tri + int(ind_size * 0.18)
        ex_bottom = ex_top + ex_h

        draw.rectangle(
            (ex_x, ex_top, ex_x + ex_w, ex_bottom),
            fill=DARK + (255,)
        )
        dot_r = max(1, int(ind_size * 0.06))
        dot_y = ex_bottom + int(ind_size * 0.05)
        draw.ellipse(
            (cx_tri - dot_r, dot_y - dot_r, cx_tri + dot_r, dot_y + dot_r),
            fill=DARK + (255,)
        )

    return canvas


def make_ico(ico_sizes=None):
    """Generate a multi-resolution ICO file as bytes."""
    if ico_sizes is None:
        ico_sizes = ICO_SIZES

    # Generate PNG data for each size
    png_data_list = []
    for s in ico_sizes:
        img = make_base_icon(s, with_pdf=(s >= 24))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_data_list.append(buf.getvalue())

    # Build ICO file manually
    count = len(png_data_list)
    header = bytearray()
    header += (0).to_bytes(2, 'little')  # reserved
    header += (1).to_bytes(2, 'little')  # type: 1=ICO
    header += count.to_bytes(2, 'little')  # count

    # Directory entries + image data
    data_offset = 6 + count * 16
    all_data = bytearray()

    for s, png_bytes in zip(ico_sizes, png_data_list):
        w = s if s < 256 else 0
        h = s if s < 256 else 0
        entry = bytearray()
        entry += w.to_bytes(1, 'little')
        entry += h.to_bytes(1, 'little')
        entry += (0).to_bytes(1, 'little')  # colors
        entry += (0).to_bytes(1, 'little')  # reserved
        entry += (1).to_bytes(2, 'little')  # planes
        entry += (32).to_bytes(2, 'little')  # bpp
        entry += len(png_bytes).to_bytes(4, 'little')  # size
        entry += data_offset.to_bytes(4, 'little')  # offset
        all_data += entry
        data_offset += len(png_bytes)

    # Append image data
    for png_bytes in png_data_list:
        all_data += png_bytes

    return bytes(header + all_data)


def generate_all():
    """Generate all icon files."""
    os.makedirs(OUT_DIR, exist_ok=True)

    # ── 1. Multi-resolution ICO ─────────────────────────────────────────────
    ico_bytes = make_ico()
    ico_path = os.path.join(OUT_DIR, "icon.ico")
    with open(ico_path, "wb") as f:
        f.write(ico_bytes)
    print(f"✓ Generated {ico_path}")
    print(f"   Sizes: {ICO_SIZES}")
    print(f"   ICO size: {len(ico_bytes):,} bytes")

    # ── 2. About dialog PNG (64x64) ──────────────────────────────────────────
    about_img = make_base_icon(ABOUT_SIZE, with_pdf=True)
    about_path = os.path.join(OUT_DIR, "icon_about.png")
    about_img.save(about_path, format="PNG")
    print(f"✓ Generated {about_path} ({ABOUT_SIZE}x{ABOUT_SIZE})")

    # ── 3. Dialog checkmark icon (32x32) ─────────────────────────────────────
    check_img = make_dialog_icon(DIALOG_SIZE, "check")
    check_path = os.path.join(OUT_DIR, "icon_dialog_check.png")
    check_img.save(check_path, format="PNG")
    print(f"✓ Generated {check_path} ({DIALOG_SIZE}x{DIALOG_SIZE})")

    # ── 4. Dialog warning icon (32x32) ───────────────────────────────────────
    warn_img = make_dialog_icon(DIALOG_SIZE, "warn")
    warn_path = os.path.join(OUT_DIR, "icon_dialog_warn.png")
    warn_img.save(warn_path, format="PNG")
    print(f"✓ Generated {warn_path} ({DIALOG_SIZE}x{DIALOG_SIZE})")

    # ── Validation ──────────────────────────────────────────────────────────
    print("\n── Validation ──")

    # Verify ICO structure
    import struct
    with open(ico_path, 'rb') as f:
        ico_data = f.read()
    _, _, count = struct.unpack_from('<HHH', ico_data, 0)
    print(f"icon.ico: {count} entries")

    from io import BytesIO
    for i in range(count):
        entry_off = 6 + i * 16
        w, h, _, _, _, _, sz, off = struct.unpack_from('<BBBBHHII', ico_data, entry_off)
        w_act = w if w != 0 else 256
        h_act = h if h != 0 else 256
        png_bytes = ico_data[off:off+sz]
        png_img = Image.open(BytesIO(png_bytes))
        # Count teal pixels to verify text rendering
        px = png_img.load()
        teal_count = sum(1 for y in range(h_act) for x in range(w_act)
                        if px[x, y][3] > 128 and px[x, y][2] > 100 and px[x, y][0] < 80 and px[x, y][1] > 100)
        has_shadow = any(px[x, y][3] == 60 and px[x, y][:3] == (0, 0, 0)
                         for y in range(h_act) for x in range(w_act))
        print(f"  {w_act:3d}x{h_act:<3d} | teal pixels: {teal_count:4d} | shadow: {has_shadow}")

    for name in ["icon_about.png", "icon_dialog_check.png", "icon_dialog_warn.png"]:
        p = os.path.join(OUT_DIR, name)
        if os.path.exists(p):
            im = Image.open(p)
            # Count non-transparent and colored pixels
            px = im.load()
            w, h = im.size
            total = w * h
            opaque = sum(1 for y in range(h) for x in range(w) if px[x, y][3] > 128)
            teal = sum(1 for y in range(h) for x in range(w)
                      if px[x, y][3] > 128 and px[x, y][2] > 100 and px[x, y][0] < 80 and px[x, y][1] > 100)
            print(f"  {name:25s} {w}x{h} mode={im.mode} | opaque: {opaque}/{total} | teal: {teal}")

    print("\n✅ All icons generated successfully!")


if __name__ == "__main__":
    generate_all()
