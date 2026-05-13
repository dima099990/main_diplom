from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import crm_required, manager_required, admin_required, get_role
from .models import (UserProfile, Customer, Part, Accessory, StockMovement,
                     RepairOrder, DeviceConditionCheck, RepairOrderService,
                     RepairOrderPart, SaleOrder, SaleOrderItem, CONDITION_ITEMS, CONDITION_STATES)
from core.models import Brand, PhoneModel, RepairService, SiteSettings, CallRequest


# ─── AUTH ────────────────────────────────────────────────────────────────────

def crm_login(request):
    if request.user.is_authenticated:
        return redirect('crm:dashboard')
    error = None
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'crm:dashboard'))
        error = "Неверный логин или пароль"
    return render(request, 'crm/login.html', {'error': error})


def crm_logout(request):
    logout(request)
    return redirect('crm:login')


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@crm_required
def dashboard(request):
    role = get_role(request.user)
    today = timezone.now().date()
    ctx = {'role': role}

    if role in ('admin', 'manager'):
        ctx['total_repairs'] = RepairOrder.objects.count()
        ctx['active_repairs'] = RepairOrder.objects.filter(status__in=['new','diagnosis','waiting_parts','in_progress']).count()
        ctx['done_today'] = RepairOrder.objects.filter(status='done', updated_at__date=today).count()
        ctx['call_requests'] = CallRequest.objects.filter(is_processed=False).count()
        ctx['low_parts'] = Part.objects.filter(quantity__lte=models_F('min_quantity')).count() if False else \
            sum(1 for p in Part.objects.all() if p.is_low_stock)
        ctx['recent_repairs'] = RepairOrder.objects.select_related('customer','phone_model','brand').order_by('-created_at')[:10]
        ctx['recent_sales'] = SaleOrder.objects.order_by('-created_at')[:5]
    else:
        ctx['my_repairs'] = RepairOrder.objects.filter(
            Q(assigned_to=request.user) | Q(created_by=request.user)
        ).exclude(status__in=['issued','cancelled']).order_by('-created_at')[:10]
        ctx['my_done_today'] = RepairOrder.objects.filter(
            Q(assigned_to=request.user) | Q(created_by=request.user),
            status='done', updated_at__date=today
        ).count()

    return render(request, 'crm/dashboard.html', ctx)


# ─── SEARCH ──────────────────────────────────────────────────────────────────

@crm_required
def search(request):
    q = request.GET.get('q', '').strip()
    results = {'customers': [], 'repairs': []}
    if q:
        results['customers'] = Customer.objects.filter(Q(name__icontains=q) | Q(phone__icontains=q))
        results['repairs'] = RepairOrder.objects.filter(
            Q(order_number__icontains=q) | Q(customer__name__icontains=q) | Q(customer__phone__icontains=q)
        ).select_related('customer', 'phone_model')
    return render(request, 'crm/search.html', {'q': q, **results})


# ─── CUSTOMERS ───────────────────────────────────────────────────────────────

@crm_required
def customer_list(request):
    q = request.GET.get('q', '').strip()
    customers = Customer.objects.annotate(repair_count=Count('repairs'))
    if q:
        customers = customers.filter(Q(name__icontains=q) | Q(phone__icontains=q))
    return render(request, 'crm/customers/list.html', {'customers': customers, 'q': q})


@crm_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    repairs = customer.repairs.select_related('brand', 'phone_model').order_by('-created_at')
    return render(request, 'crm/customers/detail.html', {'customer': customer, 'repairs': repairs})


@crm_required
def customer_edit(request, pk=None):
    customer = get_object_or_404(Customer, pk=pk) if pk else None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        if name and phone:
            if customer:
                customer.name = name; customer.phone = phone
                customer.email = request.POST.get('email','')
                customer.notes = request.POST.get('notes','')
                customer.save()
            else:
                customer = Customer.objects.create(name=name, phone=phone,
                    email=request.POST.get('email',''), notes=request.POST.get('notes',''))
            messages.success(request, 'Клиент сохранён')
            return redirect('crm:customer_detail', pk=customer.pk)
    return render(request, 'crm/customers/form.html', {'customer': customer})


