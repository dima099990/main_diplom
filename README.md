# Kayros CRM — система для сервисного центра

Простая CRM для управления ремонтами, складом, продажами и сотрудниками. Написана на Django.

---

## Как запустить

```bash
# Клонировать проект
git clone https://github.com/dima099990/main_diplom
cd diplom

# Создать виртуальное окружение
python -m venv .venv

# Активировать (Linux/Mac)
source .venv/bin/activate

# Активировать (Windows)
.venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Применить миграции
python manage.py migrate

# Заполнить тестовыми данными (опционально)
python manage.py seed_data

# Создать администратора
python manage.py createsuperuser

# Запустить сервер
python manage.py runserver
```

Открыть в браузере: http://127.0.0.1:8000

---

## Страницы

| Адрес | Что там |
|---|---|
| `/` | Публичный сайт (главная, прайс, контакты) |
| `/crm/` | CRM — вход для сотрудников |
| `/crm/repairs/` | Заказы на ремонт |
| `/crm/sales/` | Продажи |
| `/crm/warehouse/` | Склад (запчасти и аксессуары) |
| `/crm/finance/` | Финансы и зарплаты |
| `/crm/documents/` | Печать документов |
| `/admin/` | Панель Django-администратора |

---

## Роли пользователей

- **admin** — полный доступ, управление зарплатами и штрафами
- **manager** — доступ к заказам, складу, продажам
- **employee** — базовый доступ, только свои данные

---

## Настройки

Основные параметры задаются через файл `.env` (или переменные окружения):

```
SECRET_KEY=your-secret-key
DEBUG=True
USE_SQLITE=True
```

По умолчанию используется SQLite — ничего настраивать не нужно.

---

## Структура проекта

```
diplom/
├── config/          # Настройки Django (settings, urls, asgi)
├── core/            # Публичный сайт
├── crm/             # CRM: модели, представления, урлы
├── templates/       # Все HTML-шаблоны
│   ├── core/        # Шаблоны публичного сайта
│   └── crm/         # Шаблоны CRM
├── static/          # CSS, JS, изображения
├── manage.py
└── requirements.txt
```

---

## Перед деплоем

- Поменять `SECRET_KEY` на случайный
- Установить `DEBUG=False`
- Прописать `ALLOWED_HOSTS`
- Переключиться на PostgreSQL (убрать `USE_SQLITE=True`)
- Настроить Redis для уведомлений
