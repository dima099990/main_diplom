# Kayros CRM

CRM-система для сервисного центра по ремонту смартфонов.  
Включает публичный сайт, панель управления CRM и Telegram-бота с ИИ-ассистентом.

---

## Стек

| Компонент | Технология |
|-----------|-----------|
| Бэкенд | Django 6 |
| База данных | PostgreSQL (сервер) / SQLite (локально) |
| Фронтенд | Tailwind CSS, Alpine.js |
| Telegram-бот | python-telegram-bot 22 |
| ИИ-ассистент | Groq API (llama-3.3-70b) |
| Статика | WhiteNoise |

---

## Быстрый старт (локально)

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

# 4. Создать .env
cp .env.example .env
# Открыть .env и заполнить (минимум: USE_SQLITE=True, DEBUG=True)

# 5. Применить миграции
python manage.py migrate

# 6. Заполнить тестовыми данными
python manage.py seed_data

# 7. Запустить
python run.py
```

**Сайт:** http://127.0.0.1:8000  
**CRM:** http://127.0.0.1:8000/crm/  
**Логин / пароль после seed_data:** `admin` / `admin123`

---

## Деплой на сервер

### 1. Первичная настройка

```bash
# Клонировать репозиторий
cd /opt
git clone <url> main_diplom
cd main_diplom

# Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Создать и заполнить .env
cp .env.example .env
nano .env
```

Минимальный `.env` для сервера:

```env
DEBUG=False
SECRET_KEY=ваш-длинный-случайный-ключ
ALLOWED_HOSTS=ваш_ip,localhost,127.0.0.1
USE_SQLITE=False
DB_NAME=kayros_crm
DB_USER=postgres
DB_PASSWORD=ваш_пароль
DB_HOST=localhost
DB_PORT=5432
```

```bash
# Применить миграции
python3 manage.py migrate

# Собрать статику
python3 manage.py collectstatic --noinput

# Создать администратора
python3 manage.py createsuperuser

# Открыть порт
ufw allow 8000
```

---

### 2. Скрипт управления сервером (kayros)

Создать файл `/usr/local/bin/kayros`:

```bash
cat > /usr/local/bin/kayros << 'EOF'
#!/bin/bash
DIR=/opt/main_diplom
VENV=$DIR/.venv/bin/activate

start() {
  echo "Запускаю сайт..."
  cd $DIR
  source $VENV
  nohup python3 run.py --host 0.0.0.0 --port 8000 > /tmp/kayros_site.log 2>&1 &
  echo "✓ Сайт запущен (PID $!)"
}

stop() {
  pkill -f "manage.py runserver" 2>/dev/null
  pkill -f "run.py --host" 2>/dev/null
  pkill -f "bot/main.py" 2>/dev/null
  echo "✓ Все процессы остановлены"
}

status() {
  echo "=== Статус процессов ==="
  pgrep -fa "manage.py runserver" || echo "  сайт: не запущен"
  pgrep -fa "bot/main.py"         || echo "  бот:  не запущен"
}

logs() {
  tail -f /tmp/kayros_site.log
}

kill_all() {
  pkill -9 -f "manage.py runserver" 2>/dev/null
  pkill -9 -f "run.py --host" 2>/dev/null
  pkill -9 -f "bot/main.py" 2>/dev/null
  echo "✓ Принудительно остановлено"
}

case "$1" in
  start)   start   ;;
  stop)    stop    ;;
  restart) stop; sleep 1; start ;;
  status)  status  ;;
  logs)    logs    ;;
  kill)    kill_all ;;
  *) echo "Использование: kayros {start|stop|restart|status|logs|kill}" ;;
esac
EOF

chmod +x /usr/local/bin/kayros
echo "✓ Скрипт kayros установлен"
```

---

### 3. Короткие команды (~/.bashrc)

Вставить целиком в терминал сервера:

```bash
VENV=$(find /opt/main_diplom -name "activate" -path "*/bin/activate" 2>/dev/null | head -1)
echo "Venv найден: $VENV"

cat > ~/.bashrc << EOF
export PYTHONUNBUFFERED=1

DIR=/opt/main_diplom
VENV=$VENV

# Хелпер: активирует venv, запускает команду, деактивирует
_py() { source \$VENV && "\$@"; deactivate; }

# Переключатель venv
venv() {
  if [ -n "\$VIRTUAL_ENV" ]; then
    deactivate && echo "✗ venv выключен"
  else
    source \$VENV && echo "✓ venv включён"
  fi
}

# Сервис
alias start='bash /usr/local/bin/kayros start'
alias stop='bash /usr/local/bin/kayros stop'
alias restart='bash /usr/local/bin/kayros restart'
alias status='bash /usr/local/bin/kayros status'
alias kill_all='bash /usr/local/bin/kayros kill'
alias logs='bash /usr/local/bin/kayros logs'

# Git / Деплой
alias pull='cd \$DIR && git stash && git pull'
alias deploy='cd \$DIR && git stash && git pull && _py python3 manage.py collectstatic --noinput && bash /usr/local/bin/kayros restart'

# База данных
alias db_fill='cd \$DIR && _py python3 manage.py seed_data'
alias db_prices='cd \$DIR && _py python3 manage.py seed_iphone_prices'
alias db_clear='cd \$DIR && _py python3 manage.py clear_db --yes'
alias db_clear_all='cd \$DIR && _py python3 manage.py clear_db --all --yes'
alias db_reset='cd \$DIR && _py python3 manage.py reset_db --yes'

