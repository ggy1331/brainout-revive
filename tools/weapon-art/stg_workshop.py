"""STG-specific native-grid drawings. No MP40 shapes are used here."""
from PIL import Image, ImageDraw
from pathlib import Path

NATIVE=Path(__file__).resolve().parents[2]/'data/packages/base/textures/GAME'

def native(name,box=None):
    im=Image.open(NATIVE/(name+'.png')).convert('RGBA')
    if box:im=im.crop(box)
    return im.crop(im.getbbox())

def size(im,w,h):return im.resize((w,h),Image.Resampling.NEAREST)

def iron(i):
    p=Paint(11 if i==0 else 15,6 if i==0 else 8)
    w,h=p.im.size;p.tube(0,h-2,w-1,h-1)
    p.box((2,1,4,h-3),2);p.line((2,1,4,1),4)
    p.box((w-5,0,w-3,h-3),3);p.dot(w-4,0,5)
    if i:p.line((4,3,w-5,3),1);p.rivet(7,5)
    return p.im

def fitted_barrel(i):
    # Preserve native STG edge shading and front sight. Replace the complete
    # upper front from x=50, leaving the lower magazine well in the receiver.
    original=Image.open(NATIVE/'stg-skin.png').convert('RGBA')
    lengths=[27,55,43,17];jacket=lengths[i]
    out=Image.new('RGBA',(jacket+21,11));d=ImageDraw.Draw(out)
    section=original.crop((50,5,93,11))
    # Native-grid extension/cropping, no blurred or squashed texture.
    for x in range(jacket):
        sx=x if x<4 else 39+x-(jacket-4) if x>=jacket-4 else 4+(x-4)%34
        out.alpha_composite(section.crop((sx,0,sx+1,6)),(x,5))
    out.alpha_composite(original.crop((93,0,114,11)),(jacket,0))
    if i==0:
        for x in (8,15):
            d.rectangle((x,7,x+3,8),fill=METAL[0]);d.line((x+1,9,x+3,9),fill=METAL[3])
    elif i==1:
        for x in range(8,jacket-6,7):
            d.rectangle((x,7,x+3,8),fill=METAL[0]);d.line((x,6,x+3,6),fill=METAL[3])
        d.line((5,10,jacket-5,10),fill=METAL[1])
    elif i==2:
        # Carved wood panels use the game's existing FG42 grain, with STG steel
        # collars at each end. The gas tube and front sight stay above the wood.
        wood=native('fg42-skin',(60,7,86,16))
        for x in range(4,jacket-4):
            strip=wood.crop(((x-4)%wood.width,0,(x-4)%wood.width+1,min(6,wood.height)))
            out.alpha_composite(strip,(x,5))
        d.line((4,5,jacket-5,5),fill=WOOD[4]);d.line((4,10,jacket-5,10),fill=WOOD[1])
        for x in (3,jacket-4):d.line((x,5,x,10),fill=METAL[4])
    else:
        d.rectangle((6,7,10,8),fill=METAL[0]);d.line((6,6,10,6),fill=METAL[4])
    return out

def fitted_stock(i):
    if i==0:return size(native('akm-butt-default'),30,13)
    if i==1:return size(native('ak74-butt-old'),29,14)
    if i==2:
        p=Paint(4,7);p.tube(0,0,3,6);p.rivet(1,3);return p.im
    if i==3:return size(native('fg42-skin',(0,5,33,30)),29,17)
    # Retain the recognisable STG wooden cheek shape, add a rubber recoil pad.
    im=size(native('stg-skin',(0,0,25,28)),30,17)
    d=ImageDraw.Draw(im);d.line((0,5,0,15),fill=METAL[1],width=2)
    d.line((1,5,1,14),fill=METAL[3]);d.line((4,7,21,4),fill=WOOD[4])
    return im

def fitted_magazine(i):
    if i==0:return size(native('rpk74-clip-extended'),18,31)
    if i==1:return size(native('stg-clip-default'),9,17)
    if i==3:
        im=native('stg-clip-default');d=ImageDraw.Draw(im)
        d.line((4,5,7,15,10,21),fill=METAL[4]);d.line((5,6,8,16,11,22),fill=METAL[1])
        return im
    # Side elevation of a drum: axis runs across the gun, so the side view is
    # a narrow curved housing, not a circular plate facing the viewer.
    p=Paint(13,24);p.tube(3,0,9,5)
    p.poly([(2,5),(10,5),(12,8),(12,19),(10,23),(2,23),(0,20),(0,8)],1)
    p.poly([(3,6),(9,6),(10,9),(10,20),(8,22),(3,21),(2,18),(2,9)],3)
    p.line([(2,8),(2,18),(3,20)],4);p.line((4,6,8,6),5)
    p.line((11,9,11,19),0);p.line((3,22,9,22),2)
    for y in (9,13,17):p.line((4,y,8,y),2)
    p.box((5,11,7,13),1);p.dot(6,11,4)
    return p.im

