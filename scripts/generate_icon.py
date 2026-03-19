#!/usr/bin/env python3
"""Generate the aghoul macOS app icon: perfect distressed neon on stamped metal."""

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import math
import os
from scipy.ndimage import gaussian_filter

SIZE = 1024
CENTER = SIZE // 2

def make_brushed_metal(size):
    """Create stamped steel with diagonal lighting, dark base, and subtle grain."""
    img = np.zeros((size, size, 3), dtype=np.float64)
    base = np.array([0.08, 0.09, 0.10])
    img[:] = base

    y, x = np.mgrid[0:size, 0:size]
    cx, cy = size / 2, size / 2
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

    # Diagonal lighting for stamped depth
    diag = (x + y) / (2 * size)
    light = np.interp(diag, [0, 1], [0.08, -0.04])
    for c in range(3):
        img[:, :, c] += light

    # Center metallic highlight
    center_highlight = np.exp(-dist ** 2 / (2 * (size * 0.4) ** 2)) * 0.04
    for c in range(3):
        img[:, :, c] += center_highlight

    # Nearly invisible brushed rings
    for i in range(8):
        freq = 1.0 + i * 0.6
        amp = 0.0005
        ring = np.sin(dist * freq * 0.15) * amp
        for c in range(3):
            img[:, :, c] += ring

    # Grain
    noise = np.random.normal(0, 0.006, (size, size))
    for c in range(3):
        img[:, :, c] += noise

    # Deep vignette
    vignette = 1.0 - (dist / (size * 0.65)) ** 2 * 0.6
    vignette = np.clip(vignette, 0.2, 1.0)
    for c in range(3):
        img[:, :, c] *= vignette

    return np.clip(img, 0, 1)

def add_patina(img, size):
    """Add subtle rust/patina spots."""
    patina_color = np.array([0.10, 0.07, 0.04])
    y, x = np.mgrid[0:size, 0:size]
    spots = [
        (size * 0.85, size * 0.12, size * 0.08, 0.4),
        (size * 0.90, size * 0.08, size * 0.06, 0.3),
        (size * 0.15, size * 0.85, size * 0.04, 0.2),
    ]
    for sx, sy, sr, strength in spots:
        d = np.sqrt((x - sx) ** 2 + (y - sy) ** 2)
        mask = np.clip(1.0 - d / sr, 0, 1) ** 1.5
        noise = np.clip(np.random.normal(0.5, 0.35, (size, size)), 0, 1)
        mask *= noise * strength
        for c in range(3):
            img[:, :, c] = img[:, :, c] * (1 - mask) + patina_color[c] * mask
    return img

def rounded_rect_mask(size, radius, border=0):
    """Standard macOS padding and squircle shape."""
    img = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(img)
    std_padding = 20
    std_radius = 154
    border = std_padding if border == 0 else border
    radius = std_radius if radius == 0 else radius
    draw.rounded_rectangle(
        [border, border, size - 1 - border, size - 1 - border],
        radius=radius, fill=255,
    )
    return np.array(img).astype(np.float64) / 255.0

def draw_polyline_glow(canvas, pts_arr, color_inner, color_outer, tube_width=6):
    """Draw smooth neon tube with intense core and rich aura."""
    h, w = canvas.shape[:2]

    # Outer purple glow (richer, wider)
    for radius, intensity in [(120, 0.06), (70, 0.12), (40, 0.25), (20, 0.45)]:
        layer = np.zeros((h, w), dtype=np.float64)
        cv2.polylines(layer, [pts_arr], False, 1.0, int(radius * 2), cv2.LINE_AA)
        layer = gaussian_filter(layer, sigma=radius * 0.4) * intensity
        for c in range(3):
            canvas[:, :, c] += layer * color_outer[c]

    # Inner green glow (tighter, brighter)
    for radius, intensity in [(14, 0.4), (7, 0.7), (3, 0.9)]:
        layer = np.zeros((h, w), dtype=np.float64)
        cv2.polylines(layer, [pts_arr], False, 1.0, int(radius * 2), cv2.LINE_AA)
        layer = gaussian_filter(layer, sigma=radius * 0.3) * intensity
        for c in range(3):
            canvas[:, :, c] += layer * color_inner[c]

    # White-hot core
    core = np.zeros((h, w), dtype=np.float64)
    cv2.polylines(core, [pts_arr], False, 1.0, tube_width, cv2.LINE_AA)
    core_color = np.array(color_inner) * 0.2 + np.array([0.8, 0.8, 0.8])
    for c in range(3):
        canvas[:, :, c] += core * core_color[c]

