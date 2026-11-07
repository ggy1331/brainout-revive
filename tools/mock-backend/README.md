# Имитация бэкенда Anthill

Локальная замена официальных онлайн-сервисов BRAIN / OUT (`env.brainout.org` мёртв).
Один процесс на Python (только стандартная библиотека), данные — JSON-файлы в `backend-data/`.

Запуск вместе с игрой: `play-online.bat` из корня репо (бэкенд + клиент → хаб; серверы бэкенд запускает сам).
Остановить бэкенд и все его серверы: `stop-online.bat`.
Отладка без кликов: флаг клиента `--auto-continue` сам проходит заставку «нажмите, чтобы продолжить».
Вручную: `build\pyenv\Scripts\python.exe tools\mock-backend\backend.py --port 9511 [--public-host IP]`.

Игра находит бэкенд через флаг клиента `--env http://HOST:9511/environment`
(или переменную `BRAINOUT_ENV_SERVICE`). Игровой серверу нужны env `login_access_token`
(выдаёт `/login/server-token`) и `discovery_services` — это делает `play-online.ps1`.

## Что готово

| Сервис | Что умеет |
|---|---|
| environment | `/environment/<app>/<version>` → адрес discovery |
| discovery | `/discovery/services/a,b,c` → адреса сервисов (все на этом же сервере) |
| login | анонимный вход `/auth`, `/extend`, `/validate`, токен для игрового сервера `/server-token` |
| profile | `/profile/me`, `/profile/<account>`, `/profiles`; слияние и `@func` — код из anthill-common |
| market | рынок `freeplay`: склад/тайник (предметы = имя + свойства, рубли = `ru`), барахолка (заказы с хранением выставленного, покупка, снятие, возврат по сроку), настройки (`fee`, `max-price`… — можно переопределить в `backend-data/market_settings/freeplay.json`) |
| game | регионы (`local`), поиск/создание комнат, комната по номеру, список комнат (браузер серверов). **Сам запускает игровые серверы** по запросу (`lobby`, `main`, `freeplay`, `duel`, `zombie`, `custom` — таблица `GAMES` в `services/game.py`), порты с 36600, логи `build/rooms/`. Одна комната на (игру, настройки) переиспользуется, пока процесс жив |
| message | WebSocket `/message/listen` (JSON-RPC 2.0, свой минимальный WebSocket на stdlib — `services/websocket.py`): живая доставка пользователю (`user`) и группе (`social-group` = клан), `send_message` / `mark_as_read` / `delete_message` / `update_message`; история `/message/messages`, `/message/group/<класс>/<ключ>`. Рынок шлёт владельцу `order_completed` / `order_cancelled` |
| social | **кланы** (группы): создание, поиск, вступление free/approve/invite, заявки и приглашения, права и роли, исключение, передача владения, профили клана/участника с `@func`, уведомления через message — как anthill-social. **Друзья** (наша добавка, в оригинале были только друзья Steam): `/social/friends` (список со статусом friend/incoming/outgoing, «в сети», комната), `add` по нику или аккаунту (взаимно = друзья), `remove`, `invite` в комнату (сообщение `friend_invite`) |
| leaderboard | рейтинги: `top100` (игроки по K/D, присылает `PostLeaderboardPlugin` в конце матча при K/D ≥ 1,5; плюс все, у кого в профиле есть `kpd`), `clans100` (кланы), рейтинги событий; срок жизни записей |
| static | загрузка аватаров клана/профиля (`PUT /static/upload`), раздача `/static/files/<id>` |
| game: party | **пати** (игра с напарником в Зоне): WebSocket `/game/party/create/...` и `/game/party/<id>/session` (JSON-RPC, как `GameService.PartySession`), вход, выход, автостарт, `game_started` с комнатой каждому — `services/party.py` |
| revive | **синхронизация одиночной Зоны с хостом** (наша добавка, `services/revive.py`): `/revive/snapshot`, `/revive/apply`; профиль — побеждает изменённая сторона, тайник/рубли — трёхстороннее слияние (локальное + (хост − база)) |
| event, store, blog | заглушки: пустые списки |

Проверка без игры: `build\pyenv\Scripts\python.exe tools\mock-backend\test_backend.py`.

## Одиночный режим (`--solo НИК`)
`play-solo.bat` поднимает этот же бэкенд локально (порт 9521, данные `solo-data/<ник>/`) с флагом `--solo`:
«хаб» заменён Зоной конфликта на одного игрока, `--sync-host http://IP:9511` — синхронизация прогресса
с хостом при старте, `--sync-only` — только синхронизация. Первый аккаунт локального бэкенда получает прогресс,
скачанный с хоста (`adopt_pending`). Тест: `python tools\mock-backend	est_sync.py`.

## Дальше
event (события, боевой пропуск), store, недвижимость…

## Как добавлять сервис
1. Посмотреть, какие запросы шлёт игра: `build/backend-out.log` (неизвестные → 404 с путём).
2. Формат ответа — в `anthill-platform/anthill-runtime-java` (что читает клиент) и в исходниках
   соответствующего сервиса `anthill-platform/anthill-<service>`.
3. Модуль в `services/`, регистрация в `services/__init__.py`.

Подвох: клиентская библиотека разбирает JSON, только если `Content-Type` ровно `application/json`.
