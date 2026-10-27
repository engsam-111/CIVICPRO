"""Generate CIVICPRO's public home-screen monogram in required PWA sizes."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "icons"
ROOT.mkdir(parents=True, exist_ok=True)
FONT = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
for name, size, maskable in [
    ("icon-192.png", 192, False), ("icon-512.png", 512, False),
    ("maskable-512.png", 512, True), ("apple-touch-icon.png", 180, False),
]:
    image = Image.new("RGB", (size, size), "#d97706")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT, int(size * (0.36 if maskable else 0.42)))
    bounds = draw.textbbox((0, 0), "CP", font=font)
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    draw.text(((size - width) / 2, (size - height) / 2 - bounds[1]), "CP", font=font, fill="white")
    draw.rectangle((size * .3, size * .75, size * .7, size * .79), fill="#0f172a")
    image.save(ROOT / name)