def fitted_rear(i):
    # Keep the STG's sloped grip silhouette and native shaded grooves.
    im=Image.open(NATIVE/'stg-skin.png').convert('RGBA').crop((28,16,43,28))
    mask=Image.new('L',im.size);ImageDraw.Draw(mask).polygon([(6,0),(14,0),(13,4),(10,6),(8,12),(0,12),(3,6)],fill=255)
    from PIL import ImageChops
    im.putalpha(ImageChops.multiply(im.getchannel('A'),mask));d=ImageDraw.Draw(im)
    pal=WOOD if i==2 else LEATHER if i in (1,3,7) else METAL
    # Different materials retain native highlights rather than a flat fill.
    for y in range(im.height):
        for x in range(im.width):
            rgba=im.getpixel((x,y))
            if rgba[3]:
                tone=max(0,min(5,round((sum(rgba[:3])/3-20)/17)))
                d.point((x,y),fill=pal[tone])
    for y in range(2,10):
        for x in range(2,12):
            if not im.getpixel((x,y))[3]:continue
            mark= ((x+y)%4==0 if i==1 else (x-y)%5==0 if i==3 else y%3==0 if i==4 else
                   x%3==0 and y%3==0 if i==5 else (x+2*y)%6==0 if i==7 else (x+y)%3==0 if i==8 else False)
            if mark:d.point((x,y),fill=pal[3 if i in (1,3,7) else 1])
    if i==6:
        d.polygon([(7,3),(10,3),(7,8),(4,9)],fill=METAL[1]);d.line((7,3,5,7),fill=METAL[3])
    if i==9:d.line((7,3,4,9),fill=METAL[4])
    return im

METAL = ['#24221e','#33312c','#45423c','#56534c','#6b685f','#858175']
WOOD = ['#291d12','#422b15','#65421d','#875a29','#aa783c','#c18d48']
LEATHER = ['#252019','#352c20','#4c3b28','#665039','#7b6449','#8c7354']

class Paint:
    def __init__(self,w,h,palette=METAL):
        self.im=Image.new('RGBA',(w,h));self.d=ImageDraw.Draw(self.im);self.p=palette
    def c(self,c):return self.p[c] if isinstance(c,int) else c
    def poly(self,xy,c):self.d.polygon(xy,fill=self.c(c))
    def box(self,xy,c):self.d.rectangle(xy,fill=self.c(c))
    def line(self,xy,c,width=1):self.d.line(xy,fill=self.c(c),width=width)
    def dot(self,x,y,c):self.d.point((x,y),fill=self.c(c))
    def rivet(self,x,y):self.dot(x,y,1);self.dot(x,y-1,4)
    def tube(self,x0,y0,x1,y1):
        self.box((x0,y0,x1,y1),2);self.line((x0,y0,x1-1,y0),4)
        if y1-y0>2:self.line((x0+1,y0+1,x1-1,y0+1),3)
        self.line((x0,y1,x1,y1),1)

