import os
import sys
import random
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, ttk
from pathlib import Path
from math import ceil
from datetime import datetime, timezone

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    messagebox.showerror("Error", "Pillow is required. Please install it.")
    sys.exit(1)

# --- ORIGINAL CORE LOGIC ---
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".tiff", ".bmp", ".webp"}

CANVAS_SIZES = {
    "hd":     (1920, 1080),
    "square": (2000, 2000),
    "poster": (1414, 2000),
    "wide":   (2560, 1440),
}

GRID_LAYOUTS = {
    "auto": None,
    "2x5":  (2, 5),
    "3x4":  (3, 4),
    "4x3":  (4, 3),
    "5x2":  (5, 2),
}

def natural_sort_key(path):
    parts = re.split(r'(\d+)', path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]

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
    return sorted(set(photos), key=natural_sort_key)

def best_grid(n):
    if n == 0: return 1, 1
    candidates = []
    for cols in range(2, n + 1):
        rows = ceil(n / cols)
        if rows * cols >= n:
            candidates.append((cols, rows, abs(cols - rows)))
    if not candidates: return 1, n
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
    
    # Updated to handle potential differences in textbbox behavior
    try:
        bbox = draw.textbbox((0, 0), title, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(title, font=font)
        
    draw.text(((canvas.width - tw) // 2, (bar_h - th) // 2), title, font=font, fill=text_color)
    combined = Image.new("RGB", (canvas.width, canvas.height + bar_h))
    combined.paste(canvas, (0, 0))
    combined.paste(bar_img, (0, canvas.height))
    return combined

def hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def make_collage(sources, output, layout, canvas_size, padding, bg_color, shuffle_photos, title, max_photos, shadow):
    photos = collect_photos(sources)
    if not photos:
        raise ValueError("No supported photos found in the selected folder.")

    if shuffle_photos:
        random.shuffle(photos)

    if len(photos) > max_photos:
        photos = photos[:max_photos]

    n = len(photos)
    if layout == "auto":
        cols, rows = best_grid(n)
    else:
        cols, rows = GRID_LAYOUTS[layout]

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
        except Exception:
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

    if title:
        canvas = add_title(canvas, title, bg_color=bg)

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ext = out_path.suffix.lower()
    save_kwargs = {"quality": 95, "optimize": True} if ext in (".jpg", ".jpeg") else {}
    canvas.save(out_path, **save_kwargs)
    return out_path.resolve()

# --- GUI CLASS ---
class CollageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Collage Maker")
        self.root.geometry("500x550")
        self.root.resizable(False, False)

        # Variables
        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar(value=os.path.join(os.getcwd(), f"collage_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jpg"))
        self.layout_var = tk.StringVar(value="auto")
        self.canvas_var = tk.StringVar(value="hd")
        self.padding_var = tk.IntVar(value=8)
        self.bg_var = tk.StringVar(value="#ffffff")
        self.title_var = tk.StringVar()
        self.max_var = tk.IntVar(value=12)
        self.shuffle_var = tk.BooleanVar(value=False)
        self.shadow_var = tk.BooleanVar(value=True)

        self.build_ui()

    def build_ui(self):
        frame = ttk.Frame(self.root, padding=15)
        frame.pack(fill="both", expand=True)

        # Source Folder
        ttk.Label(frame, text="Source Folder:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.source_var, width=40).grid(row=0, column=1, pady=5)
        ttk.Button(frame, text="Browse", command=self.browse_source).grid(row=0, column=2, padx=5, pady=5)

        # Output File
        ttk.Label(frame, text="Output File:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.output_var, width=40).grid(row=1, column=1, pady=5)
        ttk.Button(frame, text="Browse", command=self.browse_output).grid(row=1, column=2, padx=5, pady=5)

        # Settings Grid
        settings_frame = ttk.LabelFrame(frame, text="Settings", padding=10)
        settings_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=15)

        ttk.Label(settings_frame, text="Layout:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Combobox(settings_frame, textvariable=self.layout_var, values=list(GRID_LAYOUTS.keys()), state="readonly", width=10).grid(row=0, column=1, sticky="w", pady=5)

        ttk.Label(settings_frame, text="Canvas Size:").grid(row=0, column=2, sticky="w", padx=10, pady=5)
        ttk.Combobox(settings_frame, textvariable=self.canvas_var, values=list(CANVAS_SIZES.keys()), state="readonly", width=10).grid(row=0, column=3, sticky="w", pady=5)

        ttk.Label(settings_frame, text="Padding:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Spinbox(settings_frame, from_=0, to=100, textvariable=self.padding_var, width=10).grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(settings_frame, text="Max Photos:").grid(row=1, column=2, sticky="w", padx=10, pady=5)
        ttk.Spinbox(settings_frame, from_=2, to=100, textvariable=self.max_var, width=10).grid(row=1, column=3, sticky="w", pady=5)

        ttk.Label(settings_frame, text="Collage Title:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(settings_frame, textvariable=self.title_var, width=25).grid(row=2, column=1, columnspan=3, sticky="w", pady=5)

        ttk.Label(settings_frame, text="Background Color:").grid(row=3, column=0, sticky="w", pady=5)
        self.color_btn = tk.Button(settings_frame, bg=self.bg_var.get(), width=3, command=self.choose_color)
        self.color_btn.grid(row=3, column=1, sticky="w", pady=5)

        # Checkboxes
        ttk.Checkbutton(settings_frame, text="Shuffle Photos", variable=self.shuffle_var).grid(row=4, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Checkbutton(settings_frame, text="Add Shadows", variable=self.shadow_var).grid(row=4, column=2, columnspan=2, sticky="w", pady=5)

        # Generate Button
        self.generate_btn = ttk.Button(frame, text="Generate Collage", command=self.start_generation)
        self.generate_btn.grid(row=3, column=0, columnspan=3, pady=20)

        # Status Label
        self.status_lbl = ttk.Label(frame, text="Ready.", foreground="gray")
        self.status_lbl.grid(row=4, column=0, columnspan=3)

    def browse_source(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_var.set(folder)

    def browse_output(self):
        file = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
        if file:
            self.output_var.set(file)

    def choose_color(self):
        color_code = colorchooser.askcolor(title="Choose background color")[1]
        if color_code:
            self.bg_var.set(color_code)
            self.color_btn.configure(bg=color_code)

    def start_generation(self):
        if not self.source_var.get():
            messagebox.showwarning("Missing Info", "Please select a source folder.")
            return

        self.generate_btn.config(state="disabled")
        self.status_lbl.config(text="Processing images... Please wait.", foreground="blue")
        
        # Run in a separate thread so the GUI doesn't freeze
        threading.Thread(target=self.run_collage, daemon=True).start()

    def run_collage(self):
        try:
            out_path = make_collage(
                sources=[self.source_var.get()],
                output=self.output_var.get(),
                layout=self.layout_var.get(),
                canvas_size=self.canvas_var.get(),
                padding=self.padding_var.get(),
                bg_color=self.bg_var.get(),
                shuffle_photos=self.shuffle_var.get(),
                title=self.title_var.get() if self.title_var.get() else None,
                max_photos=self.max_var.get(),
                shadow=self.shadow_var.get()
            )
            self.root.after(0, lambda: self.finish_generation(True, str(out_path)))
        except Exception as e:
            self.root.after(0, lambda: self.finish_generation(False, str(e)))

    def finish_generation(self, success, message):
        self.generate_btn.config(state="normal")
        if success:
            self.status_lbl.config(text="Done!", foreground="green")
            messagebox.showinfo("Success", f"Collage saved successfully:\n{message}")
        else:
            self.status_lbl.config(text="Error occurred.", foreground="red")
            messagebox.showerror("Error", f"An error occurred:\n{message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CollageApp(root)
    root.mainloop()
