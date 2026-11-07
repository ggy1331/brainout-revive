"""Extract the approved Gepard image; no generation, repainting or palette edits.

Full-resolution pieces retain the source RGB exactly. Game textures are direct
premultiplied BOX reductions of these same pieces, without the XM8 hand fixes.
Run from the checkout using Python with Pillow.
"""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops
from import_xm8_concept import connected_mask, polygon_mask

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/weapon-art/reference/gepard-approved.png"
GAME = ROOT / "data/packages/base/textures/GAME"
OUT = ROOT / "build/gepard-import"
SCALE = 1 / 16
ORIGIN = (865, 520)
CROP = (20, 90, 1730, 875)


def position(x, y):
    return {"x": round((x - ORIGIN[0]) * SCALE, 6), "y": round((ORIGIN[1] - y) * SCALE, 6)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGB")
    crop = source.crop(CROP)
    seeds = [(0, 0), (crop.width - 1, crop.height - 1), (700 - CROP[0], 450 - CROP[1]), (1050 - CROP[0], 400 - CROP[1])]
    background = connected_mask(crop, seeds, lambda p: 14 <= min(p) and max(p) <= 45 and max(p) - min(p) <= 16)
    foreground = connected_mask(ImageChops.invert(background), [(1000 - CROP[0], 300 - CROP[1])], lambda p: p > 0)
    alpha = Image.new("L", source.size)
    alpha.paste(foreground, CROP[:2])
    # The dark collar below the front sight shares the board's colour and has
    # a gap in its outline. Retain its original pixels explicitly, without fill.
    collar = polygon_mask(source.size, [(1452, 241), (1493, 241), (1505, 248), (1505, 305), (1458, 309), (1452, 300)])
    alpha = ImageChops.lighter(alpha, collar)
    stock = polygon_mask(source.size, [(0, 0), (585, 0), (585, 340), (0, 500)])
    magazine = polygon_mask(source.size, [(750, 638), (880, 638), (820, 875), (650, 835)])
    body = ImageChops.invert(ImageChops.lighter(stock, magazine))
    parts = [("body", "body", "gepard-skin", body), ("clip", "default", "gepard-clip-default", magazine), ("butt", "default", "gepard-butt-default", stock)]
    attachments = {}
    assembled = Image.new("RGBA", source.size)
    native_preview = Image.new("RGBA", (round(source.width * SCALE), round(source.height * SCALE)))
    records = []
    for slot, key, name, partmask in parts:
        partmask = ImageChops.multiply(partmask, alpha)
        bounds = partmask.getbbox()
        if not bounds:
            raise RuntimeError(f"Empty part: {name}")
        rgba = source.convert("RGBA")
        rgba.putalpha(partmask)
        piece = rgba.crop(bounds)
        piece.save(ROOT / "tools/weapon-art/reference" / f"{name}-hires.png")
        assembled.alpha_composite(piece, bounds[:2])
        # Pillow's RGBA BOX resize uses associated alpha, avoiding dark board
        # colours bleeding from hidden RGB into visible edge samples.
        native = piece.resize((max(1, round(piece.width * SCALE)), max(1, round(piece.height * SCALE))), Image.Resampling.BOX)
        native.save(GAME / f"{name}.png")
        native_preview.alpha_composite(native, (round(bounds[0] * SCALE), round(bounds[1] * SCALE)))
        left, top, right, bottom = bounds
        attachment = {"name": name, **position((left + right) / 2, (top + bottom) / 2), "width": piece.width * SCALE, "height": piece.height * SCALE}
        attachments[slot] = {key: attachment}
        records.append({"name": name, "bounds": bounds, "native_size": native.size, "attachment": attachment})
    assert assembled.getchannel("A").tobytes() == alpha.tobytes()
    difference = ImageChops.difference(assembled.convert("RGB"), source)
    assert ImageChops.multiply(difference, alpha.convert("RGB")).getbbox() is None, "Source pixels changed"
    left, top, right, bottom = alpha.getbbox()
    skeleton = {
        "skeleton": {"hash": "gepard-approved-concept", "spine": "4.0.36", **{k: v * 0.4 for k, v in position(left, bottom).items()}, "width": (right - left) * SCALE * 0.4, "height": (bottom - top) * SCALE * 0.4, "images": "../../../textures/GAME/", "audio": ""},
        "bones": [
            {"name": "root", "scaleX": 0.4, "scaleY": 0.4},
            {"name": "center-bone", "parent": "root", **position((left + right) / 2, (top + bottom) / 2)},
            {"name": "fire-bone", "parent": "root", **position(950, 276), "length": (1712 - 950) * SCALE * 0.4, "scaleX": 2.5, "scaleY": 2.5},
            {"name": "shell-bone", "parent": "root", **position(1000, 247), "rotation": 90, "length": 1.5, "scaleX": 2.5, "scaleY": 2.5},
            {"name": "hook-bone", "parent": "root", **position(850, 170), "length": 5, "scaleX": 2.5, "scaleY": 2.5},
        ],
        "slots": [{"name": s, "bone": "root", "attachment": k} for s, k in [("butt", "default"), ("body", "body"), ("clip", "default")]],
        "skins": [{"name": "weapon-default", "attachments": attachments}],
        "animations": {"animation": {}},
    }
    (ROOT / "data/packages/base/contents/content/animations/weapon-gepard.json").write_text(json.dumps(skeleton, indent=1) + "\n", encoding="utf-8")
    assembled.crop(alpha.getbbox()).save(OUT / "gepard-extracted.png")
    for name, color in [("on-light.png", "#eeeeee"), ("on-dark.png", "#2a2d32")]:
        preview = Image.new("RGBA", source.size, color)
        preview.alpha_composite(assembled)
        preview.crop(CROP).convert("RGB").save(OUT / name)
    native_bg = Image.new("RGBA", native_preview.size, "#2a2d32")
    native_bg.alpha_composite(native_preview)
    native_bg.resize((native_bg.width * 6, native_bg.height * 6), Image.Resampling.NEAREST).convert("RGB").save(OUT / "native-6x.png")
    (OUT / "provenance.json").write_text(json.dumps({"source": str(SOURCE.relative_to(ROOT)), "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(), "scale": SCALE, "origin": ORIGIN, "hires_visible_rgb_exact": True, "game_reduction": "Pillow RGBA BOX; no repainting or palette changes", "parts": records}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
