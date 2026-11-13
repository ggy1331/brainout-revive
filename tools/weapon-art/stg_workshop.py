"""STG-specific native-grid drawings. No MP40 shapes are used here."""
from PIL import Image, ImageDraw

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
    return {'barrel':barrel,'butt':stock,'clip':magazine,'silencer':muzzle,
            'grip':foregrip,'rear-grip':rear_grip}[slot](index)
