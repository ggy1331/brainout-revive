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
| event, store, blog | заглушки: пустые списки |

Проверка без игры: `build\pyenv\Scripts\python.exe tools\mock-backend\test_backend.py`.

## Дальше
message (`/message/listen` — WebSocket, сейчас 404), game (хаб, подбор игр), social (кланы, друзья), event (события, боевой пропуск), store, leaderboard…

## Как добавлять сервис
1. Посмотреть, какие запросы шлёт игра: `build/backend-out.log` (неизвестные → 404 с путём).
2. Формат ответа — в `anthill-platform/anthill-runtime-java` (что читает клиент) и в исходниках
   соответствующего сервиса `anthill-platform/anthill-<service>`.
3. Модуль в `services/`, регистрация в `services/__init__.py`.

Подвох: клиентская библиотека разбирает JSON, только если `Content-Type` ровно `application/json`.
