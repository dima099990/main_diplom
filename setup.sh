#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  KAYROS CRM — Автоматическая установка сервера
#  Запуск: sudo bash setup.sh
# ═══════════════════════════════════════════════════════════════════════════

set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m';   BLUE='\033[0;34m'; NC='\033[0m'

ok()   { echo -e "${GREEN}  ✓${NC} $1"; }
step() { echo -e "\n${BLUE}▶${NC}  $1"; }
warn() { echo -e "${YELLOW}  ⚠${NC}  $1"; }
err()  { echo -e "${RED}  ✗${NC}  $1"; exit 1; }

# ───────────────────────────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║      KAYROS CRM — Автоматическая установка     ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""

[ "$EUID" -ne 0 ] && err "Запустите от root:  sudo bash setup.sh"

DIR=/opt/main_diplom

# ── 1. Системные пакеты ────────────────────────────────────────────────────
step "Системные пакеты..."
apt-get update -qq
apt-get install -y -qq \
  python3 python3-pip python3-venv \
  git postgresql postgresql-contrib \
  ufw curl
ok "Пакеты установлены"

# ── 2. PostgreSQL ──────────────────────────────────────────────────────────
step "PostgreSQL..."
systemctl start postgresql  2>/dev/null || service postgresql start 2>/dev/null || true
systemctl enable postgresql 2>/dev/null || true

DB_NAME="kayros_crm"
DB_USER="kayros"

# Берём пароль из .env если уже есть, иначе генерируем
if [ -f "$DIR/.env" ] && grep -q "^DB_PASSWORD=" "$DIR/.env"; then
  DB_PASS=$(grep "^DB_PASSWORD=" "$DIR/.env" | cut -d= -f2-)
else
  DB_PASS=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24)
fi

sudo -u postgres psql -tc "SELECT 1 FROM pg_user     WHERE usename='$DB_USER'" 2>/dev/null | grep -q 1 \
  || sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null | grep -q 1 \
  || sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null

ok "PostgreSQL: БД=$DB_NAME  пользователь=$DB_USER"

# ── 3. Репозиторий ─────────────────────────────────────────────────────────
step "Репозиторий..."
if [ -d "$DIR/.git" ]; then
  warn "Репозиторий уже клонирован — выполняю git pull"
  cd "$DIR" && git stash 2>/dev/null; git pull
  ok "Репозиторий обновлён"
else
  echo ""
  read -rp "    URL репозитория (git clone): " REPO_URL
  [ -z "$REPO_URL" ] && err "URL не указан"
  git clone "$REPO_URL" "$DIR"
  ok "Репозиторий клонирован в $DIR"
fi
cd "$DIR"

# ── 4. Виртуальное окружение ───────────────────────────────────────────────
step "Виртуальное окружение..."
[ ! -d "$DIR/.venv" ] && python3 -m venv "$DIR/.venv"
source "$DIR/.venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r requirements.txt
ok "Зависимости установлены"

# ── 5. Файл .env ───────────────────────────────────────────────────────────
step "Файл .env..."
if [ ! -f "$DIR/.env" ]; then
  SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  SERVER_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
  cat > "$DIR/.env" << ENVEOF
DEBUG=False
SECRET_KEY=$SECRET
ALLOWED_HOSTS=$SERVER_IP,localhost,127.0.0.1
USE_SQLITE=False
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS
DB_HOST=localhost
DB_PORT=5432
ENVEOF
  ok ".env создан (IP: $SERVER_IP)"
else
  warn ".env уже существует — пропускаю"
fi

# ── 6. Миграции и статика ──────────────────────────────────────────────────
step "Миграции..."
"$DIR/.venv/bin/python3" manage.py migrate --noinput -v 0
ok "Миграции применены"

step "Статика..."
mkdir -p staticfiles
"$DIR/.venv/bin/python3" manage.py collectstatic --noinput -v 0
ok "Статика собрана"

deactivate

# ── 7. Суперпользователь ───────────────────────────────────────────────────
echo ""
echo -n "  Создать администратора CRM? [y/N]  "
read -r ANS_SU
if [[ "$ANS_SU" =~ ^[Yy]$ ]]; then
  "$DIR/.venv/bin/python3" manage.py createsuperuser
fi

# ── 8. Скрипт kayros ───────────────────────────────────────────────────────
step "Скрипт /usr/local/bin/kayros..."

cat > /usr/local/bin/kayros << 'KAYEOF'
#!/bin/bash
DIR=/opt/main_diplom
PROXY_FILE=$DIR/bot/proxies.txt
PROXY_BAK=$DIR/bot/proxies.txt.disabled
SEP="  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PY=$DIR/.venv/bin/python3

start() {
  [ ! -f "$PY" ] && echo "❌ venv не найден: $DIR/.venv" && exit 1
  cd $DIR
  echo "🚀 Запускаю сервер (статика собирается автоматически)..."
  nohup $PY run.py --host 0.0.0.0 --port 8000 > /tmp/kayros_site.log 2>&1 &
  echo "✓ Сайт запущен (PID $!)"
}

stop() {
  pkill -f "run.py --host" 2>/dev/null || true
  pkill -f "bot/main.py"   2>/dev/null || true
  echo "✓ Все процессы остановлены"
}

_detect_vpn() {
  VPN=$(ip -o link show up 2>/dev/null | awk '{print $2}' | tr -d ':' \
    | grep -E "^(tun|tap|wg|ppp|nordlynx|proton|vpn|warp|ovpn|pia|mullvad)" | head -1)
  [ -z "$VPN" ] && VPN=$(ip -o link show up 2>/dev/null | awk '{print $2}' | tr -d ':' \
    | grep -vE "^(lo$|eth[0-9]|ens[0-9]|enp[0-9]|eno[0-9]|em[0-9]|bond|br[-0-9]|veth|docker|lxc|lxd|virbr|dummy)" \
    | head -1)
  echo "$VPN"
}

status() {
  SITE_PID=$(pgrep -f "run.py --host" 2>/dev/null | head -1)
  [ -n "$SITE_PID" ] && S="✅ работает  (PID $SITE_PID)" || S="❌ не запущен"

  BOT_PID=$(pgrep -f "bot/main.py" 2>/dev/null | head -1)
  [ -n "$BOT_PID" ] && B="✅ работает  (PID $BOT_PID)" || B="❌ не запущен"

  if [ -f "$PROXY_FILE" ]; then
    CNT=$(grep -c "socks5" "$PROXY_FILE" 2>/dev/null || echo 0)
    P="✅ включён   ($CNT прокси)"
  elif [ -f "$PROXY_BAK" ]; then
    P="⛔ выключен  (файл скрыт)"
  else
    P="⚠️  файл не найден"
  fi

  VPN_IF=$(_detect_vpn)
  if [ -n "$VPN_IF" ]; then
    VPN_IP=$(ip addr show "$VPN_IF" 2>/dev/null | grep "inet " | awk '{print $2}' | cut -d/ -f1)
    V="✅ подключён ($VPN_IF · $VPN_IP)"
  else
    V="⛔ не подключен"
  fi

  MEM=$(free -h  | awk '/^Mem:/ {print $3" / "$2}')
  DISK=$(df -h / | awk 'NR==2  {print $3" / "$2" ("$5")"}')

  echo ""; echo "$SEP"; echo "         KAYROS CRM — Статус"; echo "$SEP"
  echo "  Сайт    :  $S"
  echo "  Бот     :  $B"
  echo "  Прокси  :  $P"
  echo "  VPN     :  $V"
  echo "$SEP"
  echo "  Память  :  $MEM"
  echo "  Диск    :  $DISK"
  echo "$SEP"; echo ""
}

proxy_toggle() {
  if [ -f "$PROXY_FILE" ]; then
    mv "$PROXY_FILE" "$PROXY_BAK"
    echo "⛔ Прокси выключен — proxies.txt скрыт"; echo "   Перезапустите: restart"
  elif [ -f "$PROXY_BAK" ]; then
    mv "$PROXY_BAK" "$PROXY_FILE"
    echo "✅ Прокси включён — proxies.txt восстановлен"; echo "   Перезапустите: restart"
  else
    echo "⚠️  Файл proxies.txt не найден"
  fi
}

logs()       { tail -f /tmp/kayros_site.log; }
force_kill() {
  pkill -9 -f "run.py --host" 2>/dev/null; pkill -9 -f "bot/main.py" 2>/dev/null
  echo "✓ Принудительно остановлено"
}

case "$1" in
  start)   start        ;;
  stop)    stop         ;;
  restart) stop; sleep 1; start ;;
  status)  status       ;;
  proxy)   proxy_toggle ;;
  logs)    logs         ;;
  kill)    force_kill   ;;
  *) echo "Использование: kayros {start|stop|restart|status|proxy|logs|kill}" ;;
