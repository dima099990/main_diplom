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
PROXY_FILE=$DIR/bot/proxies.txt
PROXY_BAK=$DIR/bot/proxies.txt.disabled

start() {
  echo "Запускаю сайт..."
  cd $DIR
  source $VENV
  nohup python3 run.py --host 0.0.0.0 --port 8000 > /tmp/kayros_site.log 2>&1 &
  echo "✓ Сайт запущен (PID $!)"
}

stop() {
  pkill -f "run.py --host" 2>/dev/null
  pkill -f "bot/main.py" 2>/dev/null
  echo "✓ Все процессы остановлены"
}

status() {
  # Сайт
  SITE_PID=$(pgrep -f "run.py --host" 2>/dev/null | head -1)
  if [ -n "$SITE_PID" ]; then
    SITE_INFO="✅ работает   (PID $SITE_PID)"
  else
    SITE_INFO="❌ не запущен"
  fi

  # Бот
  BOT_PID=$(pgrep -f "bot/main.py" 2>/dev/null | head -1)
  if [ -n "$BOT_PID" ]; then
    BOT_INFO="✅ работает   (PID $BOT_PID)"
  else
    BOT_INFO="❌ не запущен"
  fi

  # Прокси
  if [ -f "$PROXY_FILE" ]; then
    CNT=$(grep -c "socks5" "$PROXY_FILE" 2>/dev/null || echo 0)
    PROXY_INFO="✅ включён    ($CNT шт.)"
  elif [ -f "$PROXY_BAK" ]; then
    PROXY_INFO="⛔ выключен   (файл скрыт)"
  else
    PROXY_INFO="⚠️  файл не найден"
  fi

  # VPN
  VPN_IF=$(ip link show 2>/dev/null | grep -oE "(tun|wg|ppp)[0-9]+" | head -1)
  if [ -n "$VPN_IF" ]; then
    VPN_IP=$(ip addr show "$VPN_IF" 2>/dev/null | grep "inet " | awk '{print $2}' | cut -d/ -f1)
    VPN_INFO="✅ подключён  ($VPN_IF $VPN_IP)"
  else
    VPN_INFO="⛔ не подключен"
  fi

  # Память и диск
  MEM=$(free -h | awk '/^Mem:/ {print $3" / "$2}')
  DISK=$(df -h / | awk 'NR==2 {print $3" / "$2"  ("$5")"}')

  echo ""
  echo "╔══════════════════════════════════════════════╗"
  echo "║           KAYROS CRM — Статус               ║"
  echo "╠══════════════════════════════════════════════╣"
  printf "║  Сайт    %-36s║\n" "$SITE_INFO"
  printf "║  Бот     %-36s║\n" "$BOT_INFO"
  printf "║  Прокси  %-36s║\n" "$PROXY_INFO"
  printf "║  VPN     %-36s║\n" "$VPN_INFO"
  echo "╠══════════════════════════════════════════════╣"
  printf "║  Память  %-36s║\n" "$MEM"
  printf "║  Диск    %-36s║\n" "$DISK"
  echo "╚══════════════════════════════════════════════╝"
  echo ""
}

proxy_toggle() {
  if [ -f "$PROXY_FILE" ]; then
    mv "$PROXY_FILE" "$PROXY_BAK"
    echo "⛔ Прокси выключен — proxies.txt скрыт"
    echo "   Перезапустите бот: restart"
  elif [ -f "$PROXY_BAK" ]; then
    mv "$PROXY_BAK" "$PROXY_FILE"
    echo "✅ Прокси включён — proxies.txt восстановлен"
    echo "   Перезапустите бот: restart"
  else
    echo "⚠️  Файл proxies.txt не найден — нечего переключать"
  fi
}

logs() {
  tail -f /tmp/kayros_site.log
}

kill_all() {
  pkill -9 -f "run.py --host" 2>/dev/null
  pkill -9 -f "bot/main.py" 2>/dev/null
  echo "✓ Принудительно остановлено"
}

