"""Weapon-specific artwork and deterministic conversion to native sprite assets.

STG: native-grid drawings and adaptations of this game's own component artwork.
MP40: original generated parts atlas and native-game optical bodies re-fitted to
compact MP40 mounts. Each weapon and skin has its own colour palette.
"""
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
import importlib.util
import json

HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[1]/'data/packages/base/textures/GAME'
COUNTS={'barrel':4,'butt':5,'clip':4,'silencer':7,'scope':22,'grip':9,'rear-grip':10}
MP_OFFSETS={'barrel':0,'butt':4,'clip':9,'silencer':13,'grip':20,'rear-grip':29}
MP_SIZES={
 'barrel':[(30,12),(37,12),(28,11),(23,11)],
 'butt':[(31,15),(28,14),(5,7),(29,15),(24,13)],
 'clip':[(5,22),(5,31),(9,23),(7,31)],
 'silencer':[(11,5),(12,5),(14,5),(10,6),(25,5),(18,5),(13,6)],
 'grip':[(8,14),(10,7),(8,9),(21,7),(19,9),(11,13),(17,10),(27,6),(9,13)],
 'rear-grip':[(9,14),(10,14),(9,14),(10,14),(9,14),(9,14),(10,14),(9,14),(10,14),(9,14)]}
STG_OPTICS=[(13,13),(25,10),(15,8),(22,10),(17,10),(24,14),(35,7),
 (19,9),(36,12),(11,10),(29,11),(35,8),(24,14),(34,13),
 (19,10),(28,15),(23,14),(35,13),(29,15),(17,10),(13,5),(14,11)]
MP_OPTICS=['ak105-scope-pkas','fg42-scope-optical','ak74m-scope-eotech',
 'famas-scope-eot','scarl-scope-acog','ak74m-scope-eotech-magnified',
 'ar18-scope-extended','ares-shrike-scope-aimpoint','dvl10-scope',
 'fn2000-scope-truglo','m16a3-scope-acog','ak74-scope-pso','ak108-scope-burris',
 'svds-scope-pso','ak105bullpup-scope-elcan','an94-scope-tulpan',
 'bizon-scope-cobra','aac-scope-qd','9a91-scope-optical','augpara-scope-truglo',
 'aac-scope-default','aac-scope-default']
STG_NATIVE_OPTICS=['m3gg-scope-colimator','gewehr43-scope-zf4','rpk16-scope-okp7',
 'galil-scope-elbit','crossbow-scope-acog','fnfal-scope-suit','m98k-scope-optical',
 'hk416-scope-aimpoint','m21-scope-pks','mp9-scope-truglo','garand-scope-m81',
 'mosin-scope-npz','groza-scope-po4x34','m14-scope-redfield','pkm-scope-cobra',
 'lr300-scope-susat','g36c-scope-aimpoint','desert50ae-scope-optical',
 'qbu88-scope-optical','hk21-scope-elcan']

@lru_cache(None)
def load(path):return Image.open(path).convert('RGBA')

def trim(im):
    im=im.copy();im.putalpha(im.getchannel('A').point(lambda a:255 if a>=128 else 0))
    box=im.getbbox()
    if box is None:raise ValueError('Empty sprite')
    return im.crop(box)

def dominant(im):
    """Discard fragments of neighbouring atlas rows before measuring the sprite."""
    im=im.copy();w,h=im.size;alpha=im.getchannel('A').load()
    remaining={(x,y) for y in range(h) for x in range(w) if alpha[x,y]>=160}
    groups=[]
    while remaining:
        seed=remaining.pop();todo=[seed];group=[seed]
        while todo:
            x,y=todo.pop()
            for xy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if xy in remaining:remaining.remove(xy);todo.append(xy);group.append(xy)
        groups.append(group)
    largest=max(map(len,groups));mask=Image.new('L',im.size);pixels=mask.load()
    for group in groups:
        if len(group)<max(8,largest*.015):continue
        for x,y in group:pixels[x,y]=255
    im.putalpha(mask)
    return trim(im)

def fit(im,size):return trim(trim(im).resize(size,Image.Resampling.NEAREST))

