from django.contrib import admin
from .models import (UserProfile, Customer, Part, Accessory, StockMovement,
                     RepairOrder, RepairOrderService,
                     RepairOrderPart, SaleOrder, SaleOrderItem)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_editable = ('role',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'created_at')
    search_fields = ('name', 'phone', 'email')


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'phone_model', 'quantity', 'purchase_price', 'sale_price')
    list_filter = ('brand',)
    search_fields = ('name', 'sku')


@admin.register(Accessory)
class AccessoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity', 'purchase_price', 'sale_price')
    list_filter = ('category',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'movement_type', 'part', 'accessory', 'quantity', 'created_by')
    list_filter = ('movement_type',)
    readonly_fields = ('created_at', 'created_by')


class RepairOrderServiceInline(admin.TabularInline):
    model = RepairOrderService
    extra = 0


class RepairOrderPartInline(admin.TabularInline):
    model = RepairOrderPart
    extra = 0


@admin.register(RepairOrder)
class RepairOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer', 'phone_model', 'status', 'final_cost', 'created_at')
    list_filter = ('status', 'brand')
    search_fields = ('order_number', 'customer__name', 'customer__phone')
    inlines = [RepairOrderServiceInline, RepairOrderPartInline]


class SaleOrderItemInline(admin.TabularInline):
    model = SaleOrderItem
    extra = 0


@admin.register(SaleOrder)
class SaleOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer_name', 'total', 'is_finalized', 'created_at')
    inlines = [SaleOrderItemInline]
