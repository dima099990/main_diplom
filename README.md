# Kayros — Сайт сервисного центра (Django)

## Быстрый старт

```bash
# 1. Клонировать / распаковать проект
cd repair_site

# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Применить миграции
python manage.py migrate

# 5. Создать суперпользователя
python manage.py createsuperuser

# 6. Запустить сервер
python manage.py runserver
```

Сайт: http://127.0.0.1:8000  
Админка: http://127.0.0.1:8000/admin  
(При первом запуске уже есть тестовый логин: admin / admin123)
## Команды
```bash
# 1. Создание зависимостей
pip freeze > requirements.txt
```

## Страницы
- `/` — Главная
- `/about/` — О нас
- `/prices/` — Прайс-лист
- `/contacts/` — Контакты
- `/admin/` — Административная панель

## Настройка через админку
1. **Настройки сайта** — название, телефон, адрес, ссылка на Telegram-бот, часы работы
2. **Категории устройств** — iPhone, Samsung, Xiaomi и т.д.
3. **Прайс-лист** — услуги с ценами, сроками, флагом "Популярная"
4. **Отзывы** — тексты клиентов, рейтинг, устройство
5. **Заявки** — входящие заявки с формы сайта

## Структура
```
repair_site/
├── config/          # Настройки Django
├── core/            # Основное приложение
│   ├── models.py    # БД: SiteSettings, DeviceCategory, RepairService, Review, ContactRequest
│   ├── views.py     # Контроллеры страниц
│   ├── admin.py     # Настройка админ-панели
│   └── static/      # CSS, JS
└── templates/core/  # HTML-шаблоны
    ├── base.html    # Навбар + футер
    ├── home.html    # Главная
    ├── about.html   # О нас
    ├── prices.html  # Прайс-лист
    └── contacts.html
```

## Продакшен
- Сменить `SECRET_KEY` в `settings.py`
- Установить `DEBUG = False`
- Настроить `ALLOWED_HOSTS`
- Подключить PostgreSQL вместо SQLite
