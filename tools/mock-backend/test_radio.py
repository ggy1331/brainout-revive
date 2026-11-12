"""Deterministic radio clock, permissions, persistence, requests and URL tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from services.radio import Radio
from services.radio_media import video_id
from services.common import HttpError


class Store:
    def __init__(self): self.data = {}
    def get(self, c, k, default=None): return self.data.get((c, k), default)
    def put(self, c, k, v): self.data[c, k] = v


class RadioTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.store = Store()
        self.radio = Radio(self.store, lambda: self.now)
        self.present = {'owner', 'guest'}

    def state(self): return self.radio.snapshot(lambda a: a in self.present)
    def command(self, op, owner=True, **args):
        return self.radio.command('owner' if owner else 'guest', owner, dict(op=op, **args))
    def add(self, owner=True):
        self.command('add', owner, video='BaW_jenozKc', duration=20, title='Test')
        return self.radio.queue[-1]['id']

    def test_clock_seek_pause_and_late_join(self):
        first = self.add()
        self.now += 5
        self.assertEqual(self.state()['position'], 5)
        self.command('pause')
        self.now += 7
        self.assertEqual(self.state()['position'], 5)
        self.command('seek', position=13)
        self.assertEqual(self.state()['position'], 13)
        self.command('pause')
        self.now += 2
        self.assertEqual(self.state()['position'], 15)
        self.assertEqual(self.state()['current'], first)

    def test_order_repeat_shuffle_and_removal(self):
        a, b, c = self.add(), self.add(), self.add()
        self.command('move', id=c, index=1)
        self.now += 21
        self.assertEqual(self.state()['current'], c)
        self.command('next')
        self.assertEqual(self.state()['current'], b)
        self.command('next')
        self.assertEqual(self.state()['current'], a)
        self.command('shuffle')
        self.command('next')
        self.assertNotEqual(self.state()['current'], a)
        self.command('remove', id=self.state()['current'])
        self.assertIn(self.state()['current'], [t['id'] for t in self.state()['queue']])

    def test_guest_lifetime_and_persistence(self):
        a, guest = self.add(), self.add(False)
        self.command('play', id=guest)
        self.present.remove('guest')
        self.assertEqual(self.state()['current'], a)
        self.assertEqual(len(self.state()['queue']), 1)
        self.add(False)
        restored = Radio(self.store)
        self.assertEqual([t['id'] for t in restored.queue], [a])

    def test_guest_cannot_control(self):
        a = self.add()
        for op in ('next', 'pause', 'seek', 'play', 'remove', 'move', 'shuffle'):
            with self.assertRaises(HttpError) as cm:
                self.command(op, False, id=a, position=5, index=0)
            self.assertEqual(cm.exception.status, 403)

    def test_empty_queue_and_invalid_values(self):
        a = self.add()
        self.command('remove', id=a)
        self.assertEqual(self.state()['current'], '')
        self.assertTrue(self.state()['paused'])
        for duration in (float('nan'), float('inf'), -1, 999999, 'bad'):
            with self.assertRaises(HttpError):
                self.command('add', video='BaW_jenozKc', duration=duration)

    def test_url_restrictions(self):
        for url in ('https://youtu.be/BaW_jenozKc?t=3', 'https://www.youtube.com/watch?v=BaW_jenozKc',
                    'https://www.youtube.com/shorts/BaW_jenozKc'):
            self.assertEqual(video_id(url), 'BaW_jenozKc')
        for url in ('file:///secret', 'http://localhost/watch?v=BaW_jenozKc',
                    'https://youtube.com.evil/watch?v=BaW_jenozKc', '--exec calc.exe',
                    'https://youtube.com/playlist?list=test'):
            with self.assertRaises(HttpError): video_id(url)


if __name__ == '__main__': unittest.main()
