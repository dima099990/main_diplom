from django.db import models


class SiteSettings(models.Model):
    company_name = models.CharField("Название компании", max_length=100, default="Kayros")
    tagline = models.CharField("Подзаголовок", max_length=200, default="Профессиональный ремонт телефонов")
    phone = models.CharField("Телефон", max_length=30, default="+7 (999) 000-00-00")
    address = models.CharField("Адрес", max_length=300, default="г. Москва, ул. Примерная, д. 1")
    working_hours = models.CharField("Часы работы", max_length=100, default="Пн–Вс: 09:00 – 21:00")
    telegram_bot_link = models.URLField("Ссылка на Telegram-бот", default="https://t.me/your_bot")
    telegram_channel = models.URLField("Telegram-канал", blank=True)
    about_text = models.TextField("О нас (краткое)", default="Мы занимаемся ремонтом телефонов с 2015 года.")
    about_full_text = models.TextField("О нас (полное)", blank=True)
    yandex_map_embed = models.TextField("Код встраивания Яндекс.Карты", blank=True)
    google_map_embed = models.TextField("Код встраивания Google Maps", blank=True)
    warranty_days = models.PositiveIntegerField("Гарантия (дней)", default=90)

    class Meta:
        verbose_name = "Настройки сайта"
        verbose_name_plural = "Настройки сайта"

    def __str__(self):
        return self.company_name

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Brand(models.Model):
    """Марка телефона: Apple, Samsung, Xiaomi..."""
    name = models.CharField("Название", max_length=100)
    icon = models.CharField("Эмодзи", max_length=10, default="📱")
    order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Марка"
        verbose_name_plural = "Марки устройств"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class PhoneModel(models.Model):
    """Модель: iPhone 14, Galaxy S22 Ultra..."""
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='phone_models', verbose_name="Марка")
    name = models.CharField("Название модели", max_length=150)
    order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Модель телефона"
        verbose_name_plural = "Модели телефонов"
        ordering = ['brand__order', 'order', 'name']

    def __str__(self):
        return f"{self.brand.name} {self.name}"

    @property
    def full_name(self):
        return f"{self.brand.name} {self.name}"


class RepairService(models.Model):
    """Позиция прайс-листа, привязанная к модели"""
    phone_model = models.ForeignKey(PhoneModel, on_delete=models.CASCADE, related_name='services', verbose_name="Модель")
    name = models.CharField("Услуга", max_length=200)
    description = models.CharField("Доп. описание", max_length=300, blank=True)
    price_from = models.PositiveIntegerField("Цена от (₽)")
    price_to = models.PositiveIntegerField("Цена до (₽)", null=True, blank=True)
    duration = models.CharField("Срок ремонта", max_length=50, default="1–2 часа")
    is_popular = models.BooleanField("Популярная", default=False)
    is_active = models.BooleanField("Активна", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Услуга / позиция прайса"
        verbose_name_plural = "Услуги / прайс-лист"
        ordering = ['phone_model__brand__order', 'phone_model__order', 'order', 'name']

    def __str__(self):
        return f"{self.phone_model} — {self.name}"

    @property
    def price_display(self):
        if self.price_to:
            return f"{self.price_from:,}–{self.price_to:,} ₽".replace(',', ' ')
        return f"от {self.price_from:,} ₽".replace(',', ' ')


class Review(models.Model):
    author = models.CharField("Имя клиента", max_length=100)
    text = models.TextField("Текст отзыва")
    rating = models.PositiveSmallIntegerField("Оценка (1–5)", default=5)
    device = models.CharField("Устройство", max_length=100, blank=True)
    created_at = models.DateField("Дата", auto_now_add=True)
    is_active = models.BooleanField("Показывать", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"{self.author} — {self.rating}★"


class CallRequest(models.Model):
    """Заявки на обзвон клиентов (с публичной формы)"""
    name = models.CharField("Имя", max_length=100)
    phone = models.CharField("Телефон / Telegram", max_length=100)
    message = models.TextField("Сообщение", blank=True)
    created_at = models.DateTimeField("Дата заявки", auto_now_add=True)
    is_processed = models.BooleanField("Обработана", default=False)
    processed_at = models.DateTimeField("Дата обработки", null=True, blank=True)
    result = models.TextField("Результат звонка", blank=True)

    class Meta:
        verbose_name = "Заявка на обзвон"
        verbose_name_plural = "Заявки на обзвон"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} | {self.phone}"
