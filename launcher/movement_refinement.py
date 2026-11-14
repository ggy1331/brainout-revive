"""Final, repeatable v0.14.1 movement/presentation patch; also usable on installed packages."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from copy import deepcopy
from math import sin,cos,pi
import json,zlib
from arm_animations import wrist,put_arm,arm_tracks,sprint
from pair_refinement import ARMS,direction
EXCLUDED={'welrod','scorpion','tec9','mp5k','mat49','k23p','p50','peacemaker','supershorty','rgm40'}
def encode(v):return json.dumps(v,ensure_ascii=False,separators=(',',':')).encode('utf8')
def patch_actor(actor,c):
    clips=actor['animations'];setup={b['name']:b for b in actor['bones']}
    for wid,item in c.items():
        if not wid.startswith('weapon-') or item.get('slot')!='slot-secondary':continue
        comp=next((x for x in item.get('components',[]) if 'states' in x and 'animation' in x),None)
        if not comp:continue
        states=comp['states']
        if wid[7:] not in EXCLUDED:
            for action in ('hold','hit'):
                source=states.get(action)
                if not source or source not in clips:continue
                if source.startswith('refined-low-'):continue
                clip=deepcopy(clips[source]);tracks=clip.get('bones',{})
                if not all(n in tracks for arm in ARMS for n in arm):continue
                duration=max([k.get('time',0) for b in tracks.values() for keys in b.values() for k in keys] or [.08])
                result=arm_tracks()
                for i in range(25):
                    t=duration*i/24
                    near,np=wrist(setup,tracks,ARMS[0],t);far,fp=wrist(setup,tracks,ARMS[1],t)
                    # Rig X points up the chest: lower both wrists one rig unit. Keep the
                    # weapon hand axis; tuck the support palm slightly around the grip.
                    near-=1.0;far-=1.0
                    far=near+direction(np)*complex(.4,-.3)
                    fp=np+15
                    put_arm(result,setup,ARMS[0],t,near,np)
                    put_arm(result,setup,ARMS[1],t,far,fp)
                tracks.update(result)
                name='refined-low-'+wid+'-'+action;clips[name]=clip;states[action]=name
        hold=states.get('hold')
        if hold not in clips:continue
        # A full shoulder swing, with a flexing elbow and a relaxed wrist. The free arm
        # crosses the torso's side, instead of hovering next to the weapon.
        pose=sprint(clips,setup,hold,True);tracks=pose['bones']
        for n in ARMS[1]:tracks[n]={'rotate':[]}
        tracks['hand2']['translate']=[{}]
        for i in range(33):
            t=.64*i/32;phase=2*pi*i/32
            upper=190+38*sin(phase);elbow=78+16*sin(phase-.45)
            vals=(upper-setup['hand2']['rotation'],elbow-setup['palm2']['rotation'],
                  -setup['holder-secondary']['rotation']+8*sin(phase+.35))
            for n,v in zip(ARMS[1],vals):
                keys=tracks[n]['rotate'];last=keys[-1]['value'] if keys else v
                keys.append({'time':round(t,5),'value':round(last+(v-last+180)%360-180,3)})
        # Same cycle length for both arms.
        for n in ARMS[0]:
            for keys in tracks[n].values():
                for k in keys:
                    if 'time' in k:k['time']=round(k['time']*.64/.56,5)
        clips['sprint-short-'+hold]=pose
    fallback=next(s['attachments']['hat']['package'] for s in actor['skins'] if 'package' in s.get('attachments',{}).get('hat',{}))
    for skin in actor['skins']:
        at=skin.setdefault('attachments',{});package=at.get('hat',{}).get('package',fallback)
        at.setdefault('mask',{})['anon-package']=deepcopy(package)

def build(source,dest):
    with ZipFile(source) as z:
        data=json.loads(z.read('content.json'));c=data['content'];changes={}
        # Keep inert legacy IDs for old saved loadouts, but remove the perk from selection.
        c['sl-pl-anon']['enabled']=False
        c['player-anon']['components']=[p for p in c['player-anon'].get('components',[]) if not p['class'].endswith('ReplaceSlotComponent')]
        c['sl-msk-anon']={'class':'content.shop.CustomAnimationSlotItem','access':'byDefault','category':'mask','slot':'slot-mask','index':30,'items':[],
            'name':'ITEM_SPECIAL_ANON','description':'ITEM_SPECIAL_MASK_DESC','tags':'unique','components':[
            {'class':'content.components.IconComponent','tag':'client','icon':'icon-shop-special-anon'},
            {'class':'content.components.ReplaceSlotComponent','replace':{'mask':'anon-package'}}]}
        # Container drops should award the mask, not the retired specialization.
        def rewards(v):
            if isinstance(v,dict):
                for k,x in v.items():
                    if k=='content' and x=='sl-pl-anon':v[k]='sl-msk-anon'
                    else:rewards(x)
            elif isinstance(v,list):
                for x in v:rewards(x)
        rewards(c)
        path='content/animations/actor.json'
        if path in z.namelist():
            actor=json.loads(z.read(path));patch_actor(actor,c);changes[path]=encode(actor)
        else:
            # Server must use the same renamed actor states even without visual assets.
            for wid,item in c.items():
                if not wid.startswith('weapon-') or wid[7:] in EXCLUDED or item.get('slot')!='slot-secondary':continue
                for comp in item.get('components',[]):
                    st=comp.get('states',{})
                    for action in ('hold','hit'):
                        if st.get(action):st[action]='refined-low-'+wid+'-'+action
        texts=json.loads(z.read('data/texts.json'))
        texts['data']['ITEM_SPECIAL_TRAINING_DESC'].update({
            'RU':'Двойное нажатие бега: тактический спринт на 2,4 с, задержка 1 с. Смена стоек на 30% быстрее.',
            'EN':'Double-tap Run: tactical sprint for 2.4 s, with a 1 s cooldown. Stance changes are 30% faster.'})
        changes['data/texts.json']=encode(texts)
        changes['content.json']=encode(data)
        if '__H' in z.namelist():
            hashes=json.loads(z.read('__H'));hashes.update({n:zlib.crc32(v) for n,v in changes.items()});changes['__H']=encode(hashes)
        with ZipFile(dest,'w',ZIP_DEFLATED,compresslevel=3) as out:
            for entry in z.infolist():out.writestr(entry,changes.get(entry.filename,z.read(entry)))
if __name__=='__main__':
    import sys
    build(Path(sys.argv[1]),Path(sys.argv[2]))
