"""
python manage.py seed_iphone_prices

Заполняет базу данных ценами на ремонт iPhone.
Данные взяты с mobi-service.com.

Опции:
  --yes   Не спрашивать подтверждения
"""
from django.core.management.base import BaseCommand
from core.models import Brand, PhoneModel, RepairService


# ── Услуги по группам (название, duration) ────────────────────────────────────
SERVICES_TEMPLATE = [
    # (slug, name, duration, popular)
    ("diag",       "Диагностика",                              "30 мин",   False),
    ("glass",      "Замена стекла дисплея",                   "1–2 часа", True),
    ("screen_orig","Замена дисплея (оригинал)",               "1–2 часа", True),
    ("screen_oled","Замена дисплея (аналог OLED)",            "1–2 часа", False),
    ("screen_tft", "Замена дисплея (аналог TFT)",             "1–2 часа", False),
    ("battery",    "Замена аккумулятора",                     "30 мин",   True),
    ("back_glass", "Замена заднего стекла",                   "2–3 часа", False),
    ("cam_glass",  "Замена стекла камеры",                    "30 мин",   False),
    ("housing",    "Замена корпуса",                          "1–2 дня",  False),
    ("clean_dust", "Чистка сеток от пыли",                   "30 мин",   False),
    ("cam_main",   "Замена основной камеры",                  "1–2 часа", False),
    ("cam_front",  "Замена фронтальной камеры",               "1–2 часа", False),
    ("speaker_ear","Замена слухового динамика",               "1–2 часа", False),
    ("speaker_pol","Замена полифонического динамика",         "1–2 часа", False),
    ("vibro",      "Замена вибромотора",                      "30 мин",   False),
    ("charge",     "Замена шлейфа зарядки и микрофона",      "1–2 часа", False),
    ("buttons",    "Замена шлейфа кнопок",                   "1–2 часа", False),
    ("sensor",     "Замена шлейфа датчика света",            "1–2 часа", False),
    ("water",      "Чистка после влаги",                      "1–2 дня",  False),
    ("faceid",     "Ремонт Face ID",                          "1–2 дня",  False),
    ("ios_clean",  "Восстановление iOS (без данных)",         "1–2 часа", False),
    ("ios_data",   "Восстановление iOS (с данными)",         "2–3 часа", False),
    ("backup",     "Резервное копирование",                   "1–2 часа", False),
    ("app",        "Установка приложения",                    "15 мин",   False),
]

