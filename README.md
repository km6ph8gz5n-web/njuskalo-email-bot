# Telegram-бот: письмо в стиле Njuškalo

Бот на **aiogram 3** собирает текст и email, затем отправляет HTML-письмо через SMTP.

## 1. Подготовка

Нужны Python 3.10+ и токен бота от [@BotFather](https://t.me/BotFather).

```powershell
cd C:\Users\Professional\njuskalo-email-bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Файл `.env`

Откройте `.env` в корне проекта и подставьте свои значения:

| Переменная | Что указать |
|---|---|
| `BOT_TOKEN` | токен от BotFather |
| `SMTP_HOST` | для Gmail: `smtp.gmail.com` |
| `SMTP_PORT` | обычно `587` (STARTTLS) |
| `SMTP_USER` | ваш адрес Gmail |
| `SMTP_PASSWORD` | **пароль приложения**, не обычный пароль аккаунта |
| `EMAIL_FROM` | адрес отправителя (как правило тот же, что `SMTP_USER`) |
| `EMAIL_FROM_NAME` | имя в From, например `Njuškalo Notification` |
| `EMAIL_SUBJECT` | тема письма |
| `REPLY_TO` | адрес для ответов (можно совпадать с `EMAIL_FROM`) |

## 3. App Password для Gmail

1. Включите [двухэтапную аутентификацию](https://myaccount.google.com/signinoptions/two-step-verification).
2. Откройте [Пароли приложений](https://myaccount.google.com/apppasswords).
3. Создайте пароль для «Почта» / «Другое».
4. Скопируйте 16 символов в `SMTP_PASSWORD` (можно без пробелов).

Для Яндекса: `smtp.yandex.ru`, порт `587`, пароль приложения из настроек почты.  
Для Mail.ru: `smtp.mail.ru`, порт `587`.

## 4. Запуск

```powershell
python bot.py
```

В Telegram: `/start` → кнопка «Создать и отправить письмо» → текст → email. Отмена: кнопка **❌ Отмена** или `/cancel`.

## 5. Доставляемость (кратко)

- Не шлите пачками: десятки писем в минуту с одного IP/аккаунта — быстрый бан SMTP.
- Не используйте тестовые домены (`example.com`, `test.ru`) как **отправителя**. From должен совпадать с ящиком, через который идёт SMTP.
- Пишите нормальный текст: без КАПСА, «срочно/выигрыш/бесплатно», без кучи ссылок.
- Для своего домена настройте SPF, DKIM и DMARC. Gmail без этого часто кладёт письма в спам.
- Сначала проверьте на свой ящик, потом — на 1–2 реальных адреса.
- `Precedence: bulk` помечает рассылку как служебную: не смешивайте с личной перепиской и не маскируйте массовую рассылку под «личное письмо».
