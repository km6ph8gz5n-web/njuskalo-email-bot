# Инструкция по развертыванию бота на Render

## 1. Создание GitHub репозитория

1. Зайдите на https://github.com/new
2. Создайте новый репозиторий с названием `njuskalo-email-bot`
3. Не инициализируйте README (у нас уже есть файлы)
4. После создания скопируйте URL репозитория

## 2. Загрузка кода на GitHub

В папке проекта выполните команды:

```bash
cd C:\Users\Professional\njuskalo-email-bot
git remote add origin https://github.com/ВАШ_USERNAME/njuskalo-email-bot.git
git branch -M main
git push -u origin main
```

## 3. Развертывание на Render

### 3.1 Регистрация на Render
1. Зайдите на https://render.com
2. Зарегистрируйтесь через GitHub аккаунт

### 3.2 Создание Web Service
1. Нажмите "New +"
2. Выберите "Web Service"
3. Подключите ваш GitHub репозиторий
4. Render автоматически определит Python проект

### 3.3 Настройка переменных окружения

В разделе "Environment" добавьте следующие переменные:

| Переменная | Значение |
|------------|----------|
| `BOT_TOKEN` | Ваш токен от @BotFather |
| `SMTP_HOST` | smtp.gmail.com (или другой SMTP) |
| `SMTP_PORT` | 587 |
| `SMTP_USER` | ваш email@gmail.com |
| `SMTP_PASSWORD` | пароль приложения Gmail |
| `EMAIL_FROM` | ваш email@gmail.com |
| `EMAIL_FROM_NAME` | Njuškalo Notification |
| `EMAIL_SUBJECT` | Poruka s Njuškala |
| `REPLY_TO` | ваш email@gmail.com |

### 3.4 Запуск
1. Нажмите "Create Web Service"
2. Render начнет сборку и запуск
3. После успешного деплоя бот будет доступен в Telegram

## 4. Важные замечания

- Бесплатный план Render имеет ограничения по времени работы (сервис может спать при неактивности)
- Для Gmail обязательно используйте "App Password", а не обычный пароль
- Первое развертывание может занять несколько минут
- Логи доступны в панели Render во вкладке "Logs"

## 5. Проверка работы

После деплоя:
1. Откройте вашего бота в Telegram
2. Нажмите /start
3. Проверьте, что бот отвечает на команды