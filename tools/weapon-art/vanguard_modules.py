"""Original side-view STG/MP40 attachments on the native game pixel grid.

The optics atlas was generated with the built-in image tool using native game
sprites as the style reference. Other existing editable pixel drawings were
reworked locally. Native colour quantization and fitting are deterministic.
The package pass owns receiver sockets and native part separation.
"""
from pathlib import Path
from PIL import Image, ImageDraw

# Deep occlusion -> oily shadow -> steel -> worn edges, matching native receivers.
METAL=['#201f1c','#292824','#363530','#44433e','#53524c','#66655e','#77766d','#88877d']
WOOD=['#241e17','#352c20','#493221','#5b391f','#73401a','#875226','#9c6835','#b1854c']
BAKE=['#231e19','#30271c','#3b3023','#49392a','#5d4631','#75583e','#927458','#ae9271']
POLY=['#1c1f1d','#262a27','#343a35','#414747','#4d5350','#646971','#747975','#92958b']

class Pixels:
    def __init__(self,w,h,palette=METAL):
        self.im=Image.new('RGBA',(w,h));self.d=ImageDraw.Draw(self.im);self.p=palette
    def dot(self,x,y,c):self.d.point((x,y),fill=self.p[c] if isinstance(c,int) else c)
    def line(self,xy,c=4,width=1):self.d.line(xy,fill=self.p[c] if isinstance(c,int) else c,width=width)
    def box(self,xy,c=3):self.d.rectangle(xy,fill=self.p[c] if isinstance(c,int) else c)
    def poly(self,xy,c=3):self.d.polygon(xy,fill=self.p[c] if isinstance(c,int) else c)
    def hole(self,xy):self.d.rectangle(xy,fill=(0,0,0,0))
    def screw(self,x,y):
        self.dot(x,y,1);self.dot(x,y-1,5);self.dot(x+1,y,4)
    def tube(self,x0,y0,x1,y1):
        self.box((x0,y0,x1,y1),3)
        self.line((x0+1,y0,x1-1,y0),5)
        if y1-y0>2:self.line((x0+1,y0+1,x1-1,y0+1),4)
        self.line((x0,y1,x1,y1),1)
    def band(self,x,y0,y1):
        self.line((x,y0,x,y1),1);self.line((x+1,y0,x+1,y1),5)
        self.dot(x+1,y1,2)
    def vent(self,x,y,w=3,h=1):
        self.box((x,y,x+w-1,y+h-1),1);self.line((x,y+h,x+w-1,y+h),5)
    def rib(self,x,y,length):
        self.line((x,y,x+length,y),2);self.line((x+1,y+1,x+length,y+1),5)
    def finish(self):return self.im