def seated_optic(body,weapon):
    """Visible, connected low feet built for this receiver, not a tall donor rail."""
    body=trim(body);w,h=body.size;out=Image.new('RGBA',(w,h+2));out.alpha_composite(body)
    d=ImageDraw.Draw(out)
    for desired in ([w//2] if w<15 else [round(w*.32),round(w*.70)]):
        candidates=[x for x in range(w) if any(body.getpixel((x,y))[3] for y in range(h))]
        x=min(candidates,key=lambda x:abs(x-desired))
        last=max(y for y in range(h) if body.getpixel((x,y))[3])
        colour='#625e55' if weapon=='stg' else '#64645e'
        shadow='#45423c' if weapon=='stg' else '#42423e'
        d.line((x,last,x,h),fill=colour)
        if x+1<w:d.line((x+1,last+1,x+1,h),fill=shadow)
        d.line((max(0,x-1),h+1,min(w-1,x+2),h+1),fill=shadow)
    return trim(out)

@lru_cache(None)
def stg_module():
    spec=importlib.util.spec_from_file_location('stg_workshop',HERE/'stg_workshop.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

@lru_cache(None)
def raw(weapon,slot,index):
    if slot=='scope':return scope(weapon,index)
    if weapon=='stg':return trim(stg_module().draw(slot,index))
    # The source sheet orders the padded stock before the stock-delete cap;
    # the upgrade catalogue orders these two choices the other way around.
    if slot=='butt' and index in (1,2):index=3-index
    source=load(HERE/'art-sources/mp40-parts-v3.png')
    bounds=json.loads((HERE/'art-sources/mp40-parts-v3.json').read_text())[MP_OFFSETS[slot]+index]
    part=dominant(source.crop(bounds))
    if slot in ('barrel','butt','silencer'):part=ImageOps.mirror(part)
    return fit(part,MP_SIZES[slot][index])

@lru_cache(None)
def scope(weapon,index):
    if weapon=='stg':
        if index>=20:return stg_module().iron(index-20)
        part=load(NATIVE/(STG_NATIVE_OPTICS[index]+'.png')).copy()
        # Remove the donor's weapon-specific bracket, retaining the optical body.
        bottom={0:6,1:6,2:7,3:8,4:7,5:9,6:5,7:8,8:8,9:8,
                10:6,11:6,12:7,13:8,14:10,15:8,16:8,17:7,18:10,19:7}[index]
        part=part.crop((0,0,43 if index==18 else part.width,bottom))
        part=trim(part)
        if part.width>38:part=fit(part,(38,max(5,round(part.height*38/part.width))))
        if index in (12,17):
            mini=trim(load(NATIVE/'m3gg-scope-colimator.png'));out=Image.new('RGBA',(part.width,part.height+5))
            out.alpha_composite(part,(0,5));out.alpha_composite(mini,(8,0));part=out
        return seated_optic(part,'stg')
    part=load(NATIVE/(MP_OPTICS[index]+'.png')).copy()
    donor_bottom={0:9,11:10,13:9,15:11,16:10,18:9}
    if index in donor_bottom:part=part.crop((0,0,part.width,donor_bottom[index]))
    if index in (20,21):
        part=part.crop((0,0,7,6) if index==20 else (37,0,44,6))
        if index==21:
            d=ImageDraw.Draw(part);d.rectangle((3,0,5,1),fill='#5a5a54');d.point((4,2),fill='#292824')
    elif index in (12,17):
        body=trim(load(NATIVE/'m16a3-scope-acog.png'))
        mini=trim(part);out=Image.new('RGBA',(body.width+3,body.height+mini.height-1))
        out.alpha_composite(body,(0,mini.height-1));out.alpha_composite(mini,(8 if index==12 else 14,0));part=out
    else:
        part=trim(part)
        max_width=34 if index in (5,8,11,13) else 27
        if part.width>max_width:part=fit(part,(max_width,max(7,round(part.height*max_width/part.width))))
        if part.height>14:part=fit(part,(part.width,14))
    part=trim(part)
    if index>=20:return part
    if index not in donor_bottom and part.height>5:
        part=part.crop((0,0,part.width,part.height-2))
    return seated_optic(part,'mp40')

@lru_cache(None)
def palette(weapon,skin):
    suffix='' if skin=='weapon-default' else '-'+skin.removeprefix('weapon-')
    return tuple(sorted({rgb[:3] for rgb in load(NATIVE/(weapon+'-skin'+suffix+'.png')).getdata() if rgb[3]>=128}))

@lru_cache(None)
def draw(weapon,slot,index,skin='weapon-default'):
    im=raw(weapon,slot,index).copy();colours=palette(weapon,skin);mapping={};pixels=[]
    for r,g,b,a in im.getdata():
        if a<128:pixels.append((0,0,0,0));continue
        rgb=(r,g,b)
        if rgb not in mapping:mapping[rgb]=min(colours,key=lambda c:sum((c[j]-rgb[j])**2 for j in range(3)))
        pixels.append((*mapping[rgb],255))
    im.putdata(pixels);return trim(im)

def export(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    for weapon in ('stg','mp40'):
        for slot,count in COUNTS.items():
            for i in range(count):draw(weapon,slot,i).save(folder/f'vg-{weapon}-{slot}-{i}.png')

if __name__=='__main__':export(HERE/'vanguard-sprites')
