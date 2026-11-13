"""HK G11 sounds from GGY's recordings (both are a YouTube video "H&K G11/HD", recorded by GGY).

  reload source (7.4 s): magazine slid in from the top 1.0-2.1 s, locks at 2.91 s; pause;
      rotary cocking handle turned 6.2-6.8 s (click at 6.81 s).
  fire source (5.3 s): three bursts at 460 rpm (0.13 s between shots); the LAST shot of every
      burst has a free tail (0.495, 2.42, 4.385 s) -> three single-shot variants.

Output (mono, 44100 Hz, PCM16) in build/g11/audio:
  fire-1..3.wav   one shot each, 0.8 s, mean loudness FIRE_MEAN dB like ASh-12 fire (-17),
                  peaks held by a limiter at -3 dB (the recorded shots are thin: short peak, weak body);
  reload.wav      2.4 s, the magazine change only (the handle is the separate fetch, played by the
                  game only after an empty magazine): source 1.10-1.60 s (slides) at 0.25 s = the old
                  magazine pulled out, source 1.90-3.05 s at 1.15 s = the new one slid in, locks at
                  2.16 s. launcher/g11.py times the hand clip to these cues; peak -3 dB;
  fetch.wav       the cocking handle alone (1.0 s, click at 0.71 s), peak -3 dB.
Usage: python tools/weapon-art/build_g11_audio.py RELOAD.WAV FIRE.WAV FFMPEG.EXE
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/g11/audio'

FIRE_SHOTS = [0.495, 2.42, 4.385]
FIRE_LEN, FIRE_MEAN, LIMIT = 0.8, -19.0, 0.7
RELOAD_PARTS = [(1.10, 1.60, 0.25), (1.90, 3.05, 1.15)]   # source from, to, placed at
RELOAD_LEN = 2.4
FETCH_PART = (6.1, 7.1)
RELOAD_PEAK = -3.0


def level(ff, path, kind='max'):
    out = subprocess.run([ff, '-hide_banner', '-i', str(path), '-af', 'volumedetect', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    return float(re.search(kind + r'_volume: (-?[0-9.]+)', out).group(1))


def cut(ff, src, parts, dst, target, fade_out, mean=False, length=None):
    """parts (from, to[, at]) - joined one after another, or placed at `at` s on a `length` s track;
    short fades at every joint, peak (or mean) normalised to target dB"""
    filters, labels = [], []
    for i, part in enumerate(parts):
        a, b = part[:2]
        filters.append(f'[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,pan=mono|c0=0.5*c0+0.5*c1,aresample=44100,'
                       f'afade=t=in:d=0.01,afade=t=out:st={b - a - fade_out}:d={fade_out}[p{i}]')
        if len(part) > 2 and part[2] > 0:
            # explicit leading silence (adelay of this ffmpeg only shifts timestamps)
            filters.append(f'anullsrc=r=44100:cl=mono,atrim=0:{part[2]}[s{i}]')
            filters.append(f'[s{i}][p{i}]concat=n=2:v=0:a=1[q{i}]')
            labels.append(f'[q{i}]')
        else:
            labels.append(f'[p{i}]')
    if length:
        filters.append(''.join(labels) + f'amix=inputs={len(parts)}:normalize=0,apad,atrim=0:{length}[out]')
    else:
        filters.append(''.join(labels) + f'concat=n={len(parts)}:v=0:a=1[out]')
    tmp = dst.with_suffix('.tmp.wav')
    subprocess.run([ff, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(src), '-filter_complex',
                    ';'.join(filters), '-map', '[out]', '-ar', '44100', '-c:a', 'pcm_s16le', str(tmp)], check=True)
    gain = target - level(ff, tmp, 'mean' if mean else 'max')
    af = f'volume={gain}dB' + (f',alimiter=limit={LIMIT}:attack=1:release=40:level=disabled' if mean else '')
    subprocess.run([ff, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(tmp), '-af', af,
                    '-ar', '44100', '-c:a', 'pcm_s16le', str(dst)], check=True)
    tmp.unlink()
    print('%-11s %.2f s, gain %+.1f dB' % (dst.name, length or sum(p[1] - p[0] for p in parts), gain))


def main():
    reload_src, fire_src, ff = sys.argv[1:4]
    OUT.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(FIRE_SHOTS, 1):
        cut(ff, fire_src, [(t - 0.01, t - 0.01 + FIRE_LEN)], OUT / f'fire-{i}.wav', FIRE_MEAN, 0.3, mean=True)
    cut(ff, reload_src, RELOAD_PARTS, OUT / 'reload.wav', RELOAD_PEAK, 0.05, length=RELOAD_LEN)
    cut(ff, reload_src, [FETCH_PART], OUT / 'fetch.wav', RELOAD_PEAK, 0.05)


if __name__ == '__main__':
    main()
