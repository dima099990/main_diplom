from django.contrib import admin
from .models import SiteSettings, Brand, PhoneModel, RepairService, Review, CallRequest


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Основное', {'fields': ('company_name', 'tagline', 'phone', 'working_hours')}),
        ('Контакты', {'fields': ('address', 'telegram_bot_link', 'telegram_channel')}),
        ('О компании', {'fields': ('about_text', 'about_full_text', 'warranty_days')}),
        ('Карты', {'fields': ('yandex_map_embed', 'google_map_embed'), 'classes': ('collapse',)}),
    )
    def has_add_permission(self, r): return not SiteSettings.objects.exists()
    def has_delete_permission(self, r, obj=None): return False


class PhoneModelInline(admin.TabularInline):
    model = PhoneModel
    extra = 1
    fields = ('name', 'order', 'is_active')


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('icon','name','order','is_active')
    list_editable = ('order','is_active')
    inlines = [PhoneModelInline]


class RepairServiceInline(admin.TabularInline):
    model = RepairService
    extra = 1
    fields = ('name','price_from','price_to','duration','is_popular','is_active','order')


@admin.register(PhoneModel)
class PhoneModelAdmin(admin.ModelAdmin):
    list_display = ('__str__','brand','order','is_active')
    list_filter = ('brand',)
    inlines = [RepairServiceInline]


@admin.register(RepairService)
class RepairServiceAdmin(admin.ModelAdmin):
    list_display = ('name','phone_model','price_display','duration','is_popular','is_active')
    list_filter = ('phone_model__brand','is_popular','is_active')
    search_fields = ('name',)
    def price_display(self, obj): return obj.price_display
    price_display.short_description = "Цена"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('author','rating','device','is_active','order')
    list_editable = ('is_active','order')


@admin.register(CallRequest)
class CallRequestAdmin(admin.ModelAdmin):
    list_display = ('name','phone','created_at','is_processed')
    list_editable = ('is_processed',)
    readonly_fields = ('name','phone','message','created_at')
    def has_add_permission(self, r): return False
