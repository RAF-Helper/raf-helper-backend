# RAF Helper — Backend

FastAPI: Firebase JWT, PostgreSQL, Elasticsearch, мультиагентная обработка сообщений.

## Стек

- FastAPI, Uvicorn  
- PostgreSQL (async SQLAlchemy + asyncpg)  
- Elasticsearch (индексы staff, events, context_materials)  
- Firebase Admin — проверка ID token, домен `@bsu.by`, верификация email  
- OpenRouter (LangChain) — вызовы LLM  
- Presidio — маскирование PII перед агентами  

## Запуск (локально)

1. Поднять PostgreSQL и Elasticsearch.  
2. Скопировать `.env.example` в `.env`, заполнить `DATABASE_URL`, `ELASTICSEARCH_URL`, `FIREBASE_CREDENTIALS_PATH`, `OPENROUTER_API_KEY`.  
3. Положить JSON сервисного аккаунта Firebase рядом с путём из `FIREBASE_CREDENTIALS_PATH`.  
4. Установить зависимости и spaCy-модель для русского:

```bash
uv sync
uv run python -m spacy download ru_core_news_md
uv run uvicorn app:app --reload --port 8000
```

Документация API: `http://localhost:8000/docs`

## Основные маршруты

- `POST /auth/sync`, `GET /auth/me` — пользователь после Firebase  
- `GET/POST/PATCH/DELETE /chats/` — сессии чатов  
- `GET/POST /chats/{id}/messages` — история и новое сообщение (поле `agent` опционально)  
- `POST /files/` — загрузка файлов, индексация в ES  
- Админ: `/admin/staff`, `/admin/events`, `/admin/elastic`  

Stateless-роутер `POST /chat/` удалён; используйте только `/chats/...`.

## Известные ограничения

- Автоматический выбор агента без поля `agent` (оркестратор-роутер) — в разработке; клиенту лучше передавать `agent` явно.  
- Часть сценариев abstract/presentation — не полный итеративный пайплайн.  
- Alembic настроен; таблицы также создаются через `create_all` при старте — для продакшена предпочтительны миграции.

Подробнее по архитектуре — в `docs/design/` внутри репозитория.
