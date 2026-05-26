"""
python manage.py clear_db

Очищает все рабочие данные из базы, не трогая структуру таблиц.
Прайс-лист очищается всегда. Пользователи и настройки сайта сохраняются.

Опции:
  --all   Удалить вообще всё, включая пользователей и настройки
  --yes   Не спрашивать подтверждения
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import Brand, PhoneModel, RepairService, SiteSettings
from crm.models import (
    Accessory, Appointment, Branch, Customer, Expense,
    Notification, OrderHistory, Part, PaymentRecord, PayrollRecord,
    RepairOrder, RepairOrderAccessory, RepairOrderPart, RepairOrderService,
    SaleOrder, SaleOrderItem, StockMovement, Supplier, Task, UserProfile,
)

# Порядок важен (FK-зависимости)
TABLES = [
    RepairOrderService, RepairOrderPart, RepairOrderAccessory, OrderHistory,
    PaymentRecord, PayrollRecord,
    RepairOrder,
    SaleOrderItem, SaleOrder,
    Appointment,
    Expense, Task,
    StockMovement,
    Part, Accessory,
    Customer,
    Supplier,
    Notification,
    Branch,
]

TABLES_PRICES = [RepairService, PhoneModel, Brand]


class Command(BaseCommand):
    help = 'Очистить данные из базы (без удаления таблиц)'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true',
                            help='Удалить также пользователей и настройки сайта')
        parser.add_argument('--yes', action='store_true',
                            help='Не спрашивать подтверждения')

    def handle(self, *args, **options):
        clear_all = options['all']
        skip_confirm = options['yes']

        self.stdout.write(self.style.WARNING('\n⚠  ОЧИСТКА БАЗЫ ДАННЫХ'))
        if clear_all:
            self.stdout.write('   Будут удалены ВСЕ данные, включая пользователей и настройки.')
        else:
            self.stdout.write('   Будут удалены: заказы, клиенты, склад, прайс, расходы.')
            self.stdout.write('   Сохранятся: пользователи, настройки сайта.')

        if not skip_confirm:
            confirm = input('\nПродолжить? [да/нет]: ').strip().lower()
            if confirm not in ('да', 'д', 'yes', 'y'):
                self.stdout.write('Отменено.')
                return

        deleted_total = 0

        # Основные данные
        for model in TABLES:
            count, _ = model.objects.all().delete()
            if count:
                self.stdout.write(f'  Удалено {count:>5} → {model.__name__}')
                deleted_total += count

        # Прайс — чистится всегда
        for model in TABLES_PRICES:
            count, _ = model.objects.all().delete()
            if count:
                self.stdout.write(f'  Удалено {count:>5} → {model.__name__}')
                deleted_total += count

        # Дополнительно: пользователи и настройки
        if clear_all:
            count, _ = User.objects.all().delete()
            if count:
                self.stdout.write(f'  Удалено {count:>5} → User')
                deleted_total += count
            SiteSettings.objects.all().delete()
            self.stdout.write('  Удалено       → SiteSettings')

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Готово. Всего удалено записей: {deleted_total}'
        ))
        if not clear_all:
            self.stdout.write(
                '  Для заполнения тестовыми данными: python manage.py seed_data\n'
                '  Для загрузки прайса iPhone:       python manage.py seed_iphone_prices\n'
            )