# Система
alias mem='free -h'
alias disk='df -h /'
alias list='echo "
╔════════════════════════════════════════════════╗
║           KAYROS CRM — Команды                 ║
╠════════════════════════════════════════════════╣
║  СЕРВИС                                        ║
║    start         — запустить всё               ║
║    stop          — остановить всё              ║
║    restart       — перезапустить               ║
║    status        — статус процессов            ║
║    kill_all      — принудительно убить         ║
║    logs          — логи сервера                ║
╠════════════════════════════════════════════════╣
║  GIT / ДЕПЛОЙ                                  ║
║    pull          — stash + git pull            ║
║    deploy        — pull + static + restart     ║
╠════════════════════════════════════════════════╣
║  БАЗА ДАННЫХ                                   ║
║    db_fill       — заполнить рандомными данными║
║    db_prices     — загрузить прайс iPhone      ║
║    db_clear      — очистить данные (без юзеров)║
║    db_clear_all  — очистить всё + юзеры        ║
║    db_reset      — полный сброс + migrate      ║
╠════════════════════════════════════════════════╣
║  УТИЛИТЫ                                       ║
║    venv          — включить/выключить venv     ║
║    mem           — память                      ║
║    disk          — диск                        ║
║    list          — это меню                    ║
╚════════════════════════════════════════════════╝"'

EOF
source ~/.bashrc
echo "✓ .bashrc обновлён"
```

---

## Управление базой данных

| Команда Django | Короткая команда | Описание |
|---|---|---|
| `python3 manage.py seed_data` | `db_fill` | Заполнить тестовыми данными |
| `python3 manage.py seed_iphone_prices` | `db_prices` | Загрузить прайс iPhone |
| `python3 manage.py clear_db --yes` | `db_clear` | Очистить данные (без юзеров) |
| `python3 manage.py clear_db --all --yes` | `db_clear_all` | Очистить всё включая юзеров |
| `python3 manage.py reset_db --yes` | `db_reset` | Полный сброс + migrate |
| `python3 manage.py migrate` | — | Применить миграции |
| `python3 manage.py createsuperuser` | — | Создать администратора |
| `python3 manage.py collectstatic --noinput` | — | Собрать статику |

---

## Настройка Telegram-бота

1. Создать бота через [@BotFather](https://t.me/BotFather) → получить токен
2. Открыть **CRM → Настройки → Telegram-бот**
3. Вставить токен бота
4. Вставить Groq API Key (получить на [console.groq.com/keys](https://console.groq.com/keys), начинается с `gsk_`)
5. Заполнить системный промпт — описание сервисного центра

### Прокси (для серверов с блокировкой Telegram)

Добавить прокси в `bot/proxies.txt` (один на строку):
```
socks5://username:password@host:port
```

Получить бесплатные прокси: [webshare.io](https://webshare.io)

---

## Страницы

| Адрес | Описание |
|-------|----------|
| `/` | Главная |
| `/prices/` | Прайс-лист |
| `/contacts/` | Контакты |
| `/crm/` | CRM — вход / дашборд |
| `/crm/repairs/` | Заказы на ремонт |
| `/crm/appointments/` | Записи |
| `/crm/customers/` | Клиенты |
| `/crm/warehouse/` | Склад |
| `/crm/sales/` | Продажи |
| `/crm/finance/` | Финансы и зарплаты |
| `/crm/employees/` | Сотрудники |
| `/crm/analytics/` | Аналитика |
| `/crm/settings/` | Настройки |
| `/crm/filemanager/` | Файловый менеджер (только admin) |

---

## Роли пользователей

| Роль | Доступ |
|------|--------|
| `admin` | Всё: настройки, зарплаты, аналитика, файловый менеджер |
| `manager` | Заказы, клиенты, склад, продажи, задачи |
| `master` | Свои заказы, задачи, зарплата |
| `employee` | Свои заказы, задачи, зарплата |

---

## Структура проекта

```
diplom/
├── run.py                    # Точка входа — запуск сайта и бота
├── manage.py
├── requirements.txt
├── .env                      # Конфигурация (не в git)
├── .env.example
│
├── config/                   # Настройки Django
│   ├── settings.py
│   └── urls.py
│
├── core/                     # Публичный сайт
│   ├── models.py             # SiteSettings, Brand, PhoneModel, RepairService
│   ├── views.py
│   └── static/core/
│       ├── css/style.css
│       └── js/main.js
│
├── crm/                      # CRM-панель
│   ├── models.py
│   ├── views.py
│   ├── static/crm/
│   │   ├── css/crm.css
│   │   └── js/crm.js
│   └── management/commands/
│       ├── seed_data.py
│       ├── seed_iphone_prices.py
│       ├── clear_db.py
│       └── reset_db.py
│
├── bot/                      # Telegram-бот
│   ├── main.py
│   ├── ai.py                 # Groq API
│   ├── proxy.py
│   └── proxies.txt
│
├── templates/
│   ├── core/                 # Шаблоны публичного сайта
│   └── crm/                  # Шаблоны CRM
│
├── media/                    # Загружаемые файлы (логотип и т.д.)
└── storage/                  # Файловый менеджер (только для сервера)
```