def barrel(i):
    if i==0:
        p=Paint(29,11);p.tube(0,4,28,7)
        p.poly([(0,2),(12,2),(16,4),(15,9),(0,9)],2)
        p.line((1,2,11,2),4);p.line((1,8,13,8),1)
        for x in (3,8):p.box((x,4,x+2,5),0);p.dot(x+1,6,3)
        p.rivet(1,6);p.box((16,4,18,7),3)
        p.poly([(23,4),(24,1),(25,1),(25,0),(26,0),(26,4)],2);p.dot(25,0,4)
    elif i==1:
        p=Paint(43,12);p.tube(0,5,42,8)
        p.poly([(0,2),(28,2),(31,4),(30,9),(28,10),(0,10)],2)
        p.line((1,2,27,2),4);p.line((2,3,29,3),3)
        for x in (3,10,17,24):
            p.box((x,4,x+3,5),0);p.line((x+1,6,x+3,6),3)
        for x in (6,14,22):p.line((x,8,x+3,8),1)
        p.line((0,10,27,10),1);p.rivet(1,6)
        p.box((31,4,33,9),2);p.line((31,4,31,8),4)
        p.poly([(37,5),(38,1),(39,1),(39,0),(40,0),(40,5)],2);p.dot(39,0,4)
    elif i==2:
        p=Paint(39,13);p.tube(0,5,38,8)
        p.poly([(0,3),(15,3),(19,6),(18,10),(2,11),(0,9)],WOOD[2])
        p.line((2,3,14,3),WOOD[4]);p.line([(2,5),(8,6),(14,5)],WOOD[3])
        p.line([(1,9),(8,8),(16,9)],WOOD[1]);p.dot(5,5,WOOD[5])
        p.box((19,4,21,9),2);p.line((19,4,19,8),4)
        for x in (23,26,29):p.line((x,4,x,9),1);p.dot(x+1,5,4)
        p.poly([(33,5),(34,2),(35,2),(35,0),(36,0),(36,5)],2);p.dot(35,0,4)
    else:
        p=Paint(21,10);p.tube(0,4,20,7)
        p.poly([(0,2),(9,1),(13,3),(12,8),(0,8)],2)
        p.line([(1,2),(8,1),(11,2)],4);p.box((3,4,7,5),0)
        p.line((1,8,10,8),1);p.rivet(10,4)
        p.box((14,3,16,8),3);p.line((15,3,15,7),2)
        p.line([(18,4),(18,0),(19,0),(19,4)],2);p.dot(18,0,4)
    return p.im

def stock(i):
    if i==0:
        p=Paint(29,14);p.tube(23,2,28,6)
        p.line([(24,3),(3,3),(1,12),(4,13),(23,7)],2,2)
        p.line([(23,2),(3,2),(2,8)],4);p.line((5,12,22,7),3)
        p.line((2,5,1,12),1);p.rivet(25,4)
    elif i==1:
        p=Paint(27,14);p.tube(19,3,26,6)
        p.poly([(20,3),(3,1),(1,2),(0,12),(3,13),(18,8),(21,7)],2)
        p.poly([(5,5),(15,5),(14,7),(4,10)],(0,0,0,0))
        p.line((4,2,18,4),3);p.line((2,3,1,10),1);p.rivet(19,6)
    elif i==2:
        p=Paint(4,8);p.poly([(1,0),(3,1),(3,6),(1,7),(0,5),(0,2)],2)
        p.line((2,1,2,5),3);p.rivet(2,4)
    elif i==3:
        p=Paint(32,16,WOOD)
        p.poly([(31,3),(25,3),(18,5),(4,2),(1,2),(0,13),(3,15),(18,9),(31,8)],2)
        p.poly([(3,3),(17,6),(25,4),(30,4),(30,6),(18,8),(3,11)],3)
        p.line([(3,3),(16,6),(25,4)],4);p.line([(4,11),(11,9),(17,8)],1)
        p.line([(5,6),(10,6),(16,7)],2);p.line((1,4,0,12),METAL[1])
        p.dot(7,7,4);p.dot(26,5,METAL[1])
    else:
        p=Paint(26,16,LEATHER)
        p.poly([(25,4),(20,4),(17,6),(4,2),(1,2),(0,13),(4,15),(18,10),(25,9)],2)
        p.poly([(4,3),(17,7),(23,5),(23,8),(16,10),(4,12)],3)
        p.line((4,4,15,7),4);p.line([(5,13),(16,10),(23,9)],1)
        p.box((0,3,2,12),METAL[1]);p.line((1,4,1,10),METAL[2])
        p.box((8,6,15,8),2);p.line((8,6,14,6),3);p.dot(21,7,METAL[1])
    return p.im