# ─── REPAIR ORDERS ───────────────────────────────────────────────────────────

@crm_required
def repair_list(request):
    role = get_role(request.user)
    repairs = RepairOrder.objects.select_related('customer', 'brand', 'phone_model', 'assigned_to')
    if role == 'employee':
        repairs = repairs.filter(Q(assigned_to=request.user) | Q(created_by=request.user))
    status_filter = request.GET.get('status', '')
    if status_filter:
        repairs = repairs.filter(status=status_filter)
    q = request.GET.get('q', '').strip()
    if q:
        repairs = repairs.filter(Q(order_number__icontains=q)|Q(customer__name__icontains=q)|Q(customer__phone__icontains=q))
    return render(request, 'crm/repairs/list.html', {
        'repairs': repairs.order_by('-created_at'),
        'status_choices': RepairOrder.STATUS_CHOICES,
        'status_filter': status_filter, 'q': q,
    })


@crm_required
def repair_create(request):
    brands = Brand.objects.filter(is_active=True)
    employees = User.objects.filter(is_active=True)
    site = SiteSettings.get()
    
    if request.method == 'POST':
        p = request.POST
        phone = p.get('customer_phone', '').strip()
        name = p.get('customer_name', '').strip()
        customer = Customer.objects.filter(phone=phone).first()
        if not customer:
            customer = Customer.objects.create(name=name, phone=phone, email=p.get('customer_email',''))
        
        brand_id = p.get('brand')
        model_id = p.get('phone_model')
        brand = get_object_or_404(Brand, pk=brand_id)
        phone_model = get_object_or_404(PhoneModel, pk=model_id)
        
        repair = RepairOrder.objects.create(
            customer=customer, brand=brand, phone_model=phone_model,
            imei=p.get('imei',''), appearance=p.get('appearance',''),
            device_password=p.get('device_password',''), complaint=p.get('complaint',''),
            created_by=request.user,
            assigned_to_id=p.get('assigned_to') or None,
            estimated_cost=p.get('estimated_cost',0) or 0,
            notes=p.get('notes',''), warranty_days=site.warranty_days,
        )
        # Save condition check
        cond_data = {'repair_order': repair}
        for field_name, _ in CONDITION_ITEMS:
            cond_data[field_name] = p.get(f'cond_{field_name}', 'na')
        DeviceConditionCheck.objects.create(**cond_data)
        
        messages.success(request, f'Заказ {repair.order_number} создан')
        return redirect('crm:repair_detail', pk=repair.pk)
    
    return render(request, 'crm/repairs/create.html', {
        'brands': brands, 'employees': employees,
        'condition_items': CONDITION_ITEMS, 'condition_states': CONDITION_STATES,
    })


@crm_required
def repair_detail(request, pk):
    repair = get_object_or_404(RepairOrder.objects.select_related(
        'customer','brand','phone_model','assigned_to','created_by'
    ), pk=pk)
    services = repair.order_services.all()
    parts_used = repair.order_parts.select_related('part').all()
    available_services = RepairService.objects.filter(phone_model=repair.phone_model, is_active=True)
    available_parts = Part.objects.filter(
        Q(phone_model=repair.phone_model) | Q(brand=repair.brand) | Q(phone_model=None)
    ).order_by('name')
    employees = User.objects.filter(is_active=True)
    
    try:
        condition = repair.condition_check
    except DeviceConditionCheck.DoesNotExist:
        condition = None
    
    return render(request, 'crm/repairs/detail.html', {
        'repair': repair, 'services': services, 'parts_used': parts_used,
        'available_services': available_services, 'available_parts': available_parts,
        'condition': condition, 'employees': employees,
        'status_choices': RepairOrder.STATUS_CHOICES,
    })


@crm_required
@require_POST
def repair_update_status(request, pk):
    repair = get_object_or_404(RepairOrder, pk=pk)
    repair.status = request.POST.get('status', repair.status)
    repair.save(update_fields=['status', 'updated_at'])
    messages.success(request, f'Статус изменён на "{repair.get_status_display()}"')
    return redirect('crm:repair_detail', pk=pk)