case "$1" in
  start)   start         ;;
  stop)    stop          ;;
  restart) stop; sleep 1; start ;;
  status)  status        ;;
  proxy)   proxy_toggle  ;;
  logs)    logs          ;;
  kill)    kill_all      ;;
  *) echo "Использование: kayros {start|stop|restart|status|proxy|logs|kill}" ;;
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
alias proxy='bash /usr/local/bin/kayros proxy'

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
║    status        — статус: сайт/бот/прокси/vpn ║
║    kill_all      — принудительно убить         ║
║    logs          — логи сервера                ║
╠════════════════════════════════════════════════╣
║  СЕТЬ                                          ║
║    proxy         — вкл/выкл прокси (SOCKS5)   ║
╠════════════════════════════════════════════════╣
║  GIT / ДЕПЛОЙ                                  ║
║    pull          — stash + git pull            ║
║    deploy        — pull + static + restart     ║
╠════════════════════════════════════════════════╣
║  БАЗА ДАННЫХ                                   ║
║    db_fill       — заполнить тестовыми данными ║
║    db_prices     — загрузить прайс iPhone      ║
║    db_clear      — очистить данные (без юзеров)║
║    db_clear_all  — очистить всё + юзеры        ║
║    db_reset      — полный сброс + migrate      ║
╠════════════════════════════════════════════════╣
║  УТИЛИТЫ                                       ║
║    venv          — включить/выключить venv     ║
║    mem           — использование памяти        ║
║    disk          — использование диска         ║
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

Файл `bot/proxies.txt` — список SOCKS5 прокси. Бот автоматически перебирает их и берёт первый рабочий.

**Добавить прокси в Telegram одним нажатием:**

| # | Сервер | Ссылка |
|---|--------|--------|
| 1 | 38.154.203.95:5863 | [Добавить в Telegram](https://t.me/proxy?server=38.154.203.95&port=5863&user=edltkbwa&pass=4chcrqzr8gkz) |
| 2 | 198.105.121.200:6462 | [Добавить в Telegram](https://t.me/proxy?server=198.105.121.200&port=6462&user=edltkbwa&pass=4chcrqzr8gkz) |
| 3 | 64.137.96.74:6641 | [Добавить в Telegram](https://t.me/proxy?server=64.137.96.74&port=6641&user=edltkbwa&pass=4chcrqzr8gkz) |
| 4 | 209.127.138.10:5784 | [Добавить в Telegram](https://t.me/proxy?server=209.127.138.10&port=5784&user=edltkbwa&pass=4chcrqzr8gkz) |
| 5 | 38.154.185.97:6370 | [Добавить в Telegram](https://t.me/proxy?server=38.154.185.97&port=6370&user=edltkbwa&pass=4chcrqzr8gkz) |
| 6 | 84.247.60.125:6095 | [Добавить в Telegram](https://t.me/proxy?server=84.247.60.125&port=6095&user=edltkbwa&pass=4chcrqzr8gkz) |
| 7 | 142.111.67.146:5611 | [Добавить в Telegram](https://t.me/proxy?server=142.111.67.146&port=5611&user=edltkbwa&pass=4chcrqzr8gkz) |
| 8 | 194.39.32.164:6461 | [Добавить в Telegram](https://t.me/proxy?server=194.39.32.164&port=6461&user=edltkbwa&pass=4chcrqzr8gkz) |
| 9 | 191.96.254.138:6185 | [Добавить в Telegram](https://t.me/proxy?server=191.96.254.138&port=6185&user=edltkbwa&pass=4chcrqzr8gkz) |
| 10 | 31.58.9.4:6077 | [Добавить в Telegram](https://t.me/proxy?server=31.58.9.4&port=6077&user=edltkbwa&pass=4chcrqzr8gkz) |

Добавить новые прокси в `bot/proxies.txt` (один на строку):
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
