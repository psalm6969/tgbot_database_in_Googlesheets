# Постоянный запуск бота на VPS (Ubuntu/Debian)

Эта инструкция настраивает запуск через `systemd`: сервис стартует после перезагрузки VPS и автоматически перезапускается при сбое.

## Что должно быть готово

- Ubuntu или Debian с `sudo`.
- Новый токен бота от @BotFather. Токен из переписки сначала отзови.
- ID Google-таблицы и JSON-ключ сервисного аккаунта, которому выдан доступ редактора к таблице.
- SSH-доступ к VPS. Пароль или токен бота не отправляй в переписку.

## 1. Скопируй файлы на сервер

Скопируй на VPS файлы `email_capture_bot.py`, `requirements-email-bot.txt` и `email-capture-bot.service`. Положи JSON-ключ Google в `/opt/email-capture-bot/google-service-account.json`.

Из PowerShell на Windows это можно сделать через `scp` (подставь свой SSH alias/адрес):

```powershell
scp .\email_capture_bot.py .\requirements-email-bot.txt user@YOUR_VPS:/tmp/
scp .\email-capture-bot.service user@YOUR_VPS:/tmp/
scp .\google-service-account.json user@YOUR_VPS:/tmp/
```

Если SSH alias уже настроен, вместо `user@YOUR_VPS` можно указать alias из `~/.ssh/config`.

## 2. Установи Python и разложи проект

Подключись по SSH и выполни:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
sudo useradd --system --home /opt/email-capture-bot --shell /usr/sbin/nologin emailbot || true
sudo install -d -o emailbot -g emailbot -m 0750 /opt/email-capture-bot
sudo install -o emailbot -g emailbot -m 0640 /tmp/email_capture_bot.py /opt/email-capture-bot/email_capture_bot.py
sudo install -o emailbot -g emailbot -m 0640 /tmp/requirements-email-bot.txt /opt/email-capture-bot/requirements-email-bot.txt
sudo install -o emailbot -g emailbot -m 0640 /tmp/google-service-account.json /opt/email-capture-bot/google-service-account.json
sudo -u emailbot python3 -m venv /opt/email-capture-bot/.venv
sudo -u emailbot /opt/email-capture-bot/.venv/bin/pip install --upgrade pip
sudo -u emailbot /opt/email-capture-bot/.venv/bin/pip install -r /opt/email-capture-bot/requirements-email-bot.txt
```

## 3. Сохрани секреты в локальном env-файле VPS

Создай файл:

```bash
sudo nano /etc/email-capture-bot.env
```

Содержимое (подставь значения прямо на VPS):

```dotenv
TELEGRAM_BOT_TOKEN=НОВЫЙ_ТОКЕН_ОТ_BOTFATHER
GOOGLE_SPREADSHEET_ID=ID_ТАБЛИЦЫ
GOOGLE_SERVICE_ACCOUNT_FILE=/opt/email-capture-bot/google-service-account.json
BOT_STATE_FILE=/var/lib/email-capture-bot/state.json
GOOGLE_SHEET_RANGE='Задача 3'!A:D
```

Ограничь доступ к файлу и установи service unit:

```bash
sudo chown root:root /etc/email-capture-bot.env
sudo chmod 600 /etc/email-capture-bot.env
sudo install -o root -g root -m 0644 /tmp/email-capture-bot.service /etc/systemd/system/email-capture-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now email-capture-bot
```

## 4. Проверь статус и логи

```bash
sudo systemctl status email-capture-bot --no-pager
sudo journalctl -u email-capture-bot -n 50 --no-pager
```

Открой бота в Telegram, нажми **Start** и отправь тестовый адрес. Он должен появиться в Google Sheets. В логах не должно быть `401 Unauthorized`, `403` от Sheets API или сетевых тайм-аутов.

## Управление

```bash
sudo systemctl restart email-capture-bot
sudo systemctl stop email-capture-bot
sudo systemctl start email-capture-bot
```

После изменения токена или env-файла перезапусти сервис. Бот принимает сообщения от всех пользователей Telegram.
