# Проект «BRAIN / OUT: revive» — расковырять и оживить

Общий контекст проекта. Claude Code читает этот файл автоматически, поэтому всё, что важно помнить между сессиями и между участниками, пишем сюда.

Это форк https://github.com/desertkun/brainout (лицензия MIT, © 2022 desertkun — файл `LICENSE` не трогаем). Наши правки — в ветке **`revive`**, `master` = оригинал без изменений.

## Цель

1. Собрать и запустить игру **локально, оффлайн**: свой сервер и клиент, мультиплеер по LAN / Radmin VPN.
2. Разобраться, как она устроена: режимы, оружие, карты, ИИ, сеть, ассеты.
3. «Оживить»: играбельная сборка без официальных серверов, затем свои правки и моды.
4. Попутно собирать материал для цикла роликов «нейро-слопстальгия»: интересные механики, вырезанный контент, забавные находки в коде и ассетах.

## Правила работы

- Общаемся **по-русски**. Объясняй, что делаешь и зачем, коротко и без лишнего жаргона.
- Не подключаемся к официальным серверам игры, не пушим в репозиторий desertkun (remote `upstream`). Пушим только в наш репо (remote `origin`).
- Работаем в ветке `revive` (или в своих ветках от неё → pull request в `revive`). `revive` держим собираемой.
- Перед установкой системных программ (JDK, Python, Git и т.п.) — спроси.
- Новые находки, решения и грабли дописывай в раздел «Журнал» в конце файла.
- `.bat` / `.ps1` — только с переводами строк CRLF (иначе cmd ломается, особенно на кириллице). Это закреплено в `.gitattributes`.

## Об игре

- **BRAIN / OUT** — 2D-сайд-скроллер, мультиплеерный шутер «с ностальгическим постсоветским вайбом». Разработчик Desertkun, вышел в Steam 24.02.2017 (app 578310), free-to-play.
- Последний коммит оригинала 12.11.2024 (7d729dd4).
- Не путать с мобильной головоломкой «Brain Out».

## Сборка с нуля (проверено на Windows 11)

Нужно: **Git**, **JDK 17** (JDK 11 из README тоже должен подойти; 21/24 не проверяли), **Python 3.10**.

1. Python 3.10 (если нет): `winget install Python.Python.3.10 --scope user`.
2. Окружение для упаковки ассетов (из корня репо):
   ```
   %LOCALAPPDATA%\Programs\Python\Python310\python.exe -m venv build\pyenv
   build\pyenv\Scripts\python.exe -m pip install pycryptodome cffi git+https://github.com/desertkun/hjson-py
   ```
   Нужен именно **форк** hjson-py от desertkun.
3. Ассеты (~4 мин): из папки `scripts`:
   ```
   ..\build\pyenv\Scripts\python.exe make_data.py client
   ..\build\pyenv\Scripts\python.exe make_data.py server
   ```
   Штатный `gradlew make_data` **не работает**: он качает Python с `cdn.brainout.org`, а CDN мёртв. Предупреждение «no private key, making data without signing» — нормально.
4. Код (~3,5 мин): `set JAVA_HOME=C:\Program Files\Java\jdk-17` и `gradlew.bat server:dist desktop:dist`.
   Результат: `bin/server/brainout-server.jar`, `bin/client/brainout-desktop.jar`.
5. (опц.) IntelliJ: `gradlew.bat idea` → открыть `brainout.ipr`. Не давать IDE «Load Gradle project».

Всё собранное (`bin/*/packages`, jar-ы, `build/`) в git не попадает.

## Быстрый запуск

- `play-freeplay.bat` — Free Play оффлайн (сервер + клиент).
- `play-bots.bat [N]` — обычные режимы с N ботами (по умолчанию 8), карта/режим случайно из `bin/server/maps-set.json`.
- `connect.bat [IP] [ИМЯ]` — подключиться к хосту по IP (Radmin/LAN); без аргументов спрашивает, помнит последние в `connect-last.txt`. Лог — `client-last.log` рядом.
- `make-client-zip.ps1` — собрать `BrainOut-client.zip` (~258 МБ) для игроков без сборки: `connect.bat`, `client/` (jar + packages), `jre/` (jlink JDK 17, 53 МБ), README (`docs/friend-README.txt`). Выкладываем в GitHub Releases, не в git. **Пересобирать после каждой правки клиента/контента** — иначе version mismatch.
- Перед запуском закрыть предыдущий сервер (порт 36555 один).
- Логи: клиент — `build/client-last.log`; ошибки контента/локализации — `bin/client/error.log`.
- Ярлыки ищут Java в `C:\Program Files\Java\jdk-17`, иначе берут `java` из PATH.

