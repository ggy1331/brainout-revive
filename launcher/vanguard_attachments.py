"""Original, hand-authored pixel modules inspired by Vanguard's STG44/MP40 families.

No Call of Duty images/models are used. Stock receiver fragments come from this
MIT game's own sprites; every optional module is drawn here on a native pixel grid.
This final package pass is deterministic and runs for both client and server.
"""
from copy import deepcopy
from io import BytesIO
import json
import zlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'data/packages/base/textures/GAME'
INK, STEEL, EDGE, WOOD = '#242526', '#535654', '#98998c', '#69462b'

# (name, shape, upgrade properties). Each slot permits one choice; slots combine.
MUZZLES = [
    ('F8 вЂ” СЃС‚Р°Р±РёР»РёР·Р°С‚РѕСЂ', 'brake', {'accuracy':'+6','speed-coef':'*0.99'}),
    ('Р”СѓР»СЊРЅС‹Р№ РєРѕРјРїРµРЅСЃР°С‚РѕСЂ', 'compensator', {'recoil':'-8'}),
    ('РџР»Р°РјРµРіР°СЃРёС‚РµР»СЊ', 'flash', {'accuracy':'+3','recoil':'-3'}),
    ('РЈСЃРєРѕСЂРёС‚РµР»СЊ РѕС‚РґР°С‡Рё', 'booster', {'fire-rate':'*1.08','recoil':'+5'}),
    ('РўСЏР¶С‘Р»С‹Р№ РіР»СѓС€РёС‚РµР»СЊ', 'silencer', {'silent':'=1','damage':'*0.94','accuracy':'+4'}),
    ('Р›С‘РіРєРёР№ РіР»СѓС€РёС‚РµР»СЊ', 'shortsilencer', {'silent':'=1','damage':'*0.96','recoil':'-3'}),
    ('РњРЅРѕРіРѕРєР°РјРµСЂРЅС‹Р№ С‚РѕСЂРјРѕР·', 'ported', {'recoil':'-12','speed-coef':'*0.98'}),
]
GRIPS = [
    ('Carver вЂ” РІРµСЂС‚РёРєР°Р»СЊРЅР°СЏ СЂСѓРєРѕСЏС‚РєР°','vertical',{'recoil':'-7','accuracy':'+2'}),
    ('M1941 вЂ” СѓРїРѕСЂ РєРёСЃС‚Рё','stop',{'accuracy':'+5','recoil':'-4'}),
    ('M3 вЂ” РєРѕСЂРѕС‚РєР°СЏ СЂСѓРєРѕСЏС‚РєР°','short',{'speed-coef':'*1.02','accuracy':'+2'}),
    ('РЎРѕС€РєРё','bipod',{'recoil':'-10','speed-coef':'*0.96'}),
    ('GF-59 вЂ” С„РѕРЅР°СЂСЊ','light',{'accuracy':'+4'}),
    ('SMLE вЂ” РїРёСЃС‚РѕР»РµС‚РЅР°СЏ СЂСѓРєРѕСЏС‚РєР°','pistol',{'accuracy':'+7','recoil':'-3'}),
    ('M1930 вЂ” СѓРіР»РѕРІР°СЏ СЂСѓРєРѕСЏС‚РєР°','angled',{'recoil':'-6','accuracy':'+4'}),
    ('РЁС‚С‹Рє','bayonet',{'damage':'*1.03','speed-coef':'*0.98'}),
    ('Mark VI вЂ” СЃРєРµР»РµС‚РЅР°СЏ СЂСѓРєРѕСЏС‚РєР°','skeleton',{'speed-coef':'*1.03','accuracy':'+2'}),
]
OPTICS = [
    ('Nydar 47','reflex',3),('G16 2.5x','scope',10),('Slate','open',3),
    ('Mk 3 Sunfilter','sun',4),('ZC2 1.35x','lens',5),('M19 4x','flip',15),
    ('K98 Scout 10x','longscope',30),('РњРѕРЅРѕРєСѓР»СЏСЂРЅС‹Р№ РєРѕР»Р»РёРјР°С‚РѕСЂ','tube',4),
    ('1913 4вЂ“8x','variable',24),('Saturn 1.35x','round',5),('ZF4 3.5x','scope',13),
    ('Type 99 7x','longscope',25),('M38 / Slate 2.5x','hybrid',10),('Type 97 5x','scope',18),
    ('Mk 3 Mod.2 Sunfilter','sun',5),('Mk 12 РЅРѕС‡РЅРѕР№','night',14),('Mk 3 Reflector','reflex',4),
    ('1229 / Slate 3.25x','hybrid',12),('SVT-40 PU 3вЂ“6x','variable',22),
    ('Mk 18 Sunfilter','sun',6),('РћС‚РєСЂС‹С‚С‹Р№ IS01M','iron',1),('РЁРёСЂРѕРєРёР№ IS02M','wideiron',2),
]
REAR = ['Р РµР·РёРЅРѕРІР°СЏ','РћР±РјРѕС‚РєР° Р»РµРЅС‚РѕР№','РљРѕР¶Р°РЅР°СЏ','РўРєР°РЅРµРІР°СЏ','Р РёС„Р»С‘РЅР°СЏ','РЎ РЅР°СЃРµС‡РєРѕР№','РџРѕР»РёРјРµСЂРЅР°СЏ','РЎРјРѕР»СЏРЅР°СЏ','Р—РµСЂРЅРёСЃС‚Р°СЏ','РўРѕС‡РµС‡РЅР°СЏ']
BARRELS = {
 'stg': [('VDD 320 вЂ” СѓРєРѕСЂРѕС‡РµРЅРЅС‹Р№', 'short',{'accuracy':'-4','speed-coef':'*1.04'}),
         ('VDD 760 вЂ” РґР»РёРЅРЅРѕРµ С†РµРІСЊС‘','long',{'accuracy':'+10','aim-distance':'+8','speed-coef':'*0.96'}),
         ('Krausnick 620 вЂ” С‚РѕС‡РЅС‹Р№','precision',{'accuracy':'+14','recoil':'-6','fire-rate':'*0.95'}),
         ('Krausnick 220 вЂ” СЃРєРѕСЂРѕСЃС‚РЅРѕР№','rapid',{'fire-rate':'*1.12','accuracy':'-6','recoil':'+6'})],
 'mp40':[('Krausnick 317 вЂ” С‚РѕС‡РЅС‹Р№','precision',{'accuracy':'+10','aim-distance':'+7','speed-coef':'*0.97'}),
         ('VDD 285 вЂ” РєРѕР¶СѓС…','shrouded',{'recoil':'-8','accuracy':'+5'}),
         ('Krausnick 221 вЂ” Р»С‘РіРєРёР№','short',{'speed-coef':'*1.04','accuracy':'-3'}),
         ('VDD 189 вЂ” РєРѕСЂРѕС‚РєРёР№','rapid',{'fire-rate':'*1.1','recoil':'+6','accuracy':'-4'})],
}
STOCKS = {
 'stg':[('Krausnick S11S вЂ” СЃРєР»Р°РґРЅРѕР№','wire',{'speed-coef':'*1.04','recoil':'+3'}),
        ('Konstanz вЂ” С‚Р°РєС‚РёС‡РµСЃРєРёР№','tactical',{'accuracy':'+6','recoil':'-5'}),
        ('Р‘РµР· РїСЂРёРєР»Р°РґР°','removed',{'speed-coef':'*1.08','recoil':'+10','accuracy':'-6'}),
        ('VDD 27 вЂ” С‚РѕС‡РЅС‹Р№','wood',{'accuracy':'+10','speed-coef':'*0.97'}),
        ('VDD 34S вЂ” СѓС‚СЏР¶РµР»С‘РЅРЅС‹Р№','padded',{'recoil':'-12','speed-coef':'*0.96'})],
 'mp40':[('Krausnick 33M вЂ” СЃРєР»Р°РґРЅРѕР№','wire',{'speed-coef':'*1.03','recoil':'-2'}),
         ('Р‘РµР· РїСЂРёРєР»Р°РґР°','removed',{'speed-coef':'*1.07','accuracy':'-5','recoil':'+8'}),
         ('VDD 34M вЂ” СЃ Р°РјРѕСЂС‚РёР·Р°С‚РѕСЂРѕРј','padded',{'recoil':'-10','speed-coef':'*0.97'}),
         ('VDD 34M вЂ” Р¶С‘СЃС‚РєРёР№','tactical',{'accuracy':'+7','recoil':'-4'}),
         ('VDD 35M вЂ” РїСЂРѕРІРѕР»РѕС‡РЅС‹Р№','skeleton',{'speed-coef':'*1.02','accuracy':'+4'})],
}
MAGS = {'stg': [('Р›С‘РіРєРёР№ РјР°РіР°Р·РёРЅ РЅР° 50','curved',50,0.90),('РљРѕСЂРѕС‚РєРёР№ СѓСЃРёР»РµРЅРЅС‹Р№ РЅР° 20','short',20,1.13),
                ('Р‘Р°СЂР°Р±Р°РЅ РЅР° 45','drum',45,1),('РЈСЃРёР»РµРЅРЅС‹Р№ РЅР° 30','box',30,1.08)],
        'mp40':[('Р‘С‹СЃС‚СЂС‹Р№ РјР°РіР°Р·РёРЅ РЅР° 24','short',24,1),('Р›С‘РіРєРёР№ РјР°РіР°Р·РёРЅ РЅР° 32','box',32,0.93),
                ('Р‘Р°СЂР°Р±Р°РЅ РЅР° 64','drum',64,1),('РЈСЃРёР»РµРЅРЅС‹Р№ РјР°РіР°Р·РёРЅ РЅР° 32','curved',32,1.10)]}