def barrel(weapon,i):
    # Each silhouette includes its own gas/front-sight assembly and handguard seam.
    if weapon=='stg' and i==0: # short stamped shroud, long exposed pencil barrel
        p=Pixels(32,14);p.tube(0,6,31,9)
        p.poly([(0,3),(13,3),(16,5),(16,11),(0,11)],3)
        p.line((1,3,12,3),6);p.line((1,4,14,4),4);p.line((0,11,15,11),1)
        for x in (3,8,13):p.vent(x,6,2,2)
        p.line((2,9,12,9),2);p.band(16,5,10);p.band(28,5,10)
        p.poly([(26,6),(27,4),(28,4),(28,1),(29,1),(29,6)],3);p.dot(28,1,6)
        p.screw(1,7);p.line((21,7,25,7),6)
    elif weapon=='stg' and i==1: # VDD long pressed sleeve, two rows offset cooling slots
        p=Pixels(48,14);p.tube(0,6,47,9)
        p.poly([(0,3),(31,3),(34,5),(34,10),(29,12),(0,12)],3)
        p.line((1,3,29,3),6);p.line((0,4,32,4),4);p.line((1,11,30,11),2)
        for x in (3,9,15,21,27):p.vent(x,5,4,1)
        for x in (5,12,19,26):p.vent(x,8,4,1)
        p.band(34,4,10);p.line((35,5,43,5),2);p.line((36,6,45,6),5)
        p.poly([(41,6),(42,3),(43,3),(43,0),(44,0),(44,6)],3);p.dot(44,0,6)
        p.band(46,5,10);p.screw(1,8);p.dot(31,10,5)
    elif weapon=='stg' and i==2: # precision, heavy finned barrel and walnut handguard
        p=Pixels(43,15);p.tube(0,6,42,10)
        p.poly([(0,4),(20,4),(23,6),(22,12),(0,12)],WOOD[3])
        p.line((1,4,18,4),WOOD[6]);p.line((1,5,19,5),WOOD[4]);p.line((0,12,21,12),WOOD[1])
        p.line([(3,7),(8,8),(16,7),(19,8)],WOOD[2]);p.line((3,10,15,10),WOOD[5]);p.screw(2,8)
        p.band(22,4,12)
        for x in (26,29,32,35):p.band(x,5,11)
        p.poly([(36,6),(38,3),(39,3),(39,1),(40,1),(40,6)],3);p.dot(40,1,6)
        p.line((24,6,41,6),5);p.band(41,5,11)
    elif weapon=='stg': # rapid: open cage, stepped sleeve and distinctive slotted block
        p=Pixels(27,14);p.tube(0,6,26,9)
        p.poly([(0,4),(10,3),(15,4),(17,6),(15,11),(0,11)],3)
        p.line((1,4,10,3),5);p.line((1,10,13,10),2)
        p.vent(3,6,4,2);p.vent(10,5,3,2);p.dot(13,9,5);p.screw(0,7)
        p.band(17,4,10);p.band(23,5,10);p.line((24,4,24,1),5);p.dot(23,1,3)
        p.line((19,7,22,7),5)
    elif i==0: # MP40 precision: stepped heavy tube, collar, hooded post
        p=Pixels(38,13);p.tube(0,5,37,8);p.tube(0,4,16,10)
        p.line((1,4,15,4),6);p.line((1,9,15,9),2);p.band(17,4,10)
        p.line((20,5,32,5),5);p.band(33,4,9)
        p.line([(28,5),(28,2),(29,1),(32,1),(33,2),(33,5)],4);p.dot(30,3,6)
        p.screw(4,7);p.line((8,6,14,6),2);p.dot(36,6,6)
    elif i==1: # MP40 perforated heat shroud, oval openings and lower reinforcing rib
        p=Pixels(34,15);p.tube(0,6,33,9)
        p.poly([(0,3),(22,3),(25,5),(25,10),(22,12),(0,12)],3)
        p.line((1,3,21,3),6);p.line((1,4,23,4),4);p.line((0,12,21,12),1)
        for x in (3,9,15,21):p.vent(x,6,3,2)
        p.line((2,10,22,10),5);p.band(25,4,11);p.band(31,5,10)
        p.line([(28,5),(28,2),(30,1),(31,2),(31,5)],5);p.screw(0,7)
    elif i==2: # MP40 light, turned barrel with leather heat band
        p=Pixels(27,13);p.tube(0,5,26,8);p.tube(0,4,7,10)
        p.band(8,4,9);p.line((10,5,23,5),6);p.line((11,8,21,8),2)
        for x in (2,4,6):p.line((x,5,x,8),BAKE[3]);p.dot(x,5,BAKE[5])
        p.line([(20,5),(20,2),(23,1),(24,3),(24,5)],4);p.dot(22,3,6);p.band(25,4,9)
    else: # compact MP40 with conical muzzle collar and flat front sight hood
        p=Pixels(22,13);p.tube(0,5,21,9)
        p.poly([(0,3),(8,3),(10,5),(10,10),(0,10)],3)
        p.line((0,3,7,3),5);p.line((2,5,7,5),2);p.screw(2,7);p.band(10,4,10)
        p.poly([(15,5),(17,4),(20,4),(21,5),(21,9),(16,9)],3);p.line((17,4,20,4),6)
        p.line([(15,4),(15,1),(19,1),(19,4)],4);p.dot(17,3,5)
    return p.finish()