Вручную:
- Сервер (из `bin/server`), Free Play: `java -jar brainout-server.jar --offline --mode free --settings server-free.json --map freeplay-maps.shuffle` (env `game_max_players=4`).
- Сервер, обычные режимы с ботами: env `server_settings={"bots":8}`, `java -jar brainout-server.jar no 36555,36556,36557 --offline --settings server-settings.json --maps maps-set.json`.
- Клиент (из `bin/client`): `java -jar brainout-desktop.jar --offline --unsafe --name ИМЯ --connect brainout://<base64 от "IP;36555;36556;36557">`. Для localhost: `bG9jYWxob3N0OzM2NTU1OzM2NTU2OzM2NTU3`.
- `--offline`: ключей к официальной «Alpha network» нет. `--unsafe`: данные не подписаны (приватного ключа нет).
- Мультиплеер: хосту нужны входящие порты 36555 TCP, 36556 UDP, 36557 TCP для java.exe (Windows обычно спрашивает сам при первом запуске сервера).

## Наши изменения (ветка revive)

- **Всё открыто оффлайн** — `PlayerClient.unlockEverythingOffline()`: при входе в профиль добавляются все SlotItem (оружие, скины игрока, специализации), Skin (скины оружия), Upgrade/UpgradeChain (обвесы), Layout, ProfileBadge (~4629 шт.); макс. `level`/`tech-level`; skillpts/gears/nuclear-material = 999999. Отключить: env `BRAINOUT_NO_UNLOCK=1` на сервере.
- **Профили по именам** — клиент шлёт `--name` (по умолчанию имя пользователя Windows) в `HelloMsg.key` (оффлайн-сервер его раньше игнорировал); сервер хранит `bin/server/profiles/<имя>.json`, при первом входе копирует `default-profile.json`. `profiles/` не в git.
- Ярлыки запуска, скрипт архива клиента, этот файл.

## Структура репо

```
core/      общая логика (~784 файла): режимы, контент, компоненты, сеть
client/    клиент: графика, UI, ввод
server/    сервер: лобби, бой, free play, редактор карт, консоль
desktop/ steam/ android/   обёртки под платформы
data/      весь контент (~470 МБ): packages/, content/, assets/
scripts/   make_data.py — упаковка ассетов
tools/     libGDX-утилиты, particle editor, hiero, proguard
bin/       сюда собираются сервер и клиент; bin/server — конфиги и карты
docs/      Troubleshooting.md, friend-README.txt
```

## Стек

- Java (исходники 1.8, собираем JDK 17), Gradle 8.3 (wrapper)
- libGDX 1.11 (форк desertkun `1.11.1-dev`) + Box2D, box2dlights, gdx-ai, Ashley (ECS)
- Сеть: KryoNet (форк) и Kryo 5; онлайн-бэкенд Anthill Platform (оффлайн не используется)
- Анимации: Spine; контент описан в HJSON (`*.txt` в папках `smart`)
- ~1 900 .java, ~280 тыс. строк; корневой пакет `com.desertkun.brainout`

## Контент (data/packages)

- Пакеты: `base`, `sounds`, `mainmenu`, `lobby`, `freeplay`, `halloween`, `custom`, `map_*`
- Карты в ротации (16): factory, cargo, deposite, hospital, hospital_new, siber, forest, mall, warehouse, construction, bridge, tower, bunker, hangars, canyon, station. Плюс десятки кусков Free Play (`fr-*`), шаблоны, lobby, halloween, duel.
- `base/smart`: ~250 видов оружия, ~830 скинов оружия, 172 скина игрока, 134 достижения, квесты, медали, боевой пропуск, магазин, специализации, маски
- ~9 200 PNG, ~1 000 MP3, 279 Spine-анимаций; 23 языка локализации (есть RU, UA, BE)

Пример описания оружия (HJSON):

```
class = content.instrument.Weapon
id = weapon-ar15
primary = { damage = 65, clipSize = 20, fire-rate = 540, reloadTime = 3, ... }
```

## Карта кода

Пакет `com.desertkun.brainout` опущен.

