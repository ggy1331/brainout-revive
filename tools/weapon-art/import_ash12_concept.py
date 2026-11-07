"""Direct image import of the approved worn ASh-12 and reference suppressor.

No image generation or repainting. High-resolution source pixels are preserved;
game sprites are alpha-aware BOX reductions. Run with the project's Pillow Python.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageChops, ImageFilter
from import_xm8_concept import connected_mask, polygon_mask

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / 'tools/weapon-art/reference'
GAME = ROOT / 'data/packages/base/textures/GAME'
OUT = ROOT / 'build/ash12'
# The model is 85% of the first import. The reduction is baked into the
# sprites (SIZE) and the skeleton keeps the native weapon scale 0.4, so one
# sprite pixel is exactly one game pixel, like every original weapon. Scaling
# the root instead (0.34) made the pixels shimmer.
SIZE = .85
SCALE = SIZE / 16
WORLD_SCALE = .4
ORIGIN = (1080, 510)
CROP = (45, 20, 1990, 751)


def point(x, y):
    return {'x': (x - ORIGIN[0]) * SCALE, 'y': (ORIGIN[1] - y) * SCALE}


def snapped(left, top, width, height):
    """Attachment centre for a sprite whose top-left corner sits on a whole pixel."""
    x = round((left - ORIGIN[0]) * SCALE)
    y = round((ORIGIN[1] - top) * SCALE)
    return {'x': x + width / 2, 'y': y - height / 2, 'width': width, 'height': height}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(REF / 'ash12-approved.png').convert('RGB')
    crop = source.crop(CROP)
    seeds = [(0, 0), (crop.width-1, crop.height-1)]
    seeds += [(x-CROP[0], y-CROP[1]) for x,y in [(1100,150),(950,485),(1230,420)]]
    background = connected_mask(crop, seeds, lambda p: 8 <= min(p) and max(p) <= 44 and max(p)-min(p) <= 20)
    foreground = connected_mask(ImageChops.invert(background), [(1000-CROP[0],300-CROP[1])], lambda p:p>0)
    alpha = Image.new('L', source.size)
    alpha.paste(foreground, CROP[:2])
    # Exclude presentation drop-shadows using the actual weapon contour.
    silhouette = polygon_mask(source.size, [(60,580),(70,215),(135,198),(835,205),(847,90),(875,29),(902,31),(920,61),(1336,61),(1344,181),(1757,182),(1758,38),(1817,37),(1827,245),(1967,244),(1977,258),(1978,335),(1960,350),(1823,350),(1817,433),(1642,449),(1633,658),(1610,672),(1556,670),(1536,644),(1537,448),(1300,444),(1296,474),(1150,481),(1133,640),(1102,660),(1028,643),(974,590),(1033,421),(1009,375),(837,376),(831,431),(878,704),(653,724),(613,449),(585,449),(565,441),(438,439),(332,564),(157,568),(142,582)])
    alpha = ImageChops.multiply(alpha, silhouette)
    magazine = polygon_mask(source.size, [(614,444),(817,410),(883,705),(650,725)])
    body = ImageChops.invert(magazine)
    attachments = {}
    assembled = Image.new('RGBA', source.size)
    records=[]
    for slot,key,name,mask in [('body','body','ash12-skin',body),('clip','default','ash12-clip-default',magazine)]:
        mask=ImageChops.multiply(mask,alpha);bounds=mask.getbbox()
        rgba=source.convert('RGBA');rgba.putalpha(mask);piece=rgba.crop(bounds)
        piece.save(REF/(name+'-hires.png'))
        native=piece.resize((max(1,round(piece.width*SCALE)),max(1,round(piece.height*SCALE))),Image.Resampling.BOX)
        native.save(GAME/(name+'.png'));assembled.alpha_composite(piece,bounds[:2])
        if slot == 'body':
            rail = native.copy()
            pixels = rail.load()
            # Preserve the original receiver and front sight; remove only the
            # carry handle/rear sight above its base, then expose a low rail.
            x0, x1, base = round(48*SIZE), round(82*SIZE), round(10*SIZE)
            for x in range(x0, x1):
                for y in range(base+1):
                    pixels[x,y] = (0,0,0,0)
            for x in range(x0, x1+1):
                pixels[x,base] = (42,42,52,255)
                pixels[x,base-1] = (108,108,118,255) if x % 3 == 0 else (24,24,32,255)
            rail.save(GAME/'ash12-skin-rail.png')
        l,t,r,b=bounds
        attachments[slot]={key:{'name':name,**snapped(l,t,*native.size)}}
        if slot == 'body':
            attachments['body']['rail'] = {**attachments[slot][key], 'name':'ash12-skin-rail'}
        records.append({'name':name,'bounds':bounds,'native_size':native.size})
    assert assembled.getchannel('A').tobytes()==alpha.tobytes()
    diff=ImageChops.difference(assembled.convert('RGB'),source)
    assert ImageChops.multiply(diff,alpha.convert('RGB')).getbbox() is None
    photo=Image.open(REF/'ash12-suppressor-reference.png').convert('RGBA').crop((625,111,783,171))
    # Exclude the light photograph fringe before downsampling: otherwise its
    # bright edge becomes a white line along the bottom of the small sprite.
    a=photo.convert('L').point(lambda v:255 if v<125 else 0)
    a=a.filter(ImageFilter.MinFilter(3));photo.putalpha(a)
    bounds=a.getbbox();photo=photo.crop(bounds)
    # Retain the shape and light/dark pattern, but match the receiver's cool
    # graphite-grey material instead of the photograph's olive-brown cast.
    pixels=photo.load()
    for y in range(photo.height):
        for x in range(photo.width):
            r,g,b,opacity=pixels[x,y]
            tone=(.2126*r+.7152*g+.0722*b)*.95+4
            pixels[x,y]=(min(255,round(tone*.95)),min(255,round(tone*.96)),min(255,round(tone*1.08)),opacity)
    photo.save(REF/'ash12-silencer-hires.png')
    sw, sh = round(30*SIZE), round(10*SIZE)
    photo.resize((sw,sh),Image.Resampling.BOX).save(GAME/'ash12-silencer.png')
    # Same place as before (first import: centre 61.0, 13.375 at full size),
    # left/top edge snapped to the pixel grid.
    sx, sy = round(61.0*SIZE - 15*SIZE), round(13.375*SIZE + 5*SIZE)
    attachments['silencer']={'on':{'name':'ash12-silencer','x':sx+sw/2,'y':sy-sh/2,'width':sw,'height':sh}}
    # Stock G36C Aimpoint sprite (21x11, native): its bottom rests on the rail.
    ax, ay = round(point(1100,190)['x'] - 10.5), round(point(1100,190)['y'] + 11)
    attachments['scope']={'aimpoint':{'name':'g36c-scope-aimpoint','x':ax+10.5,'y':ay-5.5,'width':21,'height':11}}
    l,t,r,b=alpha.getbbox()
    skeleton={
        'skeleton':{'hash':'ash12-approved-worn','spine':'4.0.36',**{k:v*WORLD_SCALE for k,v in point(l,b).items()},'width':(r-l)*SCALE*WORLD_SCALE,'height':(b-t)*SCALE*WORLD_SCALE,'images':'../../../textures/GAME/','audio':''},
        'bones':[
            {'name':'root','scaleX':WORLD_SCALE,'scaleY':WORLD_SCALE},
            {'name':'center-bone','parent':'root',**point((l+r)/2,(t+b)/2)},
            {'name':'fire-bone','parent':'root',**point(900,296),'length':(1970-900)*SCALE*WORLD_SCALE,'scaleX':1/WORLD_SCALE,'scaleY':1/WORLD_SCALE},
            {'name':'shell-bone','parent':'root',**point(790,327),'rotation':90,'length':1.8,'scaleX':1/WORLD_SCALE,'scaleY':1/WORLD_SCALE},
            {'name':'hook-bone','parent':'root',**point(940,243),'length':5,'scaleX':1/WORLD_SCALE,'scaleY':1/WORLD_SCALE},
        ],
        'slots':[{'name':'body','bone':'root','attachment':'body'},{'name':'clip','bone':'root','attachment':'default'},{'name':'silencer','bone':'root'},{'name':'scope','bone':'root'}],
        'skins':[{'name':'weapon-default','attachments':attachments}],
        'animations':{'animation':{}},
    }
    (ROOT/'data/packages/base/contents/content/animations/weapon-ash12.json').write_text(json.dumps(skeleton,indent=1)+'\n',encoding='utf-8')
    assembled.crop(alpha.getbbox()).save(OUT/'ash12-extracted.png')
    for filename,color in [('on-light.png','#eeeeee'),('on-dark.png','#2a2d32')]:
        preview=Image.new('RGBA',source.size,color);preview.alpha_composite(assembled);preview.crop(CROP).convert('RGB').save(OUT/filename)
    (OUT/'image-provenance.json').write_text(json.dumps({'source_sha256':hashlib.sha256((REF/'ash12-approved.png').read_bytes()).hexdigest(),'scale':SCALE,'origin':ORIGIN,'hires_visible_rgb_exact':True,'parts':records},indent=2)+'\n',encoding='utf-8')
    print(records)


if __name__=='__main__':main()