def magazine(i):
    if i==2:
        p=Paint(15,23);p.tube(4,0,10,5)
        p.poly([(3,5),(11,5),(14,8),(14,18),(12,22),(3,22),(0,19),(0,8)],2)
        p.poly([(3,7),(10,6),(11,8),(11,19),(9,21),(3,20)],3)
        p.line([(2,8),(2,18),(4,20)],1);p.line((12,9,12,18),1)
        p.line((4,7,9,7),4);p.line((3,21,10,21),1)
        p.box((5,10,8,12),2);p.dot(6,10,4)
        p.line((4,15,9,15),2);p.line((4,18,9,18),2)
    else:
        w,h=[(15,31),(9,17),(0,0),(13,25)][i];p=Paint(w,h)
        p.poly([(0,0),(6,0),(7,h//2),(w-1,h-3),(w-1,h-1),(w-7,h-1),(1,h//2)],2)
        p.line([(1,1),(2,h//2),(w-7,h-3)],3)
        p.line([(5,2),(6,h//2),(w-3,h-4)],1)
        for y in range(4,h-4,4):
            x=2+max(0,y-h//2)//3
            p.box((x,y,x+2,y+1),1);p.line((x,y,x+1,y),4)
        p.line((1,2,5,2),1);p.line((w-7,h-2,w-1,h-2),3)
        if i==3:p.line((4,9,6,10),3);p.dot(7,20,4)
    return p.im

def muzzle(i):
    sizes=[(12,5),(13,6),(14,5),(10,7),(26,6),(19,5),(15,7)]
    p=Paint(*sizes[i]);w,h=p.im.size;p.tube(0,h//2-1,3,h//2+1)
    if i==0:
        p.tube(3,0,11,4);p.box((6,1,7,2),0);p.box((9,1,10,2),0)
    elif i==1:
        p.poly([(3,1),(5,0),(11,0),(12,1),(12,4),(10,5),(3,4)],2)
        p.line((5,0,10,0),4);p.box((6,1,8,2),0);p.line((6,4,9,4),1)
    elif i==2:
        p.tube(3,0,6,4);p.line((6,0,13,0),3);p.line((6,2,12,2),1);p.line((6,4,13,4),2)
        p.dot(12,0,4)
    elif i==3:
        p.poly([(3,2),(6,0),(9,0),(9,6),(6,6),(3,4)],2)
        p.line((6,0,8,0),4);p.line((5,2,8,2),3);p.line((7,5,9,5),1)
    elif i==4:
        p.poly([(3,1),(5,0),(24,0),(25,1),(25,4),(24,5),(5,5),(3,4)],2)
        p.line((6,0,23,0),4);p.line((6,1,24,1),3);p.line((5,5,23,5),1)
        p.line((7,1,7,4),1);p.line((22,1,22,4),1);p.dot(14,2,3)
    elif i==5:
        p.tube(3,0,18,4);p.line((6,0,6,4),1);p.line((15,0,15,4),1)
        p.line((8,1,13,1),3);p.dot(17,1,4)
    else:
        p.poly([(3,1),(5,0),(13,0),(14,1),(14,5),(12,6),(4,5)],2)
        p.line((5,0,12,0),4)
        for x in (6,10):p.box((x,2,x+1,4),0);p.dot(x,1,3)
    return p.im

def foregrip(i):
    dims=[(10,15),(13,7),(9,9),(25,6),(21,8),(12,15),(19,10),(29,5),(10,13)]
    p=Paint(*dims[i]);w,h=p.im.size
    p.box((1,0,w-2,1),2);p.line((2,0,w-3,0),3)
    if i==0:
        p.poly([(3,2),(8,2),(8,12),(6,14),(2,12)],WOOD[2])
        p.line((3,3,3,11),WOOD[4])
        for y in (5,8,11):p.line((4,y,7,y),WOOD[1])
    elif i==1:
        p.poly([(3,2),(10,2),(8,6),(6,6)],2);p.line((4,2,7,5),3)
    elif i==2:
        p.poly([(2,2),(7,2),(7,7),(5,8),(2,7)],LEATHER[2]);p.line((3,3,3,6),LEATHER[4])
        p.line((4,5,6,5),LEATHER[1])
    elif i==3:
        p.box((2,1,6,3),2);p.rivet(4,2)
        p.line((6,3,23,3),3);p.line((7,4,24,4),1);p.line((8,5,24,5),2)
    elif i==4:
        p.tube(0,3,20,6);p.box((16,2,20,7),2);p.line((19,3,19,6),4)
        p.line((5,3,5,6),1);p.line((13,3,13,6),1);p.box((7,1,11,3),2)
    elif i==5:
        p.poly([(5,2),(10,2),(9,8),(5,14),(1,12),(3,6)],WOOD[2])
        p.line([(5,3),(4,7),(2,11)],WOOD[4]);p.line((7,6,5,10),WOOD[1])
    elif i==6:
        p.poly([(1,2),(6,2),(13,7),(16,2),(18,2),(15,9),(12,9)],2)
        p.poly([(7,3),(13,7),(14,6),(9,3)],(0,0,0,0));p.line((3,2,12,8),3)
    elif i==7:
        p.box((0,1,7,3),LEATHER[1]);p.box((7,0,8,4),2)
        p.poly([(9,1),(25,1),(28,2),(24,3),(9,3)],3);p.line((10,1,25,1),4)
    else:
        p.poly([(2,2),(8,2),(7,11),(5,12),(1,10)],2)
        p.poly([(4,4),(6,4),(5,9),(3,9)],(0,0,0,0));p.line((2,3,2,9),3)
    # Small metal collars and wear highlights read at native resolution; avoid
    # uniformly filled silhouettes that looked unlike the shaded receiver.
    p.line((2,1,w-3,1),1)
    if i in (0,2,8):
        p.box((2,1,w-3,2),2);p.line((3,1,w-4,1),4)
        p.rivet(w//2,2)
    if i==0:
        p.line((3,4,2,11),WOOD[3]);p.dot(5,4,WOOD[4]);p.line((3,12,6,13),WOOD[1])
    elif i==1:
        p.rivet(5,3);p.line((8,3,7,5),1);p.dot(8,2,4)
    elif i==2:
        p.line((3,4,3,6),LEATHER[3]);p.line((4,7,6,7),LEATHER[1])
    elif i==4:
        p.line((1,4,14,4),3);p.dot(17,3,5);p.line((1,6,14,6),1)
        p.line((7,1,10,1),4);p.rivet(9,2)
    elif i==6:
        p.line((2,3,11,8),4);p.line((14,8,17,3),1);p.rivet(4,2);p.rivet(16,2)
    elif i==7:
        p.line((10,2,25,2),5);p.line((10,3,23,3),2)
        for x in (2,4,6):p.line((x,1,x,3),1)
        p.dot(8,0,4)
    elif i==8:
        p.line((2,4,1,9),4);p.line((3,10,6,11),1);p.dot(7,4,4)
    return p.im

def rear_grip(i):
    pal=WOOD if i==2 else LEATHER if i in (1,3,7) else METAL
    p=Paint(10,12,pal)
    shape=[(4,0),(9,0),(9,2),(6,11),(3,11),(0,9)]
    if i in (0,4):shape=[(4,0),(9,0),(9,2),(7,4),(8,5),(6,7),(6,10),(3,11),(0,9)]
    if i==6:shape=[(4,0),(9,0),(9,2),(7,10),(4,11),(1,10),(1,8)]
    p.poly(shape,2);p.line([(4,1),(2,6),(1,8)],3);p.dot(7,2,1)
    if i==0:
        for y in (3,6,9):p.line((3,y,7-y//4,y-1),1)
    elif i==1:
        for y in (2,5,8):p.line((3,y,7,y+2),4);p.dot(3,y+1,1)
    elif i==2:
        p.line([(5,2),(4,5),(3,8)],4);p.line([(6,3),(7,4),(5,8)],1);p.dot(5,10,3)
    elif i==3:
        for x,y in ((4,2),(3,4),(2,6),(1,8)):p.dot(x,y,4)
        p.line((5,3,4,8),1)
    elif i==4:
        for y in (3,5,7):p.line((3,y,7,y),1);p.dot(3,y+1,3)
    elif i==5:
        for x,y in ((5,3),(7,3),(4,5),(6,5),(3,7),(5,7),(3,9)):p.dot(x,y,0)
        p.dot(6,1,4)
    elif i==6:
        p.poly([(5,3),(7,3),(6,8),(3,9)],1);p.line((5,3,4,7),3)
    elif i==7:
        for x,y in ((4,3),(6,4),(3,6),(5,7),(2,9),(4,10)):p.dot(x,y,3)
    elif i==8:
        for x,y in ((4,3),(6,3),(3,5),(5,5),(7,5),(2,7),(4,7),(6,7),(3,9),(5,9)):p.dot(x,y,1)
    else:
        for y in (3,5,7,9):p.line((max(1,4-y//3),y,7-y//4,y),1)
        p.line((5,2,3,9),3)
    return p.im

def draw(slot,index):
    if slot=='silencer':
        sources=['ak105-muzzle-on','m3gg-barrel-muzle',None,None,'ak74-silencer','aksu-silencer','ak108-silencer']
        if sources[index]:
            im=native(sources[index]);return size(im,*[(12,4),(13,5),(1,1),(1,1),(26,6),(18,5),(15,6)][index])
    if slot=='grip' and index==3:return size(native('bar-bipod'),27,7)
    if slot=='grip' and index==5:return size(native('ots141a-grip-tactical'),11,14)
    return {'barrel':fitted_barrel,'butt':fitted_stock,'clip':fitted_magazine,'silencer':muzzle,
            'grip':foregrip,'rear-grip':fitted_rear}[slot](index)