@crm_required
@require_POST
def repair_update_assigned(request, pk):
    repair = get_object_or_404(RepairOrder, pk=pk)
    uid = request.POST.get('assigned_to')
    repair.assigned_to_id = uid if uid else None
    repair.save(update_fields=['assigned_to'])
    messages.success(request, 'Назначение обновлено')
    return redirect('crm:repair_detail', pk=pk)


@crm_required
@require_POST
def repair_add_service(request, pk):
    repair = get_object_or_404(RepairOrder, pk=pk)
    service_id = request.POST.get('service_id')
    custom_name = request.POST.get('custom_name', '').strip()
    price = request.POST.get('price', 0)
    
    if service_id:
        svc = get_object_or_404(RepairService, pk=service_id)
        RepairOrderService.objects.create(order=repair, service=svc, name=svc.name, price=price or svc.price_from)
    elif custom_name:
        RepairOrderService.objects.create(order=repair, name=custom_name, price=price)
    
    repair.recalculate_final_cost()
    messages.success(request, 'Работа добавлена')
    return redirect('crm:repair_detail', pk=pk)


@crm_required
@require_POST
def repair_remove_service(request, pk, service_pk):
    svc = get_object_or_404(RepairOrderService, pk=service_pk, order_id=pk)
    svc.delete()
    get_object_or_404(RepairOrder, pk=pk).recalculate_final_cost()
    messages.success(request, 'Работа удалена')
    return redirect('crm:repair_detail', pk=pk)


@crm_required
@require_POST
def repair_add_part(request, pk):
    repair = get_object_or_404(RepairOrder, pk=pk)
    part_id = request.POST.get('part_id')
    qty = int(request.POST.get('quantity', 1))
    price = request.POST.get('price', 0)
    
    part = get_object_or_404(Part, pk=part_id)
    use_price = float(price) if price else float(part.sale_price)
    
    RepairOrderPart.objects.create(order=repair, part=part, quantity=qty, price=use_price)
    
    # Deduct from stock
    part.quantity -= qty
    part.save(update_fields=['quantity'])
    StockMovement.objects.create(
        part=part, movement_type='repair', quantity=-qty,
        comment=f'Заказ {repair.order_number}', created_by=request.user
    )
    repair.recalculate_final_cost()
    messages.success(request, f'Запчасть "{part.name}" добавлена (списано {qty} шт.)')
    return redirect('crm:repair_detail', pk=pk)


@crm_required
@require_POST
def repair_remove_part(request, pk, part_pk):
    op = get_object_or_404(RepairOrderPart, pk=part_pk, order_id=pk)
    # Return to stock
    op.part.quantity += op.quantity
    op.part.save(update_fields=['quantity'])
    StockMovement.objects.create(
        part=op.part, movement_type='in', quantity=op.quantity,
        comment=f'Возврат из заказа {op.order.order_number}', created_by=request.user
    )
    op.delete()
    get_object_or_404(RepairOrder, pk=pk).recalculate_final_cost()
    messages.success(request, 'Запчасть удалена, возврат на склад')
    return redirect('crm:repair_detail', pk=pk)


@crm_required
def repair_print(request, pk):
    repair = get_object_or_404(RepairOrder.objects.select_related(
        'customer','brand','phone_model','assigned_to','created_by'
    ), pk=pk)
    try:
        condition = repair.condition_check
    except DeviceConditionCheck.DoesNotExist:
        condition = None
    site = SiteSettings.get()
    return render(request, 'crm/repairs/print_act.html', {
        'repair': repair, 'condition': condition, 'site': site,
        'services': repair.order_services.all(),
        'print_date': timezone.now(),
    })


# ─── WAREHOUSE ───────────────────────────────────────────────────────────────

@manager_required
def part_list(request):
    q = request.GET.get('q', '').strip()
    parts = Part.objects.select_related('brand', 'phone_model')
    if q:
        parts = parts.filter(Q(name__icontains=q)|Q(sku__icontains=q))
    brand_filter = request.GET.get('brand')
    if brand_filter:
        parts = parts.filter(brand_id=brand_filter)
    brands = Brand.objects.all()
    return render(request, 'crm/warehouse/parts.html', {
        'parts': parts, 'q': q, 'brands': brands, 'brand_filter': brand_filter,
    })