def generate_ghost_points(cx, cy, ghost_w, ghost_h):
    """Locked-in slender ghost geometry."""
    points = []
    half_w = ghost_w / 2
    dome_radius = half_w
    top_y = cy - ghost_h / 2
    dome_center_y = top_y + dome_radius
    side_bottom = cy + ghost_h / 2
    wave_depth = ghost_h * 0.12

    for angle in np.linspace(0, math.pi, 60):
        x = cx + dome_radius * math.cos(angle)
        y = dome_center_y - dome_radius * math.sin(angle)
        points.append([x, y])

    left_x = cx - half_w
    right_x = cx + half_w
    for t in np.linspace(0, 1, 20):
        y = dome_center_y + (side_bottom - dome_center_y) * t
        points.append([left_x, y])

    for t in np.linspace(0, 1, 100):
        x = left_x + (right_x - left_x) * t
        y = side_bottom - wave_depth * (1 - math.cos(t * math.pi * 4)) / 2.0
        points.append([x, y])

    for t in np.linspace(0, 1, 20):
        y = side_bottom - (side_bottom - dome_center_y) * t
        points.append([right_x, y])

    return np.array(points, dtype=np.int32)

def draw_solid_text_neon(canvas, text, cx, cy, font_size, color, glow_color, thickness=2, glow_radius=18):
    """Draw a single string as a solid, punchy neon element for small-scale legibility."""
    h, w = canvas.shape[:2]
    text_img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(text_img)

    # Force a standard monospace terminal font
    font = None
    font_paths = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFMono-Regular.otf",
        "/Library/Fonts/Courier New.ttf",
    ]
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, font_size)
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()

    # Anchor="mm" perfectly middle-centers the entire text block mathematically
    draw.text((cx, cy), text, font=font, fill=255, anchor="mm")

    text_mask = np.array(text_img).astype(np.float64) / 255.0

    # Dilate slightly to make the font bolder and more legible at small sizes
    if thickness > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (thickness, thickness))
        text_mask = cv2.dilate(text_mask, kernel)

    # Apply heavy, layered neon glow
    for sigma, intensity in [(glow_radius * 2, 0.1), (glow_radius, 0.25),
                             (glow_radius * 0.5, 0.4), (glow_radius * 0.25, 0.6)]:
        glow = gaussian_filter(text_mask, sigma=sigma) * intensity
        for c in range(3):
            canvas[:, :, c] += glow * glow_color[c]

    # Bright, solid core
    core_color = np.array(color) * 0.4 + np.array([0.6, 0.6, 0.6])
    for c in range(3):
        canvas[:, :, c] += text_mask * core_color[c]

def draw_cockeyed_eyes(canvas, cx, cy, ghost_w, color, glow_color):
    """Draw 'X' and 'x' baseline-aligned with cockeyed offset, using solid neon."""
    h, w = canvas.shape[:2]
    text_img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(text_img)

    font_large, font_small = None, None
    font_paths = ["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/SFMono-Regular.otf", "/Library/Fonts/Courier New.ttf"]
    for fp in font_paths:
        try:
            font_large = ImageFont.truetype(fp, 150)
            font_small = ImageFont.truetype(fp, 115)
            break
        except OSError:
            continue
    if not font_large:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    y_baseline = cy + int(ghost_w * 0.15)
    spacing = int(ghost_w * 0.12)
    cockeyed_lift = 12

    draw.text((cx - spacing, y_baseline), "X", font=font_large, fill=255, anchor="ms")
    draw.text((cx + spacing, y_baseline - cockeyed_lift), "x", font=font_small, fill=255, anchor="ms")

    text_mask = np.array(text_img).astype(np.float64) / 255.0

    # Dilate for bold, legible fill
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    text_mask = cv2.dilate(text_mask, kernel)

    # Heavy neon glow
    for sigma, intensity in [(36, 0.1), (18, 0.25), (9, 0.4), (4, 0.6)]:
        glow = gaussian_filter(text_mask, sigma=sigma) * intensity
        for c in range(3):
            canvas[:, :, c] += glow * glow_color[c]

    # Solid bright core
    core_color = np.array(color) * 0.4 + np.array([0.6, 0.6, 0.6])
    for c in range(3):
        canvas[:, :, c] += text_mask * core_color[c]

