"""Build model-specific single-sidearm poses on the shared character rig."""
from copy import deepcopy
from math import sin, pi
from arm_animations import component, profile, wrist
from paired_reload_art import STAGING, authored_reload, smooth, solve
from pair_refinement import ARMS, direction
from gameplay_package import encode
import json


def make_action(native, action, setup, carry, rest, geometry, styling):
    well,chamber,_,length = geometry
    tilt,draw,_ = styling
    tmax = max([.08]+[key.get('time',0) for tr in native.get('bones',{}).values()
                       for channel in tr.values() for key in channel]+
               [e.get('time',0) for e in native.get('events',[])])
    timed = action not in ('hold','aim')
    frames = [i/24 for i in range(1,int(tmax*24)+1)] if timed else []
    tracks = {a[0]:{'translate':deepcopy(carry[a[0]]['translate'])} for a in ARMS}
    for t in sorted({0,tmax,*frames}):
        phase=t/tmax
        kick=smooth(phase/.19)*(1-smooth((phase-.19)/.81))
        reach=sin(pi*phase)**2
        hand,axis=rest[ARMS[0]]
        grip,angle=rest[ARMS[1]]
        aiming=action in ('aim','aimHit')
        if aiming:
            hand += complex(.75,-.6)
            grip += complex(.75,-.6)
            axis += 1.5
        if action in ('hit','aimHit'):
            lift=kick*(.7+draw*.14)
            hand += complex(lift,lift*.8)
            grip += complex(lift*.8,lift*.85)
            axis+=kick*(5+tilt*.24)
        elif action in ('cock','fetch','addRound'):
            hand+=complex(-.65,2.1)*reach
            axis+=reach*(tilt*.8 if action!='fetch' else -tilt)
            contact=hand+direction(axis)*(chamber if action!='fetch' else well)*.23
            grip+=(contact-grip)*reach
            angle+=reach*25
        solve(tracks,setup,carry,ARMS[0],t,hand,axis)
        solve(tracks,setup,carry,ARMS[1],t,grip,angle)
    pose={'bones':tracks}
    for k in ('slots','events'):
        if native.get(k):pose[k]=deepcopy(native[k])
    return pose


def build_solos(content,actor,read,changes):
    for key in ('sl-sec-r8','sl-pair-r8'):
        if key in content:
            spec=content[key]['instrument']
            if isinstance(spec.get('skins'),list):
                spec['skins']=[skin for skin in spec['skins'] if skin]
    for key in ('sl-sec-m98kobrez','sl-pair-m98kobrez'):
        if key in content:
            upgrades=content[key]['instrument'].get('upgrades',{})
            if upgrades.get('silencer')=='upgrade-m98kobrez-silencer' and upgrades['silencer'] not in content:
                del upgrades['silencer']
    content['player-fast'].pop('states',None)
    content['player-fast'].pop('jumpForce',None)
    setup={b['name']:b for b in actor['bones']}
    clips=actor['animations']
    for pair in [k for k in content if k.startswith('paired-weapon-')]:
        wid=pair[7:]
        item=content[wid]
        comp=component(item)
        states=comp['states']
        if states.get('fetch')=='reload-1hand1-fetch':
            states['fetch']='reload-1hand-fetch'
            component(content[pair])['states']['fetch']=states['fetch']
        path='content/'+content[comp['animation']]['animation'].split(':')[1]
        model=json.loads(read(path))
        geometry=profile(model,wid)
        tilt,draw,guide=STAGING.get(wid[7:],(21,4,-104))
        # Place both wrists on the compact grip or move the support wrist out
        # to the receiver on the long models. Author poses directly in rig space.
        carry={a[0]:{'translate':[{}]} for a in ARMS}
        gun=complex(.3-draw*.13,-10.8+draw*.16)
        pitch=-90+(tilt-20)*.1
        support=gun+direction(pitch)*complex(min(6,max(1.2,geometry[3]*.17)), -2)*.6
        for arm,pos,rotation in zip(ARMS,(gun,support),(pitch,pitch+12)):
            seed=clips['paired-extend']['bones']
            neutral={n:dict(seed[n]) for n in arm}
            neutral[arm[0]]['translate']=[{}]
            solve(carry,setup,neutral,arm,0,pos,rotation)
        rest={arm:wrist(setup,carry,arm,0) for arm in ARMS}
        actions={name:act for act,name in states.items() if name in clips}
        for action in ('reload','fetch','cock','addRound','aim','aimHit','hold','hit'):
            for key,v in content.items():
                if key.startswith(('skin-'+wid+'-','upgrade-'+wid[7:]+'-')):
                    for part in v.get('components',[]):
                        rep=part.get('replace',{})
                        if isinstance(rep,dict) and rep.get(action) in clips:actions[rep[action]]=action
        if item.get('looseCylinder'):
            prefix='rsh-cylinder-' if item.get('groupEjection') else 'cylinder-'
            for i in range(1,item['primary']['clipSize']+1):actions[prefix+str(i)]='reload'
        for name,action in actions.items():
            native=clips[name]
            if action=='reload':
                pose=authored_reload(native,setup,carry,'single',model,wid,rest)
                if native.get('slots',{}).get('special'):
                    pose.setdefault('slots',{})['special']=deepcopy(native['slots']['special'])
            else:
                pose=make_action(native,action,setup,carry,rest,geometry,(tilt,draw,guide))
            clips['solo-'+wid+'-'+name]=pose
        mount=next((s for s in model['slots'] if s['name'] in ('clip','magazine','grip')),None)
        if not mount or not any(e.get('string') in ('unloaded','welrod-take') for e in clips[states['reload']].get('events',[])):continue
        if mount['bone']!='pair-mag-travel':
            model['bones'].append({'name':'pair-mag-travel','parent':mount['bone']})
            mount['bone']='pair-mag-travel'
        model['slots'].remove(mount)
        model['slots'].insert(0,mount)
        for p in item['components']:
            if isinstance(p.get('actions'),list):
                p['actions']=[a for a in p['actions'] if not(a.get('type')=='updateSlot' and a.get('slot')==mount['name'] and a.get('for') in ('unloaded','loaded','welrod-take','welrod-seat'))]
        changes[path]=encode(model)
