"""One-shot script that mirrors what `flutter_launcher_icons` produces.
Run this if the Flutter SDK isn't installed in your dev box; otherwise
prefer `dart run flutter_launcher_icons`. Output is committed so the
icon ships pre-generated.

Sources (relative to repo root):
  school_erp_mobile/jaikalki/assets/icons/ic_launcher_foreground.png
  school_erp_mobile/jaikalki/assets/icons/ic_launcher_background.png
  school_erp_mobile/jaikalki/assets/icons/ic_launcher_monochrome.png
  school_erp_mobile/jaikalki/assets/icons/app_icon.png   (1024x1024)
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]  # school_erp_mobile/jaikalki
ASSETS = REPO / "assets" / "icons"
ANDROID_RES = REPO / "android" / "app" / "src" / "main" / "res"
IOS_APPICON = REPO / "ios" / "Runner" / "Assets.xcassets" / "AppIcon.appiconset"

fg = Image.open(ASSETS / "ic_launcher_foreground.png").convert("RGBA")
bg = Image.open(ASSETS / "ic_launcher_background.png").convert("RGBA")
mono = Image.open(ASSETS / "ic_launcher_monochrome.png").convert("RGBA")
master = Image.open(ASSETS / "app_icon.png").convert("RGBA")

# --- Android: adaptive icon layers per density -----------------------------

ANDROID_DENSITIES = [
    ("mdpi", 108),
    ("hdpi", 162),
    ("xhdpi", 216),
    ("xxhdpi", 324),
    ("xxxhdpi", 432),
]

# --- Android: legacy flat icon per density ---------------------------------

LEGACY_SIZES = [
    ("mdpi", 48),
    ("hdpi", 72),
    ("xhdpi", 96),
    ("xxhdpi", 144),
    ("xxxhdpi", 192),
]


def composite_legacy(size: int) -> Image.Image:
    """Adaptive layers are 432 with a 264 safe zone in the center, but
    legacy icons are full-bleed. Background covers the whole tile and
    the foreground sits on top, both centered."""
    out = bg.resize((size, size), Image.LANCZOS).copy()
    fg_resized = fg.resize((size, size), Image.LANCZOS)
    out.alpha_composite(fg_resized)
    return out


def round_icon(square: Image.Image) -> Image.Image:
    """Mask the legacy icon into a circle for ic_launcher_round."""
    from PIL import ImageDraw

    size = square.size[0]
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(square, (0, 0), mask)
    return out


for density, px in ANDROID_DENSITIES:
    out_dir = ANDROID_RES / f"mipmap-{density}"
    out_dir.mkdir(parents=True, exist_ok=True)
    fg.resize((px, px), Image.LANCZOS).save(out_dir / "ic_launcher_foreground.png")
    bg.resize((px, px), Image.LANCZOS).save(out_dir / "ic_launcher_background.png")
    mono.resize((px, px), Image.LANCZOS).save(out_dir / "ic_launcher_monochrome.png")

for density, px in LEGACY_SIZES:
    out_dir = ANDROID_RES / f"mipmap-{density}"
    out_dir.mkdir(parents=True, exist_ok=True)
    flat = composite_legacy(px)
    flat.save(out_dir / "ic_launcher.png")
    round_icon(flat).save(out_dir / "ic_launcher_round.png")

# --- Android: adaptive-icon XML resource -----------------------------------

ANYDPI = ANDROID_RES / "mipmap-anydpi-v26"
ANYDPI.mkdir(parents=True, exist_ok=True)

adaptive_xml = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@mipmap/ic_launcher_background"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>
    <monochrome android:drawable="@mipmap/ic_launcher_monochrome"/>
</adaptive-icon>
"""
(ANYDPI / "ic_launcher.xml").write_text(adaptive_xml)
(ANYDPI / "ic_launcher_round.xml").write_text(adaptive_xml)

# --- iOS: AppIcon.appiconset PNGs from the 1024 master ---------------------

IOS_SPECS = [
    ("Icon-App-20x20@1x.png", 20),
    ("Icon-App-20x20@2x.png", 40),
    ("Icon-App-20x20@3x.png", 60),
    ("Icon-App-29x29@1x.png", 29),
    ("Icon-App-29x29@2x.png", 58),
    ("Icon-App-29x29@3x.png", 87),
    ("Icon-App-40x40@1x.png", 40),
    ("Icon-App-40x40@2x.png", 80),
    ("Icon-App-40x40@3x.png", 120),
    ("Icon-App-60x60@2x.png", 120),
    ("Icon-App-60x60@3x.png", 180),
    ("Icon-App-76x76@1x.png", 76),
    ("Icon-App-76x76@2x.png", 152),
    ("Icon-App-83.5x83.5@2x.png", 167),
    ("Icon-App-1024x1024@1x.png", 1024),
]

# Apple rejects transparency in the App Store icon.
master_rgb = Image.new("RGB", master.size, (255, 252, 247))  # warm-white background
master_rgb.paste(master, mask=master.split()[3])

for name, size in IOS_SPECS:
    master_rgb.resize((size, size), Image.LANCZOS).save(IOS_APPICON / name)

print("done")
