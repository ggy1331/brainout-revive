"""Read packed sprites and check real alpha contact, including barrel combinations."""
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
import json,re
ROOT=Path(__file__).resolve().parents[2]
with ZipFile(ROOT/'bin/client/packages/base.zip') as z:
    atlas=z.read('content/textures/GAME.atlas').decode()
    page=Image.open(z.open('content/textures/vanguard-modules.png')).convert('RGBA')
    content=json.loads(z.read('content.json'))['content']
    regions={}
    for match in re.finditer(r'([^\n]+)\n  rotate: false\n  xy: (\d+), (\d+)\n  size: (\d+), (\d+)',atlas):
        name,x,y,w,h=match.groups()
        if name.startswith('vg-'):regions[name]=page.crop((int(x),int(y),int(x)+int(w),int(y)+int(h)))
    total=0;failures=[]
    for weapon in ('stg','mp40'):
        model=json.loads(z.read('content/animations/weapon-'+weapon+'.json'))
        bones={b['name']:(b.get('x',0),b.get('y',0)) for b in model['bones']}
        # Compare in root-local pixel coordinates. Its global transform applies
        # equally to every part, including the children used for muzzle/grip.
        bones['root']=(0,0)
        slots={s['name']:s['bone'] for s in model['slots']}
        ox,oy=(-35.2,19.06) if weapon=='stg' else (-7.48,17)
        def pixels(a,slot,offsets={}):
            im=regions[a.get('path',a['name'])];bx,by=bones[slots[slot]]
            offset=offsets.get(slots[slot],{});bx+=offset.get('x',0);by+=offset.get('y',0)
            left=round(a['x']+bx-a['width']/2-ox)
            top=round(oy-a['y']-by-a['height']/2)
            return {(left+x,top+y) for y in range(im.height) for x in range(im.width) if im.getpixel((x,y))[3]}
        def contact(part,host,label):
            global total
            total+=1
            # Shared edge is contact, diagonal-only pixels are not a mounting joint.
            hits=sum((x,y) in host or any(p in host for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))) for x,y in part)
            if hits<2:failures.append((label,hits))
        for skin in model['skins']:
            a=skin['attachments']
            if 'body' not in a:continue
            body=pixels(a['body']['default'],'body')
            native=Image.open(ROOT/'data/packages/base/textures/GAME'/(weapon+'-skin.png')).convert('RGBA')
            rows=[y for y in range(native.height) if native.getpixel((native.width-1,y))[3]]
            expected_axis=oy-(min(rows)+max(rows)+1)/2
            assert abs(bones['vg-tip'][1]-expected_axis)<.001, (weapon,'native muzzle axis')
            for key,attachment in a['silencer'].items():
                assert attachment['y']==0, (key,'muzzle device must share bore axis')
            for slot in ('butt','barrel','scope','rear-grip','clip'):
                for key,part in a[slot].items():
                    if key=='default':continue
                    contact(pixels(part,slot),body,(weapon,skin['name'],key))
            for barrel_key,barrel in a['barrel'].items():
                offsets={} if barrel_key=='default' else content[barrel_key]['components'][0]['boneOffsets']
                front=pixels(barrel,'barrel')
                for slot in ('grip','silencer'):
                    for key,part in a[slot].items():
                        contact(pixels(part,slot,offsets),front|body,(weapon,skin['name'],barrel_key,key))
    for failure in failures:print('DISCONNECTED',failure)
    assert not failures, f'{len(failures)} disconnected combinations'
    print('ATTACHMENT_CONNECTIONS_PASS',total,'mounts and barrel combinations, all skins')
