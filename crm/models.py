from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Brand, PhoneModel, RepairService

CONDITION_ITEMS = [
    ('display', 'Дисплей'),
    ('touchscreen', 'Тачскрин / сенсор'),
    ('front_camera', 'Фронтальная камера'),
    ('rear_camera', 'Основная камера'),
    ('speaker_earpiece', 'Разговорный динамик'),
    ('speaker_loud', 'Громкоговоритель'),
    ('microphone', 'Микрофон'),
    ('face_id', 'Face ID / Touch ID'),
    ('home_button', 'Кнопка Home'),
    ('volume_buttons', 'Кнопки громкости'),
    ('power_button', 'Кнопка питания'),
    ('charging_port', 'Разъём зарядки'),
    ('wifi', 'Wi-Fi'),
    ('bluetooth', 'Bluetooth'),
    ('gps', 'GPS'),
    ('cellular', 'Сотовая связь / SIM'),
    ('vibration', 'Вибромотор'),
    ('battery', 'Аккумулятор'),
    ('nfc', 'NFC'),
    ('body', 'Корпус (царапины/повреждения)'),
]

CONDITION_STATES = [
    ('ok', 'Работает'),
    ('broken', 'Не работает'),
    ('na', 'Не проверено'),
]


class UserProfile(models.Model):
    ROLES = [
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
        ('employee', 'Сотрудник'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField("Роль", max_length=20, choices=ROLES, default='employee')
    phone = models.CharField("Телефон", max_length=30, blank=True)

    class Meta:
        verbose_name = "Профиль сотрудника"
        verbose_name_plural = "Профили сотрудников"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self): return self.role == 'admin'
    @property
    def is_manager(self): return self.role in ('admin', 'manager')
    @property
    def is_employee(self): return True  # all roles can act as employee


class Customer(models.Model):
    name = models.CharField("ФИО", max_length=200)
    phone = models.CharField("Телефон", max_length=30)
    email = models.EmailField("Email", blank=True)
    notes = models.TextField("Примечания", blank=True)
    created_at = models.DateTimeField("Дата добавления", auto_now_add=True)

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} | {self.phone}"


