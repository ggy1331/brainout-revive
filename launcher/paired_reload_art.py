"""Author dual-wield reloads in wrist space. Old clips supply gameplay cues only."""
from copy import deepcopy
from math import acos, degrees
from pair_refinement import ARMS, angle, direction, offset

# Presentation pitch, draw towards the chest, and magazine guide angle.
# The first two are actor-space art direction; the third is in sprite space.
STAGING = {
    'aps':(18,4,-102), 'baltiets':(23,3.6,-106), 'beretta':(21,3.8,-104),
    'browning':(24,3.7,-107), 'colt':(25,4,-108), 'coltds':(39,3.4,-90),
    'cz75':(20,3.6,-106), 'desert':(15,4.8,-103), 'desert50ae':(13,5,-103),
    'fiveseven':(19,4.1,-103), 'flare':(35,3.7,-90), 'fnx45':(20,4.2,-104),
    'fort12':(23,3.6,-105), 'jericho':(18,4.2,-105), 'judge':(29,4.4,-90),
    'k23p':(14,4.8,-95), 'luger':(28,3.7,-115), 'm93r':(16,4.3,-104),
    'm98kobrez':(11,5,-90), 'magnum':(30,4.4,-90), 'makarov':(26,3.5,-104),
    'mat49':(10,5,-91), 'mateba':(26,4.8,-90), 'mauser':(16,4.3,90),
    'mp443':(21,3.8,-106), 'mp5k':(11,5.2,-96), 'mr412':(34,4,-90),
    'msp':(41,3.3,-90), 'nagant':(37,3.8,-90), 'ots33':(17,4,-103),
    'p50':(7,5.6,90), 'qsz92':(19,3.9,-105), 'p99':(24,3.6,-107), 'peacemaker':(38,4.1,-90),
    'pistol':(23,3.8,-105), 'pistol-s':(19,4.2,-105), 'r8':(28,4.6,-90),
    'rgm40':(12,5,-90), 'rhino':(32,3.9,-90), 'rsh12':(23,5,-90),
    'scorpion':(13,5,-82), 'sigsauer':(22,4,-105), 'supershorty':(12,5.4,-90),
    'taurus':(22,3.7,-104), 'tec9':(12,4.7,-90), 'tt':(26,3.6,-106),
    'usp':(20,4,-105), 'usp-match':(16,4.6,-105), 'vp70':(21,4,-104),
    'welrod':(14,4.5,-92),
}


def smooth(t):
    t = max(0, min(1, t))
    return t*t*(3-2*t)


def envelope(t, start, stop):
    return smooth((t-start)/max(.00001, stop-start))


def vector_key(t, point):
    return dict(time=round(t,5), x=round(point.real,4), y=round(point.imag,4))


def align_markers(actor):
    # The visible fallback sprite is in holder space. The runtime reads its
    # child's raw translation in gun pixels to drive a real magazine attachment.
    for side in ('left','right'):
        name = 'pair-magazine-'+side
        marker = next(b for b in actor['bones'] if b['name']==name)
        alignment = name+'-alignment'
        if marker['parent'] != alignment:
            index = actor['bones'].index(marker)
            actor['bones'].insert(index, dict(name=alignment, parent=marker['parent']))
            marker['parent'] = alignment


def solve(tracks, setup, carry, arm, t, point, pitch):
    upper, palm, holder = [setup[n] for n in arm]
    origin = offset(upper)+offset(carry[arm[0]]['translate'][0])
    delta = (point-origin)/upper.get('scaleX',1)
    a,b = abs(offset(palm)),abs(offset(holder))
    elbow = degrees(acos(max(-.94,min(.995,(abs(delta)**2-a*a-b*b)/(2*a*b)))))
    first = angle(delta)-angle(a+b*direction(elbow))-angle(offset(palm))
    second = first+angle(offset(palm))+elbow-angle(offset(holder))
    angles = (first-upper['rotation'],second-first-palm['rotation'],pitch-second-holder['rotation'])
    for n,value in zip(arm,angles):
        keys = tracks.setdefault(n,{}).setdefault('rotate',[])
        previous = keys[-1]['value'] if keys else carry[n]['rotate'][0]['value']
        keys.append(dict(time=round(t,5),value=round(previous+(value-previous+180)%360-180,3)))


