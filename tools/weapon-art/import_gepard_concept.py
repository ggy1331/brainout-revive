"""Extract the approved Gepard image; no generation, repainting or palette edits.

Full-resolution pieces retain the source RGB exactly. Game textures are reduced
16x on one pixel grid shared by all parts (whole-pixel positions, hard alpha edge,
shared palette), plus a lengthened 45-round magazine; Cobra and PBS sprites come
from the Bizon.
Run from the checkout using Python with Pillow.
"""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter
from import_xm8_concept import connected_mask, polygon_mask

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/weapon-art/reference/gepard-approved.png"
GAME = ROOT / "data/packages/base/textures/GAME"
OUT = ROOT / "build/gepard-import"
SCALE = 1 / 16
ORIGIN = (865, 520)
CROP = (20, 90, 1730, 875)


COLORS = 28
ALPHA_CUT = 120
# the pixel grid: concept pixel (GRID_OX + 16 i, GRID_OY + 16 j) starts game pixel (i, j);
# GRID_X / GRID_Y = unit coordinates of game pixel (0, 0)'s left / top edge
GRID_OX, GRID_OY = ORIGIN[0] % 16, ORIGIN[1] % 16
GRID_X, GRID_Y = (GRID_OX - ORIGIN[0]) // 16, (ORIGIN[1] - GRID_OY) // 16
RECEIVER_REAR = 590   # concept x of the back of the receiver (the stock starts behind it)
MUZZLE_DEVICE = 1500  # concept x where the muzzle device starts
BORE_Y = 268          # concept y of the bore axis
MAG_SPLIT = 760       # concept y where the magazine is lengthened
MAG_EXTRA = 112       # concept rows added: 45 rounds instead of 30 (+7 game px)
MAG_SLOPE = -0.38     # concept px left per row down the magazine (its forward tilt)
# room below the concept (895 px tall) for the longer magazine
GRID_W, GRID_H = (1756 - GRID_OX) // 16, (895 + MAG_EXTRA - GRID_OY) // 16 + 1


def position(x, y):
    return {"x": round((x - ORIGIN[0]) * SCALE, 6), "y": round((ORIGIN[1] - y) * SCALE, 6)}


def reduce_on_grid(rgba):
    """Concept-sized RGBA -> game-sized RGBA on the shared grid, hard alpha edge."""
    box = (GRID_OX, GRID_OY, GRID_OX + GRID_W * 16, GRID_OY + GRID_H * 16)
    small = rgba.crop(box).resize((GRID_W, GRID_H), Image.Resampling.BOX)  # RGBA BOX = premultiplied
    px = small.load()
    for y in range(GRID_H):
        for x in range(GRID_W):
            r, g, b, a = px[x, y]
            px[x, y] = (0, 0, 0, 0) if a < ALPHA_CUT else (r, g, b, 255)
    rgb = small.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=2))
    out = rgb.convert("RGBA")
    out.putalpha(small.getchannel("A"))
    return out


def extend_magazine(rgba, bounds):
    """45-round magazine: the 30-round one with MAG_EXTRA rows repeated at MAG_SPLIT,
    each repeated row shifted along the magazine's tilt."""
    out = Image.new("RGBA", (rgba.width, rgba.height + MAG_EXTRA))
    out.paste(rgba.crop((0, 0, rgba.width, MAG_SPLIT)), (0, 0))
    row = rgba.crop((0, MAG_SPLIT, rgba.width, MAG_SPLIT + 1))
    for k in range(MAG_EXTRA):
        out.alpha_composite(row, (round(MAG_SLOPE * k), MAG_SPLIT + k))
    lower = rgba.crop((0, MAG_SPLIT, rgba.width, rgba.height))
    out.alpha_composite(lower, (round(MAG_SLOPE * MAG_EXTRA), MAG_SPLIT + MAG_EXTRA))
    return out


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
    native_preview = Image.new("RGBA", (GRID_W, GRID_H))
    records = []
    layers = []
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
        layers.append((slot, key, name, rgba))
        if slot == "clip":
            layers.append((slot, "extended", "gepard-clip-extended", extend_magazine(rgba, bounds)))
        records.append({"name": name, "bounds": bounds})
    # Game sprites: every part is reduced on ONE pixel grid anchored at ORIGIN,
    # so all parts and attachment positions sit on whole game pixels (root 0.4,
    # 1 sprite px = 1 unit). Hard alpha edge and one shared palette, as for the
    # XM8 / OSV-96: the soft edges and fractional sizes of the first import
    # (71.69x33.81 units for a 72x34 sprite) made the gun shimmer.
    reduced = [(slot, key, name, reduce_on_grid(rgba)) for slot, key, name, rgba in layers]
    opaque = [p[:3] for *_, im in reduced for p in im.getdata() if p[3]]
    sample = Image.new("RGB", (len(opaque), 1))
    sample.putdata(opaque)
    palette = sample.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT)
    for slot, key, name, im in reduced:
        q = im.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE).convert("RGBA")
        q.putalpha(im.getchannel("A"))
        box = q.getbbox()
        native = q.crop(box)
        native.save(GAME / f"{name}.png")
        native_preview.alpha_composite(native, box[:2])
        w, h = native.size
        left_unit, top_unit = box[0] + GRID_X, GRID_Y - box[1]
        attachments.setdefault(slot, {})[key] = {"name": name, "x": left_unit + w / 2, "y": top_unit - h / 2, "width": w, "height": h}
        if slot == "body":
            body_top = top_unit
    # Attachments from other guns, placed on the same whole-pixel grid.
    # Cobra (as on the AKM: left edge 3 px behind the receiver rear, mark 6 px above the body top).
    cobra_left = round((RECEIVER_REAR - ORIGIN[0]) * SCALE) + 3
    attachments["scope"] = {"cobra": {"name": "bizon-scope-cobra", "x": cobra_left + 10.5, "y": body_top + 6 - 10.5, "width": 21, "height": 21}}
    # PBS from the Bizon: starts where the muzzle device starts, centred on the bore.
    sil_left = round((MUZZLE_DEVICE - ORIGIN[0]) * SCALE)
    sil_top = round((ORIGIN[1] - BORE_Y) * SCALE + 4)
    attachments["silencer"] = {"on": {"name": "bizon-silencer", "x": sil_left + 17, "y": sil_top - 4, "width": 34, "height": 8}}
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
        "slots": [{"name": s, "bone": "root", "attachment": k} for s, k in [("butt", "default"), ("body", "body"), ("clip", "default")]]
                 + [{"name": s, "bone": "root"} for s in ("scope", "silencer")],
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
    (OUT / "provenance.json").write_text(json.dumps({"source": str(SOURCE.relative_to(ROOT)), "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(), "scale": SCALE, "origin": ORIGIN, "hires_visible_rgb_exact": True, "game_reduction": "one 16x pixel grid anchored at ORIGIN, premultiplied BOX, hard alpha edge, shared 28-colour palette", "parts": records}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