esac
KAYEOF

chmod +x /usr/local/bin/kayros
ok "Скрипт kayros установлен"

# ── 9. Алиасы .bashrc ─────────────────────────────────────────────────────
step "Настройка команд ~/.bashrc..."

VENV_PATH=$(find "$DIR" -name "activate" -path "*/bin/activate" 2>/dev/null | head -1)

cat > ~/.bashrc << 'BASHEOF'
export PYTHONUNBUFFERED=1

DIR=/opt/main_diplom
PY=$DIR/.venv/bin/python3

venv() {
  VENV=$(find $DIR -name "activate" -path "*/bin/activate" 2>/dev/null | head -1)
  if [ -n "$VIRTUAL_ENV" ]; then deactivate && echo "✗ venv выключен"
  elif [ -n "$VENV" ]; then source $VENV && echo "✓ venv включён"
  else echo "❌ venv не найден в $DIR"; fi
}

# Сервис
alias start='bash /usr/local/bin/kayros start'
alias stop='bash /usr/local/bin/kayros stop'
alias restart='bash /usr/local/bin/kayros restart'
alias status='bash /usr/local/bin/kayros status'
alias kill='bash /usr/local/bin/kayros kill'
alias logs='bash /usr/local/bin/kayros logs'
alias proxy='bash /usr/local/bin/kayros proxy'

