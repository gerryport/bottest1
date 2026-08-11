# Telegram-бот — базовая версия (приветствие + кнопки)

## Что делает
- `/start` — приветствие и главное меню с inline-кнопками
- Кнопки "О нас" / "Помощь" с возвратом назад
- `/help` — то же меню

## Локальный запуск
```bash
pip install -r requirements.txt
export BOT_TOKEN="ваш_токен_от_BotFather"
python bot.py
```

## Деплой на Railway

1. Создайте новый репозиторий на GitHub и загрузите туда эти файлы
   (bot.py, requirements.txt, Procfile, runtime.txt, .gitignore).
2. На https://railway.app → **New Project** → **Deploy from GitHub repo**,
   выберите этот репозиторий.
3. Railway автоматически определит Python-проект по `requirements.txt`
   и запустит процесс из `Procfile` (`worker: python bot.py`).
4. Откройте вкладку **Variables** в настройках сервиса и добавьте:
   - `BOT_TOKEN` = токен, полученный от @BotFather
5. Убедитесь, что в настройках сервиса выбран тип процесса **worker**
   (не web) — боту на long polling не нужен открытый HTTP-порт.
6. Deploy. В логах должно появиться `🤖 Бот запущен...`

## Дальнейшее развитие
Каркас специально сделан простым, чтобы дальше добавлять:
- новые команды (`CommandHandler`)
- новые кнопки и разделы меню (`CallbackQueryHandler`)
- хранение данных (БД, например Railway Postgres)

Просто скажите, что должен уметь бот дальше — добавим.
