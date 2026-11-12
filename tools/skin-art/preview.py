"""Setup-pose preview of player skins from actor.json (no animation, attachment colour ignored).

    python tools/skin-art/preview.py out.png grenadier terror alpha
"""
import json,math,os,sys
from PIL import Image
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A=json.load(open(ROOT+'/data/packages/base/contents/content/animations/actor.json',encoding='utf-8'))
G=ROOT+'/data/packages/base/textures/GAME'
EXTRA=[]  # extra texture dirs searched first
bones={b['name']:b for b in A['bones']}
def mul(m,n):
    a,b,c,d,e,f=m; A_,B,C,D,E,F=n
    return (a*A_+b*D, a*B+b*E, a*C+b*F+c, d*A_+e*D, d*B+e*E, d*C+e*F+f)
def local(x=0,y=0,r=0,sx=1,sy=1):
    c,s=math.cos(math.radians(r)),math.sin(math.radians(r))
    return (c*sx,-s*sy,x, s*sx,c*sy,y)
W={}
def world(n):
    if n in W: return W[n]
    b=bones[n]; m=local(b.get('x',0),b.get('y',0),b.get('rotation',0),b.get('scaleX',1),b.get('scaleY',1))
    if 'parent' in b: m=mul(world(b['parent']),m)
    W[n]=m; return m
def load(name):
    for d in EXTRA+[G]:
        p=d+'/'+name+'.png'
        if os.path.exists(p): return Image.open(p).convert('RGBA')
    return None
SK={s['name']:s for s in A['skins']}
DRAW=['torso-back','backpack','ghand2','gpalm2','gfoot2','gknee2','gleg2','torso','gfoot1','gknee1','gleg1','body','ghead','hat','ghand1','gpalm1']
def render(parts,scale=8,hat=None,out=None,bg=(90,110,90,255)):
    """parts: dict slot->(skinname) or slot->attachment dict"""
    size=100*scale; img=Image.new('RGBA',(size,size),bg)
    for sl in DRAW:
        src=parts.get(sl)
        if src is None: continue
        if isinstance(src,str):
            att=SK[src]['attachments'].get(sl,{})
            key='player-default' if sl!='hat' else hat
            if key not in att: continue
            d=dict(att[key]); 
        else: d=dict(src)
        tex=load(d.get('path') or d.get('name') or 'x')
        if tex is None: continue
        bone=[s['bone'] for s in A['slots'] if s['name']==sl][0]
        m=mul(world(bone),local(d.get('x',0),d.get('y',0),d.get('rotation',0),d.get('scaleX',1),d.get('scaleY',1)))
        w,h=d.get('width',tex.width),d.get('height',tex.height)
        # attachment: image centered, size w,h ; map pixel (u,v) -> local (u - w/2, h/2 - v) *(w/tex.w)
        k=w/tex.width
        img_m=mul(m,(k,0,-w/2, 0,-k,h/2))
        # screen: X = (wx+45)*scale, Y=(45-wy)*scale  (origin offset)
        scr=mul((scale,0,45*scale, 0,-scale,62*scale),img_m)
        a,b,c,dd,e,f=scr; det=a*e-b*dd
        inv=(e/det,-b/det,(b*f-e*c)/det, -dd/det,a/det,(dd*c-a*f)/det)
        layer=tex.transform((size,size),Image.AFFINE,inv,resample=Image.NEAREST)
        img.alpha_composite(layer)
    if out: img.save(out)
    return img
def skin_parts(n): return {sl:n for sl in DRAW}
if __name__=='__main__':
    names=sys.argv[2:]; scale=6
    tiles=[render(skin_parts(n),scale).crop((24*scale,14*scale,68*scale,98*scale)) for n in names]
    from PIL import ImageDraw
    w,h=tiles[0].size; sh=Image.new('RGBA',(len(tiles)*w,h+14))
    for i,t in enumerate(tiles):
        sh.paste(t,(i*w,14)); ImageDraw.Draw(sh).text((i*w+4,0),names[i],fill='white')
    sh.save(sys.argv[1])
