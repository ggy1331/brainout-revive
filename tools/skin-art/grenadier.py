"""Pixel art of the 'grenadier' player skin (built from the silhouettes of terror/raider/sof).

    python tools/skin-art/grenadier.py [OUT]   # writes the 9 GAME textures + the shop icon to OUT
Textures go to data/packages/base/textures/GAME, the icon to textures/ICONS.
"""
import os,sys
from PIL import Image
S=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
G=ROOT+'/data/packages/base/textures/GAME'
OUT=sys.argv[1] if len(sys.argv)>1 else S+'/out'; os.makedirs(OUT,exist_ok=True); NAME='grenadier'
def hx(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))+(255,)
PAL={
 'O':'#170f1a',
 # skin
 'l':'#d8a888','L':'#c48c6c','S':'#a2684e','D':'#784632','t':'#5e4038',
 # headset / mic
 'H':'#1c1b1e','h':'#3e3d42','M':'#2a292c',
 'B':'#3e2a22',  # stubble
 'E':'#170f1a',
 # scarf
 's':'#4c4a44','X':'#6e6a5e','T':'#8e897a','r':'#9a5530',
 # tee
 'k':'#1f1d22','K':'#2e2c32',
 # carrier
 'p':'#3c3e40','P':'#55585a','Q':'#6c7072','q':'#888c8c',
 'y':'#c8a020','Y':'#e8cc48',
 # belt
 'b':'#2a2a2e','n':'#232126','N':'#302e33','m':'#8a8c8e',
 # gloves
 'g':'#262220','G':'#a26c38','J':'#c68c4c','w':'#3a3a3e',
}
def grid(rows,origin,size):
    im=Image.new('RGBA',size,(0,0,0,0)); px=im.load(); ox,oy=origin
    w=len(rows[0])
    for y,r in enumerate(rows):
        assert len(r)==w,(y,r,len(r),w)
        for x,c in enumerate(r):
            if c!='.': px[ox+x,oy+y]=hx(PAL[c])
    return im
HEAD=[
"..OOOOOOO..",
".OHHSLLlLO.",
".OHSSSLllLO",
"ODHSSSSLLLO",
"ODHSSSSLLLL",
"OHHHSSSLLLL",
"OHhHSSSDDSO",
"OHhHSSLELSO",
"OHHHMSSLLLL",
"ODSSSMMMMSO",
".ODBBSBBBSO",
".OXXsXXsXXO",
"..sXTXXsTX.",
"...XXsXTXO.",
".....OOOO..",
]
BODY=[
".......OXTTXXO.......",
"....OOsXTTXXTXXO.....",
"..OkksXXTXXTXXsXO....",
".OkKkksXXsXrXsKkkkO..",
".OPPPOkkPPkkkkkPPkO..",
"OPQQPPOkPQkKKKkPQPkO.",
"OPpPpPpOPQQQQQQQQQPO.",
"OPPPPPPOPQPPPPPPPQPO.",
"OPpPpPpOPQPPPPyYPPPO.",
"OPPPPPPOPQPPPPyyPPPO.",
"OPpPpPpOPQPPPPPPPPPO.",
"OPPPPPPOPQPPPPPPPPPO.",
"OPpPpPpOPPpppppppPPO.",
"OPPPPPPOPOOOOOOOOOOO.",
"OPPPPPPOPQPQQPQQPQQO.",
"OPpPpPOQQQPQrQPQrQPQO",
"OPPPPPOQPPPQPPPQPPPQO",
"OPpPpPOQPPPQPPPQPPPQO",
"OPPPPPOQPPPQPPPQPPPQO",
".OpPpPOQPpPQPpPQPpPQO",
"OPPPPPOPpppPpppPpppPO",
"ObbbbbbbbbbbmmbbbbbbO",
"ObNNNNNNNNNNmmNNNNNbO",
"OnNNnnOnnnnnnnnnnnnnO",
"OnNNnnOnnNnnnnnnnNnnO",
"OnnnnnOnnnnnnnnnnnnnO",
".OnnnnOnnnnnO.....OnO",
"......OOOOOOO.....OOO",
]
HAND=[
"....KKkk...........",
"..KKKKkkkLLSLLSSD..",
".KKKKKkkkLLtLLStSD.",
"kKKKKkkkSLtLLttLSDD",
"kkKKkkkkSLLtLSLSSDD",
".kkkkkkkSSStSSSSSDD",
".OkkkkkODDDDDDDDD..",
"..OOOOOOOO.........",
]
PALM=[
"LLSSLLSD...gGGg..",
"LtLLtLLSwwgGJJGgg",
"LLtLLLtSwwgGGJGgg",
"SSSttSSDwwgggGgg.",
"DSSSSDDDwwgggggg.",
".DDDDD.....gggg..",
]
def recolor(src,mp):
    im=Image.open(f'{G}/{src}.png').convert('RGBA'); px=im.load()
    for y in range(im.height):
        for x in range(im.width):
            p=px[x,y]
            if p[3]:
                k='#%02x%02x%02x'%p[:3]
                if k in mp: px[x,y]=hx(mp[k])[:3]+(p[3],)
    return im