@manager_required
def part_create(request):
    brands = Brand.objects.filter(is_active=True)
    phone_models = PhoneModel.objects.select_related('brand').filter(is_active=True)
    if request.method == 'POST':
        p = request.POST
        part = Part.objects.create(
            name=p['name'], sku=p.get('sku',''),
            brand_id=p.get('brand') or None, phone_model_id=p.get('phone_model') or None,
            quantity=p.get('quantity',0), min_quantity=p.get('min_quantity',1),
            purchase_price=p.get('purchase_price',0), sale_price=p.get('sale_price',0),
            notes=p.get('notes',''),
        )
        if int(p.get('quantity',0)) > 0:
            StockMovement.objects.create(part=part, movement_type='in',
                quantity=int(p.get('quantity',0)), comment='Начальный остаток', created_by=request.user)
        messages.success(request, f'Запчасть "{part.name}" добавлена')
        return redirect('crm:part_list')
    return render(request, 'crm/warehouse/part_form.html', {'brands': brands, 'phone_models': phone_models})


@manager_required
def part_edit(request, pk):
    part = get_object_or_404(Part, pk=pk)
    brands = Brand.objects.filter(is_active=True)
    phone_models = PhoneModel.objects.select_related('brand').filter(is_active=True)
    if request.method == 'POST':
        p = request.POST
        part.name=p['name']; part.sku=p.get('sku','')
        part.brand_id=p.get('brand') or None; part.phone_model_id=p.get('phone_model') or None
        part.min_quantity=p.get('min_quantity',1)
        part.purchase_price=p.get('purchase_price',0); part.sale_price=p.get('sale_price',0)
        part.notes=p.get('notes','')
        part.save()
        messages.success(request, 'Запчасть обновлена')
        return redirect('crm:part_list')
    return render(request, 'crm/warehouse/part_form.html', {'part': part, 'brands': brands, 'phone_models': phone_models})


@manager_required
@require_POST
def part_stock_in(request, pk):
    part = get_object_or_404(Part, pk=pk)
    qty = int(request.POST.get('quantity', 0))
    if qty > 0:
        part.quantity += qty; part.save(update_fields=['quantity'])
        StockMovement.objects.create(part=part, movement_type='in', quantity=qty,
            comment=request.POST.get('comment',''), created_by=request.user)
        messages.success(request, f'Добавлено {qty} шт. на склад')
    return redirect('crm:part_list')


@manager_required
@require_POST
def part_stock_out(request, pk):
    part = get_object_or_404(Part, pk=pk)
    qty = int(request.POST.get('quantity', 0))
    if qty > 0:
        part.quantity -= qty; part.save(update_fields=['quantity'])
        StockMovement.objects.create(part=part, movement_type='out', quantity=-qty,
            comment=request.POST.get('comment','Ручное списание'), created_by=request.user)
        messages.success(request, f'Списано {qty} шт.')
    return redirect('crm:part_list')


@manager_required
def accessory_list(request):
    q = request.GET.get('q', '').strip()
    accessories = Accessory.objects.all()
    if q:
        accessories = accessories.filter(Q(name__icontains=q)|Q(sku__icontains=q))
    cat_filter = request.GET.get('cat', '')
    if cat_filter:
        accessories = accessories.filter(category=cat_filter)
    return render(request, 'crm/warehouse/accessories.html', {
        'accessories': accessories, 'q': q,
        'categories': Accessory.CATEGORIES, 'cat_filter': cat_filter,
    })


@manager_required
def accessory_create(request):
    if request.method == 'POST':
        p = request.POST
        acc = Accessory.objects.create(
            name=p['name'], category=p.get('category','other'), sku=p.get('sku',''),
            compatible_with=p.get('compatible_with',''),
            quantity=p.get('quantity',0), min_quantity=p.get('min_quantity',2),
            purchase_price=p.get('purchase_price',0), sale_price=p.get('sale_price',0),
            notes=p.get('notes',''),
        )
        if int(p.get('quantity',0)) > 0:
            StockMovement.objects.create(accessory=acc, movement_type='in',
                quantity=int(p.get('quantity',0)), comment='Начальный остаток', created_by=request.user)
        messages.success(request, f'Аксессуар "{acc.name}" добавлен')
        return redirect('crm:accessory_list')
    return render(request, 'crm/warehouse/accessory_form.html', {'categories': Accessory.CATEGORIES})