def generate_icon():
    size = SIZE
    metal = make_brushed_metal(size)
    metal = add_patina(metal, size)

    border = 20
    corner_radius = 154
    plaque_mask = rounded_rect_mask(size, corner_radius, border)

    canvas = np.zeros((size, size, 4), dtype=np.float64)
    for c in range(3):
        canvas[:, :, c] = metal[:, :, c]
    canvas[:, :, 3] = 1.0

    inner_bezel_mask = rounded_rect_mask(size, corner_radius - 10, border + 10)
    bezel_frame_mask = np.clip(plaque_mask - inner_bezel_mask, 0, 1)
    bezel_color = np.array([0.15, 0.16, 0.17])
    for c in range(3):
        canvas[:, :, c] = canvas[:, :, c] * (1 - bezel_frame_mask * 0.8) + bezel_color[c] * bezel_frame_mask * 0.8

    green_outer_rect = rounded_rect_mask(size, corner_radius - 30, border + 77)
    green_inner_rect = rounded_rect_mask(size, corner_radius - 51, border + 101)
    green_border_mask = np.clip(green_outer_rect - green_inner_rect, 0, 1)

    # Smooth perimeter-based dimming — no hard cuts, just gentle brightness waves
    # Map a slow sine wave along the border perimeter for organic dimming
    y_grid, x_grid = np.mgrid[0:size, 0:size]
    angle_from_center = np.arctan2(y_grid - size/2, x_grid - size/2)
    # 3 smooth brightness dips around the perimeter
    dim_wave = 0.65 + 0.35 * np.cos(angle_from_center * 3 + 1.2)
    green_border_mask *= dim_wave

    green = np.array([0.35, 1.0, 0.45])
    glow1 = gaussian_filter(green_border_mask, sigma=8) * 0.5
    glow2 = gaussian_filter(green_border_mask, sigma=20) * 0.3
    for c in range(3):
        canvas[:, :, c] += green_border_mask * green[c] * 0.9 # Bright core of broken line
        canvas[:, :, c] += glow1 * green[c]
        canvas[:, :, c] += glow2 * green[c]

    # Pop the purple and green
    purple_neon = np.array([0.7, 0.2, 1.0]) # Highly saturated
    ghost_green = np.array([0.3, 1.0, 0.5])

    ghost_w = size * 0.48
    ghost_h = size * 0.56
    cy_adjusted = CENTER

    ghost_pts = generate_ghost_points(CENTER, cy_adjusted, ghost_w, ghost_h)
    closed_pts = np.vstack([ghost_pts, ghost_pts[0:1]])
    closed_arr = closed_pts.reshape(-1, 1, 2)

    rgb_surface = canvas[:, :, :3]
    draw_polyline_glow(rgb_surface, closed_arr, ghost_green, purple_neon, tube_width=6)

    # Solid neon Xx eyes — single string for perfect kerning and dock legibility
    eye_y = cy_adjusted - int(ghost_h * 0.10)
    draw_solid_text_neon(
        rgb_surface, "Xx", CENTER, eye_y,
        font_size=160, color=ghost_green, glow_color=ghost_green, thickness=2
    )

    for c in range(3):
        canvas[:, :, c] = rgb_surface[:, :, c] * green_outer_rect
    canvas[:, :, 3] = green_outer_rect

    canvas_output = np.clip(canvas, 0, 1)
    canvas_uint8 = (canvas_output * 255).astype(np.uint8)

    output_img = Image.fromarray(canvas_uint8, "RGBA")
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "aghoul_icon.png"))
    output_img.save(output_path)
    print(f"Final perfect match icon saved to {output_path}")

if __name__ == "__main__":
    generate_icon()
