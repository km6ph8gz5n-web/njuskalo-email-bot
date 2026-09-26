# Развертывание на Railway (бесплатно)

## Почему Railway?
- **Действительно бесплатный тариф** - $5 кредитов/месяц 
- Поддержка Python ботов без ограничений по типу сервиса
- Простое развертывание из GitHub

## Инструкция по развертыванию:

### 1. Регистрация на Railway
1. Зайдите на https://railway.app
2. Нажмите "Start a project"
3. Авторизуйтесь через GitHub

### 2. Создание проекта
1. Нажмите "New Project"
2. Выберите "Deploy from GitHub repo"
3. Найдите и выберите `njuskalo-email-bot`
4. Railway автоматически определит Python проект

### 3. Настройка переменных окружения
1. После создания проекта нажмите на вкладку "Variables"
2. Добавьте переменные (нажмите "New Variable"):

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | `8996320425:AAG2U02r7p1WJW6DatGL_FoJgaHJgJ2lUVs` |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `budavafel@gmail.com` |
| `SMTP_PASSWORD` | `fdtj qduz hnyk cizf` |
| `EMAIL_FROM` | `budavafel@gmail.com` |
| `EMAIL_FROM_NAME` | `Njuškalo Notification` |
| `EMAIL_SUBJECT` | `Poruka s Njuškala` |
| `REPLY_TO` | `budavafel@gmail.com` |

### 4. Запуск
1. Railway автоматически начнет развертывание
2. Следите за логами во вкладке "Logs"
3. После успешного запуска бот будет работать

### 5. Проверка
1. Откройте Telegram
2. Найдите вашего бота
3. Напишите `/start`
4. Проверьте работу

## Преимущества Railway перед Render:
- ✅ Действительно бесплатный тариф
- ✅ Нет ограничений по типу сервиса
- ✅ Поддержка long-running процессов
- ✅ Автоматический перезапуск при ошибках