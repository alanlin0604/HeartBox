"""Rebuild Android adaptive launcher icons from brand source PNG.

The previous foreground PNGs filled the full 108dp canvas (logo edge-to-edge),
which lets launcher masks (Pixel circle, Samsung squircle, etc.) crop the
HeartBox cup-and-spoon glyph at the top and bottom. Adaptive icon spec
allows arbitrary masks, so the foreground logo must sit inside the safe
zone (66dp diameter circle in the center 72dp box, ~66% of canvas).

This script regenerates:
  - mipmap-*/ic_launcher_foreground.png  (logo at 65% centered, transparent)
  - mipmap-*/ic_launcher_background.png  (solid brand peach #FFF7ED)
  - mipmap-*/ic_launcher.png              (legacy: logo on peach bg, 80%)
  - mipmap-*/ic_launcher_round.png        (legacy round: same as ic_launcher)

Run: python frontend/scripts/rebuild-android-icons.py
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
BRAND_LOGO = ROOT.parent / 'brand' / 'heartbox-icon-flat-1024.png'
RES = ROOT / 'android' / 'app' / 'src' / 'main' / 'res'

# Adaptive icon canvas sizes per density (108dp × density-multiplier).
ADAPTIVE_SIZES = {
    'mipmap-ldpi':    81,
    'mipmap-mdpi':    108,
    'mipmap-hdpi':    162,
    'mipmap-xhdpi':   216,
    'mipmap-xxhdpi':  324,
    'mipmap-xxxhdpi': 432,
}

# Legacy icon canvas (48dp × density-multiplier).
LEGACY_SIZES = {
    'mipmap-ldpi':    36,
    'mipmap-mdpi':    48,
    'mipmap-hdpi':    72,
    'mipmap-xhdpi':   96,
    'mipmap-xxhdpi':  144,
    'mipmap-xxxhdpi': 192,
}

BACKGROUND_HEX = '#FFF7ED'  # orange-50, warm peach. Visible on any mask shape.
LOGO_RATIO_ADAPTIVE = 0.65  # 65% of canvas — sits inside the 66dp safe zone.
LOGO_RATIO_LEGACY = 0.80    # 80% on the legacy icon (already shaped by mask).


def load_logo() -> Image.Image:
    if not BRAND_LOGO.exists():
        raise SystemExit(f'Brand source missing: {BRAND_LOGO}')
    return Image.open(BRAND_LOGO).convert('RGBA')


def make_foreground(canvas: int, logo: Image.Image) -> Image.Image:
    """Logo inside a transparent canvas, centered at LOGO_RATIO_ADAPTIVE."""
    img = Image.new('RGBA', (canvas, canvas), (0, 0, 0, 0))
    target = int(canvas * LOGO_RATIO_ADAPTIVE)
    resized = logo.resize((target, target), Image.LANCZOS)
    offset = (canvas - target) // 2
    img.paste(resized, (offset, offset), resized)
    return img


def make_background(canvas: int) -> Image.Image:
    """Solid peach square. Mask renders it as whatever shape launcher prefers."""
    return Image.new('RGBA', (canvas, canvas), BACKGROUND_HEX)


def make_legacy(canvas: int, logo: Image.Image) -> Image.Image:
    """Pre-masked classic icon for Android <8 / older launcher fallbacks."""
    bg = Image.new('RGBA', (canvas, canvas), BACKGROUND_HEX)
    target = int(canvas * LOGO_RATIO_LEGACY)
    resized = logo.resize((target, target), Image.LANCZOS)
    offset = (canvas - target) // 2
    bg.paste(resized, (offset, offset), resized)
    return bg


def make_legacy_round(canvas: int, logo: Image.Image) -> Image.Image:
    """Round-masked legacy icon for old launchers that request _round.png."""
    base = make_legacy(canvas, logo)
    mask = Image.new('L', (canvas, canvas), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, canvas - 1, canvas - 1), fill=255)
    out = Image.new('RGBA', (canvas, canvas), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)
    return out


def main():
    logo = load_logo()
    print(f'Loaded brand source: {BRAND_LOGO} ({logo.size})')
    written = 0
    for density, size in ADAPTIVE_SIZES.items():
        d = RES / density
        d.mkdir(parents=True, exist_ok=True)
        make_foreground(size, logo).save(d / 'ic_launcher_foreground.png', optimize=True)
        make_background(size).save(d / 'ic_launcher_background.png', optimize=True)
        legacy_size = LEGACY_SIZES[density]
        make_legacy(legacy_size, logo).save(d / 'ic_launcher.png', optimize=True)
        make_legacy_round(legacy_size, logo).save(d / 'ic_launcher_round.png', optimize=True)
        written += 4
        print(f'  {density}: foreground {size}px, legacy {legacy_size}px [ok]')
    print(f'Wrote {written} icon files.')


if __name__ == '__main__':
    main()
