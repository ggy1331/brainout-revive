"""Native-resolution original pixel paintings for the STG / MP40 module set.

Every design below has an individual silhouette and construction details. The
neutral blued-steel and warm dirt ramps were sampled from this game's STG/MP40,
not from COD. Pixel coordinates are the art, not vector placeholders scaled down.
No antialiasing, gradients at display resolution, outlines around every shape,
or upscaled/reduced intermediate artwork. Reproducible PNG masters live alongside
the source sprites after export().
"""
from pathlib import Path
from PIL import Image, ImageDraw

# Deep occlusion -> oily shadow -> steel -> worn edges, matching native receivers.
METAL=['#20201e','#292927','#373736','#464646','#555555','#6f6f6f','#7a7a7a','#999991']
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
        p=Pixels(24,22);p.tube(5,0,19,3);p.screw(12,2)
        p.line([(9,4),(4,19),(1,20)],2,width=2);p.line([(10,4),(5,19),(1,19)],5)
        p.line([(15,4),(20,19),(23,19)],3,width=2);p.line((16,4,21,18),5)
        p.band(7,9,12);p.band(18,11,13);p.box((0,20,4,21),2);p.box((20,20,23,21),2)
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
    # Feed necks maintain the stock weapon's insertion point. Distinct pressed ribs.
    if (weapon=='stg' and i==2) or (weapon=='mp40' and i==2):
        wide=24 if weapon=='stg' else 27;h=26 if weapon=='stg' else 29;p=Pixels(wide,h)
        mid=wide//2;p.tube(mid-3,0,mid+2,7)
        p.d.ellipse((0,6,wide-1,h-1),fill=METAL[2]);p.d.arc((1,6,wide-2,h-2),180,290,fill=METAL[5])
        p.d.ellipse((4,10,wide-5,h-5),outline=METAL[4]);p.d.arc((4,10,wide-5,h-5),40,170,fill=METAL[1])
        p.box((mid-1,15,mid+1,17),1);p.dot(mid,15,5)
        p.line((mid-6,14,mid-3,16),3);p.line((mid+4,20,mid+7,22),1)
        p.dot(4,12,6);p.dot(wide-4,h-9,3);p.line((mid-1,1,mid-1,5),5)
    elif weapon=='stg':
        dims=[(15,33),(10,18),(13,26)];w,h=dims[0 if i==0 else 1 if i==1 else 2];p=Pixels(w,h)
        p.poly([(0,0),(7,0),(8,h//2),(w-1,h-3),(w-1,h-1),(w-8,h-1),(3,h//2)],3)
        p.line([(1,0),(2,h//2),(w-7,h-2)],5);p.line([(7,1),(8,h//2),(w-1,h-4)],2)
        for offset in (3,5):p.line([(offset,4),(offset+1,h//2),(w-7+offset//2,h-5)],2)
        p.line((w-8,h-2,w-1,h-2),5);p.line((1,2,6,2),1);p.dot(2,5,6)
        if i==3:p.band(3,8,11);p.dot(7,18,5)
    else:
        w=7 if i==0 else 8 if i==1 else 9;h=21 if i==0 else 31;p=Pixels(w,h)
        p.poly([(0,0),(w-2,0),(w-1,h-2),(w-2,h-1),(1,h-1)],3)
        p.line((1,1,1,h-3),5);p.line((w-2,2,w-2,h-3),1)
        p.line((3,4,3,h-5),2);p.line((4,4,4,h-5),4);p.line((1,h-2,w-1,h-2),5)
        p.box((0,0,w-2,2),2);p.dot(2,0,6)
        if i==3:
            for y in (10,17,24):p.dot(5,y,1);p.dot(5,y+1,4)
        elif i==1:p.line((2,6,2,14),6);p.dot(5,22,5)
    return p.finish()

def optic(i):
    """22 separate layouts, not a single tube rescaled for different magnifications."""
    sizes=[(15,11),(24,11),(13,10),(18,10),(17,10),(26,13),(39,10),(19,10),
           (35,12),(18,12),(28,10),(36,11),(26,15),(31,11),(21,10),(31,16),
           (17,12),(29,16),(30,13),(19,12),(12,7),(15,7)]
    p=Pixels(*sizes[i]);w,h=p.im.size
    def mount(x0,x1):
        p.box((x0,h-3,x1,h-2),2);p.line((x0,h-3,x1,h-3),4)
        p.line((x0-2,h-1,x1+2,h-1),3);p.screw(x0+1,h-2)
    def glass(x,y0,y1):p.line((x,y0,x,y1),'#758880');p.dot(x,y0,'#a3b0a4')
    if i==0: # Nydar: high angled plate, tiny tubular base
        mount(4,11);p.poly([(4,8),(3,2),(5,0),(12,0),(14,3),(13,8)],2)
        p.hole((5,2,11,6));p.line([(4,2),(5,1),(11,1),(13,3)],5);glass(12,3,6);p.screw(4,8)
    elif i==1: # short G16 with wide ocular and offset adjustment
        mount(8,17);p.tube(1,3,22,7);p.band(2,2,8);p.band(19,1,8)
        p.box((10,0,13,3),3);p.line((10,0,13,0),5);glass(22,3,6);p.screw(15,5)
    elif i==2: # low open Slate hood
        mount(3,9);p.line([(2,7),(2,2),(4,1),(9,1),(11,3),(11,7)],3,width=1)
        p.line((4,1,8,1),6);glass(10,3,5);p.box((2,6,9,7),2);p.dot(4,6,5)
    elif i==3: # shallow sunshade, long cantilever foot
        mount(6,13);p.tube(2,3,16,6);p.poly([(0,2),(14,1),(17,2),(17,3),(1,3)],3)
        p.line((2,2,15,1),5);glass(15,4,5);p.screw(8,5)
    elif i==4: # ZC2 short oblique lens housing
        mount(5,12);p.poly([(1,4),(3,1),(12,1),(16,3),(15,7),(3,7)],3)
        p.line((4,1,11,1),5);p.band(4,2,6);glass(15,3,6);p.dot(8,5,2)
    elif i==5: # flip scope with exposed hinge below ocular
        mount(9,20);p.tube(2,3,24,7);p.band(2,2,8);p.band(21,2,8)
        p.box((12,0,16,3),3);p.line((12,0,16,0),5);p.screw(10,9);p.line((7,8,9,10),5);glass(24,3,6)
    elif i==6: # K98 Scout long thin scope with two distinct narrow rings
        mount(11,28);p.tube(0,3,38,6);p.band(1,2,7);p.band(33,1,7)
        p.band(12,2,8);p.band(27,2,8);p.box((19,0,22,3),3);p.line((19,0,22,0),5);glass(38,3,5)
    elif i==7: # monocular enclosed reflector, oval protective lip
        mount(4,13);p.tube(1,2,17,6);p.band(2,1,7);p.band(15,1,7);glass(17,2,5)
        p.box((7,0,10,2),2);p.dot(8,0,5);p.screw(9,4)
    elif i==8: # long variable with knurled ocular ring and large objective
        mount(12,25);p.tube(1,4,33,8);p.band(2,2,9);p.tube(26,2,34,9)
        for x in (5,7,9):p.band(x,3,8)
        p.box((16,0,20,4),3);p.line((16,0,20,0),5);p.band(22,3,9);glass(34,3,7)
    elif i==9: # Saturn round aperture cutout with a broad base
        mount(4,12);p.d.ellipse((3,0,16,9),fill=METAL[3]);p.d.ellipse((5,2,14,7),fill=(0,0,0,0))
        p.d.arc((3,0,16,9),185,290,fill=METAL[6]);glass(14,3,6);p.box((5,8,12,9),2)
    elif i==10: # ZF4 low asymmetric objective and two tiny clamp screws
        mount(9,19);p.tube(0,3,26,6);p.tube(20,2,27,7);p.band(2,2,7);p.band(10,2,8)
        p.box((14,0,18,3),3);p.line((14,0,18,0),5);glass(27,3,6);p.screw(20,8)
    elif i==11: # Type99 straight long tube with rear sun shield
        mount(12,26);p.tube(0,3,35,7);p.tube(0,2,7,8);p.band(10,2,8);p.band(28,2,8)
        p.box((18,0,20,3),3);p.dot(18,0,5);glass(35,4,6);p.line((2,3,6,3),6)
    elif i==12: # piggyback compact open sight on a 2.5x scope
        mount(7,18);p.tube(1,7,24,11);p.band(3,6,12);p.band(21,6,12);glass(24,7,10)
        p.line([(9,6),(8,2),(10,0),(16,0),(18,2),(18,6)],3);p.line((10,0,15,0),6);glass(17,2,4)
    elif i==13: # Type97 long offset tube with tall front ring
        mount(10,22);p.tube(0,4,30,7);p.band(1,3,8);p.tube(23,2,30,8)
        p.band(9,3,8);p.box((17,0,20,4),3);p.line((17,0,20,0),5);glass(30,3,6);p.screw(23,9)
    elif i==14: # Mk3 Mod2 protected sunfilter with side rail
        mount(7,15);p.poly([(1,4),(4,1),(18,1),(20,3),(19,7),(2,7)],3)
        p.line((5,1,17,1),5);p.line((2,5,11,5),2);p.band(13,2,7);glass(19,3,6);p.screw(5,6)
    elif i==15: # early night optic: bulky stepped objective, battery and clamp
        mount(12,23);p.tube(1,6,30,12);p.tube(21,4,30,13);p.band(3,5,12);p.band(20,5,12)
        p.box((7,2,17,6),2);p.line((8,2,16,2),5);p.box((12,0,15,2),3)
        p.line((7,8,15,8),4);p.screw(17,9);glass(30,6,11);p.dot(9,5,4)
    elif i==16: # tall raked reflector, round windage knob
        mount(4,12);p.poly([(3,9),(2,4),(5,0),(13,0),(16,4),(14,9)],3)
        p.hole((5,3,12,7));p.line([(4,3),(6,1),(12,1)],5);glass(13,3,7);p.screw(3,8)
    elif i==17: # longer hybrid with offset plate / adjustment tower
        mount(9,22);p.tube(0,8,28,12);p.band(3,7,13);p.band(24,6,13);glass(28,8,11)
        p.line([(10,7),(9,2),(11,1),(18,1),(20,3),(19,7)],3);p.line((11,1,17,1),5);glass(19,3,5)
        p.box((5,5,7,8),3);p.dot(5,5,5)
    elif i==18: # PU telescopic sight with slanted side bracket
        mount(9,20);p.tube(0,4,29,8);p.band(1,3,9);p.band(24,3,9)
        p.box((12,0,16,4),3);p.line((12,0,16,0),6);p.band(7,3,9);glass(29,4,7)
        p.line((7,9,10,11),5);p.screw(19,10);p.dot(18,6,1)
    elif i==19: # Mk18 bridge roof with forward glass and exposed base wheel
        mount(4,13);p.poly([(1,5),(4,1),(15,1),(18,4),(17,8),(3,8)],3)
        p.hole((5,3,14,6));p.line((5,1,14,1),5);glass(16,4,6);p.screw(5,9);p.dot(10,8,5)
    elif i==20:
        mount(3,8);p.line([(2,3),(2,0),(4,0),(5,3),(8,3),(9,0),(11,0),(11,3)],3);p.dot(3,0,6);p.dot(10,0,5)
    else:
        mount(4,10);p.line([(0,3),(1,0),(4,0),(5,3),(10,3),(11,0),(14,0),(14,3)],3);p.line((1,0,3,0),6);p.line((11,0,13,0),5)
    return p.finish()

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

def draw(weapon,slot,index):
    if slot=='barrel':return barrel(weapon,index)
    if slot=='butt':return stock(weapon,index)
    if slot=='clip':return magazine(weapon,index)
    if slot=='silencer':return muzzle(index)
    if slot=='scope':return optic(index)
    if slot=='grip':return foregrip(index)
    if slot=='rear-grip':return rear_grip(index,weapon)
    raise KeyError(slot)

def export(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    for weapon in ('stg','mp40'):
        for slot,count in [('barrel',4),('butt',5),('clip',4),('silencer',7),('scope',22),('grip',9),('rear-grip',10)]:
            for i in range(count):draw(weapon,slot,i).save(folder/f'vg-{weapon}-{slot}-{i}.png')

if __name__=='__main__':export(Path(__file__).resolve().parents[2]/'tools/weapon-art/vanguard-sprites')