# ── Цены по моделям (slug -> price_from) ──────────────────────────────────────
# Источник: mobi-service.com
MODELS_PRICES = {
    "iPhone 15 Pro Max": {
        "diag": 0, "glass": 10800, "screen_orig": 39000, "screen_oled": 17400,
        "battery": 7700, "back_glass": 6800, "cam_glass": 2500, "housing": 16500,
        "clean_dust": 1000, "cam_main": 9100, "cam_front": 8700,
        "speaker_ear": 4000, "speaker_pol": 5000, "vibro": 2000,
        "charge": 6400, "buttons": 5800, "sensor": 8100,
        "water": 2000, "faceid": 10200,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 15 Pro": {
        "diag": 0, "glass": 10200, "screen_orig": 36000, "screen_oled": 15900,
        "battery": 7500, "back_glass": 6500, "cam_glass": 2500, "housing": 15000,
        "clean_dust": 1000, "cam_main": 8800, "cam_front": 8200,
        "speaker_ear": 3800, "speaker_pol": 4800, "vibro": 2000,
        "charge": 6200, "buttons": 5500, "sensor": 7800,
        "water": 2000, "faceid": 9800,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 15 Plus": {
        "diag": 0, "glass": 9500, "screen_orig": 28000, "screen_oled": 13500,
        "battery": 7000, "back_glass": 6000, "cam_glass": 2200, "housing": 13000,
        "clean_dust": 1000, "cam_main": 7500, "cam_front": 7000,
        "speaker_ear": 3500, "speaker_pol": 4500, "vibro": 2000,
        "charge": 5800, "buttons": 5000, "sensor": 7000,
        "water": 2000, "faceid": 8500,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 15": {
        "diag": 0, "glass": 8900, "screen_orig": 24000, "screen_oled": 12000,
        "battery": 6500, "back_glass": 5500, "cam_glass": 2000, "housing": 12000,
        "clean_dust": 1000, "cam_main": 7000, "cam_front": 6500,
        "speaker_ear": 3200, "speaker_pol": 4200, "vibro": 2000,
        "charge": 5500, "buttons": 4800, "sensor": 6500,
        "water": 2000, "faceid": 8000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 14 Pro Max": {
        "diag": 0, "glass": 10400, "screen_orig": 38300, "screen_oled": 11800,
        "battery": 7300, "back_glass": 7800, "cam_glass": 2500, "housing": 11100,
        "clean_dust": 1000, "cam_main": 8700, "cam_front": 7500,
        "speaker_ear": 4000, "speaker_pol": 4800, "vibro": 2000,
        "charge": 5700, "buttons": 5100, "sensor": 6700,
        "water": 2000, "faceid": 7000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 14 Pro": {
        "diag": 0, "glass": 9800, "screen_orig": 34000, "screen_oled": 10500,
        "battery": 7000, "back_glass": 7200, "cam_glass": 2500, "housing": 10500,
        "clean_dust": 1000, "cam_main": 8200, "cam_front": 7000,
        "speaker_ear": 3800, "speaker_pol": 4500, "vibro": 2000,
        "charge": 5400, "buttons": 4800, "sensor": 6300,
        "water": 2000, "faceid": 6800,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 14 Plus": {
        "diag": 0, "glass": 8500, "screen_orig": 22000, "screen_oled": 9500,
        "battery": 6500, "back_glass": 6500, "cam_glass": 2200, "housing": 9800,
        "clean_dust": 1000, "cam_main": 7000, "cam_front": 6200,
        "speaker_ear": 3500, "speaker_pol": 4200, "vibro": 2000,
        "charge": 5000, "buttons": 4500, "sensor": 5800,
        "water": 2000, "faceid": 6200,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 14": {
        "diag": 0, "glass": 7800, "screen_orig": 18500, "screen_oled": 8800,
        "battery": 6000, "back_glass": 6000, "cam_glass": 2000, "housing": 9200,
        "clean_dust": 1000, "cam_main": 6500, "cam_front": 5800,
        "speaker_ear": 3200, "speaker_pol": 4000, "vibro": 2000,
        "charge": 4800, "buttons": 4200, "sensor": 5500,
        "water": 2000, "faceid": 6000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone SE 2022": {
        "diag": 0, "glass": 4500, "screen_orig": 9500, "screen_oled": 7500,
        "battery": 3800, "back_glass": 3800, "cam_glass": 1500, "housing": 7000,
        "clean_dust": 1000, "cam_main": 4500, "cam_front": 3800,
        "speaker_ear": 2500, "speaker_pol": 2800, "vibro": 1000,
        "charge": 3500, "buttons": 3000, "sensor": 4000,
        "water": 2000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 13 Pro Max": {
        "diag": 0, "glass": 8500, "screen_orig": 28000, "screen_oled": 10500,
        "battery": 6000, "back_glass": 6500, "cam_glass": 2200, "housing": 10000,
        "clean_dust": 1000, "cam_main": 8000, "cam_front": 6500,
        "speaker_ear": 3500, "speaker_pol": 4200, "vibro": 2000,
        "charge": 5000, "buttons": 4500, "sensor": 6000,
        "water": 2000, "faceid": 6500,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 13 Pro": {
        "diag": 0, "glass": 8000, "screen_orig": 24000, "screen_oled": 9800,
        "battery": 5800, "back_glass": 6000, "cam_glass": 2000, "housing": 9500,
        "clean_dust": 1000, "cam_main": 7500, "cam_front": 6000,
        "speaker_ear": 3300, "speaker_pol": 4000, "vibro": 2000,
        "charge": 4800, "buttons": 4200, "sensor": 5800,
        "water": 2000, "faceid": 6200,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 13": {
        "diag": 0, "glass": 7000, "screen_orig": 18000, "screen_oled": 8500,
        "battery": 5500, "back_glass": 5500, "cam_glass": 1800, "housing": 8500,
        "clean_dust": 1000, "cam_main": 6500, "cam_front": 5500,
        "speaker_ear": 3000, "speaker_pol": 3500, "vibro": 1500,
        "charge": 4500, "buttons": 3800, "sensor": 5200,
        "water": 2000, "faceid": 5800,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 13 mini": {
        "diag": 0, "glass": 6500, "screen_orig": 16000, "screen_oled": 8000,
        "battery": 5200, "back_glass": 5000, "cam_glass": 1700, "housing": 8000,
        "clean_dust": 1000, "cam_main": 6000, "cam_front": 5200,
        "speaker_ear": 2800, "speaker_pol": 3200, "vibro": 1500,
        "charge": 4200, "buttons": 3500, "sensor": 4800,
        "water": 2000, "faceid": 5500,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 12 Pro Max": {
        "diag": 0, "glass": 6000, "screen_orig": 19300, "screen_oled": 8300,
        "battery": 5700, "back_glass": 5000, "cam_glass": 2400, "housing": 9500,
        "clean_dust": 1000, "cam_main": 9300, "cam_front": 5300,
        "speaker_ear": 3800, "speaker_pol": 3500, "vibro": 2000,
        "charge": 4400, "buttons": 3800, "sensor": 5300,
        "water": 2000, "faceid": 5500,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 12 Pro": {
        "diag": 0, "glass": 5500, "screen_orig": 16500, "screen_oled": 7800,
        "battery": 5400, "back_glass": 4500, "cam_glass": 2200, "housing": 9000,
        "clean_dust": 1000, "cam_main": 8500, "cam_front": 5000,
        "speaker_ear": 3500, "speaker_pol": 3300, "vibro": 2000,
        "charge": 4200, "buttons": 3500, "sensor": 5000,
        "water": 2000, "faceid": 5200,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 12": {
        "diag": 0, "glass": 5000, "screen_orig": 13500, "screen_oled": 7200,
        "battery": 5000, "back_glass": 4000, "cam_glass": 2000, "housing": 8000,
        "clean_dust": 1000, "cam_main": 7000, "cam_front": 4500,
        "speaker_ear": 3200, "speaker_pol": 3000, "vibro": 1500,
        "charge": 4000, "buttons": 3200, "sensor": 4500,
        "water": 2000, "faceid": 5000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 12 mini": {
        "diag": 0, "glass": 4800, "screen_orig": 12500, "screen_oled": 6800,
        "battery": 4800, "back_glass": 3800, "cam_glass": 1900, "housing": 7500,
        "clean_dust": 1000, "cam_main": 6500, "cam_front": 4200,
        "speaker_ear": 3000, "speaker_pol": 2800, "vibro": 1500,
        "charge": 3800, "buttons": 3000, "sensor": 4200,
        "water": 2000, "faceid": 4800,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone SE 2020": {
        "diag": 0, "glass": 3800, "screen_orig": 8500, "screen_oled": 6500,
        "battery": 3500, "back_glass": 3200, "cam_glass": 1500, "housing": 6500,
        "clean_dust": 1000, "cam_main": 4000, "cam_front": 3500,
        "speaker_ear": 2500, "speaker_pol": 2500, "vibro": 1000,
        "charge": 3200, "buttons": 2800, "sensor": 3800,
        "water": 2000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 11 Pro Max": {
        "diag": 0, "glass": 6000, "screen_orig": 14000, "screen_oled": 8000,
        "battery": 4800, "back_glass": 4500, "cam_glass": 2000, "housing": 8500,
        "clean_dust": 1000, "cam_main": 7500, "cam_front": 5000,
        "speaker_ear": 3500, "speaker_pol": 3200, "vibro": 1500,
        "charge": 4000, "buttons": 3500, "sensor": 4800,
        "water": 2000, "faceid": 6000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 11 Pro": {
        "diag": 0, "glass": 5500, "screen_orig": 12500, "screen_oled": 7500,
        "battery": 4500, "back_glass": 4200, "cam_glass": 1800, "housing": 8000,
        "clean_dust": 1000, "cam_main": 7000, "cam_front": 4800,
        "speaker_ear": 3300, "speaker_pol": 3000, "vibro": 1500,
        "charge": 3800, "buttons": 3300, "sensor": 4500,
        "water": 2000, "faceid": 5800,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 11": {
        "diag": 0, "glass": 4700, "screen_orig": 7400, "screen_oled": 5900,
        "battery": 4100, "back_glass": 3000, "cam_glass": 1700, "housing": 5700,
        "clean_dust": 1000, "cam_main": 4300, "cam_front": 4100,
        "speaker_ear": 3000, "speaker_pol": 2500, "vibro": 1000,
        "charge": 3300, "buttons": 2900, "sensor": 4000,
        "water": 2000, "faceid": 5000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone XR": {
        "diag": 0, "glass": 4200, "screen_orig": 7000, "screen_oled": 5500,
        "battery": 3800, "back_glass": 2800, "cam_glass": 1700, "housing": 5500,
        "clean_dust": 1000, "cam_main": 4000, "cam_front": 4200,
        "speaker_ear": 2800, "speaker_pol": 2500, "vibro": 1000,
        "charge": 3000, "buttons": 2800, "sensor": 3800,
        "water": 2000, "faceid": 4800,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone XS Max": {
        "diag": 0, "glass": 4500, "screen_orig": 9500, "screen_oled": 7000,
        "battery": 4000, "back_glass": 3000, "cam_glass": 1700, "housing": 6000,
        "clean_dust": 1000, "cam_main": 4500, "cam_front": 4800,
        "speaker_ear": 3000, "speaker_pol": 2500, "vibro": 1000,
        "charge": 3200, "buttons": 2800, "sensor": 4200,
        "water": 2000, "faceid": 5000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone XS": {
        "diag": 0, "glass": 4000, "screen_orig": 8500, "screen_oled": 6500,
        "battery": 3800, "back_glass": 2800, "cam_glass": 1700, "housing": 5800,
        "clean_dust": 1000, "cam_main": 4200, "cam_front": 4600,
        "speaker_ear": 2800, "speaker_pol": 2500, "vibro": 1000,
        "charge": 3000, "buttons": 2600, "sensor": 4000,
        "water": 2000, "faceid": 4800,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone X": {
        "diag": 0, "glass": 3500, "screen_orig": 8200, "screen_oled": 6100,
        "battery": 3600, "back_glass": 2500, "cam_glass": 1700, "housing": 5600,
        "clean_dust": 1000, "cam_main": 3900, "cam_front": 4600,
        "speaker_ear": 3000, "speaker_pol": 2500, "vibro": 1000,
        "charge": 3000, "buttons": 2800, "sensor": 4000,
        "water": 2000, "faceid": 4500,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 8 Plus": {
        "diag": 0, "glass": 2800, "screen_orig": 5500, "screen_oled": 4200,
        "battery": 2800, "back_glass": 2200, "cam_glass": 1500, "housing": 4500,
        "clean_dust": 1000, "cam_main": 3000, "cam_front": 2500,
        "speaker_ear": 2000, "speaker_pol": 2000, "vibro": 1000,
        "charge": 2500, "buttons": 2200, "sensor": 3000,
        "water": 2000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 8": {
        "diag": 0, "glass": 2500, "screen_orig": 4800, "screen_oled": 3800,
        "battery": 2500, "back_glass": 2000, "cam_glass": 1500, "housing": 4000,
        "clean_dust": 1000, "cam_main": 2800, "cam_front": 2200,
        "speaker_ear": 1800, "speaker_pol": 1800, "vibro": 1000,
        "charge": 2300, "buttons": 2000, "sensor": 2800,
        "water": 2000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 7 Plus": {
        "diag": 0, "glass": 2300, "screen_orig": 3800, "screen_oled": 3200,
        "battery": 2400, "cam_glass": 1500, "housing": 4200,
        "clean_dust": 1000, "cam_main": 2600, "cam_front": 2800,
        "speaker_ear": 2000, "speaker_pol": 2000, "vibro": 1000,
        "charge": 2500, "buttons": 2300, "sensor": 3300,
        "water": 2000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 7": {
        "diag": 0, "glass": 2100, "screen_orig": 3300, "screen_oled": 2700,
        "battery": 2200, "cam_glass": 1500, "housing": 4000,
        "clean_dust": 1000, "cam_main": 2400, "cam_front": 2600,
        "speaker_ear": 2000, "speaker_pol": 2000, "vibro": 1000,
        "charge": 2300, "buttons": 2200, "sensor": 3100,
        "water": 2000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 6s Plus": {
        "diag": 0, "glass": 1900, "screen_orig": 3000, "screen_oled": 2400,
        "battery": 2000, "cam_glass": 1300, "housing": 3800,
        "clean_dust": 1000, "cam_main": 2200, "cam_front": 2000,
        "speaker_ear": 1800, "speaker_pol": 1800, "vibro": 1000,
        "charge": 2200, "buttons": 2000, "sensor": 2800,
        "water": 2000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 6s": {
        "diag": 0, "glass": 1800, "screen_orig": 2800, "screen_oled": 2200,
        "battery": 1800, "cam_glass": 1200, "housing": 3500,
        "clean_dust": 1000, "cam_main": 2000, "cam_front": 1800,
        "speaker_ear": 1600, "speaker_pol": 1600, "vibro": 800,
        "charge": 2000, "buttons": 1800, "sensor": 2500,
        "water": 2000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 6 Plus": {
        "diag": 0, "glass": 1700, "screen_orig": 2600, "screen_oled": 2000,
        "battery": 1700, "cam_glass": 1200, "housing": 3500,
        "clean_dust": 1000, "cam_main": 2000, "cam_front": 1700,
        "speaker_ear": 1500, "speaker_pol": 1500, "vibro": 800,
        "charge": 1900, "buttons": 1700, "sensor": 2400,
        "water": 2000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
    "iPhone 6": {
        "diag": 0, "glass": 1500, "screen_orig": 2400, "screen_oled": 1800,
        "battery": 1500, "cam_glass": 1000, "housing": 3200,
        "clean_dust": 1000, "cam_main": 1800, "cam_front": 1500,
        "speaker_ear": 1400, "speaker_pol": 1400, "vibro": 800,
        "charge": 1700, "buttons": 1500, "sensor": 2200,
        "water": 2000,
        "ios_clean": 1700, "ios_data": 2000, "backup": 1700, "app": 500,
    },
}

# Карта slug -> индекс в SERVICES_TEMPLATE
SLUG_INDEX = {s[0]: i for i, s in enumerate(SERVICES_TEMPLATE)}


class Command(BaseCommand):
    help = 'Заполнить прайс-лист ценами на ремонт iPhone (данные с mobi-service.com)'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Без подтверждения')

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            f'\nЗагрузка цен на ремонт iPhone ({len(MODELS_PRICES)} моделей)\n'
            '   Существующие модели Apple iPhone будут дополнены/обновлены.\n'
        ))

        if not options['yes']:
            confirm = input('Продолжить? [да/нет]: ').strip().lower()
            if confirm not in ('да', 'д', 'yes', 'y'):
                self.stdout.write('Отменено.')
                return

        # Получаем или создаём бренд Apple
        brand, created = Brand.objects.get_or_create(
            name='Apple',
            defaults={'icon': '🍎', 'emoji': '🍎', 'is_active': True, 'order': 1}
        )
        if created:
            self.stdout.write('  [+] Создан бренд Apple')
        else:
            self.stdout.write('  [=] Бренд Apple уже существует')

        total_models = 0
        total_services = 0

        for model_name, prices in MODELS_PRICES.items():
            phone_model, m_created = PhoneModel.objects.get_or_create(
                brand=brand,
                name=model_name,
                defaults={'is_active': True}
            )
            action = 'создана' if m_created else 'обновлена'

            svc_count = 0
            for slug, price_from in prices.items():
                if slug not in SLUG_INDEX:
                    continue
                tmpl = SERVICES_TEMPLATE[SLUG_INDEX[slug]]
                _, _, duration, popular = tmpl
                name = tmpl[1]

                RepairService.objects.update_or_create(
                    phone_model=phone_model,
                    name=name,
                    defaults={
                        'price_from': price_from,
                        'price_to': None,
                        'duration': duration,
                        'is_popular': popular,
                        'is_active': True,
                    }
                )
                svc_count += 1

            marker = '[+]' if m_created else '[~]'
            self.stdout.write(f'  {marker} {model_name} ({action}) — {svc_count} услуг')
            total_models += 1
            total_services += svc_count

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово! Загружено: {total_models} моделей, {total_services} услуг\n'
            f'  CRM -> Услуги и цены -> Apple\n'
        ))