# Git / Деплой
alias pull='cd $DIR && git stash && git pull'
alias deploy='cd $DIR && git stash && git pull && bash /usr/local/bin/kayros restart'

# База данных — явный путь к Python venv
alias db_fill='cd $DIR && $PY manage.py seed_data'
alias db_prices='cd $DIR && $PY manage.py seed_iphone_prices'
alias db_clear='cd $DIR && $PY manage.py clear_db --yes'
alias db_clear_all='cd $DIR && $PY manage.py clear_db --all --yes'
alias db_reset='cd $DIR && $PY manage.py reset_db --yes'

# Система
alias mem='free -h'
alias disk='df -h /'
alias list='echo "
╔════════════════════════════════════════════════╗
║           KAYROS CRM — Команды                 ║
╠════════════════════════════════════════════════╣
║  СЕРВИС                                        ║
║    start        — запустить всё                ║
║    stop         — остановить всё               ║
║    restart      — перезапустить                ║
║    status       — сайт / бот / прокси / vpn   ║
║    kill         — принудительно убить всё      ║
║    logs         — логи сервера (tail -f)       ║
╠════════════════════════════════════════════════╣
║  СЕТЬ                                          ║
║    proxy        — вкл / выкл прокси SOCKS5    ║
╠════════════════════════════════════════════════╣
║  GIT / ДЕПЛОЙ                                  ║
║    pull         — stash + git pull             ║
║    deploy       — pull + restart               ║
╠════════════════════════════════════════════════╣
║  БАЗА ДАННЫХ                                   ║
║    db_fill      — заполнить тестовыми данными  ║
║    db_prices    — загрузить прайс iPhone       ║
║    db_clear     — очистить данные (без юзеров) ║
║    db_clear_all — очистить всё + юзеры         ║
║    db_reset     — полный сброс + migrate       ║
╠════════════════════════════════════════════════╣
║  УТИЛИТЫ                                       ║
║    venv         — включить / выключить venv    ║
║    mem          — использование памяти         ║
║    disk         — использование диска          ║
║    list         — это меню                     ║
╚════════════════════════════════════════════════╝"'

BASHEOF

sed -i "s|__VENV__|$VENV_PATH|g" ~/.bashrc
# shellcheck source=/dev/null
source ~/.bashrc 2>/dev/null || true
ok "Команды настроены"

# ── 10. Файрвол ────────────────────────────────────────────────────────────
step "Файрвол..."
ufw allow 8000/tcp 2>/dev/null && ok "Порт 8000 открыт" \
  || warn "ufw недоступен — откройте порт 8000 вручную"

# ── 11. Запуск ─────────────────────────────────────────────────────────────
echo ""
echo -n "  Запустить сервер сейчас? [y/N]  "
read -r ANS_START
if [[ "$ANS_START" =~ ^[Yy]$ ]]; then
  bash /usr/local/bin/kayros start
fi

# ── Итог ───────────────────────────────────────────────────────────────────
SERVER_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║           ✅  Установка завершена!               ║"
echo "  ╠══════════════════════════════════════════════════╣"
printf "  ║  Сайт : http://%-33s║\n" "$SERVER_IP:8000  "
printf "  ║  CRM  : http://%-33s║\n" "$SERVER_IP:8000/crm/  "
echo "  ╠══════════════════════════════════════════════════╣"
echo "  ║  Следующие шаги:                                 ║"
echo "  ║    1. source ~/.bashrc                           ║"
echo "  ║    2. list          — все команды                ║"
echo "  ║    3. CRM → Настройки → токен бота + Groq ключ  ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""