- **Точки входа:** `server/src/.../BrainOutServer.java` (флаги `--offline`, `--mode`, `--settings`, `--maps`; env `server_settings` JSON → `bots`, `exec`), `client/src/.../BrainOutClient.java` (`--connect`, `--unsafe`, `--offline`, `--name`).
- **Режимы:** общая логика `core/.../mode`, серверная `server/.../mode/Server*Realization.java` (Normal, Deathmatch, CTF, Domination, Assault, Duel, GunGame, FoxHunt, Zombie, WinterWar, Free, Lobby, Editor/Editor2), клиентская `client/.../mode`. Free Play отдельно: `server/.../mode/freeplay`.
- **Ротация карт/режимов:** `bin/server/maps-set.json` (`maps`, `modes` с настройками, `sets` карта→режимы). Источник `server/.../server/mapsource/MapSetSource.java`.
- **ИИ ботов:** `server/.../bot/` — стек задач (`TaskStack`, `TaskHunter`, `TaskFollowAndShootTarget`, `TaskHoldAFlag`, `TaskAssaultAFlag`...), Free Play боты `bot/freeplay` + `bin/server/freeplay-bots.json`. Добор ботов в команды: `server/.../client/ClientList.ensureBots()`, бот-клиент `BotClient.java`.
- **Оружие и контент:** HJSON в `data/packages/base/smart/` (Weapons, Player Skins, Player Specializations = перки, General Upgrades, Shop, Achievements, Battle Pass, Quests, Content/Levels*). Java-классы контента `core/.../content` (Weapon в `content/instrument`, апгрейды `content/upgrades`, слоты/магазин `content/shop`).
- **Замки и прогресс:** `core/.../content/ContentLockTree.java` (открытие по статам), `core/.../online/UserProfile.java` (`items`, `stats`, `hasItem` — true, если предмет есть в `items`, независимо от замков), уровни `Levels Default.txt` (68 ур.) и `Levels Tech.txt`.
- **Профиль оффлайн:** `PlayerClient.setupOfflineProfile(name)`, сохранение — `ClientProfile.dumpProfile`. Оффлайн-игрок = admin (доступны все консольные команды).
- **Сеть:** KryoNet, сообщения `core/.../common/msg/{client,server}` (~160 классов), порты 36555 TCP / 36556 UDP, 36557 HTTP.
- **Консоль сервера (админ):** `server/.../server/console/` — 60 команд: `Give`, `UnlockOwnable`, `SpawnBot`, `SpawnBotPlayer`, `God`, `Teleport`, `Rain`, `TimeOfTheDay`, `Slowmo`, `GameSpeed`, `Boom`, `Impulse101`, `WinGame`, `SkipWarmUp`, `SwitchMap`...

## План

- [x] Этап 1. Собрать ассеты, клиент и сервер
- [x] Этап 2. Запустить Free Play оффлайн
- [x] Этап 3. Карта кода: режимы, оружие, ИИ, сеть, сохранения
- [x] Этап 4. Мультиплеер по LAN / Radmin VPN (проверен только на одном ПК)
- [ ] Этап 4.1. Сыграть по-настоящему с другого ПК
- [ ] Этап 5. Свои правки: баланс, оружие, карты, вырезанный контент
- [ ] Параллельно: копить находки для роликов в разделе «Журнал»

## Известные грабли

- CDN `cdn.brainout.org` мёртв (KeyCDN 404) → Python ставим сами, см. «Сборка с нуля».
- В README оригинала упоминается Python 2 — устарело.
- Ярлыки `bin/*.bat` оригинала ссылаются на встроенный `bin\bin\java.exe`, которого в репо нет → пользуемся нашими `play-*.bat`.
- В логе клиента «Class Server*Component is not registered in the reflection» — серверные классы, клиенту не мешают.
- `.gitattributes` упоминает Git LFS для `rt.jar` и `bin/obfuscated/...`, но таких файлов в репо нет — LFS фактически не нужен.

## Журнал

- 2026-11-05 — Изучили репо, клонировали, ветка `revive`. JDK 17 подходит, все Java-зависимости (jitpack, anthill, kryonet-форк, gdx-dev) скачались.
- 2026-11-05 — CDN мёртв → Python 3.10 через winget, venv `build/pyenv`, `make_data.py` вручную: 15 пакетов, клиент 204 МБ, сервер 19 МБ.
- 2026-11-05 — Free Play запущен оффлайн: игрок «fefe», карта forest, стартовое оружие ТОЗ-34.
- Находка: при старте Free Play сервер генерирует лут — телефоны, часы, VHS-плеер и кассеты, пейджеры, дискеты; и случайный **код бункера**.
- 2026-11-05 — Выдача всего оффлайн (747ce37c). Боты в обычных режимах встроены — env `server_settings={"bots":N}`; проверено: Deathmatch на hospital, 8 ботов.
- Находки для роликов: консольная команда **`Impulse101`** — отсылка к чит-коду Half-Life (M4A1, магнум, бинокль, гранаты). У ботов русские имена. Медаль `medal-5year` упомянута в карточке, но самого контента нет — недоделанная награда за 5 лет. Комментарий в `Client.java`: «allow to farm bots up until 10 level».
- 2026-11-06 — Был обрыв клиента без дампа `hs_err`, лог тогда не писался — причина неизвестна. Теперь ярлыки пишут лог.
- 2026-11-06 — Мультиплеер (2b7d9060): профили по именам. Проверено на одном ПК через Radmin-IP: два клиента + 6 ботов, режим normal на tower, разные команды; клиент из архива со встроенным JRE доходит до игры.
- 2026-11-06 — Репо перенесено на GitHub (приватное), сюда же — CLAUDE.md, ярлыки, `make-client-zip.ps1`.
