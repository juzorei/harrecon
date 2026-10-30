# harrecon

[English](README.md) | [Русский](README.ru.md)

Скилл и CLI, превращающие HAR-захват в инвентаризацию приватного API, схемы ответов и типизированный Python-клиент — офлайн, только stdlib.

У сайта без документированного API всё равно есть API: его вызывает фронтенд, и HAR-захват записывает каждый вызов. Обычный путь — перечитывать запросы руками, забыть заголовок и отлаживать вслепую. `harrecon` делает извлечение сам и оставляет человеку только решения:

```text
$ harrecon inventory capture.har
captured 6 entries, 2 JSON endpoints

auth mechanisms:
  authorization: Bearer: Bearer e…(32 chars)

  GET /v1/lots/{id}  [api.example.com] 200/200

$ harrecon schema capture.har "GET /v1/lots/{id}"
object
  id: int
  title: string
  price: number

$ harrecon diff worked.har broken.har
  ~ GET /v1/lots/{id}  schema changed:  + currency: string
```

## Что в репозитории

- **[skills/har-to-api-client](skills/har-to-api-client)** — гигиена захвата (Preserve log, HAR *с content*, захватить запрос авторизации), определение механизмов авторизации, оговорки вывода схем (слитые образцы ≠ документация), ревью клиента, отладка сломанного скрейпера через diff и проговоренные границы ToS: свой аккаунт, публичные данные, rate limits; без обхода авторизации.
- **tools/harrecon** — CLI ([README](tools/harrecon/README.md)): `inventory` / `schema` / `diff` / `gen`, redaction авторизации, скелеты типизированных клиентов, офлайн-тесты на фикстурных захватах.

## Установка

```bash
pip install harrecon
npx skills add juzorei/harrecon
```

## Рамки

Исследование совместимости сервисов, которые ты уполномочен использовать: свой аккаунт, публичные данные, вежливые клиенты. Не для обхода авторизации и скрейпинга против правил сервиса.

Лицензия MIT.
