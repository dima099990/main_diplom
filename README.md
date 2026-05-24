# Kayros CRM

CRM-система для сервисного центра по ремонту смартфонов.  
Включает публичный сайт, панель управления CRM и Telegram-бота с ИИ-ассистентом.

---

## Стек

| Компонент | Технология |
|-----------|-----------|
| Бэкенд | Django 6 |
| База данных | SQLite (локально) / PostgreSQL (сервер) |
| Фронтенд | Tailwind CSS, Alpine.js |
| Telegram-бот | python-telegram-bot 22 |
| ИИ-ассистент | Groq API (llama-3.3-70b) |
| Прокси | SOCKS5 через Webshare.io (для серверов с блокировкой Telegram) |

---

## Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <url> && cd diplom

# 2. Создать виртуальное окружение
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / Mac
source .venv/bin/activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Создать .env (скопировать из примера)
cp .env.example .env

# 5. Применить миграции
python manage.py migrate

# 6. Заполнить тестовыми данными (опционально)
python manage.py seed_data

# 7. Запустить
python run.py
```

**Сайт:** http://127.0.0.1:8000  
**CRM:** http://127.0.0.1:8000/crm/  
**Логин / пароль после seed_data:** `admin` / `admin123`

---

## Все команды

### Запуск приложения

| Команда | Описание |
|---------|----------|
| `python run.py` | Запустить сайт + бот |
| `python run.py --site-only` | Запустить только сайт (без бота) |
| `python run.py --bot-only` | Запустить только Telegram-бота |
| `python run.py --host 0.0.0.0 --port 8000` | Запустить на всех интерфейсах (для сервера) |
| `python run.py --host 0.0.0.0 --port 8000 --site-only` | Только сайт, доступен снаружи |

### Управление базой данных

| Команда | Описание |
|---------|----------|
| `python manage.py migrate` | Применить все миграции |
| `python manage.py makemigrations` | Создать новые миграции после изменений моделей |
| `python manage.py seed_data` | Заполнить БД тестовыми данными (бренды, прайс, сотрудники, 40 заказов) |
| `python manage.py clear_db` | Очистить транзакционные данные (заказы, клиенты, склад, продажи) |
| `python manage.py clear_db --all` | Очистить всё включая справочники и пользователей |
| `python manage.py clear_db --yes` | Очистить без запроса подтверждения |
| `python manage.py reset_db` | **Полный сброс БД** — удаляет всё, пересоздаёт структуру, предлагает создать суперюзера |
| `python manage.py reset_db --yes` | Полный сброс без подтверждения |

### Администрирование Django

| Команда | Описание |
|---------|----------|
| `python manage.py createsuperuser` | Создать нового администратора |
| `python manage.py changepassword <username>` | Сменить пароль пользователя |
| `python manage.py collectstatic` | Собрать статику в папку staticfiles (для продакшна) |
| `python manage.py shell` | Открыть Django-консоль (Python REPL с доступом к моделям) |
| `python manage.py dbshell` | Открыть консоль базы данных |
| `python manage.py check` | Проверить проект на ошибки конфигурации |
| `python manage.py showmigrations` | Показать список всех миграций и их статус |

### Виртуальное окружение и пакеты

| Команда | Описание |
|---------|----------|
| `pip install -r requirements.txt` | Установить все зависимости |
| `pip freeze` | Показать все установленные пакеты с версиями |
| `pip list` | Показать установленные пакеты |
| `pip install <пакет>` | Установить пакет |
| `pip uninstall <пакет>` | Удалить пакет |

---

## Настройка Telegram-бота

1. Создать бота через [@BotFather](https://t.me/BotFather) → получить токен
2. Открыть **CRM → Настройки → Telegram-бот**
3. Вставить токен бота
4. Вставить Groq API Key (получить на [console.groq.com/keys](https://console.groq.com/keys), бесплатно, начинается с `gsk_`)
5. Заполнить системный промпт — описание вашего сервисного центра

### Прокси (для серверов в России)

Если сервер находится в России и Telegram заблокирован — бот автоматически использует SOCKS5-прокси из файла `bot/proxies.txt`.

Формат файла (один прокси на строку):
```
socks5://username:password@host:port
```

Получить бесплатные прокси: [webshare.io](https://webshare.io) → Proxy List → скачать в формате IP:PORT:USER:PASS.

При запуске бот сам перебирает прокси и берёт первый рабочий. Если все недоступны — запускается без прокси.

---

## Файл .env

```env
# Режим отладки
DEBUG=False