class Part(models.Model):
    """Запчасти на складе"""
    name = models.CharField("Название", max_length=200)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Марка")
    phone_model = models.ForeignKey(PhoneModel, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Модель")
    sku = models.CharField("Артикул", max_length=100, blank=True)
    quantity = models.IntegerField("Количество", default=0)
    min_quantity = models.PositiveIntegerField("Мин. остаток (предупреждение)", default=1)
    purchase_price = models.DecimalField("Закупочная цена", max_digits=10, decimal_places=2, default=0)
    sale_price = models.DecimalField("Цена продажи / списания", max_digits=10, decimal_places=2, default=0)
    notes = models.TextField("Примечания", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Запчасть"
        verbose_name_plural = "Запчасти"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_quantity

    @property
    def is_out_of_stock(self):
        return self.quantity <= 0


class Accessory(models.Model):
    """Аксессуары для продажи"""
    CATEGORIES = [
        ('case', 'Чехлы'), ('glass', 'Стёкла / плёнки'),
        ('charger', 'Зарядки / кабели'), ('audio', 'Наушники'),
        ('other', 'Прочее'),
    ]
    name = models.CharField("Название", max_length=200)
    category = models.CharField("Категория", max_length=20, choices=CATEGORIES, default='other')
    sku = models.CharField("Артикул", max_length=100, blank=True)
    compatible_with = models.CharField("Совместимость", max_length=200, blank=True)
    quantity = models.IntegerField("Количество", default=0)
    min_quantity = models.PositiveIntegerField("Мин. остаток", default=2)
    purchase_price = models.DecimalField("Закупочная цена", max_digits=10, decimal_places=2, default=0)
    sale_price = models.DecimalField("Цена продажи", max_digits=10, decimal_places=2, default=0)
    notes = models.TextField("Примечания", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Аксессуар"
        verbose_name_plural = "Аксессуары"
        ordering = ['category', 'name']

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_quantity

    @property
    def is_out_of_stock(self):
        return self.quantity <= 0


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('in', 'Поступление'),
        ('out', 'Списание (ручное)'),
        ('repair', 'Использовано в ремонте'),
        ('sale', 'Продажа'),
    ]
    part = models.ForeignKey(Part, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements', verbose_name="Запчасть")
    accessory = models.ForeignKey(Accessory, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements', verbose_name="Аксессуар")
    movement_type = models.CharField("Тип", max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField("Кол-во (+/-)")
    comment = models.TextField("Комментарий", blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Движение склада"
        verbose_name_plural = "История движений"
        ordering = ['-created_at']

    def __str__(self):
        item = self.part or self.accessory
        return f"{self.get_movement_type_display()} | {item} | {self.quantity:+d}"


def _next_number(model, prefix):
    year = timezone.now().year
    last = model.objects.filter(order_number__startswith=f'{prefix}-{year}-').order_by('-id').first()
    num = int(last.order_number.split('-')[-1]) + 1 if last else 1
    return f'{prefix}-{year}-{num:04d}'


class RepairOrder(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('diagnosis', 'Диагностика'),
        ('waiting_parts', 'Ожидание запчастей'),
        ('in_progress', 'В работе'),
        ('done', 'Готов к выдаче'),
        ('issued', 'Выдан'),
        ('cancelled', 'Отменён'),
    ]
    STATUS_COLORS = {
        'new': '#6c757d', 'diagnosis': '#fd7e14', 'waiting_parts': '#ffc107',
        'in_progress': '#0d6efd', 'done': '#198754', 'issued': '#198754', 'cancelled': '#dc3545',
    }

    order_number = models.CharField("Номер заказа", max_length=20, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='repairs', verbose_name="Клиент")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, verbose_name="Марка")
    phone_model = models.ForeignKey(PhoneModel, on_delete=models.PROTECT, verbose_name="Модель")
    imei = models.CharField("IMEI", max_length=50, blank=True)
    appearance = models.TextField("Внешний вид / комплектация", blank=True)
    device_password = models.CharField("Пароль устройства", max_length=100, blank=True)
    complaint = models.TextField("Жалоба клиента", blank=True)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='new')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_repairs')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_repairs', verbose_name="Назначен")
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    estimated_cost = models.DecimalField("Предварительная стоимость", max_digits=10, decimal_places=2, default=0)
    final_cost = models.DecimalField("Итоговая стоимость", max_digits=10, decimal_places=2, default=0)
    notes = models.TextField("Внутренние заметки", blank=True)
    warranty_days = models.PositiveIntegerField("Гарантия (дней)", default=90)

    class Meta:
        verbose_name = "Заказ на ремонт"
        verbose_name_plural = "Заказы на ремонт"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_number} | {self.customer.name} | {self.phone_model}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = _next_number(RepairOrder, 'R')
        super().save(*args, **kwargs)

    @property
    def status_color(self):
        return self.STATUS_COLORS.get(self.status, '#6c757d')

    def recalculate_final_cost(self):
        services_total = sum(s.price for s in self.order_services.all())
        parts_total = sum(p.price * p.quantity for p in self.order_parts.all())
        self.final_cost = services_total + parts_total
        self.save(update_fields=['final_cost'])


class DeviceConditionCheck(models.Model):
    repair_order = models.OneToOneField(RepairOrder, on_delete=models.CASCADE, related_name='condition_check')
    # 20 condition fields
    display = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    touchscreen = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    front_camera = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    rear_camera = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    speaker_earpiece = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    speaker_loud = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    microphone = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    face_id = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    home_button = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    volume_buttons = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    power_button = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    charging_port = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    wifi = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    bluetooth = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    gps = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    cellular = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    vibration = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    battery = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    nfc = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')
    body = models.CharField(max_length=10, choices=CONDITION_STATES, default='na')

    class Meta:
        verbose_name = "Проверка функционала"

    def get_items(self):
        """Returns list of (label, state) for template rendering"""
        result = []
        for field_name, label in CONDITION_ITEMS:
            result.append({
                'field': field_name,
                'label': label,
                'state': getattr(self, field_name),
                'state_display': dict(CONDITION_STATES).get(getattr(self, field_name), ''),
            })
        return result


class RepairOrderService(models.Model):
    """Работа/услуга в заказе"""
    order = models.ForeignKey(RepairOrder, on_delete=models.CASCADE, related_name='order_services')
    service = models.ForeignKey(RepairService, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField("Название работы", max_length=200)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Работа"
        verbose_name_plural = "Работы"

    def __str__(self):
        return f"{self.name} — {self.price}₽"


class RepairOrderPart(models.Model):
    """Запчасть в заказе"""
    order = models.ForeignKey(RepairOrder, on_delete=models.CASCADE, related_name='order_parts')
    part = models.ForeignKey(Part, on_delete=models.PROTECT, verbose_name="Запчасть")
    quantity = models.PositiveIntegerField("Количество", default=1)
    price = models.DecimalField("Цена за шт.", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Запчасть в заказе"
        verbose_name_plural = "Запчасти в заказе"

    def __str__(self):
        return f"{self.part.name} x{self.quantity}"

    @property
    def total(self):
        return self.price * self.quantity


class SaleOrder(models.Model):
    order_number = models.CharField("Номер", max_length=20, unique=True)
    customer_name = models.CharField("Имя покупателя", max_length=200, blank=True)
    customer_phone = models.CharField("Телефон", max_length=30, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField("Итого", max_digits=10, decimal_places=2, default=0)
    notes = models.TextField("Примечания", blank=True)
    is_finalized = models.BooleanField("Завершён", default=False)

    class Meta:
        verbose_name = "Продажа"
        verbose_name_plural = "Продажи"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_number} | {self.total}₽"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = _next_number(SaleOrder, 'S')
        super().save(*args, **kwargs)

    def recalculate_total(self):
        self.total = sum(i.price * i.quantity for i in self.items.all())
        self.save(update_fields=['total'])


class SaleOrderItem(models.Model):
    order = models.ForeignKey(SaleOrder, on_delete=models.CASCADE, related_name='items')
    accessory = models.ForeignKey(Accessory, on_delete=models.PROTECT, verbose_name="Аксессуар")
    quantity = models.PositiveIntegerField("Кол-во", default=1)
    price = models.DecimalField("Цена за шт.", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Позиция продажи"
        verbose_name_plural = "Позиции продажи"

    @property
    def total(self):
        return self.price * self.quantity
