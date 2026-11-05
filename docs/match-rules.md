# Свои правила матчей

Всё правится в текстовых файлах в `bin/server/`, перекомпилировать ничего не нужно — только перезапустить сервер.

## Быстро: `play-match.bat`

```
play-match.bat [режим] [карта] [пресет] [боты]      (- = пропустить)
```

| Пример | Что будет |
|---|---|
| `play-match.bat gungame mall - 6` | GunGame на «Торговом центре», 6 ботов |
| `play-match.bat deathmatch - knife-only 4` | Все против всех, только ножи, карта любая подходящая |
| `play-match.bat normal hospital super-hard` | Обычный режим, хардкор без миникарты и трассеров |
| `play-ctf.bat 6` | Захват флага на `bunker_ctf`, 6 ботов |
| `play-duel.bat` | Дуэль 1×1, только живые игроки |

Режим закрепляется на следующие матчи, карты меняются среди тех, что его поддерживают.

**Режимы:** `normal`, `deathmatch`, `domination`, `assault`, `ctf`, `foxhunt` (Охотник), `gungame`. Зомби — отдельно, `play-zombie.bat`.

**Карты и какие режимы на них идут** — раздел `sets` в `maps-set.json`.

## Пресеты (`server-settings.json` → `presets`)

| Пресет | Правила |
|---|---|
| `knife-only` | Только нож |
| `toz34-only` | Только ТОЗ-34 и нож |
| `classic-only` | Только «классическое» оружие |
| `no-primary` | Без основного оружия: пистолеты, гранаты, нож |
| `hard` | Огонь по своим, нет миникарты, короткая видимость, дольше подбор, только классика |
| `super-hard` | Как `hard` + без трассеров и без характеристик оружия |

Свой пресет — скопировать блок и поменять:
- `defines` — переключатели: `friendlyFire`, `minimapEnabled`, `shortVisibility`, `tracers`, `weaponStats`, `primary`/`secondary`/`special` (`"disabled"` — запретить слот), `crawl`, `dropBullets`…
- `limit-slots` — какие слоты экипировки разрешены;
- `limit-tags` — оружие только с этими тегами (`classic`, `toz34`…).

## Параметры режимов (`maps-set.json` → `modes`)

| Режим | Что крутить |
|---|---|
| `normal` | `tickets` — запас возрождений команды, `ticketsForNewPlayer` |
| `deathmatch` | `tickets`, `ticketsForNewPlayer` |
| `domination` | `winPoints` — очки до победы, `takeFlagPoints`, `holdFlagTime`, `holdFlagPoints` |
| `ctf` | `winPoints` — сколько раз занести флаг, `chips` |
| `foxhunt` | `tickets` |

## Дуэли (`server-duel.json`)

`deathsRequired` — сколько смертей до поражения (3), `damageCoef` — множитель урона (4), в `defines` выключены гранаты, бур, чат и миникарта. После дуэли — автоматический реванш тех же двоих (оффлайн-правка: в оригинале «ещё раз» шло через официальный подбор игроков).

## Зомби (`zombie-set.json`)

Волны: `amount` (сколько зомби) + `addPerPlayer`, `maxConcurrentAmount` (одновременно на карте), `waveTime`, `spawnSpeed`, `reward`, оружие зомби в `kinds`. `wavePause` — пауза между волнами. Можно добавить свои волны.

## Боты

Число ботов — последний параметр ярлыков (`server_settings={"bots":N}`). Боты добирают команды до N и уходят, когда приходят живые игроки.