@manager_required
def accessory_edit(request, pk):
    acc = get_object_or_404(Accessory, pk=pk)
    if request.method == 'POST':
        p = request.POST
        acc.name=p['name']; acc.category=p.get('category','other'); acc.sku=p.get('sku','')
        acc.compatible_with=p.get('compatible_with','')
        acc.min_quantity=p.get('min_quantity',2)
        acc.purchase_price=p.get('purchase_price',0); acc.sale_price=p.get('sale_price',0)
        acc.notes=p.get('notes',''); acc.save()
        messages.success(request, 'Аксессуар обновлён')
        return redirect('crm:accessory_list')
    return render(request, 'crm/warehouse/accessory_form.html', {'acc': acc, 'categories': Accessory.CATEGORIES})


@manager_required
@require_POST
def accessory_stock_in(request, pk):
    acc = get_object_or_404(Accessory, pk=pk)
    qty = int(request.POST.get('quantity', 0))
    if qty > 0:
        acc.quantity += qty; acc.save(update_fields=['quantity'])
        StockMovement.objects.create(accessory=acc, movement_type='in', quantity=qty,
            comment=request.POST.get('comment',''), created_by=request.user)
        messages.success(request, f'Добавлено {qty} шт.')
    return redirect('crm:accessory_list')


@manager_required
def stock_movements(request):
    movements = StockMovement.objects.select_related('part','accessory','created_by').order_by('-created_at')[:200]
    return render(request, 'crm/warehouse/movements.html', {'movements': movements})


# ─── SALES ───────────────────────────────────────────────────────────────────

@crm_required
def sale_list(request):
    sales = SaleOrder.objects.select_related('created_by').order_by('-created_at')
    role = get_role(request.user)
    if role == 'employee':
        sales = sales.filter(created_by=request.user)
    return render(request, 'crm/sales/list.html', {'sales': sales})


@crm_required
def sale_create(request):
    accessories = Accessory.objects.filter(quantity__gt=0)
    if request.method == 'POST':
        sale = SaleOrder.objects.create(
            customer_name=request.POST.get('customer_name',''),
            customer_phone=request.POST.get('customer_phone',''),
            notes=request.POST.get('notes',''),
            created_by=request.user,
        )
        messages.success(request, f'Продажа {sale.order_number} создана. Добавьте товары.')
        return redirect('crm:sale_detail', pk=sale.pk)
    return render(request, 'crm/sales/create.html', {'accessories': accessories})


@crm_required
def sale_detail(request, pk):
    sale = get_object_or_404(SaleOrder, pk=pk)
    if request.method == 'POST' and 'add_item' in request.POST:
        acc_id = request.POST.get('accessory_id')
        qty = int(request.POST.get('quantity', 1))
        acc = get_object_or_404(Accessory, pk=acc_id)
        price = request.POST.get('price', acc.sale_price)
        SaleOrderItem.objects.create(order=sale, accessory=acc, quantity=qty, price=price)
        sale.recalculate_total()
        messages.success(request, f'Добавлено: {acc.name}')
        return redirect('crm:sale_detail', pk=pk)
    
    accessories = Accessory.objects.filter(quantity__gt=0)
    return render(request, 'crm/sales/detail.html', {
        'sale': sale, 'accessories': accessories,
    })


@crm_required
@require_POST
def sale_remove_item(request, pk, item_pk):
    item = get_object_or_404(SaleOrderItem, pk=item_pk, order_id=pk)
    item.delete()
    get_object_or_404(SaleOrder, pk=pk).recalculate_total()
    messages.success(request, 'Позиция удалена')
    return redirect('crm:sale_detail', pk=pk)


