# Проект «BRAIN / OUT: revive» — расковырять и оживить

Общий контекст проекта. Claude Code читает этот файл автоматически, поэтому всё, что важно помнить между сессиями и между участниками, пишем сюда.

Наш репо: https://github.com/ggy1331/brainout-revive (публичный с 2026-11-07). Это форк https://github.com/desertkun/brainout (лицензия MIT, © 2022 desertkun — файл `LICENSE` не трогаем). Наши правки — в ветке **`revive`**, `master` = оригинал без изменений.

## Команда

- **GGY** (GitHub `ggy1331`) — владелец репо, хост сервера.
- **Семён** (GitHub `markozph`) — соавтор, участник репо с правом записи. В разговоре зовём его Семёном. Когда коммит сделан по его идее, баг-репорту или с его участием — добавляем трейлер `Co-authored-by: Семён <349534636+markozph@users.noreply.github.com>`, тогда GitHub покажет его соавтором коммита.
- Другие игроки (без доступа к репо): Orel3287, SMGN1L.

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
- `play-zombie.bat [N]` — **зомби-кооп**: игроки против 3 волн вооружённых зомби на карте halloween (`bin/server/zombie-set.json`), N — боты-союзники (по умолчанию 0).
- `play-match.bat [режим] [карта] [пресет] [боты]` — **свой матч** (`-` = пропустить): режим закрепляется (`keep-mode`), пресеты правил `knife-only`, `toz34-only`, `classic-only`, `no-primary`, `hard`, `super-hard`. Подробно: `docs/match-rules.md`.
- `play-ctf.bat [боты] [пресет]` — захват флага на `bunker_ctf` (CTF теперь и в обычной ротации).
- `play-duel.bat` — дуэль 1×1 (только живые игроки, 3 смерти, авто-реванш).
- `play-xm8-test.bat [боты]` (и `play-gepard-test.bat`, `play-xm8-gepard-test.bat`) — deathmatch с полным арсеналом, включая XM8 и Гепард. Только новые пушки: `play-match.bat deathmatch - xm8-gepard|xm8-only|gepard-only [боты]`.
- `play-online.bat [ник]` — **онлайн-режим с имитацией бэкенда** (`tools/mock-backend`): главное меню → **хаб** → матчи, как в оригинале. Бэкенд сам запускает игровые серверы (`build/rooms/*.log`); профили, рубли, рынок, кланы, друзья — в `backend-data/`. Адрес для друзей — Radmin-IP (26.x.x.x) определяется сам (или env `BRAINOUT_PUBLIC_HOST`). `stop-online.bat` — остановить бэкенд и его серверы. Подробно: `tools/mock-backend/README.md`.
- `connect-online.bat [IP] [ник]` — друг подключается к онлайну хоста (`--env http://IP:9511/environment --name ник`). Ник = отдельный онлайн-аккаунт (`DESKTOP_PROFILE_NAME`), даже на одном ПК.
- `play-solo.bat [ник] [IP хоста]` — **одиночная Зона конфликта (PvE)** на этом ПК: локальная имитация бэкенда (`--solo`, порт 9521, данные `solo-data/<ник>/`) + сервер Зоны на одного игрока + клиент. Прогресс (профиль, тайник, рубли) синхронизируется с онлайн-бэкендом хоста до и после игры, если хост доступен (`services/revive.py`). Работает и из архива друзей (там свой `python/` и `server/`).
- `connect.bat [IP] [ИМЯ]` — подключиться к хосту по IP (Radmin/LAN); без аргументов спрашивает, помнит последние в `connect-last.txt`. Лог — `client-last.log` рядом.
- `make-client-zip.ps1` — собрать `BrainOut-client.zip` (~258 МБ) для игроков без сборки: `connect.bat`, `client/` (jar + packages), `jre/` (jlink JDK 17, 53 МБ), README (`docs/friend-README.txt`). Выкладываем в GitHub Releases, не в git. **Пересобирать после каждой правки клиента/контента** — иначе version mismatch.
- Перед запуском закрыть предыдущий сервер (порт 36555 один).
- Логи: сервер — `build/server-last.log` (UTF-16, пишет `play-*.bat` через PowerShell Tee-Object; читать `type` или `iconv -f utf-16`), клиент — `build/client-last.log`; ошибки контента/локализации — `bin/client/error.log`.
- `play-*.bat` запускают клиент только после строки `Initialized!` в логе сервера (до 90 с): порт сервер открывает раньше, чем догружается. Падение сервера ловим по точной фразе `ERROR: Failed to load.` — просто «Failed to load» встречается в нормальном логе (`Failed to load content for content card` про medal-5year) и ложно срабатывало в Free Play.
- Если старый клиент ещё открыт, новый может не запуститься (лог `client-last.log` занят) — закрывайте старые окна игры.
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
- **Borderless вместо эксклюзивного полноэкранного режима** — `DesktopLauncher`: при `fullscreen` окно без рамки на весь монитор в разрешении рабочего стола + `setAutoIconify(false)`. Старый режим: env `BRAINOUT_EXCLUSIVE_FULLSCREEN=1`. Окно на **1 пиксель выше** экрана (`BRAINOUT_WINDOW_HEIGHT_DELTA`, по умолчанию 1): иначе Windows/драйвер считают его полноэкранной игрой и выводят мимо композитора — OBS и скриншоты видят чёрный кадр.
- **Карты без превью не роняют клиент** — `menu/ui/MapIcons`: в `EndGameMenu` (голосование за следующую карту) и `MapSelectionMenu` вместо `new Image(skin, "map-" + name)`; нет картинки `map-<имя>` → пустое изображение. Раньше конец любого матча на halloween/duel/bunker_ctf/своей карте = падение клиента.
- **Зомби-режим** включён ярлыком `play-zombie.bat`.
- **`room_settings` после `--maps`** — `BrainOutServer`: настройки комнаты (режим/карта/пресет) применяются после создания источника карт; раньше NPE при `room_settings` + `--maps`.
- **CTF: боты воюют** — `ServerCTFRealization.getBotStartingTask` → `TaskHunter` (в оригинале `null`, боты стояли). Флаг (chip) боты не носят. CTF добавлен в `maps-set.json` (`bunker_ctf`).
- **Дуэли оффлайн** — `ServerDuelRealization`: без онлайна не требуется плата `ru` (раньше кик `MENU_NOT_ENOUGH_RU`), после победы — сообщение в чат и авто-реванш той же пары (раньше комната зависала: награда/«ещё раз» шли через онлайн-сервисы).
- **Зона конфликта: напарник и одиночка** — пати в имитации (`services/party.py`), приглашение `--free-play-join <party>` в `SocialController` открывает лобби напарника; одиночный PvE `play-solo.bat` с синхронизацией прогресса (`services/revive.py`, `connect-online.bat` перед онлайном отправляет несинхронизированный одиночный прогресс).
- **Расширение контента** (ветка `content-expansion`): новые пушки **XM8** (`weapon-xm8`, звуки M4A1) и **ПП «Гепард»** (`weapon-gepard`, звуки АКС-74У); обвесы «как в Таркове» — 79 модификаций для АК-74, M4A1, MP5, СВД, Glock, XM8 (`Upgrades/Gunsmith/`, генерирует `tools/weapon-art/gunsmith.py`); песочный скин XM8; в меню модификаций — прокрутка и компактные кнопки, когда вариантов много.
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
- 2026-11-06 — **Первая игра по сети через Radmin работает** (игроки GGY, markozph, Orel3287). Открытые баги (логов не было, причина не найдена):
  1. Иногда вечное «соединение установлено, загрузка» при запуске сервера. Гипотеза: клиент стартовал через фиксированные 8 с, раньше, чем сервер догрузился → теперь ждём `Initialized!`.
  2. FoxHunt («Охотник», `MODE_FOXHUNT`): игрок не мог возродиться, помог перезапуск сервера. По коду `ServerFoxHuntRealization.canSpawn` всегда `allowed` → вероятно, сбой состояния (смена «лиса» в `setPlayerAsFox` молча выходит, если `playerData == null`; или переход на следующую карту после конца матча). Ждём лог.
