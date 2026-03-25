# Collage Maker

Built with Python and Tkinter, powered by [Pillow](https://python-pillow.org/).

---

## Features

### Grid Layout Options
| Layout | Description |
|--------|-------------|
| `auto` | Automatically picks the most balanced grid for your photo count |
| `2x5`  | 2 columns, 5 rows |
| `3x4`  | 3 columns, 4 rows |
| `4x3`  | 4 columns, 3 rows |
| `5x2`  | 5 columns, 2 rows |

### Canvas Size Presets
| Preset | Dimensions |
|--------|-----------|
| `hd` | 1920 × 1080 |
| `square` | 2000 × 2000 |
| `poster` | 1414 × 2000 |
| `wide` | 2560 × 1440 |

### Adjustable Padding
Control the spacing (in pixels) between photos and around the edges of the canvas. Set it to `0` for a seamless look, or increase it for a clean framed style.

### Background Color Picker
Choose any background color using the built-in color picker. The selected color fills the canvas behind and between all photos.

### Collage Title
Optionally add a title to your collage. It is rendered as a text bar appended to the bottom of the image, using the same background color as the canvas.

### Max Photos Limit
Set the maximum number of photos to include (2–100). If your folder has more photos than the limit, only the first N are used (or a random N if shuffle is enabled).

### Shuffle Photos
Enable this option to randomize the order photos appear in the collage. Great for creating varied layouts from the same folder.

### Drop Shadows
Toggle soft drop shadows behind each photo cell for a polished, layered look.

### Custom Output Path
Choose exactly where your collage is saved and in what format. Supports `.jpg` (compressed) and `.png` (lossless) output.

---

## Requirements

- Python 3.8+
- [Pillow](https://pypi.org/project/Pillow/)

```bash
pip install Pillow
```

---

## Usage

```bash
python gui.py
```

1. Click **Browse** to select a folder containing your photos.
2. Choose an output file path and format.
3. Adjust settings (layout, canvas size, padding, etc.).
4. Click **Generate Collage** and wait for the confirmation.

---

## Supported Image Formats

`.jpg` · `.jpeg` · `.png` · `.heic` · `.tiff` · `.bmp` · `.webp`

---

## License

The Unlicense