@crm_required
@require_POST
def sale_finalize(request, pk):
    sale = get_object_or_404(SaleOrder, pk=pk)
    if sale.is_finalized:
        messages.error(request, 'Продажа уже завершена')
        return redirect('crm:sale_detail', pk=pk)
    for item in sale.items.all():
        item.accessory.quantity -= item.quantity
        item.accessory.save(update_fields=['quantity'])
        StockMovement.objects.create(
            accessory=item.accessory, movement_type='sale', quantity=-item.quantity,
            comment=f'Продажа {sale.order_number}', created_by=request.user
        )
    sale.is_finalized = True; sale.save(update_fields=['is_finalized'])
    messages.success(request, f'Продажа {sale.order_number} завершена, товары списаны со склада')
    return redirect('crm:sale_detail', pk=pk)


# ─── CALL REQUESTS ───────────────────────────────────────────────────────────

@manager_required
def call_request_list(request):
    show_all = request.GET.get('all', '')
    requests = CallRequest.objects.order_by('-created_at')
    if not show_all:
        requests = requests.filter(is_processed=False)
    return render(request, 'crm/call_requests/list.html', {'requests': requests, 'show_all': show_all})


@manager_required
@require_POST
def call_request_update(request, pk):
    cr = get_object_or_404(CallRequest, pk=pk)
    cr.is_processed = True
    cr.result = request.POST.get('result', '')
    cr.processed_at = timezone.now()
    cr.save()
    messages.success(request, 'Заявка обработана')
    return redirect('crm:call_request_list')


# ─── USERS (Admin only) ───────────────────────────────────────────────────────

@admin_required
def user_list(request):
    users = User.objects.select_related('profile').filter(is_active=True).order_by('username')
    return render(request, 'crm/users/list.html', {'users': users})


@admin_required
def user_create(request):
    if request.method == 'POST':
        p = request.POST
        username = p.get('username','').strip()
        password = p.get('password','').strip()
        if not username or not password:
            messages.error(request, 'Логин и пароль обязательны')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Такой логин уже существует')
        else:
            user = User.objects.create_user(
                username=username, password=password,
                first_name=p.get('first_name',''), last_name=p.get('last_name',''),
                email=p.get('email','')
            )
            UserProfile.objects.filter(user=user).update(role=p.get('role','employee'), phone=p.get('phone',''))
            messages.success(request, f'Пользователь {username} создан')
            return redirect('crm:user_list')
    return render(request, 'crm/users/form.html', {'roles': UserProfile.ROLES})


@admin_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if request.method == 'POST':
        p = request.POST
        user.first_name=p.get('first_name',''); user.last_name=p.get('last_name','')
        user.email=p.get('email',''); user.save()
        profile.role=p.get('role','employee'); profile.phone=p.get('phone',''); profile.save()
        if p.get('new_password'):
            user.set_password(p['new_password']); user.save()
        messages.success(request, 'Пользователь обновлён')
        return redirect('crm:user_list')
    return render(request, 'crm/users/form.html', {'edit_user': user, 'profile': profile, 'roles': UserProfile.ROLES})


# ─── API (for Telegram bot / ChatGPT) ────────────────────────────────────────

def api_prices(request):
    """JSON API: полный прайс-лист для бота"""
    data = []
    for brand in Brand.objects.filter(is_active=True).prefetch_related('phone_models__services'):
        brand_data = {'id': brand.id, 'name': brand.name, 'models': []}
        for model in brand.phone_models.filter(is_active=True):
            model_data = {'id': model.id, 'name': model.full_name, 'services': []}
            for svc in model.services.filter(is_active=True):
                model_data['services'].append({
                    'id': svc.id, 'name': svc.name,
                    'price_from': svc.price_from,
                    'price_to': svc.price_to,
                    'price_display': svc.price_display,
                    'duration': svc.duration,
                    'is_popular': svc.is_popular,
                })
            if model_data['services']:
                brand_data['models'].append(model_data)
        if brand_data['models']:
            data.append(brand_data)
    return JsonResponse({'brands': data}, json_dumps_params={'ensure_ascii': False})


def api_models_for_brand(request, brand_id):
    """AJAX: получить модели для выбранного бренда"""
    models = list(PhoneModel.objects.filter(brand_id=brand_id, is_active=True).values('id','name').order_by('order','name'))
    return JsonResponse({'models': models})
