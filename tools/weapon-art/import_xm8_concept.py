"""Import the approved artwork without repainting or resampling its RGB pixels.

Run from the checkout with a Python environment containing Pillow:
  python tools/weapon-art/import_xm8_concept.py
Only the three visual regions, visual bounds and attachment transforms are written.
Weapon definitions, sound/effect sets, animation states, bones and upgrades stay intact.
"""
from collections import deque
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/weapon-art/reference/xm8-approved.png"
TEXTURES = ROOT / "data/packages/base/textures/GAME"
SKELETON = ROOT / "data/packages/base/contents/content/animations/weapon-xm8.json"
OUTPUT = ROOT / "build/xm8-concept-import"
# One isotropic transform for all three pieces: no silhouette distortion.
SCALE = (83.79 - 23.15) / (1718 - 905)
ORIGIN_X = 905 - 23.15 / SCALE
ORIGIN_Y = 439 + 4.4 / SCALE
CROP = (40, 90, 1735, 665)


def connected_mask(image, seeds, predicate):
    width, height = image.size
    pixels = image.load()
    visited = bytearray(width * height)
    queue = deque(seeds)
    while queue:
        x, y = queue.popleft()
        if not (0 <= x < width and 0 <= y < height):
            continue
        index = y * width + x
        if visited[index] or not predicate(pixels[x, y]):
            continue
        visited[index] = 255
        queue.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
    return Image.frombytes("L", image.size, bytes(visited))


def polygon_mask(size, points):
    mask = Image.new("L", size)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    return mask


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    original = Image.open(SOURCE).convert("RGB")
    cropped = original.crop(CROP)
    # Connected neutral charcoal belongs to the presentation board. The black
    # outline stops this flood at the actual artwork. Explicit seeds reach the
    # enclosed carry-handle and trigger-guard openings without erasing controls.
    seeds = [(0, 0), (cropped.width - 1, cropped.height - 1), (900 - CROP[0], 230 - CROP[1]), (710 - CROP[0], 415 - CROP[1]), (760 - CROP[0], 420 - CROP[1])]
    background = connected_mask(cropped, seeds, lambda p: 18 <= max(p) <= 65 and max(p) - min(p) <= 8)
    foreground = ImageChops.invert(background)
    # Remove isolated board noise; retain the connected complete rifle.
    foreground = connected_mask(foreground, [(1000 - CROP[0], 340 - CROP[1])], lambda p: p > 0)
    alpha = Image.new("L", original.size)
    alpha.paste(foreground, CROP[:2])
    stock_mask = polygon_mask(original.size, [(0, 220), (610, 220), (610, 228), (568, 365), (510, 390), (0, 600)])
    magazine_mask = polygon_mask(original.size, [(837, 442), (950, 433), (1045, 665), (860, 665)])
    magazine_mask = ImageChops.multiply(magazine_mask, ImageChops.invert(stock_mask))
    body_mask = ImageChops.invert(ImageChops.lighter(stock_mask, magazine_mask))
    parts = [
        ("body", "body", "xm8-skin", body_mask),
        ("clip", "default", "xm8-clip-default", magazine_mask),
        ("butt", "default", "xm8-butt-default", stock_mask),
    ]
    data = json.loads(SKELETON.read_text(encoding="utf-8"))
    attachments = data["skins"][0]["attachments"]
    recomposed = Image.new("RGBA", original.size)
    records = []
    for slot, key, name, mask in parts:
        mask = ImageChops.multiply(mask, alpha)
        bounds = mask.getbbox()
        if bounds is None:
            raise RuntimeError(f"Empty {name}")
        rgba = original.convert("RGBA")
        rgba.putalpha(mask)
        piece = rgba.crop(bounds)
        piece.save(TEXTURES / f"{name}.png")
        recomposed.alpha_composite(piece, bounds[:2])
        left, top, right, bottom = bounds
        attachments[slot][key].update({
            "x": round(((left + right) / 2 - ORIGIN_X) * SCALE, 6),
            "y": round((ORIGIN_Y - (top + bottom) / 2) * SCALE, 6),
            "width": round((right - left) * SCALE, 6),
            "height": round((bottom - top) * SCALE, 6),
        })
        records.append({"region": name, "source_bounds": bounds, "source_pixels": piece.size, "attachment": attachments[slot][key]})
    expected = original.convert("RGBA")
    expected.putalpha(alpha)
    assert recomposed.getchannel("A").tobytes() == alpha.tobytes(), "Layer split changed opacity"
    rgb_difference = ImageChops.difference(recomposed.convert("RGB"), original)
    assert ImageChops.multiply(rgb_difference, alpha.convert("RGB")).getbbox() is None, "Layer split changed source pixels"
    attachments["silencer"]["on"]["y"] = round((ORIGIN_Y - 315) * SCALE, 6)
    left, top, right, bottom = alpha.getbbox()
    data["skeleton"].update({
        "x": round((left - ORIGIN_X) * SCALE * 0.4, 6),
        "y": round((ORIGIN_Y - bottom) * SCALE * 0.4, 6),
        "width": round((right - left) * SCALE * 0.4, 6),
        "height": round((bottom - top) * SCALE * 0.4, 6),
    })
    # Keep every bone and animation intact. Only visual attachment rectangles change.
    SKELETON.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    bounds = alpha.getbbox()
    recomposed.crop(bounds).save(OUTPUT / "xm8-extracted.png")
    for color, filename in [((235, 235, 235, 255), "on-light.png"), ((42, 45, 50, 255), "on-dark.png")]:
        preview = Image.new("RGBA", original.size, color)
        preview.alpha_composite(recomposed)
        preview.crop((40, 90, 1735, 665)).save(OUTPUT / filename)
    (OUTPUT / "provenance.json").write_text(json.dumps({
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "scale": SCALE, "origin": [ORIGIN_X, ORIGIN_Y], "parts": records,
        "recomposition_exact": True,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