- 2026-11-06 — Репо на GitHub: https://github.com/ggy1331/brainout-revive (приватное, основная ветка `revive`, `master` = оригинал). Сюда же — CLAUDE.md, ярлыки, `make-client-zip.ps1`. Релиз **v0.1** с `BrainOut-client.zip`: https://github.com/ggy1331/brainout-revive/releases/tag/v0.1. Новый релиз: `make-client-zip.ps1`, затем `gh release create vX.Y BrainOut-client.zip -R ggy1331/brainout-revive --target revive` (без `-R` gh берёт upstream desertkun и получает 404).
- 2026-11-06 — **Alt+Tab** (858c408a, релиз **v0.2**). Воспроизведено тестом (PowerShell: keybd_event Alt+Tab, ShowWindow, снимки экрана): в эксклюзивном полноэкранном режиме LWJGL3/GLFW сворачивает игру при потере фокуса (`iconic=True`), при возврате переключает видеорежим, один раз окно не развернулось. Обрыва связи и падений не было — игра в 1.11 продолжает рендер и сеть в свёрнутом виде. Решение — borderless; после него Alt+Tab не сворачивает, картинка на месте. Протокол не менялся: клиент v0.1 к серверу тоже подключается.
- 2026-11-06 — **Зомби-режим** (ветка `zombie` → `revive`, релиз **v0.3**). Был готов целиком, но без ярлыка: `ServerZombieRealization` (~900 строк), карта `halloween`, пакет `halloween`, 3 волны в `zombie-set.json` (зомби с M4A1/АК-74 → MP5/LR300 → Minimi/РПГ-7/SPAS-12; число растёт с игроками; между волнами 15 с и ящик патронов в точке `supplies`). Правила: зомби бьют вдвое слабее; погиб во время волны — наблюдаешь до следующей; все погибли — победа зомби. Параметр `bots` добавляет союзников в команду игроков. Найден и исправлен вылет клиента на экране итогов (нет превью `map-halloween`). В тесте без живого игрока матч проигрывается за ~40 с — ожидаемо.
- 2026-11-06 — **CTF, дуэли, свои правила** (ветка `modes` → `revive`). Найдены и исправлены 4 оффлайн-бага (см. «Наши изменения»). Проверено: CTF 4 бота — боты гибнут/возрождаются после старта матча; `play-match.bat deathmatch - knife-only 3` — «Preset has been used: knife-only» (визуально не смотрел — монитор спал); дуэль — 2 клиента, 3 убийства через консоль сервера `for <id> kill` → «Offline duel completed… rematch», клиенты живы. **Тестировать сервер через stdin**: консоль сервера читает команды из stdin от имени root (`for <id> kill`, `skipwarmup`, `map`, `give`…); PowerShell-StreamWriter шлёт BOM первой строкой — сначала отправить пустую строку. Клиент в этом наборе правок не менялся → новый релиз не нужен.
- 2026-11-06 — **Разведка онлайн-части** («вернуть всё, что есть в файлах»). «Зона конфликта» = Free Play (`MENU_JOIN_CONFLICT_ZONE`). Режим запускается, но всё вокруг него — онлайн: рубли (`ru`), тайник/инвентарь, барахолка между игроками (orders), крафт, **недвижимость** (личные квартиры — карты `apt-1-1…10`, `RealEstateItem`) живут в сервисе **Market** бэкенда Anthill; клиент ходит туда **напрямую** (`MarketMenu`, `NewSellOrderMenu`, `MarketCraftingMenu`, `realestate/*`…). Хаб/лобби, подбор матчей, дуэли «ещё раз» — `GameService` (game-master); кланы/друзья — `SocialService`; события/боевой пропуск — `EventService`; магазин — `StoreService`; плюс Profile, Leaderboard, Message, Blog, Promo, Static.
  - Весь бэкенд **открыт**: github.com/anthill-platform (MIT, Python/Tornado, последние коммиты 2021–2023), есть `anthill-market` (без файла лицензии!) и `anthill-dev` (docker-compose со всеми сервисами, админка на :9500, root/anthill).
  - Клиент знает бэкенд через одну константу `Version.ENV_SERVICE = "https://env.brainout.org"` → `AnthillRuntime.Create(...)`, gamespace `brainout:desktop`; умеет создавать **анонимный аккаунт** (`CSOnlineInit`).
  - Настроек официального бэкенда (товары рынка, события, магазин, конфиги game-master) в репо **нет** — восстанавливать по коду клиента/сервера.
