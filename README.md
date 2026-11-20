# Telegram-бот: email → Google Sheets

Проект принимает сообщения с email в Telegram, валидирует адрес и добавляет строку в лист `Задача 3` Google-таблицы. В таблицу записываются время, email, Telegram username/ID и Telegram update ID. Бот принимает сообщения от всех пользователей.

## Файлы

- `email_capture_bot.py` — long-polling бот на Python.
- `email-capture-bot.service` — постоянный запуск на Ubuntu/Debian через systemd.
- `BOT_SETUP_RU.md` — настройка Google Sheets, сервисного аккаунта и локальный запуск.
- `DEPLOY_VPS_RU.md` — установка на VPS.
- `AI_content_department_and_competitors.xlsx` — рабочая таблица с листами «Задача 1», «Задача 2», «Задача 3».

## Быстрый старт на Ubuntu 24.04

1. Настрой Google Sheets API и сервисный аккаунт; дай ему права редактора на таблицу.
2. Положи JSON-ключ в `/opt/email-capture-bot/google-service-account.json`.
3. Установи зависимости из `requirements-email-bot.txt`.
4. Задай в `/etc/email-capture-bot.env` переменные `TELEGRAM_BOT_TOKEN`, `GOOGLE_SPREADSHEET_ID` и `GOOGLE_SERVICE_ACCOUNT_FILE`.
5. Установи `email-capture-bot.service`, затем включи и запусти его через `systemctl enable --now email-capture-bot`.

Подробные команды и диагностика находятся в инструкциях. Секреты в репозиторий не добавлять.
