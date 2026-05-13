from django.urls import path
from . import views

app_name = 'crm'

urlpatterns = [
    path('login/', views.crm_login, name='login'),
    path('logout/', views.crm_logout, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('search/', views.search, name='search'),

    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/new/', views.customer_edit, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),

    # Repairs
    path('repairs/', views.repair_list, name='repair_list'),
    path('repairs/new/', views.repair_create, name='repair_create'),
    path('repairs/<int:pk>/', views.repair_detail, name='repair_detail'),
    path('repairs/<int:pk>/status/', views.repair_update_status, name='repair_status'),
    path('repairs/<int:pk>/assign/', views.repair_update_assigned, name='repair_assign'),
    path('repairs/<int:pk>/add-service/', views.repair_add_service, name='repair_add_service'),
    path('repairs/<int:pk>/remove-service/<int:service_pk>/', views.repair_remove_service, name='repair_remove_service'),
    path('repairs/<int:pk>/add-part/', views.repair_add_part, name='repair_add_part'),
    path('repairs/<int:pk>/remove-part/<int:part_pk>/', views.repair_remove_part, name='repair_remove_part'),
    path('repairs/<int:pk>/print/', views.repair_print, name='repair_print'),

    # Warehouse
    path('warehouse/parts/', views.part_list, name='part_list'),
    path('warehouse/parts/new/', views.part_create, name='part_create'),
    path('warehouse/parts/<int:pk>/edit/', views.part_edit, name='part_edit'),
    path('warehouse/parts/<int:pk>/stock-in/', views.part_stock_in, name='part_stock_in'),
    path('warehouse/parts/<int:pk>/stock-out/', views.part_stock_out, name='part_stock_out'),
    path('warehouse/accessories/', views.accessory_list, name='accessory_list'),
    path('warehouse/accessories/new/', views.accessory_create, name='accessory_create'),
    path('warehouse/accessories/<int:pk>/edit/', views.accessory_edit, name='accessory_edit'),
    path('warehouse/accessories/<int:pk>/stock-in/', views.accessory_stock_in, name='accessory_stock_in'),
    path('warehouse/movements/', views.stock_movements, name='stock_movements'),

    # Sales
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/new/', views.sale_create, name='sale_create'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('sales/<int:pk>/remove-item/<int:item_pk>/', views.sale_remove_item, name='sale_remove_item'),
    path('sales/<int:pk>/finalize/', views.sale_finalize, name='sale_finalize'),

    # Call requests
    path('call-requests/', views.call_request_list, name='call_request_list'),
    path('call-requests/<int:pk>/update/', views.call_request_update, name='call_request_update'),

    # Users
    path('users/', views.user_list, name='user_list'),
    path('users/new/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
]