def save(im,part): im.save(f'{OUT}/player-default-{part}-{NAME}.png')
save(grid(HEAD,(11,8),(32,32)),'head')
save(grid(BODY,(7,3),(32,32)),'body')

SKIN={'#d9b69e':PAL['L'],'#d4a38f':PAL['S'],'#bd7870':'#8e5a44'}
hand=recolor('player-default-hand-terror',SKIN); hp=hand.load()
for y in range(32):
    for x in range(9,9+7):
        if hp[x,y][3]: hp[x,y]=hx(PAL['K'] if y<=13 else PAL['k'])
for (x,y) in [(9+10,11+2),(9+11,11+3),(9+14,11+3)]: hp[x,y]=hx(PAL['t'])
save(hand,'hand')
palm=recolor('player-default-palm-terror',dict(SKIN,**{'#282828':PAL['g'],'#494949':PAL['J']}))
pp=palm.load()
for y in range(32):
    for x in range(13+8,13+10):
        if pp[x,y][3] and pp[x,y][:3]==hx(PAL['O'])[:3]: pp[x,y]=hx(PAL['w'])
for (x,y) in [(13+3,14+1),(13+4,14+2)]: pp[x,y]=hx(PAL['t'])
save(palm,'palm')
# legs: recolor sof
PANTS={'#171413':'#1a171b','#292a2f':'#2b292e','#3c3c41':'#3e3b40','#27271c':'#2b292e','#373b33':'#3e3b40','#4d5255':'#4c494e','#323d3f':'#2f2d32','#252c33':'#222024','#596064':'#45434a','#252729':'#222024'}
BOOT={'#171413':'#1b1512','#292a2f':'#33271e','#3c3c41':'#4a3a2a'}
def patch(im,origin,rows,pal):
    px=im.load(); ox,oy=origin
    for y,r in enumerate(rows):
        for x,c in enumerate(r):
            if c!='.' and px[ox+x,oy+y][3]: px[ox+x,oy+y]=hx(pal[c])
    return im
RUST={'r':'#6b3a22','R':'#8a4e2c'}
# rust patch on the front (top rows) of the thigh, near the knee end (right)
LEGP=["RRRR","rRRR","rrRr"]
leg2=recolor('player-default-leg-sof2',PANTS); patch(leg2,(11+13,9+1),LEGP,RUST); leg2.save(f'{OUT}/player-default-leg-{NAME}2.png')
leg=recolor('player-default-leg-sof',PANTS); patch(leg,(11+13,9+1),LEGP,RUST); save(leg,'leg')
save(recolor('player-default-knee-sof',PANTS),'knee')
save(recolor('player-default-foot-sof',BOOT),'foot')
save(recolor('player-default-torso-sof',PANTS),'torso')
print('ok')
# icon: front view, recolored from the terror icon
ICON={'#282828':'#45474a','#353e3d':'#55585a','#5b665e':'#6c7072','#69756c':'#888c8c','#2c3831':'#3c3e40','#282723':'#3a3b3d',
      '#2f4e31':'#2b292e','#33321e':'#6e6a5e','#56533d':'#8e897a','#8c1800':'#4c4a44','#dc605d':'#9a5530'}
ic=Image.open(ROOT+'/data/packages/base/textures/ICONS/icon-player-skin-terror.png').convert('RGBA'); ip=ic.load()
for y in range(ic.height):
    for x in range(ic.width):
        p=ip[x,y]
        if p[3]:
            k='#%02x%02x%02x'%p[:3]
            if k in ICON: ip[x,y]=hx(ICON[k])[:3]+(p[3],)
ic.save(f'{OUT}/icon-player-skin-{NAME}.png')
ip=ic.load()
for (x,y) in [(42,27),(43,27),(42,28),(43,28)]: ip[x,y]=hx(PAL['y'])
ip[43,27]=hx(PAL['Y'])
ic.save(f'{OUT}/icon-player-skin-{NAME}.png')