def sprite(weapon, slot, index, skin='weapon-default'):
    # Each module is independently painted at native resolution in the art source.
    import importlib.util
    global _ART_MODULE
    if '_ART_MODULE' not in globals():
        spec=importlib.util.spec_from_file_location('vanguard_pixel_art',ROOT/'tools/weapon-art/vanguard_modules.py')
        _ART_MODULE=importlib.util.module_from_spec(spec);spec.loader.exec_module(_ART_MODULE)
    return _ART_MODULE.draw(weapon,slot,index,skin)


def build(source,target):
    with ZipFile(source) as z:
        out={n:z.read(n) for n in z.namelist()}
    content=json.loads(out['content.json']);c=content['content']
    actor_path='content/animations/actor.json'
    actor=json.loads(out[actor_path])
    for name,clip in actor['animations'].items():
        if not name.startswith(('pair-left-','pair-right-')):continue
        left=name.startswith('pair-left-')
        opposite=('hand2','palm2','holder-secondary','pair-magazine-right') if left else ('hand1','palm1','holder-primary','pair-magazine-left')
        for section in ('bones','slots','ik','transform'):
            if section in clip:
                clip[section]={k:v for k,v in clip[section].items() if not any(k==n or k.startswith(n+'-') for n in opposite)}
    out[actor_path]=json.dumps(actor,ensure_ascii=False,separators=(',',':')).encode()
    texts=json.loads(out['data/texts.json']);labels=texts['data']
    for key,ru,en in [('barrel','Ствол / цевьё','Barrel / handguard'),('butt','Приклад','Stock'),('clip','Магазин','Magazine'),('scope','Прицел','Optic'),('silencer','Дульное устройство','Muzzle'),('grip','Подствольный модуль','Underbarrel'),('rear-grip','Рукоятка','Rear grip')]:
        labels['ATTACHMENT_SLOT_'+key.replace('-','_').upper()]={'RU':ru.upper().replace('Ё','Е'),'EN':en.upper()}
    images={}; catalog=[]
    def put(name,im): images[name]=im;return name
    def attachment(name,im,x,y):
        put(name,im);return {'name':name,'path':name,'x':round(x,3),'y':round(y,3),'width':im.width,'height':im.height}
    for weapon in ('stg','mp40'):
        path='content/animations/weapon-'+weapon+'.json';m=json.loads(out[path]);upgrades={}
        # Split the stock body at natural seams. Default silhouette is pixel-identical.
        parts={'stg':(25,78),'mp40':(8,57)}[weapon]
        tip = 78.8 if weapon=='stg' else 75.52
        m['bones'].append({'name':'vg-tip','parent':'root','x':tip,'y':11.56 if weapon=='stg' else 11.5})
        grip_x,grip_y=(51.8,8.06) if weapon=='stg' else (51.52,10.0)
        m['bones'].append({'name':'vg-underbarrel','parent':'root','x':grip_x,'y':grip_y})
        for slot in ('butt','barrel','scope','silencer','grip','rear-grip'):
            m['slots'].insert(-1,{'name':slot,'bone':'vg-tip' if slot=='silencer' else 'vg-underbarrel' if slot=='grip' else 'root',**({'attachment':'default'} if slot in ('butt','barrel','scope','rear-grip') else {})})
        for skin in m['skins']:
            a=skin['attachments'];body=a.get('body',{}).get('default')
            if not body:continue
            original=Image.open(ART/(body['name']+'.png')).convert('RGBA');x0=body['x']-original.width/2;y=body['y']
            left,right=parts
            # Split the native rear sight and pistol grip as well. Optional parts
            # replace them rather than being pasted over a second visible shape.
            clean=original.copy();top=y+original.height/2
            gripbox=(28,16,43,28) if weapon=='stg' else (0,13,12,27)
            polygon=[(34,16),(42,16),(41,20),(38,22),(36,28),(28,28),(31,22)] if weapon=='stg' else [(5,13),(11,13),(11,16),(9,18),(7,24),(6,27),(0,27),(0,22),(3,17)]
            mask=Image.new('L',original.size);ImageDraw.Draw(mask).polygon(polygon,fill=255)
            grip=original.copy();grip.putalpha(Image.composite(original.getchannel('A'),Image.new('L',original.size),mask))
            clean.putalpha(Image.composite(Image.new('L',original.size),original.getchannel('A'),mask))
            scopebox=(left,0,right,5 if weapon=='stg' else 3)
            for slot,box,img in [('rear-grip',gripbox,grip),('scope',scopebox,original)]:
                art=img.crop(box);name='vg-'+weapon+'-'+skin['name']+'-'+slot+'-native'
                a.setdefault(slot,{})['default']=attachment(name,art,x0+(box[0]+box[2])/2,top-(box[1]+box[3])/2)
            clean.paste((0,0,0,0),scopebox)
            for slot,l,r in [('butt',0,left),('body',left,right),('barrel',right,original.width)]:
                art=clean.crop((l,0,r,original.height));name='vg-'+weapon+'-'+skin['name']+'-'+slot
                a.setdefault(slot,{})['default']=attachment(name,art,x0+(l+r)/2,y)
            a['body'].pop('unfolded',None)
        positions={'stg':{'butt':(-23,2),'barrel':(65,12),'clip':(26,-12),'scope':(22,23),'silencer':(86,12),'grip':(48,-1),'rear-grip':(1,-3)},
                   'mp40':{'butt':(-18,1),'barrel':(69,11),'clip':(38,-7),'scope':(29,22),'silencer':(91,11),'grip':(47,0),'rear-grip':(4,-3)}}[weapon]
        options={'barrel':BARRELS[weapon],'butt':STOCKS[weapon],'silencer':MUZZLES,'grip':GRIPS,
                 'scope':[(name,shape,{'aim-distance':f'+{distance}','accuracy':f'+{min(12,2+distance//3)}'}) for name,shape,distance in OPTICS],
                 'rear-grip':[(name+' СЂСѓРєРѕСЏС‚РєР°','rear',{'recoil':f'-{2+i%5}','accuracy':f'+{1+i%3}','reload-time':f'-{0.02*(i%4):.2f}'}) for i,name in enumerate(REAR)],
                 'clip':[(name,shape,{'clip-size':f'={size}','damage':f'*{damage}','reload-time':'-0.35' if shape=='short' else '+0.45' if shape=='drum' else '+0.1'}) for name,shape,size,damage in MAGS[weapon]]}
        for slot,items in options.items():
            upgrades[slot]=[]
            for i,(label,shape,props) in enumerate(items):
                key=f'vg-{weapon}-{slot}-{i}';art=sprite(weapon,slot,i);x,y=positions[slot]
                delta = 0; delta_y = 0; grip_delta_y = 0
                # All vertices share the native receiver's pixel grid. Measure
                # connections from alpha, not from canvas centres.
                origin_x,origin_y=(-35.2,19.06) if weapon=='stg' else (-7.48,17.0)
                def edge_center(axis,edge):
                    pts=[j for j in range(art.height if axis=='x' else art.width)
                         if art.getpixel((edge,j) if axis=='x' else (j,edge))[3]>128]
                    return (min(pts)+max(pts)+1)/2 if pts else (art.height if axis=='x' else art.width)/2
                if slot=='silencer':
                    x=art.width/2;y=edge_center('x',0)-art.height/2
                elif slot=='barrel':
                    seam=origin_x+parts[1];seam_y=origin_y-(8 if weapon=='stg' else 5.5)
                    top=seam_y+edge_center('x',0)
                    x=seam+art.width/2;y=top-art.height/2
                    delta=seam+art.width-tip
                    delta_y=(top-edge_center('x',art.width-1))-(11.56 if weapon=='stg' else 11.5)
                    mount_column=max(0,min(art.width-1,round(grip_x-seam)))
                    occupied=[row for row in range(art.height) if art.getpixel((mount_column,row))[3]>128]
                    if occupied:grip_delta_y=top-max(occupied)-1-grip_y
                elif slot=='butt':
                    seam=origin_x+parts[0];socket_y=origin_y-(9.5 if weapon=='stg' else 7)
                    x=seam-art.width/2;y=socket_y+edge_center('x',art.width-1)-art.height/2
                elif slot=='scope':
                    x=origin_x+(54 if weapon=='stg' else 29)
                    # One native pixel of overlap keeps the actual mounting feet
                    # seated despite fractional render scales. Art is alpha-trimmed.
                    y=origin_y-(6 if weapon=='stg' else 4)+art.height/2
                elif slot=='grip':
                    x=0;y=-art.height/2
                elif slot=='rear-grip':
                    socket=origin_x+(38 if weapon=='stg' else 8)
                    x=socket+art.width/2-edge_center('y',0)
                    y=origin_y-(16 if weapon=='stg' else 13)-art.height/2
                elif slot=='clip':
                    socket=23.31 if weapon=='stg' else 37.98
                    x=socket+art.width/2-edge_center('y',0)
                    y=(2.23 if weapon=='stg' else 11)-art.height/2
                a=attachment(key,art,x,y)
                for skin in m['skins']:
                    if 'body' not in skin['attachments']:continue
                    fitted=deepcopy(a)
                    if skin['name']!='weapon-default':
                        painted=sprite(weapon,slot,i,skin['name'])
                        name=key+'-'+skin['name']
                        put(name,painted);fitted['path']=name
                    skin['attachments'].setdefault(slot,{})[key]=fitted
                label=label.replace('—','-').replace('ё','е').replace('×','x')
                label=('STG: ' if weapon=='stg' else 'MP40: ')+label
                textkey=key.upper().replace('-','_');labels[textkey]={'RU':label,'EN':label}
                stat='; '.join(f'{k}: {v}' for k,v in props.items())
                labels[textkey+'_DESC']={'RU':label+'. '+stat,'EN':label+'. '+stat}
                components=[{'class':'content.components.ReplaceSlotComponent','classToReplace':'data.components.WeaponAnimationComponentData','replace':{slot:key},'tag':'client'},
                            {'class':'content.components.IconComponent','big-icon':key,'tag':'client'}]
                if slot=='barrel': components[0]['boneOffsets']={'vg-tip':{'x':delta,'y':delta_y},'fire-bone':{'x':delta,'y':delta_y},'vg-underbarrel':{'y':grip_delta_y}}
                if slot=='grip' and shape=='light': components.extend(deepcopy(c['gs-ak74-tactical-light']['components'][2:]))
                if slot=='silencer' and shape=='flash': components.append({'class':'content.components.SuppressBulletAttachmentsComponent','suppress':'fire-bone','tag':'client'})
                if props.get('silent')=='=1':
                    components.extend(deepcopy(c['gs-ak74-silencer-pbs1']['components'][2:]))
                c[key]={'class':'content.upgrades.Upgrade','access':'byDefault','name':textkey,'description':textkey+'_DESC','properties':props,'components':components}
                upgrades[slot].append(key);catalog.append({'weapon':weapon,'slot':slot,'id':key,'name':label,'properties':props})
        c['sl-pri-'+weapon]['instrument']['upgrades']=upgrades
        out[path]=json.dumps(m,ensure_ascii=False,separators=(',',':')).encode()
    labels['DESC_AKIMBO']={'RU':'РћСЂСѓР¶РёРµ РІ РґРІСѓС… СЂСѓРєР°С…: Р›РљРњ/РџРљРњ вЂ” СЃС‚СЂРµР»СЊР±Р°, R вЂ” РѕРґРЅРѕРІСЂРµРјРµРЅРЅР°СЏ РїРµСЂРµР·Р°СЂСЏРґРєР° (Serbu Рё Peacemaker вЂ” РїРѕРѕС‡РµСЂС‘РґРЅРѕ). Р’Р·РІРµРґРµРЅРёРµ РЅРµР·Р°РІРёСЃРёРјРѕ. РўРѕС‡РЅРѕСЃС‚СЊ Г—0,5, РѕС‚РґР°С‡Р° Г—2.',
                          'EN':'Dual wield: left/right click fire, R reloads both hands (Serbu and Peacemaker reload sequentially). Independent chambering. Half accuracy, double recoil.'}
    out['content.json']=json.dumps(content,ensure_ascii=False,separators=(',',':')).encode()
    out['data/texts.json']=json.dumps(texts,ensure_ascii=False,separators=(',',':')).encode()
    # One extra nearest-filtered atlas page, using native sprite dimensions.
    if 'content/textures/GAME.atlas' in out:
        width=512;cellw,cellh=128,40;height=((len(images)+3)//4)*cellh
        page=Image.new('RGBA',(width,height));atlas='\n\nvanguard-modules.png\nformat: RGBA8888\nfilter: Nearest,Nearest\nrepeat: none\n'
        for i,(name,im) in enumerate(images.items()):
            x=(i%4)*cellw;y=(i//4)*cellh;page.alpha_composite(im,(x,y))
            atlas+=f'{name}\n  rotate: false\n  xy: {x}, {y}\n  size: {im.width}, {im.height}\n  orig: {im.width}, {im.height}\n  offset: 0, 0\n  index: -1\n'
        b=BytesIO();page.save(b,'PNG');out['content/textures/vanguard-modules.png']=b.getvalue()
        out['content/textures/GAME.atlas']+=atlas.encode()
        preview=ROOT/'build/attachments-preview.png';page.resize((width*2,height*2),Image.Resampling.NEAREST).save(preview)
    (ROOT/'build/attachments-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
    if '__H' in out:
        out['__H'] = json.dumps({name:zlib.crc32(data) for name,data in out.items()
                                if name != '__H' and not name.endswith('/')},separators=(',',':')).encode()
    with ZipFile(target,'w',ZIP_DEFLATED) as z:
        for name,data in out.items():z.writestr(name,data)
    print('Original STG/MP40 modules:',len(catalog),target)