- 2026-11-07 — Docker не вариант: в BIOS выключена виртуализация (`systeminfo`: «Виртуализация включена во встроенном ПО: Нет»), WSL нет. Решили писать **имитацию бэкенда** на Python (`tools/mock-backend`, ветка `online`). Справочники — клоны anthill-* в `C:\Users\GGY\brain_out\anthill\` (вне репо).
- 2026-11-07 — **Онлайн-режим заработал** с имитацией: клиент `--env http://127.0.0.1:9511/environment` → environment → discovery (13 сервисов) → `POST /login/auth` (credential=anonymous, клиент сам генерит username/key и хранит их) → игровой сервер онлайн (env `login_access_token`, `discovery_services`) → `/login/validate` + `/login/extend` → `GET /profile/me` (404 → новый профиль) → `POST /profile/me` сохраняет. Повторный вход — «Got the profile!». Грабли: runtime парсит JSON только при `Content-Type: application/json` ровно (с `; charset` молча падает в NPE, без логов). Логика `@func`/слияния профиля взята из anthill-common (MIT) — `services/anthill_profile.py`. В онлайне unlock-all **не** применяется (он только в `setupOfflineProfile`) — прогресс «честный».
- 2026-11-07 — **Market в имитации** (рубли, тайник, барахолка). Игра использует один рынок `freeplay`; всю конвертацию «предмет ↔ запись рынка» делает сама (`MarketUtils`: `ru`, `instrument`, `consumable`, `armor`, `skin`, `radio`, `realestate`, `rsitem`). Рубли — и стат профиля `ru` (кошелёк: награды `RuRewardComponent`, комиссии, пропуск контрактов), и предмет `ru` на складе; переводы между ними делает сервер (`PlayerHandlers`). Серверная часть рынка — в основном недвижимость (`rsPlaceObject`, `generatePremises`, `assembleRealEstateItem`…). Тайник — «Personal Container» на карте Free Play; при входе в зону старый контейнер профиля `p` переносится на рынок (`convertItemsToMarket`). Автотест `tools/mock-backend/test_backend.py` поймал баг: `Profile.merge_data` возвращает **новый** корень, а не меняет переданный — до фикса профили сохранялись пустыми. Free Play онлайн запускается, профиль пишется. **Не проверено в игре**: тайник/барахолка/квартиры через интерфейс (нужны клики живого игрока).
- 2026-11-07 — **Хаб вернулся** (сервис game в имитации). Путь клиента: `CSWaitForUser` → `CSGetRegions` (`/game/regions`) → `CSGetBlogUpdates` (`/blog/blog/main`) → `CSFindLobby` (`POST /game/join/brainout/lobby/valpha2`) → подключение по `{id, key, location{host, ports}}`. Игры, которые просит клиент: `lobby`, `main`, `freeplay`, `duel`, `zombie`, `custom` (+ `room/<id>/join`, `rooms/...` для браузера серверов). Официально ключ комнаты проверял game-controller через **ZeroMQ `ipc://`** (Linux) — не имитируем: клиент теперь **всегда** шлёт и access token (`CSConnected`), сервер без контроллера проверяет игрока по токену («exchanging key in an old way»). Сервер хаба стартует за ~3 с. Клиент: флаг `--auto-continue` для тестов без кликов.
- 2026-11-07 — **Сообщения в имитации.** Друзей как системы у игры **не было**: `GameUser.getFriends()` в обычной сборке пустой, в Steam-сборке (`GameSteamUser`) — друзья из Steam API; у Anthill runtime нет API друзей. «Социалка» игры = **кланы** (сервис social, группы `social-group`) и сообщения. Сообщения слушает **игровой сервер** от имени каждого игрока (`PlayerClient.messageSession`, WebSocket `/message/listen`) и пересылает клиенту (`SocialController`): `clan_chat`, `group_request`, `engage_conflict`, уведомления рынка `order_completed`/`order_cancelled` (их шлёт сервис market владельцу заказа, флаг `remove_delivered`). JSON-RPC runtime обрабатывает входящие вызовы **только с `id`** — пуши нумеруем. Проверено: автотест (WebSocket-пуш, уведомление о покупке, личное сообщение, история) + игра: сервер хаба открывает сессию и грузит историю, все ответы 200.
- 2026-11-07 — **Кланы и свои друзья**, релиз **v0.4** (ветка `online` влита в `revive`). Кланы: 21 операция `SocialService`, почти все вызывает **игровой сервер** (`PlayerHandlers`), клиент только ищет (`BrowseClansMenu`); уведомления шлются только если игра передала `notify`. Друзья — новая функция: `GameUser` (базовый, не Steam) берёт список с `<social>/friends` через Unirest (кэш, обновление раз в 10 с), `InviteMenu` — поле «Ник друга» + «Добавить», входящие запросы «нажмите, чтобы принять»; `SocialController` — попапы `friend_request` и `friend_invite` («X зовёт вас в игру» → disconnect → `CSJoinRoom`). Сервер пересылает клиенту все сообщения без своего обработчика (`PlayerMessages`), но слушает их **только в хабе и Free Play**. Ник: клиент шлёт `ChangeNameMsg`, если `--name` отличается от имени в профиле. Ячейка аккаунта — env `DESKTOP_PROFILE_NAME` (`DesktopEnvironment.getUniqueId`), по умолчанию `desktop` — ярлыки ставят её = ник. Проверено: автотест (кланы, друзья) + два живых клиента через Radmin-IP: оба в хабе со своими никами, взаимное добавление → друг «в сети, комната 1». Грабли: `stop-online.bat` искал путь с `\`, а процесс запущен с `/` → висел старый бэкенд на порту; поиск по нику может найти дубли — берём того, кто в сети, иначе новейший. **Не проверено глазами**: окна друзей/кланов, попапы (нужны клики).
- 2026-11-07 — **Онлайн: перенос оффлайн-профилей и вся прокачка по умолчанию.** `PlayerClient.reviveOnlineProfile()` (после загрузки/создания онлайн-профиля и после `ChangeNameMsg`): если есть `bin/server/profiles/<ник>.json` (игры по сети до онлайна) — один раз импортируется целиком (стат `revive-imported=1`), затем `unlockEverythingOffline()` (как в оффлайне; выключить — env `BRAINOUT_NO_UNLOCK=1`). Проверено: GGY → онлайн-аккаунт №4, 4640 предметов, 67 убийств; Semyon2 (без оффлайн-профиля) → +4630 предметов. Оффлайн-профили целы: GGY, markozph, Orel3287, SMGN1L (+ тестовые Alpha/Beta/Friend). Друзья получат свои вещи, если зайдут в онлайн **под тем же ником**. Профиль пишется в бэкенд не сразу, а периодически/при выходе (`Profile N was saved`).
- 2026-11-07 — **Чат, Топ-100, кланы.** Чат проверен клавиатурой (keybd_event Y → текст → Enter): в матче сервер получил «Chat [everyone]: …» (кириллица проходит; в логе кракозябры из-за кодировки Tee). Сервер теперь пишет каждое сообщение чата в лог (`PlayerClient.received(ChatSendMsg)` → «Chat [mode]: …»). В хабе чат открывался **только кнопкой** (`LobbyMenu.openLobbyChat`), клавиши `Y`/`U` там не работали → добавлен `LobbyMenu.keyDown` (не срабатывает, когда фокус в текстовом поле). Хаб-чат клавишей автотестом **не подтвердился** (сообщение не дошло до сервера), глазами не проверен — экран отдавал чёрные снимки. Клановый чат = сообщения `clan_chat` (payload name/text/credential) в группу `social-group`. Рейтинги: сервис leaderboard (`top100` по `kpd`, `clans100`), сервис static (аватары кланов — без него создание клана с аватаром падало). Релиз **v0.5**.
- 2026-11-07 — **Чёрный экран в OBS и на скриншотах** (релиз **v0.6**). Замер яркости GDI-снимка (как OBS «Захват экрана»): окно ровно 1920×1080 → 0 (чёрный кадр), −1 px → видно, но поверх вылезает панель задач, +1 px → нормальная картинка, игра на весь экран. Причина: окно без рамки ровно в размер монитора система «повышает» до прямого полноэкранного вывода в обход композитора DWM. ПК: RTX 3060 Ti, одна видеокарта (не гибридная). Решение — высота +1 по умолчанию.
- Идеи на потом (из разбора контента): «несерьёзное» оружие — `weapon-water`, `weapon-snowball-blaster`, `weapon-paint`, игрушечный молоток; вырезанный режим **WinterWar** — только пустые заглушки в core/client/server; вороны во Free Play (`weapon-crow`, `TaskCrow`); встроенный редактор карт (`Editor`, `Editor2`).
- 2026-11-07 — Репозиторий сделан **публичным**: релизы качаются без аккаунта GitHub. Перед этим проверили: Radmin-IP нигде нет, профили и `backend-data/` не в git; почта GGY в истории коммитов осталась (решили не переписывать историю).
- 2026-11-07 — **Зона конфликта: онлайн + одиночная PvE** (релиз **v0.7**). Вход из хаба уже был в игре: объект `active-menu-freeplay` → `FreePlayQuestsMenu` с кнопками «Играть одному» (`CSFreeplaySolo` → `/game/join/.../freeplay`, общая комната) и «С напарником» (`FreePlayPartnerLobby` → **пати** Anthill: WebSocket JSON-RPC `party`/`message`, `game_started` с комнатой) — пати дописана в имитацию. Тайник и рубли Зоны живут **только** в сервисе market, офлайн-сервер их не умеет → одиночка = та же имитация бэкенда локально (`--solo`: игра `lobby` подменена Зоной на 1 игрока, клиент из хаба сразу попадает в Зону). Синхронизация с хостом: флаги `dirty` на каждой стороне (хук `Storage.on_put`), профиль — побеждает изменённая сторона (обе — новее по времени), тайник — трёхстороннее слияние, первый запуск — профиль берётся с хоста (`adopt_pending` при создании аккаунта). Проверено: автотест `test_sync.py` (6 сценариев) + живая игра: прогресс GGY (копия бэкенда) подтянулся в одиночку (4640 предметов, 777 ₽ в тайнике), после выхода «профиль → хост»; одиночка из распакованного архива (переносной Python из установленного 3.10 + jlink JRE) доходит до Зоны. Грабли: серверу в jlink-JRE нужен модуль `jdk.httpserver` (иначе падает на встроенной старой копии `com.sun.net.httpserver` → `sun/misc/ServiceConfigurationError`); venv-`python.exe` — лаунчер, серверы комнат ему «внуки» → гасим всё дерево; PowerShell-фильтр `CommandLine -match 'brainout-server'` находит и сам bash, в котором запущен, — фильтровать по `Name='java.exe'`. **Не проверено глазами**: объект Зоны в хабе и игра с напарником через интерфейс (нужны два живых игрока).
- 2026-11-07 — **Своя пушка XM8** (ветка `xm8`, отдельная папка-worktree `brainout-xm8`, тестовый ярлык `play-xm8-test.bat` = deathmatch с правилом `xm8-only`: у всех, включая ботов, только XM8). Как устроена пушка: `smart/Weapons/<имя>/` — `Weapon.txt` (характеристики, звуки, анимации рук), `Store Item.txt` (слот, категория, скины, обвесы, патроны, теги), `Animation.txt` → Spine-скелет `contents/content/animations/weapon-<имя>.json` (кости `fire-bone`, `hook-bone`, `center-bone`, `shell-bone`, `laser-bone` + слоты body/clip/butt/scope/silencer с картинками из `textures/GAME`), `Skins/`, `Upgrades/` (цепочки прокачки — `UpgradeChain` с `prefix`), название в `localization/input.json`. Иконку в магазине/слоте игра рисует сама из скелета — отдельная картинка не нужна. Спрайты XM8 нарисованы кодом: `tools/weapon-art/xm8.py` (тени/блики считаются автоматически по форме деталей), скелет взят от G36 (те же точки крепления), глушитель — картинка от G36C, звуки — от M4A1. Статы: урон 52, темп 750, магазин 30, точность 38, отдача 32, перезарядка 1,0 с, 5.56×45. Проверено в игре: иконка в слоте, боты с XM8, убийства «[XM8]». Свой персонаж с пушкой в руках на снимке не попал (ещё не возродился).

- 2026-11-07 — **XM8: прямой перенос утверждённого концепта** в тестовый клиент. Исходник tools/weapon-art/reference/xm8-approved.png; воспроизводимый импорт tools/weapon-art/import_xm8_concept.py (Pillow, без генерации и перерисовки RGB). Корпус, магазин и приклад выделены из исходной картинки и используют единый масштаб в Spine; кости/слоты/дорожки сохранены. Глушитель уже был подключён, изменено только его визуальное положение на новом стволе. Статы, звуки, Animation.txt и определения апгрейдов не менялись (проверены хешами). Пакеты клиента/сервера пересобраны; проверено в живой игре: модель в руках и в меню модификаций с глушителем. Подробности — tools/weapon-art/README.md. Старая процедурная xm8.py и предшествующие незакоммиченные правки сохранены; резервная копия до импорта — build/xm8-before-concept-import/.
- 2026-11-07 — **XM8 в пиксельном размере.** Текстуры концепта (1201 px в длину) игра сжимала «по ближайшему пикселю» → рябь в руках и в слоте. Скрипт `tools/weapon-art/pixelize_xm8.py` уменьшает детали до родного размера (корпус 90×36, приклад 40×21, магазин 13×16, 1 px = 1 единица, как у оригинальных пушек), общая палитра 28 цветов, надпись XM8 закрашена (на таком размере — пятно). Большие детали сохранены в `tools/weapon-art/reference/*-hires.png`. Проверено в игре: в руках, на полу и в слоте — ровно, без ряби.

- 2026-11-07 — **ПП Гепард в тестовой сборке XM8.** Добавлен weapon-gepard/sl-pri-gepard; утверждённый концепт сохранён в tools/weapon-art/reference/gepard-approved.png и напрямую разделён на корпус, магазин и приклад (import_gepard_concept.py). Полноразмерные детали сохраняют исходные RGB; игровые текстуры — прямое BOX-уменьшение в 16 раз без новой генерации, закрашивания и замены палитры. Весь звуковой компонент взят у АКС-74У (aksu) и проверен на совпадение; стартовые параметры и анимации рук — MP5. Локализация Гепард, пресет gepard-only и play-gepard-test.bat (по умолчанию 4 бота). Пакеты клиента/сервера собраны и проверены; в живом локальном матче видны модель в руках/слоте, стрельба и перезарядка до полного магазина+патронника. Захват экрана после проверки отключён, тестовая игра оставлена открытой. Предшествующие правки обвесов и XM8 сохранены. Документация — docs/gepard-test.md.

- 2026-11-07 — **Гепард: три ветки прокачки и общий тест с XM8.** Подключены штатные пятиуровневые UpgradeChain точности, отдачи и перезарядки с prefix=gepard. Пятые уровни дают точность 45, отдачу 25 и reloadTime 0,75 с; база, изображение и звуки не менялись. Пакеты клиента/сервера пересобраны. play-xm8-test.bat теперь запускает общий пресет xm8-gepard, добавлен явный play-xm8-gepard-test.bat; отдельные xm8-only/gepard-only сохранены. Обычный play-bots.bat в этом checkout также видит обе пушки в полном арсенале. Живая проверка: сервер принимает покупки всех трёх цепочек и сохраняет выбранные уровни 5 в профиле Gepard-Upgrades-Test; обе пушки разрешены общим пресетом. Захват экрана отключён.

- 2026-11-07 — **Гепард в полном арсенале, баланс.** Общие пакеты bin/client и bin/server в brainout-xm8 пересобраны: полный арсенал через play-bots.bat включает Гепард, XM8 и оригинальное оружие. play-bots.bat теперь очищает унаследованный room_settings, чтобы тестовые ограничения не попадали в обычные матчи. Урон Гепарда = 42,5 (АКС-74У 50 × 0,85), темп 700 выстр./мин (запрошенный диапазон 600–750). Три цепочки модификаций и звуки АКС-74У сохранены. Проверено в обоих готовых пакетах: одинаковые определения оружия, точное соотношение урона, темп, наличие остальных пушек и всех трёх модификаций; CRLF у ярлыка сохранён. Уже запущенные матчи используют прежний контент до перезапуска.

- 2026-11-07 — Разобрано устройство оружия по ресурсам и исходникам: 250 описаний Weapon, 246 экспортов weapon-*, 252 исходных проекта Spine, 2823 имени связанных PNG. Карта устройства и ключевые классы — docs/weapons-architecture.md. Движения рук/перезарядок в actor.json отделены от скелета оружия; события instrument-action управляют деталями, эффектами и собственными дорожками оружия. Найдена ссылка weapon-pistol-s.fetch на отсутствующую в actor.json дорожку reload-1hand1-fetch; не исправлялась.

- 2026-11-07 — **Обвесы «как в Таркове»** (тестовая ветка `xm8` → `content-expansion`). `tools/weapon-art/gunsmith.py` берёт существующие картинки обвесов из игры и вешает их на АК-74, M4A1, MP5, СВД, Glock 17 и XM8: прицелы (крепление по центру основания на планку), глушители (начинаются там, где начинается дульное устройство; высота — по каналу ствола, меряется по пикселям корпуса), рукоятки, фонари/ЛЦУ, магазины, сошки, подствольники (ГП-30, M203). Всего 79 модификаций, `access = byDefault`; скрипт идемпотентен — перезаписывает скелеты, Store Item и названия. Меню модификаций (`UpgradeInstrumentMenu`, `UpgradeInventoryInstrumentMenu`) получило прокрутку и компактные кнопки — иначе 15+ вариантов не влезали. XM8: прицел снимает ручку для переноски со встроенным коллиматором (вариант корпуса с планкой, `xm8_rail.py`); песочный скин в стиле BF: Bad Company 2 — перекраска только оливковых пикселей (`xm8_sand.py`, запускать **после** gunsmith.py). Баланс XM8: отдача 35, как у M4A1, цепочка прокачки отдачи убрана (с ней и обвесами выходило 5). **Грабли:** `make_data.py` читает `localization/input.json` в кодировке по умолчанию (cp1251 на Windows) → не-ASCII строки писать только как `\uXXXX`, иначе в игре кракозябры. `big-icon` у скина — это картинка оружия в HUD/инвентаре, а не образец цвета: 32×16 иконку туда не ставить.

- 2026-11-07 — **content-expansion влита в revive**, релиз **v0.8** (XM8, ПП «Гепард», 79 обвесов): https://github.com/ggy1331/brainout-revive/releases/tag/v0.8. Проверено: клиент из распакованного архива (jlink JRE) доходит до матча deathmatch с пресетом xm8-gepard, в error.log нет ошибок по новому контенту. Серверный jar не менялся (правки только в клиенте и контенте), но пакеты сервера пересобраны — хосту нужны свежие `bin/server/packages`.