def stock(weapon,i):
    # Connection at the extreme right, bore-facing upper edge.
    if (weapon=='stg' and i==2) or (weapon=='mp40' and i==1):
        p=Pixels(5,10);p.box((2,2,4,8),2);p.line((2,2,4,2),5);p.line((1,3,1,7),3);p.screw(3,5);return p.finish()
    if i==0:
        p=Pixels(31 if weapon=='stg' else 33,20);w=p.im.width
        p.tube(w-7,4,w-1,8);p.screw(w-4,6)
        p.line([(w-6,6),(5,5),(3,7),(1,17),(3,18),(w-9,10)],2,width=2)
        p.line([(w-6,5),(5,4),(3,6),(1,16)],5)
        p.line([(3,18),(7,16),(w-10,10)],4)
        p.line((4,9,3,16),3);p.dot(2,18,1);p.band(w-8,4,9)
        if weapon=='mp40':p.line((7,6,w-12,7),3);p.dot(w-10,9,6)
    elif (weapon=='stg' and i==1) or (weapon=='mp40' and i==3):
        p=Pixels(29,18,POLY);p.tube(19,4,28,7)
        p.poly([(22,4),(18,3),(4,2),(2,3),(1,16),(5,16),(14,11),(22,10)],3)
        p.line([(4,2),(17,3),(21,4)],5);p.line([(4,15),(12,11),(20,9)],2)
        p.poly([(7,7),(16,7),(13,10),(7,12)],1)
        p.line((7,7,15,7),4);p.line((2,4,1,15),1);p.line((3,5,2,13),4)
        p.screw(18,7);p.screw(4,5);p.band(23,4,8)
        if weapon=='mp40':p.line((7,3,14,4),BAKE[3]);p.dot(14,4,BAKE[5])
    elif weapon=='stg' and i==3:
        p=Pixels(34,21,WOOD)
        p.poly([(33,4),(27,4),(19,7),(6,4),(2,3),(0,18),(3,20),(10,17),(23,12),(33,10)],3)
        p.poly([(3,4),(8,5),(20,8),(28,5),(32,5),(32,7),(22,11),(9,14),(2,16)],4)
        p.line([(3,4),(9,6),(20,8),(28,5)],6)
        p.line([(3,18),(11,15),(21,12),(30,9)],2)
        p.line([(5,9),(10,9),(15,11),(22,10)],3);p.line([(5,13),(10,11),(16,12)],5)
        p.line((1,5,0,17),1);p.line((2,6,1,16),METAL[4]);p.screw(7,10);p.screw(29,7)
    elif (weapon=='stg' and i==4) or (weapon=='mp40' and i==2):
        p=Pixels(33,22,BAKE)
        p.poly([(32,5),(25,5),(20,7),(5,4),(2,5),(0,19),(5,21),(19,13),(32,11)],3)
        p.poly([(5,5),(18,8),(24,6),(29,6),(29,9),(17,12),(5,17)],4)
        p.line([(5,5),(19,8),(24,6),(29,6)],5);p.line([(6,18),(17,13),(29,10)],2)
        p.poly([(2,4),(5,5),(3,20),(0,19)],METAL[1]);p.line((2,6,1,17),METAL[4])
        p.box((10,8,20,10),2);p.line((11,8,19,8),5);p.screw(25,8)
        for x,y in ((7,12),(11,13),(16,11)):p.dot(x,y,5)
        if weapon=='mp40':p.line((8,7,14,9),METAL[3]);p.line((7,15,12,13),METAL[2])
    else: # MP40 35M wire stock with small wood cheek rest and sling loop
        p=Pixels(31,19);p.tube(23,4,30,8);p.screw(26,6)
        p.line([(24,5),(5,3),(3,5),(1,16),(4,17),(22,10)],3,width=2)
        p.line([(24,4),(5,2),(3,4),(1,15)],5);p.line((4,17,22,10),2)
        p.poly([(7,2),(19,4),(19,6),(6,4)],WOOD[3]);p.line((8,2,18,4),WOOD[5])
        p.line([(6,14),(8,14),(8,16),(6,16),(6,14)],2);p.dot(23,8,6)
    return p.finish()

