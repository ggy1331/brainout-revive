"""Prove media paths use memory/pipes, with bounded writes and decoder cleanup."""
import io
import json
import sys
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
from services import radio_media as media
from services.common import HttpError


class Decoder:
    def __init__(self):
        self.stdout = io.BytesIO(b'\x01\x02' * 15000)
        self.killed = False
    def poll(self): return None if not self.killed else 0
    def kill(self): self.killed = True
    def wait(self): return 0


class Handler:
    def __init__(self, broken=False):
        self.connection = SimpleNamespace(setsockopt=lambda *a: None, settimeout=lambda *a: None)
        self.parts, self.headers = [], {}
        def write(data):
            if broken: raise BrokenPipeError()
            self.parts.append(data)
        self.wfile = SimpleNamespace(write=write)
    def send_response(self, status): self.status = status
    def send_header(self, key, value): self.headers[key] = value
    def end_headers(self): pass


class StreamTests(unittest.TestCase):
    def setUp(self):
        media._metadata.clear()
        self.info = dict(video='jNQXAC9IVRw', title='Test', duration=19,
                         url='https://example.invalid/audio', headers={})

    def test_metadata_never_opens_files_and_disables_ytdlp_cache(self):
        app = SimpleNamespace()
        with patch.object(media, 'tool', return_value='yt-dlp'), \
             patch.object(media, 'run', return_value=json.dumps(self.info)) as run, \
             patch('builtins.open', side_effect=AssertionError('Disk write')), \
             patch.object(Path, 'open', side_effect=AssertionError('Disk write')):
            first = media.resolve(app, 'jNQXAC9IVRw')
            self.assertEqual(first['duration'], 19)
            self.assertNotIn('url', first)
            media.resolve(app, 'jNQXAC9IVRw')
            self.assertEqual(run.call_count, 1)
            self.assertIn('--no-cache-dir', run.call_args[0][0])
            self.assertIn('--skip-download', run.call_args[0][0])

    def test_pcm_is_bounded_and_decoder_closed_on_disconnect(self):
        for broken in (False, True):
            decoder, handler = Decoder(), Handler(broken)
            with patch.object(media, 'source', return_value=self.info), \
                 patch.object(media, 'tool', return_value='ffmpeg'), \
                 patch.object(media.subprocess, 'Popen', return_value=decoder) as spawn, \
                 patch.object(Path, 'open', side_effect=AssertionError('Disk write')):
                media.media(SimpleNamespace(), 'jNQXAC9IVRw', 7).serve(handler)
                command = spawn.call_args[0][0]
                self.assertEqual(command[-1], 'pipe:1')
                self.assertEqual(command[command.index('-ss')+1], '7.0')
                self.assertTrue(decoder.killed)
                self.assertTrue(decoder.stdout.closed)
                self.assertEqual(handler.headers['Cache-Control'], 'no-store')
                if not broken:
                    self.assertEqual(sum(map(len, handler.parts)), 30000)
                    self.assertLessEqual(max(map(len, handler.parts)), 8192)

    def test_invalid_seek_rejected_before_starting_decoder(self):
        for position in (-1, float('nan'), float('inf'), 'bad', 3601):
            with self.assertRaises(HttpError):
                media.media(SimpleNamespace(), 'jNQXAC9IVRw', position)

    def test_migration_removes_only_legacy_audio_not_playlist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'radio-cache'
            folder.mkdir()
            (folder / 'jNQXAC9IVRw.ogg').write_bytes(b'old audio')
            (folder / 'jNQXAC9IVRw.json').write_text('{}')
            (folder / 'keep.txt').write_text('unrelated')
            (root / 'hub-radio').mkdir()
            playlist = root / 'hub-radio/playlist.json'
            playlist.write_text('{"queue":[]}')
            media.clear_legacy_cache(SimpleNamespace(storage=SimpleNamespace(root=root)))
            self.assertEqual([p.name for p in folder.iterdir()], ['keep.txt'])
            self.assertTrue(playlist.exists())


if __name__ == '__main__': unittest.main()
