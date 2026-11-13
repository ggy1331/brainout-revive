"""Check native receiver reconstruction, sprite exports and package checksums."""
from pathlib import Path
from zipfile import ZipFile
import json
import re
import zlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'data/packages/base/textures/GAME'
with ZipFile(ROOT / 'bin/client/packages/base.zip') as archive:
    atlas = archive.read('content/textures/GAME.atlas').decode()
    page = Image.open(archive.open('content/textures/vanguard-modules.png')).convert('RGBA')
    for weapon in ('stg', 'mp40'):
        model = json.loads(archive.read('content/animations/weapon-' + weapon + '.json'))
        for skin in model['skins']:
            if 'body' not in skin['attachments']:
                continue
            suffix = '' if skin['name'] == 'weapon-default' else '-' + skin['name'][7:]
            native = Image.open(ART / (weapon + '-skin' + suffix + '.png')).convert('RGBA')
            result = Image.new('RGBA', native.size)
            ox, oy = (-35.2, 19.06) if weapon == 'stg' else (-7.48, 17)
            for slot in ('butt', 'body', 'barrel', 'rear-grip', 'scope'):
                attachment = skin['attachments'][slot]['default']
                match = re.search(re.escape(attachment['name']) +
                    r'\n  rotate: false\n  xy: (\d+), (\d+)\n  size: (\d+), (\d+)', atlas)
                x, y, width, height = map(int, match.groups())
                image = page.crop((x, y, x + width, y + height))
                result.alpha_composite(image, (round(attachment['x'] - width/2 - ox),
                                               round(oy - attachment['y'] - height/2)))
            # RGB below fully transparent pixels has no visual meaning.
            for original, rebuilt in zip(native.getdata(), result.getdata()):
                assert original == rebuilt or original[3] == rebuilt[3] == 0, (weapon, skin['name'])
            print('NATIVE_APPEARANCE_PASS', weapon, skin['name'])
    hashes = json.loads(archive.read('__H'))
    assert all(zlib.crc32(archive.read(key)) == value for key, value in hashes.items())
    print('PACKAGE_CRC_PASS')

for weapon in ('stg', 'mp40'):
    paths = list((ROOT / 'tools/weapon-art/vanguard-sprites').glob('vg-' + weapon + '-*.png'))
    assert len(paths) == 61
    for path in paths:
        image = Image.open(path).convert('RGBA')
        assert set(image.getchannel('A').getdata()) <= {0, 255}, path
    drum = Image.open(ROOT / 'tools/weapon-art/vanguard-sprites' / ('vg-' + weapon + '-clip-2.png'))
    assert drum.height > drum.width * 1.5, 'Drum must retain its side profile'
print('SPRITE_EXPORTS_PASS 122')