def muzzle(i):
    # Distinct axial profiles; subdued edge highlights, no cartoon outline.
    sizes=[(13,6),(12,7),(14,6),(11,8),(29,7),(21,6),(16,8)]
    p=Pixels(*sizes[i]);w,h=p.im.size;p.tube(0,h//2-1,4,h//2+1)
    if i==0:
        p.tube(3,1,12,4);p.band(4,0,5);p.vent(7,2,2);p.vent(10,2,1);p.dot(12,1,6)
    elif i==1:
        p.poly([(3,2),(5,0),(10,0),(11,2),(11,5),(5,6),(3,4)],3)
        p.line((5,0,9,0),5);p.vent(6,2,3,1);p.vent(6,4,3,1);p.line((10,2,10,4),1)
    elif i==2:
        p.tube(3,1,13,4);p.band(4,0,5)
        p.line((7,1,12,1),5);p.line((7,3,13,3),0);p.line((8,4,12,4),3);p.dot(13,2,6)
    elif i==3:
        p.poly([(3,2),(5,1),(8,0),(10,1),(10,6),(8,7),(5,6),(3,4)],3)
        p.line((5,1,8,0),6);p.line((6,6,8,6),1);p.band(5,2,5);p.line((9,2,9,5),2)
    elif i==4:
        p.poly([(3,2),(5,0),(26,0),(28,2),(28,5),(26,6),(5,6),(3,4)],3)
        p.line((6,0,25,0),5);p.line((6,1,26,1),4);p.line((6,5,26,5),2);p.line((6,6,25,6),1)
        p.band(7,1,5);p.band(24,1,5);p.line((11,3,15,3),2);p.dot(17,2,5);p.dot(27,2,6)
    elif i==5:
        p.tube(3,0,20,5);p.band(5,0,5);p.band(18,0,5)
        p.line((8,2,16,2),4);p.line((7,4,17,4),2);p.dot(20,1,6)
        p.dot(11,1,5);p.dot(15,3,3)
    else:
        p.poly([(3,2),(5,0),(14,0),(15,1),(15,6),(14,7),(5,7),(3,5)],3)
        p.line((5,0,13,0),6);p.line((5,7,13,7),1)
        for x in (6,10):p.vent(x,2,2,3)
        p.line((14,1,14,6),4);p.dot(15,2,6)
    return p.finish()

def foregrip(i):
    if i==0:
        p=Pixels(13,18,BAKE);p.box((1,0,12,2),METAL[3]);p.line((2,0,11,0),METAL[5])
        p.poly([(4,3),(10,3),(9,16),(7,17),(3,15)],3);p.line((4,4,3,13),5)
        for y in (6,9,12):p.line((5,y,8,y),1);p.dot(5,y+1,4)
        p.dot(7,16,1);p.screw(8,4)
    elif i==1:
        p=Pixels(16,9);p.tube(0,0,15,2);p.poly([(3,3),(10,3),(10,7),(7,8),(5,6)],3)
        p.line([(4,3),(6,6),(8,7)],5);p.line((11,3,14,3),1);p.screw(12,1)
    elif i==2:
        p=Pixels(14,12,POLY);p.tube(0,0,13,2);p.poly([(4,3),(10,3),(9,10),(6,11),(3,9)],3)
        p.line((4,4,3,8),5);p.line((5,9,8,9),1);p.screw(8,4);p.dot(6,7,2)
    elif i==3:
        p=Pixels(23,7);p.box((0,0,6,2),2);p.screw(3,2)
        p.line((4,3,20,3),3);p.line((5,4,21,4),1)
        p.line((5,5,22,5),3);p.line((7,6,22,6),1)
        p.line((18,3,21,3),4)
    elif i==4:
        p=Pixels(24,9);p.tube(2,3,22,7);p.tube(17,2,23,8);p.band(4,2,8);p.band(15,2,8)
        p.box((6,0,13,2),2);p.line((6,0,13,0),5);p.screw(8,1)
        p.line((22,3,22,7),6);p.line((23,4,23,6),7);p.dot(11,4,5)
    elif i==5:
        p=Pixels(15,19,WOOD);p.box((1,0,14,2),METAL[3]);p.line((2,0,13,0),METAL[6])
        p.poly([(6,3),(12,3),(11,8),(7,17),(4,18),(1,15)],3)
        p.line([(6,4),(4,10),(2,14)],5);p.line([(10,4),(9,9),(5,16)],1)
        p.line((5,8,8,10),2);p.line((4,12,6,13),4);p.screw(8,5)
    elif i==6:
        p=Pixels(22,12,POLY);p.tube(0,0,21,2);p.poly([(1,3),(7,3),(15,8),(19,3),(21,3),(18,11),(13,11)],3)
        p.poly([(7,4),(16,9),(17,7),(9,4)],0);p.line([(2,3),(14,10),(17,10)],5)
        p.screw(18,2);p.line((4,1,14,1),4)
    elif i==7:
        p=Pixels(34,9);p.tube(0,2,10,5);p.band(4,1,7);p.line((10,0,10,8),3)
        p.poly([(11,3),(29,3),(33,4),(28,6),(11,6)],4);p.line((12,3,29,3),7)
        p.line((12,5,27,5),2);p.dot(30,4,5);p.screw(3,4)
    else:
        p=Pixels(14,16);p.tube(0,0,13,2);p.poly([(4,3),(10,3),(9,14),(4,15),(2,13)],3)
        p.poly([(5,5),(8,5),(7,11),(4,12)],0);p.line((4,4,3,12),5);p.dot(6,14,5);p.screw(9,2)
    return p.finish()

def magazine(weapon,i):
    # A drum's axle runs along the barrel: its SIDE silhouette is a narrow
    # cylinder, not the round end-cap that the previous drawing showed.
    if i==2:
        p=Pixels(13 if weapon=='stg' else 12,23 if weapon=='stg' else 25)
        w,h=p.im.size
        p.poly([(3,0),(8,0),(8,5),(w-2,7),(w-1,9),(w-1,h-4),
                (w-3,h-1),(2,h-1),(0,h-4),(0,9),(2,7),(3,5)],2)
        p.line((4,0,7,0),4);p.line((4,1,4,5),3)
        p.poly([(2,8),(w-4,7),(w-3,9),(w-3,h-4),(w-5,h-2),(2,h-3)],3)
        p.line([(2,8),(w-4,7),(w-3,8)],4)
        p.line((1,10,1,h-5),1);p.line((w-2,10,w-2,h-5),1)
        for y in (11,15,19):
            if y<h-3:p.line((3,y,w-4,y),2);p.line((3,y+1,w-5,y+1),3)
        p.line((3,h-2,w-4,h-2),1);p.dot(4,8,5)
        return p.finish()
    # Match native feed width, grain and curvature. Extended/short versions
    # change the sheet-metal silhouette, retaining the original game's finish.
    native=Image.open(Path(__file__).resolve().parents[2]/'data/packages/base/textures/GAME'/f'{weapon}-clip-default.png').convert('RGBA')
    if weapon=='mp40':
        h=22 if i==0 else 31;w=5 if i!=3 else 6
        p=Pixels(w,h);p.poly([(1,0),(w-2,0),(w-1,h-2),(w-2,h-1),(1,h-1),(0,3)],2)
        p.line((1,1,1,h-3),3);p.line((w-2,2,w-2,h-3),1)
        p.line((1,h-2,w-2,h-2),4);p.line((1,3,w-2,3),1)
        if i==1:
            p.line((2,6,2,h-5),3);p.dot(3,12,4)
        if i==3:
            for y in (8,15,22):p.dot(3,y,1);p.dot(3,y+1,3)
        return p.finish()
    h=32 if i==0 else 17 if i==1 else 25
    w=15 if i==0 else 10 if i==1 else 13;p=Pixels(w,h)
    bend=h//2
    p.poly([(0,0),(6,0),(7,bend-1),(w-2,h-4),(w-1,h-2),(w-1,h-1),
            (w-7,h-1),(w-9,h-5),(1,bend)],2)
    p.line([(1,1),(2,bend),(w-7,h-3)],3)
    p.line([(5,2),(6,bend),(w-3,h-4)],1)
    for y in range(4,h-4,5):
        x=1 if y<bend else 1+int((y-bend)*(w-8)/max(1,h-bend-4))
        p.line((x+1,y,x+3,y+1),4);p.dot(x+3,y+2,1)
    p.line((1,2,5,2),1);p.line((w-7,h-2,w-1,h-2),3)
    if i==3:p.line((3,9,6,10),1);p.dot(5,14,4)
    return p.finish()


OPTIC_SIZES=[(13,13),(25,9),(15,7),(22,9),(16,9),(24,13),(36,6),
             (18,8),(36,11),(10,10),(29,10),(35,7),(24,13),(34,12),
             (18,10),(28,14),(23,13),(35,12),(29,14),(16,10),(13,4),(14,10)]

def optic(i):
    # AI-painted original atlas; convert once to the native grid, then map to
    # the game's restrained steel ramp. Retain transparent side-view silhouettes.
    atlas=Image.open(Path(__file__).resolve().parent/'art-sources/vanguard-optics.png').convert('RGBA')
    cw,ch=atlas.width//4,atlas.height//6
    x,y=(i%4)*cw,(i//4)*ch
    im=atlas.crop((x,y,x+cw,y+ch));alpha=im.getchannel('A').point(lambda a:255 if a>=128 else 0)
    box=alpha.getbbox();im.putalpha(alpha);im=im.crop(box).resize(OPTIC_SIZES[i],Image.Resampling.NEAREST)
    return im

def rear_grip(i,weapon):
    # Individual surface treatments and silhouettes, not flat recolors.
    palette=METAL if i in (0,4,5,8,9) else BAKE if i in (1,2,3,7) else POLY
    p=Pixels(11,15,palette)
    p.poly([(3,0),(9,1),(10,3),(7,13),(5,14),(0,12)],3)
    p.line([(3,1),(2,6),(0,11)],4);p.line([(9,3),(7,11),(5,13)],1)
    if i==0:
        for y in (4,7,10):p.line((3,y,7,y-1),1);p.line((3,y+1,6,y),4)
        p.screw(6,2)
    elif i==1:
        for y in (3,6,9):p.line([(2,y),(7,y+2),(8,y+2)],5);p.line((2,y+1,6,y+3),2)
        p.poly([(4,11),(6,11),(6,14),(4,13)],4)
    elif i==2:
        p.line([(4,2),(3,7),(2,10)],5);p.line([(6,3),(7,5),(5,10)],2)
        for y in (3,6,9,12):p.dot(1 if y>8 else 3,y,6)
        p.screw(7,3)
    elif i==3:
        for x,y in ((4,2),(6,3),(3,5),(5,6),(2,8),(4,9),(2,11),(5,12)):p.dot(x,y,5);p.dot(x+1,y,2)
        p.line((3,1,8,2),4)
    elif i==4:
        for x,y in ((3,3),(3,6),(2,9)):p.line((x,y,x+4,y),1);p.line((x,y+1,x+3,y+1),5)
        p.screw(6,2)
    elif i==5:
        for x,y in ((4,3),(6,4),(3,6),(5,7),(2,9),(4,10)):p.line((x,y,x+1,y+1),1);p.dot(x,y-1,5)
        p.dot(5,12,5)
    elif i==6:
        p.poly([(4,3),(8,3),(7,10),(3,12),(2,10)],2);p.line((4,4,3,10),4);p.screw(6,2);p.screw(4,11)
        p.dot(7,5,5)
    elif i==7:
        p.poly([(3,3),(8,4),(7,9),(4,12),(1,10)],2)
        for x,y in ((3,4),(6,5),(2,8),(4,9),(5,11)):p.dot(x,y,4);p.dot(x+1,y+1,1)
    elif i==8:
        for x,y in ((4,3),(7,3),(3,5),(5,6),(7,7),(2,8),(4,9),(6,10),(3,11),(4,12)):p.dot(x,y,5 if (x+y)%3==0 else 1)
        p.screw(6,2)
    else:
        for y in (3,5,7,9,11):
            for x in range(max(1,4-y//4),8-y//5,2):p.dot(x,y,1);p.dot(x,y+1,4)
        p.dot(5,12,5)
    if weapon=='mp40':p.line((3,0,8,1),BAKE[5])
    return p.finish()

def raw_draw(weapon,slot,index):
    if slot=='barrel':return barrel(weapon,index)
    if slot=='butt':return stock(weapon,index)
    if slot=='clip':return magazine(weapon,index)
    if slot=='silencer':return muzzle(index)
    if slot=='scope':return optic(index)
    if slot=='grip':return foregrip(index)
    if slot=='rear-grip':return rear_grip(index,weapon)
    raise KeyError(slot)

def draw(weapon,slot,index):
    im=raw_draw(weapon,slot,index)
    if slot=='butt' and im.width>8:
        im=im.resize((min(im.width,30),max(12,round(im.height*.72))),Image.Resampling.NEAREST)
    elif slot=='rear-grip':
        im=im.resize((9,12 if weapon=='stg' else 14),Image.Resampling.NEAREST)
    elif slot=='grip' and index not in (3,4,7):
        im=im.resize((max(6,round(im.width*.75)),max(6,round(im.height*.78))),Image.Resampling.NEAREST)
    elif slot=='silencer':
        im=im.resize((max(8,round(im.width*.86)),max(3,im.height-1)),Image.Resampling.NEAREST)
    # Quantization uses only the game's metal/wood colours and hard alpha.
    native=Path(__file__).resolve().parents[2]/'data/packages/base/textures/GAME'
    palette=set()
    for name in ('stg-skin','mp40-skin','stg-clip-default'):
        for r,g,b,a in Image.open(native/(name+'.png')).convert('RGBA').getdata():
            if a>128:palette.add((r,g,b))
    palette=sorted(palette)
    mapped=[];cache={}
    for r,g,b,a in im.getdata():
        if a<128:mapped.append((0,0,0,0));continue
        # Keep accents, but suppress the heavy bright outline of old art.
        if slot!='scope' and max(r,g,b)>115:
            r,g,b=int(r*.86),int(g*.86),int(b*.86)
        k=(r,g,b)
        if k not in cache:cache[k]=min(palette,key=lambda c:sum((c[j]-k[j])**2 for j in range(3)))
        mapped.append((*cache[k],255))
    out=Image.new('RGBA',im.size);out.putdata(mapped);return out

def export(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    for weapon in ('stg','mp40'):
        for slot,count in [('barrel',4),('butt',5),('clip',4),('silencer',7),('scope',22),('grip',9),('rear-grip',10)]:
            for i in range(count):draw(weapon,slot,i).save(folder/f'vg-{weapon}-{slot}-{i}.png')

if __name__=='__main__':export(Path(__file__).resolve().parents[2]/'tools/weapon-art/vanguard-sprites')
