# Лабораторная работа №8: 

Выполнила: Сергеева Виталия Викторовна, 03_МОАИС_рбд2

![Структура проекта](img2.png)

Проект состоит из Flask-приложения (`app/`: handlers, services, repositories, security, validators), миграций БД, демо-скриптов (`password_demo.py`, `sql_demo.py`), статики (js/css) и конфигурации Nginx.

## 1. Безопасность на уровне приложения

**Хеширование паролей** (`app/security.py`):

![security.py](img3.png)

Пароли не хранятся в открытом виде. Перед bcrypt пароль сжимается через SHA-256 + base64 (bcrypt принимает максимум 72 байта). Также здесь генерируется CSRF-токен и описаны роли: `user` (`profile.read`, `profile.write`) и `admin` (дополнительно `users.read`, `users.delete`).

**Аутентификация и авторизация** (`app/handlers/auth_handler.py`):

![auth_handler.py](img4.png)

Декоратор `login_required` проверяет сессию по cookie и сверяет CSRF-токен из заголовка `X-CSRF-Token` с токеном в сессии (через `secrets.compare_digest`). Декоратор `require_permission` проверяет права роли.

## 2. HTTPS

Самоподписанный сертификат генерируется через openssl:

![Генерация сертификата](img5.png)

При первом заходе браузер (Kaspersky) ругается на недоверенный сертификат — это нормально для self-signed:

![Предупреждение о сертификате](img10.png)

После принятия открывается приложение по `https://localhost:8443`:

![Главная страница](img11.png)

Проверка TLS — используется TLS 1.3, шифр AES-256-GCM:

![Проверка TLS](img15.png)

Все HTTP-запросы редиректятся на HTTPS (301):

![Редирект на HTTPS](img14.png)

## 3. Конфигурация Nginx

![nginx.conf](img6.png)

Основные настройки:
- rate limiting зон (`limit_req_zone`) для API и страницы логина — защита от брутфорса;
- upstream `backend` с двумя репликами приложения (`api1:5000`, `api2:5000`) — балансировка нагрузки;
- редирект 80 → 443, HTTPS-сервер на 443 порту;
- security-заголовки подключаются из отдельного файла;
- кеширование статики (`location ~* \.(css|js)`: `Cache-Control: public, immutable`);
- обработка ошибок upstream: 502 Bad Gateway и 504 Gateway Timeout возвращаются в JSON;
- proxy_pass на бэкенд для `/api/`.

Запуск через Docker Compose:

![docker compose up](img7.png)

![Статус контейнеров](img8.png)

Конфигурация проверена (`nginx -t` — syntax is ok), миграции БД применены:

![Миграции БД](img9.png)

## 4. Проверка security-заголовков и статики

Ответы Nginx содержат security-заголовки: `Strict-Transport-Security`, `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Content-Security-Policy: default-src 'self'`:

![Заголовки главной страницы](img12.png)

Статика отдаётся Nginx с кешированием на 30 дней (`max-age=2592000, immutable`):

![Заголовки статики](img13.png)

## 5. Reverse proxy, балансировка и отказоустойчивость

Запрос `/api/health` проходит через Nginx на бэкенд:

![api/health](img16.png)

Видно, что запросы распределяются между api1 и api2 (заголовок `X-Served-By`):

![Балансировка](img17.png)

При остановке api1 сервис продолжает работать на api2:

![Отказ api1](img18.png)

При остановке обоих реплик Nginx возвращает 504 Gateway Timeout с JSON-ошибкой, в логах — `upstream timed out`:

![Отказ обоих реплик](img19.png)

То же самое при долгом запросе `/api/slow?seconds=15` (таймаут 5с):

![Таймаут slow](img20.png)

После возобновления работы запросы снова отдаются с 200:

![Восстановление](img21.png)

## 6. Регистрация, аутентификация, CSRF

Регистрация трёх пользователей (Anna, Boris, Carol) — 201 Created:

![Регистрация](img22.png)

Логин устанавливает cookie сессии с флагами `Secure, HttpOnly, SameSite=Strict` и возвращает `csrf_token`:

![Логин](img23.png)

Без cookie запрос к `/api/me` возвращает 401 Unauthorized:

![401 Unauthorized](img24.png)

Проверка CSRF: PUT-запрос без токена или с неверным токеном → 403 `CSRF_FAILED`; с правильным токеном → 200 OK:

![Проверка CSRF](img25.png)

## 7. Проверка прав доступа (авторизация)

Обычный пользователь **не может** редактировать чужой профиль (403 `You can modify only your own profile`), **не может** получить список пользователей (403 `users.read`):

![IDOR-проверка](img26.png)

После назначения роли admin (`make_admin`) Anna видит список пользователей и может редактировать чужие профили. Обычный пользователь по-прежнему получает 403:

![Права админа](img27.png)

Удаление пользователя: у обычного пользователя — 403, у админа — 204 No Content:

![Удаление пользователя](img28.png)

## 8. Защита паролей

Демо-скрипт показывает, почему нельзя хранить пароли в открытом виде и почему быстрый SHA-256 без соли уязвим к rainbow-таблицам. bcrypt с случайной солью делает перебор практически невозможным:

![Password demo](img29.png)

В базе данных хранятся только bcrypt-хеши:

![Хеши в БД](img30.png)

## 9. Защита от SQL-инъекций

Демонстрация: уязвимый код со строковой подстановкой допускает `' OR '1'='1` и `UNION SELECT`, а параметризованные запросы (`?`) обрабатывают ввод как обычный текст:

![SQL injection demo](img31.png)

Проверка через API: SQLi-атака на логин не проходит (401), попытка `DROP TABLE` в имени пользователя просто сохраняется строкой — таблица не удаляется:

![SQLi через API](img32.png)

## 10. XSS

XSS-пayload сохраняется в профиле через API:

![XSS payload](img33.png)

На уязвимой странице (рендер через `innerHTML`) скрипт выполняется. Cookies пустые, потому что у cookie стоит флаг `HttpOnly`:

![XSS vulnerable](img34.png)

Страница с CSP блокирует inline-обработчики — в консоли видно, что CSP запретила выполнение:

![CSP блокировка](img35.png)

Безопасная страница (рендер через `textContent`) выводит payload как обычный текст:

![XSS safe](img36.png)

## 11. CORS

Ответы содержат `Access-Control-Allow-Origin: http://localhost:8081` — разрешён только конкретный origin, чужой origin не подставляется:

![CORS-заголовки](img37.png)

Preflight-запрос OPTIONS проходит успешно (200), разрешены методы DELETE, GET, POST, PUT и заголовки `content-type`, `x-csrf-token`:

![Preflight](img38.png)

Запрос к защищённому ресурсу без авторизации — 401:

![401 для /api/users](img39.png)

Страница `cors-test` с разрешённого origin `http://localhost:8081` успешно получает данные:

![CORS allowed](img40.png)

С origin `http://localhost:8082` браузер блокирует запрос (нет `Access-Control-Allow-Origin`):

![CORS blocked](img41.png)

## 12. Rate limiting (защита от брутфорса)

10 подряд идущих попыток логина: первые 6 проходят до приложения (401), остальные отсекаются на Nginx с кодом 429 Too Many Requests:

![429 Too Many Requests](img42.png)

В логах Nginx видно `limiting requests, excess ... by zone "login"`:

![Логи rate limit](img43.png)
