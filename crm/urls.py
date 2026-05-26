from django.urls import path
from . import views

app_name = 'crm'

urlpatterns = [
    # Auth
    path('login/', views.crm_login, name='login'),
    path('logout/', views.crm_logout, name='logout'),

    # Dashboard & Search
    path('', views.dashboard, name='dashboard'),
    path('search/', views.search, name='search'),

    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/new/', views.customer_edit, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/api/search/', views.customer_search_api, name='customer_search_api'),

    # Repairs (Orders)
    path('repairs/', views.repair_list, name='repair_list'),
    path('repairs/new/', views.repair_create, name='repair_create'),
    path('repairs/<int:pk>/', views.repair_detail, name='repair_detail'),
    path('repairs/<int:pk>/status/', views.repair_update_status, name='repair_update_status'),
    path('repairs/<int:pk>/assign/', views.repair_update_assigned, name='repair_update_assigned'),
    path('repairs/<int:pk>/device/', views.repair_update_device, name='repair_update_device'),
    path('repairs/api/models/', views.models_by_brand_api, name='models_by_brand_api'),
    path('repairs/<int:pk>/add-service/', views.repair_add_service, name='repair_add_service'),
    path('repairs/<int:pk>/remove-service/<int:service_pk>/', views.repair_remove_service, name='repair_remove_service'),
    path('repairs/<int:pk>/add-part/', views.repair_add_part, name='repair_add_part'),
    path('repairs/<int:pk>/remove-part/<int:part_pk>/', views.repair_remove_part, name='repair_remove_part'),
    path('repairs/<int:pk>/add-accessory/', views.repair_add_accessory, name='repair_add_accessory'),
    path('repairs/<int:pk>/remove-accessory/<int:accessory_pk>/', views.repair_remove_accessory, name='repair_remove_accessory'),
    path('repairs/<int:pk>/comment/', views.repair_add_comment, name='repair_add_comment'),
    path('repairs/<int:pk>/pay/', views.repair_pay, name='repair_pay'),
    path('repairs/<int:pk>/print/', views.repair_print, name='repair_print'),

    # Warehouse
    path('warehouse/parts/', views.warehouse_parts, name='warehouse_parts'),
    path('warehouse/parts/new/', views.part_create, name='part_create'),
    path('warehouse/parts/<int:pk>/edit/', views.part_edit, name='part_edit'),
    path('warehouse/parts/<int:pk>/stock-in/', views.part_stock_in, name='part_stock_in'),
    path('warehouse/parts/<int:pk>/stock-out/', views.part_stock_out, name='part_stock_out'),
    path('warehouse/accessories/', views.warehouse_accessories, name='warehouse_accessories'),
    path('warehouse/accessories/new/', views.accessory_create, name='accessory_create'),
    path('warehouse/accessories/<int:pk>/edit/', views.accessory_edit, name='accessory_edit'),
    path('warehouse/accessories/<int:pk>/stock-in/', views.accessory_stock_in, name='accessory_stock_in'),
    path('warehouse/movements/', views.stock_movements, name='stock_movements'),
    path('warehouse/suppliers/', views.supplier_list, name='supplier_list'),

    # Sales
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/new/', views.sale_create, name='sale_create'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('sales/<int:pk>/remove-item/<int:item_pk>/', views.sale_remove_item, name='sale_remove_item'),
    path('sales/<int:pk>/finalize/', views.sale_finalize, name='sale_finalize'),

    # Finance
    path('finance/', views.finance, name='finance'),
    path('finance/expense/create/', views.expense_create, name='expense_create'),
    path('finance/payroll/my/', views.payroll_my, name='payroll_my'),
    path('finance/payroll/<int:employee_pk>/', views.payroll_employee, name='payroll_employee'),
    path('finance/payroll/<int:employee_pk>/add/', views.payroll_add_record, name='payroll_add_record'),

    # Analytics
    path('analytics/', views.analytics, name='analytics'),

    # Tasks
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/status/', views.task_update_status, name='task_update_status'),

    # Branches
    path('branches/', views.branch_list, name='branch_list'),
    path('branches/save/', views.branch_save, name='branch_save'),
    path('branches/<int:pk>/delete/', views.branch_delete, name='branch_delete'),

    # Employees
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/new/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('profile/', views.my_profile, name='my_profile'),

    # Notifications
    path('notifications/', views.notifications, name='notifications'),

    # Settings
    path('settings/company/', views.settings_company, name='settings_company'),

    # Documents
    path('documents/', views.document_list, name='document_list'),
    path('documents/blank/<str:doc_type>/', views.document_blank_print, name='document_blank_print'),

    # Appointments
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/new/', views.appointment_create, name='appointment_create'),
    path('appointments/<int:pk>/edit/', views.appointment_edit, name='appointment_edit'),
    path('appointments/<int:pk>/delete/', views.appointment_delete, name='appointment_delete'),
    path('appointments/<int:pk>/status/', views.appointment_update_status, name='appointment_update_status'),
    path('appointments/<int:pk>/to-order/', views.appointment_to_order, name='appointment_to_order'),

    # Call requests
    path('call-requests/', views.call_request_list, name='call_request_list'),
    path('call-requests/<int:pk>/update/', views.call_request_update, name='call_request_update'),

    # Legacy user management (redirect to employees)
    path('users/', views.employee_list, name='user_list'),
    path('users/new/', views.employee_create, name='user_create'),
    path('users/<int:pk>/edit/', views.employee_edit, name='user_edit'),

    # File Manager
    path('filemanager/', views.filemanager, name='filemanager'),
    path('filemanager/upload/', views.filemanager_upload, name='filemanager_upload'),
    path('filemanager/rename/', views.filemanager_rename, name='filemanager_rename'),
    path('filemanager/download/', views.filemanager_download, name='filemanager_download'),
    path('filemanager/mkdir/', views.filemanager_mkdir, name='filemanager_mkdir'),
    path('filemanager/delete/', views.filemanager_delete, name='filemanager_delete'),

    # Price list editor
    path('prices/', views.price_list, name='price_list'),
    path('prices/brand/save/', views.price_brand_save, name='price_brand_save'),
    path('prices/brand/<int:pk>/delete/', views.price_brand_delete, name='price_brand_delete'),
    path('prices/service/save/', views.price_service_save, name='price_service_save'),
    path('prices/service/<int:pk>/delete/', views.price_service_delete, name='price_service_delete'),
    path('prices/model/save/', views.price_model_save, name='price_model_save'),
    path('prices/model/<int:pk>/delete/', views.price_model_delete, name='price_model_delete'),
]