def perk_text(text):
    text['ITEM_SPECIAL_TRAINING_DESC'].update(dict(
        EN="Double-tap Run and hold on the second press for a short tactical sprint.",
        RU="Дважды нажмите кнопку бега и удерживайте её после второго нажатия для короткого тактического спринта.",
        UA="Двічі натисніть кнопку бігу й утримуйте її після другого натискання для короткого тактичного спринту.",
        BE="Двойчы націсніце кнопку бегу і ўтрымлівайце яе пасля другога націску для кароткага тактычнага спрынту.",
        DE="Lauftaste zweimal drücken und beim zweiten Mal halten, um kurz taktisch zu sprinten.",
        FR="Appuyez deux fois sur la touche de course et maintenez-la la seconde fois pour un court sprint tactique.",
        ES="Pulsa dos veces el botón de correr y mantenlo pulsado la segunda vez para un breve esprint táctico.",
        IT="Premi due volte il comando di corsa e tienilo premuto la seconda volta per un breve scatto tattico.",
        PL="Naciśnij dwukrotnie klawisz biegu i przytrzymaj go za drugim razem, aby wykonać krótki sprint taktyczny.",
        PT="Pressione o botão de corrida duas vezes e segure na segunda para um breve sprint tático.",
        CS="Dvakrát stiskni klávesu běhu a při druhém stisku ji podrž pro krátký taktický sprint.",
        EL="Πάτησε δύο φορές το πλήκτρο τρεξίματος και κράτησέ το τη δεύτερη φορά για ένα σύντομο τακτικό σπριντ.",
        HR="Dvaput pritisni tipku za trčanje i zadrži je drugi put za kratki taktički sprint.",
        HU="Nyomd meg kétszer a futás gombját, és másodszor tartsd lenyomva egy rövid taktikai sprinthez.",
        KO="달리기 버튼을 두 번 누르고 두 번째에 길게 누르면 짧은 전술 질주를 합니다.",
        LT="Dukart spauskite bėgimo klavišą ir antrą kartą palaikykite, kad trumpai sprintuotumėte.",
        LV="Divreiz nospied skriešanas taustiņu un otrajā reizē turi to, lai veiktu īsu taktisko sprintu.",
        NL="Druk tweemaal op de rentoets en houd hem de tweede keer ingedrukt voor een korte tactische sprint.",
        RO="Apasă de două ori tasta de alergare și ține-o apăsată a doua oară pentru un sprint tactic scurt.",
        SL="Dvakrat pritisni tipko za tek in jo drugič zadrži za kratek taktični sprint.",
        SR="Двапут притисни тастер за трчање и задржи га други пут за кратак тактички спринт.",
        TR="Kısa bir taktik depar için koşma tuşuna iki kez bas ve ikinci basışta basılı tut.",
        ZH="连按两次奔跑键，第二次按住即可进行短暂的战术冲刺。"))
