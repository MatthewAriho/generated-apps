"""Generate ClearSpend app icon and presplash images.

Run: python assets/generate_icon.py
Requires: pip install Pillow
"""
from __future__ import annotations
import math
import os

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Install Pillow: pip install Pillow")
    raise SystemExit(1)


def draw_icon(size: int = 512) -> Image.Image:
    """Draw the ClearSpend logo: teal circle with a white dollar-chart symbol."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle - teal
    pad = int(size * 0.02)
    draw.ellipse([pad, pad, size - pad, size - pad], fill=(0, 150, 136, 255))

    # Inner subtle ring
    ring_pad = int(size * 0.06)
    draw.ellipse(
        [ring_pad, ring_pad, size - ring_pad, size - ring_pad],
        fill=(0, 137, 123, 255),
    )

    cx, cy = size // 2, size // 2

    # Dollar sign - clean, bold
    dollar_w = int(size * 0.06)
    dollar_h = int(size * 0.38)
    dollar_top = cy - dollar_h // 2

    # S-curve of the dollar sign (two arcs)
    s_width = int(size * 0.22)
    arc_h = dollar_h // 2

    # Top arc (curves right)
    arc_box_top = [
        cx - s_width // 2,
        dollar_top,
        cx + s_width // 2,
        dollar_top + arc_h,
    ]
    draw.arc(arc_box_top, 180, 0, fill="white", width=int(size * 0.04))

    # Bottom arc (curves left)
    arc_box_bot = [
        cx - s_width // 2,
        dollar_top + arc_h,
        cx + s_width // 2,
        dollar_top + dollar_h,
    ]
    draw.arc(arc_box_bot, 0, 180, fill="white", width=int(size * 0.04))

    # Vertical line through dollar sign
    line_ext = int(size * 0.05)
    draw.line(
        [(cx, dollar_top - line_ext), (cx, dollar_top + dollar_h + line_ext)],
        fill="white",
        width=int(size * 0.035),
    )

    # Small chart bars at bottom-right (spending indicator)
    bar_base_x = cx + int(size * 0.18)
    bar_base_y = cy + int(size * 0.2)
    bar_w = int(size * 0.045)
    bar_gap = int(size * 0.015)
    bar_heights = [0.08, 0.14, 0.1, 0.18]

    for i, bh in enumerate(bar_heights):
        bx = bar_base_x + i * (bar_w + bar_gap)
        by = bar_base_y
        h = int(size * bh)
        # Bars in lighter teal/white
        color = (200, 255, 250, 200)
        draw.rectangle([bx, by - h, bx + bar_w, by], fill=color)

    return img


def draw_presplash(width: int = 720, height: int = 1280) -> Image.Image:
    """Draw a presplash screen: dark background with centered logo."""
    img = Image.new("RGB", (width, height), (26, 26, 46))
    icon = draw_icon(256)
    # Center the icon
    ix = (width - 256) // 2
    iy = (height - 256) // 2 - 40
    img.paste(icon, (ix, iy), icon)

    # App name below icon
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except Exception:
        font = ImageFont.load_default()

    text = "ClearSpend"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    tx = (width - tw) // 2
    ty = iy + 256 + 30
    draw.text((tx, ty), text, fill=(0, 200, 180), font=font)

    return img


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))

    # App icon (512x512)
    icon = draw_icon(512)
    icon_path = os.path.join(out_dir, "icon.png")
    icon.save(icon_path)
    print(f"Icon saved: {icon_path}")

    # Smaller icon for notifications (192x192)
    icon_sm = draw_icon(192)
    icon_sm_path = os.path.join(out_dir, "icon_192.png")
    icon_sm.save(icon_sm_path)
    print(f"Small icon saved: {icon_sm_path}")

    # Presplash
    presplash = draw_presplash()
    presplash_path = os.path.join(out_dir, "presplash.png")
    presplash.save(presplash_path)
    print(f"Presplash saved: {presplash_path}")

    print("\nUpdate buildozer.spec:")
    print(f"  icon.filename = assets/icon.png")
    print(f"  presplash.filename = assets/presplash.png")


if __name__ == "__main__":
    main()