def authored_reload(native, setup, carry, side, model, wid, rest):
    from arm_animations import profile
    well,chamber,_,size = profile(model,wid)
    short = wid.removeprefix('weapon-')
    pitch, draw, guide = STAGING.get(short,(21,min(5,3+size*.07),-104))
    events = deepcopy(native.get('events',[]))
    cues = {e.get('string'):e.get('time',0) for e in events}
    end = max([.15]+[k.get('time',0) for tr in native.get('bones',{}).values()
                       for keys in tr.values() for k in keys]+list(cues.values()))
    out = cues.get('unloaded',cues.get('welrod-take'))
    seat = cues.get('loaded',cues.get('welrod-seat'))
    detachable = out is not None and seat is not None and seat>out
    marker = 'pair-magazine-'+('left' if side=='single' else side)
    scale = model['bones'][0].get('scaleX',1)
    if short=='mauser':well=complex(12,8)
    if short=='welrod':well=complex(-1,-3)
    if abs(well)<.01:well=complex(-.5,-2.5)
    depth = 23
    for skin in model['skins']:
        for slot in ('magazine','clip'):
            for sprite in skin.get('attachments',{}).get(slot,{}).values():
                depth=max(depth,sprite.get('height',0)+4)
    if short=='p50':depth=24
    active,other = ARMS if side!='right' else ARMS[::-1]
    tracks={a[0]:{'translate':[deepcopy(carry[a[0]]['translate'][0])]} for a in ARMS}
    pose={'bones':tracks}
    if events:pose['events']=events
    times={0,end,*cues.values(),*(e.get('time',0) for e in events)}
    times.update(i/30 for i in range(1,int(end*30)+1))
    if detachable:
        gap=seat-out
        clear,leave,arrive,line=(out+gap*f for f in (.32,.43,.54,.64))
        times.update((clear,leave,arrive,line))
        tracks[marker]={'translate':[]}
        tracks[marker+'-alignment']={'translate':[]}
        pose['slots']={marker:{'attachment':[{'name':None},{'time':out,'name':'magazine'},
            {'time':leave,'name':None},{'time':arrive,'name':'magazine'},{'time':seat,'name':None}]}}
    load_events=[e.get('time',0) for e in events if (e.get('string') or '').startswith(('add-bullet','insert','drop-bullet'))]
    if not detachable and not load_events:load_events=[end*.56]
    base,axis=rest[active]
    off,offaxis=rest[other]
    # Both hands use the same shoulder-relative workspace, with clearance for
    # the second slide. The support pistol stays tipped away from the active one.
    for t in sorted(times):
        stage=envelope(t,0,out if detachable else end*.20)*(1-envelope(t,seat if detachable else end*.79,end))
        slide=0j
        if detachable:
            ext=envelope(t,out,clear)*(1-envelope(t,line,seat))
            sweep=envelope(t,clear,leave)*(1-envelope(t,arrive,line))
            slide=direction(guide)*depth*ext + complex(-6,0)*sweep
            tracks[marker]['translate'].append(vector_key(t,slide))
            tracks[marker+'-alignment']['translate'].append(vector_key(t,well*scale+slide*(scale-1)))
            beat=envelope(t,line,seat)*(1-envelope(t,seat,min(end,seat+.14)))
            local=well+slide*.44
        else:
            beat=max((smooth(1-abs(t-e)/min(.115,end*.15)) for e in load_events),default=0)
            local=chamber+complex(-5*(1-beat),-3*(1-beat))
        gun=axis+stage*(pitch-3*beat)
        # Forearms fold towards a common point just forward of the chest.
        working=complex(-3.1,-9.1+draw*.48)
        anchor=base+(working-base)*stage+complex(-.25,.32)*beat*stage
        hand_scale=setup[active[0]].get('scaleX',1)*setup[active[2]].get('scaleX',1)*scale
        contact=anchor+direction(gun)*local*hand_scale
        # Offset the parked grip so the two silhouettes remain distinct.
        support=off+(contact+(0j if side=='single' else complex(-1.65,1.2))-off)*stage
        solve(tracks,setup,carry,active,t,anchor,gun)
        solve(tracks,setup,carry,other,t,support,offaxis-stage*(35+pitch*.38))
    # Filter the redundant elbow/shoulder joints in time. Keep the designed
    # wrist angle and endpoints; very short event intervals must not snap a hand.
    from bisect import bisect_right
    for arm in (active,other):
        rotations=[tracks[n]['rotate'] for n in arm]
        stamps=[k['time'] for k in rotations[0]]
        values=[[k['value'] for k in keys] for keys in rotations]
        def sample(row,t):
            if t<=0:return row[0]
            if t>=stamps[-1]:return row[-1]
            i=bisect_right(stamps,t)-1
            f=(t-stamps[i])/(stamps[i+1]-stamps[i])
            return row[i]+(row[i+1]-row[i])*f
        for i,t in enumerate(stamps):
            width=min(.095,t,end-t)
            for j in (0,1):
                pts=[sample(values[j],t+width*f/4) for f in range(-4,5)]
                rotations[j][i]['value']=round(sum(v*w for v,w in zip(pts,(1,2,3,4,5,4,3,2,1)))/25,3)
            rotations[2][i]['value']=round(sum(row[i] for row in values)-sum(keys[i]['value'] for keys in rotations[:2]),3)
    if side=='right':
        for e in events:
            if e['name']=='instrument-action':e['string']='offhand/'+e['string']
    return pose
