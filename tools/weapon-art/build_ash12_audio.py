"""Convert the user-provided MW2019 Oden bank to game-ready PCM WAV.

Requires the portable vgmstream-cli decoder (pass its path as argument). Event to
WEM mappings were verified with wwiser + the PAYDAY 2 name list; no guessed groups.
"""
from pathlib import Path
import array
import audioop
import hashlib
import json
import math
import struct
import subprocess
import sys
import wave

ROOT=Path(__file__).resolve().parents[2]
BANK=ROOT/'tools/weapon-art/reference/ash12-oden.bnk'
OUT=ROOT/'build/ash12/audio'
GAME=ROOT/'data/packages/sounds/contents/content/sounds/ash12'
REGULAR=[370589041,588980768,133896818,100686234,140924713]
SUPPRESSED=[85182597,137311004,228973385]
RELOAD={'clip_in':472963915,'clip_in_place':1059901871,'clip_out':907653214,'grab_clip':79455714,'grab_end':756798118,'hand_release':591225509,'lever_pull':17865208,'lever_release':283993142,'take_new':891154560}
RATE=44100


def read_pcm(key):
    with wave.open(str(OUT/f'{key}.wav')) as w:
        raw=w.readframes(w.getnframes());channels=w.getnchannels();rate=w.getframerate()
        assert w.getsampwidth()==2
    if channels==2:raw=audioop.tomono(raw,2,.5,.5)
    elif channels!=1:raise ValueError(channels)
    if rate!=RATE:raw=audioop.ratecv(raw,2,1,rate,RATE,None)[0]
    return array.array('h',raw)


def write_pcm(name, samples):
    with wave.open(str(GAME/(name+'.wav')),'wb') as w:
        w.setparams((1,2,RATE,0,'NONE','not compressed'));w.writeframes(samples.tobytes())


def shot(key,gain):
    samples=read_pcm(key);step=int(RATE*.02);end=0
    for i in range(0,len(samples),step):
        block=samples[i:i+step]
        rms=math.sqrt(sum(v*v for v in block)/max(1,len(block)))
        if rms>64:end=i+len(block)
    samples=samples[:min(len(samples),max(int(.2*RATE),end+int(.08*RATE)))]
    fade=int(.012*RATE)
    return array.array('h',(int(v*gain*min(1,(len(samples)-i)/fade)) for i,v in enumerate(samples)))


def sequence(duration,events):
    result=[0]*round(duration*RATE)
    for time,name,gain in events:
        samples=read_pcm(RELOAD[name]);start=round(time*RATE)
        for i,v in enumerate(samples[:max(0,len(result)-start)]):result[start+i]+=int(v*gain)
    assert max(map(abs,result))<32767,'Reload mix would clip'
    return array.array('h',result)


def main():
    decoder=Path(sys.argv[1]).resolve();OUT.mkdir(parents=True,exist_ok=True);GAME.mkdir(parents=True,exist_ok=True)
    raw=BANK.read_bytes();chunks={};pos=0
    while pos+8<=len(raw):
        tag=raw[pos:pos+4];n=struct.unpack_from('<I',raw,pos+4)[0];chunks[tag]=raw[pos+8:pos+8+n];pos+=8+n
    entries={}
    for pos in range(0,len(chunks[b'DIDX']),12):
        key,start,size=struct.unpack_from('<III',chunks[b'DIDX'],pos);entries[key]=chunks[b'DATA'][start:start+size]
    for key in set(REGULAR+SUPPRESSED+list(RELOAD.values())):
        wem=OUT/f'{key}.wem';wem.write_bytes(entries[key])
        subprocess.run([str(decoder),'-i','-o',str(wem.with_suffix('.wav')),str(wem)],check=True,capture_output=True)
    for i,key in enumerate(REGULAR,1):write_pcm(f'fire-{i}',shot(key,.55))
    for i,key in enumerate(SUPPRESSED,1):write_pcm(f'fire-s-{i}',shot(key,.4))
    write_pcm('reload',sequence(2.8,[(.08,'grab_clip',.7),(.48,'clip_out',.7),(1.15,'take_new',.7),(1.65,'clip_in',.7),(2.08,'clip_in_place',.65),(2.24,'grab_end',.6),(2.58,'hand_release',.6)]))
    write_pcm('fetch',sequence(.65,[(.02,'lever_pull',.75),(.3,'lever_release',.75)]))
    (ROOT/'tools/weapon-art/reference/ash12-audio-provenance.json').write_text(json.dumps({'source':'User supplied MW2019 Oden sounds.zip / weapon_shak12.bnk','bank_sha256':hashlib.sha256(raw).hexdigest(),'event_regular':'shak12_fire [suppressed=regular]','regular_wem_ids':REGULAR,'event_suppressed':'shak12_fire [suppressed=suppressed_a]','suppressed_wem_ids':SUPPRESSED,'reload_events':{'wp_shak12_'+k:v for k,v in RELOAD.items()},'format':'PCM16 mono 44100 Hz; trailing near-silence trimmed on shots; gains 0.55 regular / 0.4 suppressed; staged reload 2.8 s and fetch 0.65 s'},indent=2)+'\n',encoding='utf-8')
    print('Built 5 regular shots, 3 suppressed shots, reload and fetch WAVs.')


if __name__=='__main__':main()
