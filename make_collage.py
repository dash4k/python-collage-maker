#!/usr/bin/env python3
import os
import sys
import argparse
import random
from pathlib import Path
from math import ceil
from datetime import datetime, timezone

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("Pillow is required. Install it with:")
    print("   pip install Pillow --break-system-packages")
    sys.exit(1)


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".tiff", ".bmp", ".webp"}

CANVAS_SIZES = {
    "hd":     (1920, 1080),
    "square": (2000, 2000),
    "poster": (1414, 2000),
    "wide":   (2560, 1440),
}

GRID_LAYOUTS = {
    "2x5":  (2, 5),
    "3x4":  (3, 4),
    "4x3":  (4, 3),
    "5x2":  (5, 2),
    "auto": None,
}


def collect_photos(sources):
    photos = []
    for src in sources:
        p = Path(src)
        if p.is_dir():
            for ext in SUPPORTED_EXTENSIONS:
                photos.extend(p.glob(f"*{ext}"))
                photos.extend(p.glob(f"*{ext.upper()}"))
        elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            photos.append(p)
    return sorted(set(photos))


def best_grid(n):
    candidates = []
    for cols in range(2, n + 1):
        rows = ceil(n / cols)
        if rows * cols >= n:
            candidates.append((cols, rows, abs(cols - rows)))
    candidates.sort(key=lambda x: (x[2], x[0]))
    cols, rows, _ = candidates[0]
    return cols, rows


def fit_and_crop(img, cell_w, cell_h):
    src_ratio = img.width / img.height
    dst_ratio = cell_w / cell_h
    if src_ratio > dst_ratio:
        new_h = cell_h
        new_w = int(src_ratio * cell_h)
    else:
        new_w = cell_w
        new_h = int(cell_w / src_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - cell_w) // 2
    top  = (new_h - cell_h) // 2
    return img.crop((left, top, left + cell_w, top + cell_h))


def add_title(canvas, title, bg_color, text_color=(0, 0, 0)):
    bar_h   = max(60, canvas.height // 18)
    bar_img = Image.new("RGB", (canvas.width, bar_h), color=bg_color)
    draw    = ImageDraw.Draw(bar_img)
    font_size = bar_h - 20
    font = None
    for font_path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]:
        if Path(font_path).exists():
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), title, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((canvas.width - tw) // 2, (bar_h - th) // 2), title, font=font, fill=text_color)
    combined = Image.new("RGB", (canvas.width, canvas.height + bar_h))
    combined.paste(canvas, (0, 0))
    combined.paste(bar_img, (0, canvas.height))
    return combined


def hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_collage(
    sources,
    output      = "collages/"+ datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S") + ".jpg",
    layout      = "auto",
    canvas_size = "hd",
    padding     = 8,
    bg_color    = "#1a1a1a",
    shuffle     = False,
    title       = None,
    max_photos  = 12,
    shadow      = True,
):
    photos = collect_photos(sources)
    if not photos:
        print("No supported photos found.")
        sys.exit(1)

    if shuffle:
        random.shuffle(photos)

    if len(photos) < 10:
        print(f"Warning: only {len(photos)} photo(s) found. Recommended: 10-12.")
    if len(photos) > max_photos:
        print(f"Found {len(photos)} photos - using first {max_photos}.")
        photos = photos[:max_photos]

    n = len(photos)
    print(f"Using {n} photo(s)")

    if layout == "auto":
        cols, rows = best_grid(n)
    else:
        cols, rows = GRID_LAYOUTS[layout]
    print(f"Grid: {cols} cols x {rows} rows")

    canvas_w, canvas_h = CANVAS_SIZES[canvas_size]
    bg = hex_to_rgb(bg_color)
    canvas = Image.new("RGB", (canvas_w, canvas_h), color=bg)

    cell_w = (canvas_w - padding * (cols + 1)) // cols
    cell_h = (canvas_h - padding * (rows + 1)) // rows

    for idx, photo_path in enumerate(photos):
        col = idx % cols
        row = idx // cols
        x = padding + col * (cell_w + padding)
        y = padding + row * (cell_h + padding)

        try:
            img = Image.open(photo_path).convert("RGB")
        except Exception as e:
            print(f"  Skipping {photo_path.name}: {e}")
            continue

        cell = fit_and_crop(img, cell_w, cell_h)

        if shadow:
            s = max(3, padding // 2)
            shadow_layer = Image.new("RGBA", (cell_w + s * 4, cell_h + s * 4), (0, 0, 0, 0))
            draw = ImageDraw.Draw(shadow_layer)
            draw.rectangle([s*2, s*2, s*2 + cell_w, s*2 + cell_h], fill=(0, 0, 0, 120))
            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=s))
            canvas.paste(shadow_layer.convert("RGB"), (x - s, y - s), mask=shadow_layer.split()[3])

        canvas.paste(cell, (x, y))
        print(f"  [{row+1},{col+1}] {photo_path.name}")

    if title:
        canvas = add_title(canvas, title, bg_color=bg)

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ext = out_path.suffix.lower()
    save_kwargs = {"quality": 95, "optimize": True} if ext in (".jpg", ".jpeg") else {}
    canvas.save(out_path, **save_kwargs)
    print(f"\nCollage saved: {out_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a photo collage from 10-12 images.",
        epilog="""
Examples:
  python make_collage.py ~/Photos/trip/ --output trip.jpg
  python make_collage.py a.jpg b.jpg c.jpg --layout 3x4 --title "Summer 2024"
  python make_collage.py ~/Photos/ --canvas square --shuffle --no-shadow
        """
    )
    parser.add_argument("sources", nargs="+", help="Photo files or folders")
    parser.add_argument("--output",    "-o", default="collages/" + datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S") + ".jpg")
    parser.add_argument("--layout",    "-l", default="auto",   choices=list(GRID_LAYOUTS.keys()))
    parser.add_argument("--canvas",    "-c", default="hd",     choices=list(CANVAS_SIZES.keys()))
    parser.add_argument("--padding",   "-p", type=int, default=8)
    parser.add_argument("--bg",                default="#ffffff")
    parser.add_argument("--title",     "-t",   default=None)
    parser.add_argument("--shuffle",           action="store_true")
    parser.add_argument("--no-shadow",         action="store_true")
    parser.add_argument("--max",               type=int, default=12)
    args = parser.parse_args()

    make_collage(
        sources     = args.sources,
        output      = args.output,
        layout      = args.layout,
        canvas_size = args.canvas,
        padding     = args.padding,
        bg_color    = args.bg,
        shuffle     = args.shuffle,
        title       = args.title,
        max_photos  = args.max,
        shadow      = not args.no_shadow,
    )