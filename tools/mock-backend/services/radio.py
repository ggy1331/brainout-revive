"""Authoritative hub radio. Call under Hub.lock; no network or media work here."""
import math
import random
import re
import secrets
import time
from .common import HttpError


class Radio:
    def __init__(self, storage, clock=time.monotonic):
        self.storage, self.clock = storage, clock
        saved = storage.get('hub-radio', 'playlist', {}) if storage else {}
        self.queue = saved.get('queue', [])
        self.shuffle = saved.get('shuffle', False)
        self.current = self.queue[0]['id'] if self.queue else ''
        self.started, self.offset = clock(), 0.0
        self.paused, self.revision = not bool(self.queue), 0

    def save(self):
        if self.storage:
            self.storage.put('hub-radio', 'playlist', {
                'queue': [t for t in self.queue if not t.get('requester')], 'shuffle': self.shuffle})

    def track(self):
        return next((t for t in self.queue if t['id'] == self.current), None)

    def position(self):
        return self.offset + (0 if self.paused else self.clock() - self.started)

    def select(self, track):
        self.current = track['id'] if track else ''
        self.offset, self.started = 0.0, self.clock()
        self.paused = not bool(track)
        self.revision += 1

    def advance(self):
        if not self.queue:
            self.select(None)
            return
        idx = next((i for i, t in enumerate(self.queue) if t['id'] == self.current), -1)
        choices = [t for t in self.queue if t['id'] != self.current]
        self.select(random.choice(choices) if self.shuffle and choices else self.queue[(idx + 1) % len(self.queue)])

    def snapshot(self, present):
        old = len(self.queue)
        self.queue = [t for t in self.queue if not t.get('requester') or present(t['requester'])]
        if len(self.queue) != old:
            self.revision += 1
        if not self.track() and self.queue:
            self.select(self.queue[0])
        elif not self.queue and self.current:
            self.select(None)
        track = self.track()
        if track and not self.paused and self.position() >= track['duration']:
            self.advance()
        return {'queue': [dict(t) for t in self.queue], 'current': self.current,
                'position': self.position(), 'paused': self.paused,
                'shuffle': self.shuffle, 'revision': self.revision}

    def command(self, account, owner, args):
        op = args.get('op')
        if not owner and op != 'add':
            raise HttpError(403, {'error': 'Управление радио доступно хозяину хаба.'})
        if op == 'add':
            video = str(args.get('video', ''))
            try:
                duration = float(args.get('duration', 0))
            except (ValueError, TypeError):
                duration = 0
            if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video) or not math.isfinite(duration) or not 1 <= duration <= 3600:
                raise HttpError(400, {'error': 'Нужен ролик YouTube продолжительностью до часа.'})
            if len(self.queue) >= 100 or (not owner and sum(t.get('requester') == account for t in self.queue) >= 10):
                raise HttpError(409, {'error': 'Очередь заполнена.'})
            self.queue.append({'id': secrets.token_hex(8), 'video': video, 'duration': duration,
                               'title': str(args.get('title', video))[:180],
                               'requester': '' if owner else account})
            if not self.current:
                self.select(self.queue[-1])
        elif op == 'next':
            self.advance()
        elif op == 'pause':
            self.offset, self.started = self.position(), self.clock()
            self.paused = not self.paused
        elif op == 'shuffle':
            self.shuffle = not self.shuffle
        elif op in ('play', 'remove', 'move'):
            track = next((t for t in self.queue if t['id'] == args.get('id')), None)
            if not track:
                raise HttpError(404)
            if op == 'play':
                self.select(track)
            elif op == 'remove':
                idx = self.queue.index(track)
                self.queue.remove(track)
                if track['id'] == self.current:
                    self.select(self.queue[idx % len(self.queue)] if self.queue else None)
            else:
                try:
                    target = int(args.get('index'))
                except (ValueError, TypeError):
                    raise HttpError(400)
                self.queue.remove(track)
                self.queue.insert(max(0, min(len(self.queue), target)), track)
        elif op == 'seek':
            try:
                position = float(args.get('position'))
            except (ValueError, TypeError):
                raise HttpError(400)
            if not math.isfinite(position) or not self.track():
                raise HttpError(400)
            self.offset = max(0, min(position, self.track()['duration']))
            self.started = self.clock()
        else:
            raise HttpError(400)
        self.revision += 1
        self.save()
        return {'ok': True}
