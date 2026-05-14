"""
python manage.py seed_data

Заполняет базу тестовыми данными: филиалы, сотрудники, клиенты,
запчасти, аксессуары, заказы, продажи, платежи.
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Brand, PhoneModel, RepairService, SiteSettings
from crm.models import (
    Accessory, Branch, Customer, Expense,
    OrderHistory, Part, PaymentRecord, PayrollRecord, RepairOrder,
    RepairOrderPart, RepairOrderService, SaleOrder, SaleOrderItem,
    StockMovement, Supplier, Task, UserProfile,
)


class Command(BaseCommand):
    help = 'Заполнить базу тестовыми данными'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Очистить перед заполнением')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Очищаю базу...')
            RepairOrder.objects.all().delete()
            SaleOrder.objects.all().delete()
            Customer.objects.all().delete()
            Part.objects.all().delete()
            Accessory.objects.all().delete()
            Supplier.objects.all().delete()
            Branch.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        self.stdout.write('Создаю тестовые данные...')

        # ── Site settings
        settings, _ = SiteSettings.objects.get_or_create(pk=1, defaults={
            'company_name': 'Kayros Service',
            'phone': '+7 (495) 123-45-67',
            'address': 'г. Москва, ул. Примерная, д. 1',
            'working_hours': 'Пн–Сб 10:00–20:00',
            'warranty_days': 90,
        })
        if not settings.company_name:
            settings.company_name = 'Kayros Service'
            settings.save()

        # ── Brands & models
        brands_data = {
            'Apple': ['iPhone 13', 'iPhone 14', 'iPhone 14 Pro', 'iPhone 15', 'iPhone 15 Pro Max', 'iPad Air 5'],
            'Samsung': ['Galaxy S22', 'Galaxy S23 Ultra', 'Galaxy A54', 'Galaxy A34', 'Galaxy S24'],
            'Xiaomi': ['Redmi Note 12', 'Xiaomi 13', 'POCO X5 Pro', 'Redmi 12C'],
            'Huawei': ['P50 Pro', 'Mate 50', 'Nova 11'],
            'Honor': ['Magic5 Pro', 'Honor 90'],
        }
        brand_objs = {}
        model_objs = {}
        for brand_name, models in brands_data.items():
            brand, _ = Brand.objects.get_or_create(name=brand_name, defaults={'emoji': '📱', 'order': 0, 'is_active': True})
            brand_objs[brand_name] = brand
            model_objs[brand_name] = []
            for i, m in enumerate(models):
                mo, _ = PhoneModel.objects.get_or_create(brand=brand, name=m, defaults={'order': i, 'is_active': True})
                model_objs[brand_name].append(mo)

        # ── Repair services
        services_data = [
            ('Замена дисплея (оригинал)', 12000, 18000),
            ('Замена дисплея (копия)', 4500, 8000),
            ('Замена аккумулятора', 2500, 4500),
            ('Замена задней крышки', 1500, 3000),
            ('Замена кнопки питания', 1200, 2500),
            ('Замена разъёма зарядки', 1800, 3500),
            ('Диагностика', 500, 500),
            ('Чистка от влаги', 2000, 3500),
            ('Замена микрофона', 1500, 2800),
            ('Замена камеры (фронт)', 2000, 4000),
            ('Замена камеры (основная)', 3500, 7000),
            ('Восстановление прошивки', 1000, 2000),
        ]
        for brand_name, models in model_objs.items():
            for model in models[:3]:
                for svc_name, price_from, price_to in services_data[:6]:
                    RepairService.objects.get_or_create(
                        phone_model=model, name=svc_name,
                        defaults={
                            'price_from': price_from + random.randint(-1000, 2000),
                            'price_to': price_to,
                            'is_active': True, 'is_popular': random.random() > 0.6,
                        }
                    )

        # ── Branches
        branches = []
        for name, addr in [
            ('Основной (Центр)', 'ул. Тверская, 15'),
            ('Филиал (Север)', 'Ленинградский пр-т, 80'),
            ('Филиал (Юг)', 'Варшавское ш., 46'),
        ]:
            b, _ = Branch.objects.get_or_create(name=name, defaults={'address': addr, 'is_active': True})
            branches.append(b)

        # ── Suppliers
        suppliers = []
        for name in ['ТехноЗапчасти', 'МобайлПарт', 'РемонтОпт', 'PhoneSpare']:
            s, _ = Supplier.objects.get_or_create(name=name, defaults={
                'phone': '+7 (800) 000-00-00', 'is_active': True,
            })
            suppliers.append(s)

        # ── Admin user
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@kayros.ru', 'admin123')
            admin.first_name = 'Администратор'
            admin.last_name = 'Системы'
            admin.save()
            UserProfile.objects.update_or_create(user=admin, defaults={'role': 'admin', 'branch': branches[0]})
            self.stdout.write(self.style.SUCCESS('  admin / admin123'))

        # ── Staff
        staff_data = [
            ('manager1', 'Алексей', 'Петров', 'manager', 5, 3, branches[0]),
            ('master1', 'Иван', 'Сидоров', 'master', 15, 0, branches[0]),
            ('master2', 'Дмитрий', 'Козлов', 'master', 12, 0, branches[1]),
            ('master3', 'Артём', 'Новиков', 'master', 18, 0, branches[2]),
            ('manager2', 'Ольга', 'Смирнова', 'manager', 5, 5, branches[1]),
        ]
        staff = []
        for username, fn, ln, role, rp, ap, branch in staff_data:
            if not User.objects.filter(username=username).exists():
                u = User.objects.create_user(username, f'{username}@kayros.ru', 'pass123',
                                             first_name=fn, last_name=ln)
                UserProfile.objects.update_or_create(
                    user=u, defaults={
                        'role': role, 'branch': branch,
                        'repair_percent': rp, 'accessory_percent': ap, 'base_salary': 25000,
                    }
                )
                staff.append(u)
            else:
                staff.append(User.objects.get(username=username))

        masters = [u for u in staff if hasattr(u, 'profile') and u.profile.role == 'master']
        managers = [u for u in staff if hasattr(u, 'profile') and u.profile.role in ('manager', 'admin')]

        # ── Parts
        parts_data = [
            ('Дисплей iPhone 15 Pro Max (оригинал)', 'Apple', 'iPhone 15 Pro Max', 8500, 15000, 3, 2),
            ('Дисплей iPhone 14 (копия)', 'Apple', 'iPhone 14', 3500, 7000, 8, 2),
            ('Дисплей Samsung S23 Ultra', 'Samsung', 'Galaxy S23 Ultra', 9000, 16000, 4, 2),
            ('Аккумулятор iPhone 14', 'Apple', 'iPhone 14', 800, 2200, 15, 3),
            ('Аккумулятор Samsung S22', 'Samsung', 'Galaxy S22', 700, 1800, 12, 3),
            ('Разъём зарядки iPhone 15', 'Apple', 'iPhone 15', 500, 1500, 10, 3),
            ('Задняя крышка iPhone 13 (чёрная)', 'Apple', 'iPhone 13', 1200, 2800, 6, 2),
            ('Камера основная Samsung A54', 'Samsung', 'Galaxy A54', 2200, 4500, 3, 1),
            ('Динамик разговорный iPhone 14', 'Apple', 'iPhone 14', 400, 1200, 8, 3),
            ('Стекло защитное Redmi Note 12', 'Xiaomi', 'Redmi Note 12', 150, 500, 20, 5),
        ]
        part_objs = []
        for name, brand_name, model_name, pp, sp, qty, min_qty in parts_data:
            brand = brand_objs.get(brand_name)
            model = next((m for m in model_objs.get(brand_name, []) if m.name == model_name), None)
            p, created = Part.objects.get_or_create(name=name, defaults={
                'brand': brand, 'phone_model': model,
                'sku': f'SKU-{random.randint(1000, 9999)}',
                'purchase_price': pp, 'sale_price': sp,
                'quantity': qty, 'min_quantity': min_qty,
                'supplier': random.choice(suppliers),
            })
            part_objs.append(p)

        # ── Accessories
        acc_data = [
            ('Чехол Apple iPhone 15 Pro (прозрачный)', 'case', 120, 450, 30, 5),
            ('Чехол Samsung Galaxy S24 Ultra (чёрный)', 'case', 90, 380, 25, 5),
            ('Стекло защитное iPhone 15 Pro Max', 'glass', 80, 350, 40, 10),
            ('Стекло Privacy iPhone 14', 'glass', 100, 450, 20, 5),
            ('Кабель USB-C 1m (оригинал)', 'charger', 200, 700, 50, 10),
            ('Зарядник 20W USB-C', 'charger', 350, 1200, 20, 5),
            ('Наушники AirPods Pro 2 (реплика)', 'audio', 1500, 4500, 8, 2),
            ('Наушники Bluetooth TWS', 'audio', 500, 1800, 15, 3),
            ('Держатель в машину магнитный', 'other', 180, 650, 12, 3),
            ('Power Bank 10000mAh', 'other', 800, 2200, 6, 2),
        ]
        acc_objs = []
        for name, cat, pp, sp, qty, min_qty in acc_data:
            a, _ = Accessory.objects.get_or_create(name=name, defaults={
                'category': cat, 'purchase_price': pp, 'sale_price': sp,
                'quantity': qty, 'min_quantity': min_qty,
                'supplier': random.choice(suppliers),
            })
            acc_objs.append(a)

        # ── Customers
        customers_data = [
            ('Иван Петров', '+7 (916) 123-45-67', 'ivan@mail.ru'),
            ('Мария Сидорова', '+7 (926) 234-56-78', 'maria@gmail.com'),
            ('Алексей Козлов', '+7 (903) 345-67-89', ''),
            ('Елена Новикова', '+7 (915) 456-78-90', 'elena@yandex.ru'),
            ('Дмитрий Соколов', '+7 (917) 567-89-01', ''),
            ('Анна Морозова', '+7 (925) 678-90-12', 'anna@mail.ru'),
            ('Сергей Волков', '+7 (919) 789-01-23', ''),
            ('Наталья Лебедева', '+7 (916) 890-12-34', 'natasha@gmail.com'),
            ('Михаил Семёнов', '+7 (929) 901-23-45', ''),
            ('Ирина Федорова', '+7 (910) 012-34-56', 'irina@yandex.ru'),
            ('Павел Орлов', '+7 (926) 111-22-33', ''),
            ('Юлия Виноградова', '+7 (905) 222-33-44', 'julia@mail.ru'),
        ]
        customers = []
        for name, phone, email in customers_data:
            c, _ = Customer.objects.get_or_create(phone=phone, defaults={
                'name': name, 'email': email,
            })
            customers.append(c)

        # ── Repair Orders
        statuses = ['new', 'diagnosis', 'waiting_parts', 'in_progress', 'done', 'issued', 'cancelled']
        status_weights = [1, 2, 2, 3, 2, 5, 1]
        created_orders = []

        for i in range(40):
            days_ago = random.randint(0, 90)
            created_at = timezone.now() - timedelta(days=days_ago)
            brand_name = random.choice(list(brand_objs.keys()))
            brand = brand_objs[brand_name]
            model = random.choice(model_objs[brand_name])
            customer = random.choice(customers)
            master = random.choice(masters) if masters else None
            manager = random.choice(managers) if managers else None
            status = random.choices(statuses, weights=status_weights)[0]
            branch = random.choice(branches)

            complaints = [
                'Не включается', 'Разбит экран', 'Не заряжается',
                'Не работает камера', 'Нет звука', 'Не работает Wi-Fi',
                'Намок, не работает', 'Трещина на корпусе',
                'Глючит сенсор', 'Не видит SIM-карту',
            ]

            order = RepairOrder(
                customer=customer, brand=brand, phone_model=model,
                complaint=random.choice(complaints),
                status=status,
                created_by=manager,
                assigned_to=master,
                branch=branch,
                warranty_days=90,
                estimated_cost=random.choice([2000, 3500, 5000, 7500, 12000, 15000]),
            )
            order.save()
            order.created_at = created_at
            order.save(update_fields=['created_at'])

            # Add services
            available_svcs = list(RepairService.objects.filter(phone_model=model, is_active=True))
            if available_svcs:
                svc = random.choice(available_svcs)
                price = svc.price_from + Decimal(random.randint(0, 2000))
                RepairOrderService.objects.create(order=order, service=svc, name=svc.name, price=price)

            # Add parts
            if part_objs and random.random() > 0.4:
                part = random.choice(part_objs)
                qty = random.randint(1, 2)
                if part.quantity >= qty:
                    RepairOrderPart.objects.create(order=order, part=part, quantity=qty, price=part.sale_price)

            order.recalculate_final_cost()

            # Payment for issued orders
            if status == 'issued':
                order.is_paid = True
                order.paid_at = created_at + timedelta(hours=random.randint(1, 48))
                order.save(update_fields=['is_paid', 'paid_at'])
                PaymentRecord.objects.create(
                    repair_order=order,
                    payment_type='repair',
                    method=random.choice(['cash', 'card', 'transfer']),
                    amount=order.final_cost,
                    branch=branch,
                    created_by=manager,
                    created_at=order.paid_at,
                )

            OrderHistory.objects.create(
                order=order, event_type='created',
                description=f'Заказ создан. {customer.name}, {model}',
                user=manager, created_at=created_at,
            )
            created_orders.append(order)

        # ── Sales
        for i in range(15):
            customer = random.choice(customers)
            days_ago = random.randint(0, 60)
            created_at = timezone.now() - timedelta(days=days_ago)
            sale = SaleOrder(
                customer_name=customer.name,
                customer_phone=customer.phone,
                created_by=random.choice(managers) if managers else None,
                branch=random.choice(branches),
                is_finalized=random.random() > 0.3,
                payment_method=random.choice(['cash', 'card']),
            )
            sale.save()
            sale.created_at = created_at
            sale.save(update_fields=['created_at'])

            items = random.sample(acc_objs, min(random.randint(1, 3), len(acc_objs)))
            for acc in items:
                SaleOrderItem.objects.create(
                    order=sale, accessory=acc,
                    quantity=random.randint(1, 2), price=acc.sale_price,
                )
            sale.recalculate_total()

            if sale.is_finalized:
                PaymentRecord.objects.create(
                    sale_order=sale,
                    payment_type='sale',
                    method=sale.payment_method,
                    amount=sale.total,
                    created_by=sale.created_by,
                )

        # ── Expenses
        expense_data = [
            ('rent', 'Аренда помещения за месяц', 85000),
            ('utilities', 'Электроэнергия', 12000),
            ('marketing', 'Таргетированная реклама', 25000),
            ('equipment', 'Паяльная станция', 18000),
            ('parts', 'Закупка запчастей', 45000),
            ('other', 'Хозяйственные расходы', 5000),
        ]
        admin_user = User.objects.filter(is_superuser=True).first()
        for cat, desc, amt in expense_data:
            Expense.objects.get_or_create(description=desc, defaults={
                'category': cat,
                'amount': Decimal(amt),
                'date': timezone.now().date().replace(day=1),
                'created_by': admin_user,
            })

        # ── Tasks
        task_titles = [
            'Позвонить клиенту Петрову по заказу',
            'Заказать запчасти у поставщика',
            'Обновить прайс-лист',
            'Провести инвентаризацию склада',
            'Настроить CRM систему',
        ]
        for title in task_titles:
            Task.objects.get_or_create(title=title, defaults={
                'priority': random.choice(['low', 'medium', 'high']),
                'status': random.choice(['open', 'in_progress']),
                'assigned_to': random.choice(staff) if staff else None,
                'created_by': admin_user,
                'due_date': timezone.now().date() + timedelta(days=random.randint(1, 14)),
            })

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Создано: {len(created_orders)} заказов, {len(customers)} клиентов, '
            f'{len(part_objs)} запчастей, {len(acc_objs)} аксессуаров\n'
            f'Логин: admin / admin123\n'
            f'Мастера: master1, master2, master3 / pass123\n'
            f'Менеджеры: manager1, manager2 / pass123'
        ))