# Секретный ключ Django (обязательно сменить в продакшне)
SECRET_KEY=ваш-длинный-случайный-ключ

# Разрешённые хосты (через запятую)
ALLOWED_HOSTS=161.104.32.125,localhost,127.0.0.1

# База данных
USE_SQLITE=True                  # True = SQLite, False = PostgreSQL

# PostgreSQL (если USE_SQLITE=False)
DB_NAME=kayros_crm
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

---

## Страницы сайта

| Адрес | Описание |
|-------|----------|
| `/` | Главная |
| `/about/` | О компании |
| `/prices/` | Прайс-лист |
| `/contacts/` | Контакты |

## Страницы CRM

| Адрес | Описание |
|-------|----------|
| `/crm/` | Вход / дашборд |
| `/crm/repairs/` | Заказы на ремонт |
| `/crm/appointments/` | Записи на ремонт |
| `/crm/customers/` | Клиенты |
| `/crm/warehouse/` | Склад (запчасти, аксессуары) |
| `/crm/sales/` | Продажи аксессуаров |
| `/crm/finance/` | Финансы и расчёт зарплат |
| `/crm/employees/` | Сотрудники |
| `/crm/documents/` | Печать актов и документов |
| `/crm/analytics/` | Аналитика |
| `/crm/settings/` | Настройки компании и бота |

---

## Роли пользователей

| Роль | Доступ |
|------|--------|
| `admin` | Всё: настройки, зарплаты всех, штрафы, аналитика |
| `manager` | Заказы, клиенты, склад, продажи, задачи |
| `employee` | Свои заказы, свои задачи, своя зарплата |

Роль назначается в **CRM → Сотрудники → редактировать**.

---

## Структура проекта

```
diplom/
├── run.py                    # Точка входа — запуск сайта и бота
├── manage.py                 # Django management
├── requirements.txt
├── .env                      # Конфигурация (не в git)
├── .env.example              # Пример конфигурации
│
├── config/                   # Настройки Django
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── core/                     # Публичный сайт
│   ├── models.py             # SiteSettings, Brand, PhoneModel, RepairService
│   ├── views.py
│   ├── urls.py
│   └── context_processors.py
│
├── crm/                      # CRM-панель
│   ├── models.py             # RepairOrder, Customer, Appointment...
│   ├── views.py
│   ├── urls.py
│   ├── decorators.py         # @crm_required, @admin_required
│   ├── signals.py            # Автосоздание профиля пользователя
│   └── management/commands/
│       ├── seed_data.py      # Тестовые данные
│       └── clear_db.py       # Очистка БД
│
├── bot/                      # Telegram-бот
│   ├── main.py               # Точка входа бота
│   ├── db.py                 # Работа с БД через Django ORM
│   ├── ai.py                 # Groq API (ИИ-ассистент)
│   ├── proxy.py              # Автовыбор рабочего SOCKS5-прокси
│   ├── proxies.txt           # Список прокси
│   ├── django_setup.py       # Инициализация Django вне веб-сервера
│   └── handlers/
│       ├── start.py          # /start, регистрация клиента
│       ├── booking.py        # Запись на ремонт (диалог)
│       ├── prices.py         # Поиск цен
│       └── chat.py           # ИИ-чат, запись через нейросеть
│
└── templates/
    ├── core/                 # Шаблоны публичного сайта
    └── crm/                  # Шаблоны CRM
```

---

## Деплой на сервер

```bash
# 1. Загрузить файлы на сервер
git pull  # или scp/ftp

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Применить миграции
python manage.py migrate

# 4. Собрать статику
python manage.py collectstatic --noinput

# 5. Запустить (доступен снаружи по IP)
python run.py --host 0.0.0.0 --port 8000

# В фоне (не закрывается при отключении SSH)
nohup python run.py --host 0.0.0.0 --port 8000 > app.log 2>&1 &

# Через screen
screen -S kayros
python run.py --host 0.0.0.0 --port 8000
# Ctrl+A, D — отсоединиться
screen -r kayros  # вернуться
```

**Порт в фаерволе (Ubuntu):**
```bash
ufw allow 8000
```
