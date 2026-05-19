#!/usr/bin/env python3
"""
YT-PDFCleaner Icon Generator (v3 — Apple blue).

Generates Apple-style YT brand icons in the script's own directory.

Outputs to <script_dir>/:
  - icon.png              (256×256 RGBA)
  - icon.ico              (16, 24, 32, 48, 64, 128, 256 multi-res)
  - icon_dialog_check.png (48×48 green check)
  - icon_dialog_warn.png  (48×48 amber warning)

NOTE: icon_about.png is no longer needed — About dialog uses Label text badge.
"""

import os
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Apple Brand Colors ───────────────────────────────────────────────────────
APPLE_BLUE  = (0, 113, 227)       # #0071E3
DARK        = (29, 29, 31)        # #1D1D1F
DARK_BG     = (40, 40, 42)        # slightly lighter dark for icon bg
WHITE       = (255, 255, 255)
SUCCESS_GREEN = (48, 209, 88)     # #30D158
WARNING_AMBER  = (255, 159, 10)   # #FF9F0A

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Sizes ────────────────────────────────────────────────────────────────────
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
DIALOG_SIZE = 48

# ── Font discovery (cross-platform) ──────────────────────────────────────────
FONT_PATHS = [
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    # macOS
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    # Windows
    "C:\\Windows\\Fonts\\segoeuib.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
    "C:\\Windows\\Fonts\\segoeui.ttf",
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


def make_base_icon(size, with_badge=True):
    """
    Create Apple-style YT icon at given size.
    Returns an RGBA Image.
    """
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # ── Geometry ───────────────────────────────────────────────────────────
    pad = max(1, size // 20)
    r = max(2, size // 6)
    x1, y1 = pad, pad
    x2, y2 = size - pad - 1, size - pad - 1

    # ── Drop shadow (sizes >= 48) ──────────────────────────────────────────
    if size >= 48:
        shadow_offset = max(1, size // 48)
        shadow_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow_img)
        sd.rounded_rectangle(
            (x1 + shadow_offset, y1 + shadow_offset,
             x2 + shadow_offset, y2 + shadow_offset),
            radius=r, fill=(0, 0, 0, 50)
        )
        blur_r = max(1, size // 64)
        shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=blur_r))
        canvas = Image.alpha_composite(canvas, shadow_img)

    # ── Background rounded rect ────────────────────────────────────────────
    draw = ImageDraw.Draw(canvas)
    rounded_rect(draw, (x1, y1, x2, y2), r, fill=APPLE_BLUE + (255,))

    # Subtle white inner border
    if size >= 32:
        draw.rounded_rectangle((x1, y1, x2, y2), radius=r,
                               outline=(255, 255, 255, 50), width=max(1, size // 64))

    # ── Draw "YT" letters ──────────────────────────────────────────────────
    yt_text = "YT"
    font_size = int(size * 0.48)
    font = find_font(font_size, bold=True) or ImageFont.load_default()

    try:
        bbox = draw.textbbox((0, 0), yt_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except Exception:
        tw, th = font_size * 0.6 * len(yt_text), font_size

    cx = size // 2
    cy = size // 2
    y_center_offset = -int(size * 0.04) if (with_badge and size >= 24) else 0

    tx = cx - tw // 2
    ty = cy - th // 2 + y_center_offset
    draw.text((tx, ty), yt_text, fill=WHITE + (255,), font=font)

    # ── Draw "PDF" badge ───────────────────────────────────────────────────
    if with_badge and size >= 24:
        pdf_text = "PDF"
        pdf_font_size = int(size * 0.15)
        pdf_font = find_font(pdf_font_size, bold=True) or ImageFont.load_default()

        try:
            pdf_bbox = draw.textbbox((0, 0), pdf_text, font=pdf_font)
            ptw = pdf_bbox[2] - pdf_bbox[0]
            pth = pdf_bbox[3] - pdf_bbox[1]
        except Exception:
            ptw, pth = pdf_font_size * 0.6 * len(pdf_text), pdf_font_size

        badge_pad_x = max(2, int(size * 0.03))
        badge_pad_y = max(1, int(size * 0.02))
        badge_r = max(1, int(size * 0.03))
        badge_y = ty + th + int(size * 0.03)
        bx1 = cx - ptw // 2 - badge_pad_x
        by1 = badge_y - badge_pad_y
        bx2 = cx + ptw // 2 + badge_pad_x
        by2 = badge_y + pth + badge_pad_y
        bx1 = max(x1 + 2, bx1)
        bx2 = min(x2 - 2, bx2)
        by2 = min(y2 - 2, by2)

        if bx2 > bx1 and by2 > by1:
            # Dark badge background
            badge_bg = (20, 20, 22, 230)
            rounded_rect(draw, (bx1, by1, bx2, by2), badge_r, fill=badge_bg)
            if size >= 32:
                draw.rounded_rectangle((bx1, by1, bx2, by2), radius=badge_r,
                                       outline=WHITE + (60,), width=max(1, size // 64))
            pdf_tx = cx - ptw // 2
            pdf_ty = badge_y
            draw.text((pdf_tx, pdf_ty), pdf_text, fill=WHITE + (255,), font=pdf_font)

    return canvas


def make_dialog_icon(size, variant):
    """
    Create dialog icon with YT badge + status indicator.
    variant: 'check' for success, 'warn' for warning
    """
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    pad = max(1, size // 10)
    r = max(2, size // 5)
    x1, y1 = pad, pad
    x2, y2 = size - pad - 1, size - pad - 1

    # Apple blue rounded square
    rounded_rect(draw, (x1, y1, x2, y2), r, fill=APPLE_BLUE + (255,))
    draw.rounded_rectangle((x1, y1, x2, y2), radius=r,
                           outline=(255, 255, 255, 40), width=1)

    # Mini "YT" text
    yt_font_size = int(size * 0.38)
    font = find_font(yt_font_size, bold=True) or ImageFont.load_default()
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
    draw.text((tx, ty), "YT", fill=WHITE + (255,), font=font)

    # Status indicator
    ind_size = int(size * 0.38)
    ind_x = size - ind_size - int(size * 0.04)
    ind_y = size - ind_size - int(size * 0.04)

    if variant == "check":
        # Green checkmark circle
        draw.ellipse(
            (ind_x, ind_y, ind_x + ind_size, ind_y + ind_size),
            fill=SUCCESS_GREEN + (255,),
            outline=WHITE + (200,),
            width=max(1, int(size * 0.04))
        )
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
        triangle = [(cx_tri, ty_tri), (cx_tri - hw, by), (cx_tri + hw, by)]
        draw.polygon(triangle, fill=WARNING_AMBER + (255,))
        ex_w = max(1, int(ind_size * 0.12))
        ex_h = int(ind_size * 0.3)
        ex_x = cx_tri - ex_w // 2
        ex_top = ty_tri + int(ind_size * 0.18)
        ex_bottom = ex_top + ex_h
        draw.rectangle((ex_x, ex_top, ex_x + ex_w, ex_bottom), fill=DARK + (255,))
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

    png_data_list = []
    for s in ico_sizes:
        img = make_base_icon(s, with_badge=(s >= 24))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_data_list.append(buf.getvalue())

    count = len(png_data_list)
    header = bytearray()
    header += (0).to_bytes(2, 'little')
    header += (1).to_bytes(2, 'little')  # type: ICO
    header += count.to_bytes(2, 'little')

    data_offset = 6 + count * 16
    all_data = bytearray()

    for s, png_bytes in zip(ico_sizes, png_data_list):
        w = s if s < 256 else 0
        h = s if s < 256 else 0
        entry = bytearray()
        entry += w.to_bytes(1, 'little')
        entry += h.to_bytes(1, 'little')
        entry += (0).to_bytes(1, 'little')
        entry += (0).to_bytes(1, 'little')
        entry += (1).to_bytes(2, 'little')  # planes
        entry += (32).to_bytes(2, 'little')  # bpp
        entry += len(png_bytes).to_bytes(4, 'little')
        entry += data_offset.to_bytes(4, 'little')
        all_data += entry
        data_offset += len(png_bytes)

    for png_bytes in png_data_list:
        all_data += png_bytes

    return bytes(header + all_data)


def generate_all():
    """Generate all icon files."""
    os.makedirs(OUT_DIR, exist_ok=True)

    # ── 1. Large PNG ─────────────────────────────────────────────────────────
    png_img = make_base_icon(256, with_badge=True)
    png_path = os.path.join(OUT_DIR, "icon.png")
    png_img.save(png_path, format="PNG")
    print(f"✓ Generated {png_path} (256x256)")

    # ── 2. Multi-resolution ICO ──────────────────────────────────────────────
    ico_bytes = make_ico()
    ico_path = os.path.join(OUT_DIR, "icon.ico")
    with open(ico_path, "wb") as f:
        f.write(ico_bytes)
    print(f"✓ Generated {ico_path}")
    print(f"   Sizes: {ICO_SIZES}")
    print(f"   ICO size: {len(ico_bytes):,} bytes")

    # ── 3. Dialog checkmark icon ─────────────────────────────────────────────
    check_img = make_dialog_icon(DIALOG_SIZE, "check")
    check_path = os.path.join(OUT_DIR, "icon_dialog_check.png")
    check_img.save(check_path, format="PNG")
    print(f"✓ Generated {check_path} ({DIALOG_SIZE}x{DIALOG_SIZE})")

    # ── 4. Dialog warning icon ───────────────────────────────────────────────
    warn_img = make_dialog_icon(DIALOG_SIZE, "warn")
    warn_path = os.path.join(OUT_DIR, "icon_dialog_warn.png")
    warn_img.save(warn_path, format="PNG")
    print(f"✓ Generated {warn_path} ({DIALOG_SIZE}x{DIALOG_SIZE})")

    # ── Validation ──────────────────────────────────────────────────────────
    print("\n── Validation ──")
    import struct
    with open(ico_path, 'rb') as f:
        ico_data = f.read()
    _, _, count = struct.unpack_from('<HHH', ico_data, 0)
    print(f"icon.ico: {count} entries")
    from io import BytesIO
    for i in range(count):
        entry_off = 6 + i * 16
        w, h, *_ = struct.unpack_from('<BBBBHHII', ico_data, entry_off)
        w_act = w or 256
        h_act = h or 256
        print(f"  {w_act:3d}x{h_act:<3d}")

    for name in ["icon.png", "icon_dialog_check.png", "icon_dialog_warn.png"]:
        p = os.path.join(OUT_DIR, name)
        if os.path.exists(p):
            im = Image.open(p)
            print(f"  {name:25s} {im.size[0]}x{im.size[1]} mode={im.mode}")

    print("\n✅ All icons generated successfully!")


if __name__ == "__main__":
    generate_all()
