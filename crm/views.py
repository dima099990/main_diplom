from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q, Sum, Avg
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Brand, CallRequest, PhoneModel, RepairService, SiteSettings
from .decorators import admin_required, crm_required, manager_required
from .models import (
    Accessory, Branch, Customer, Expense,
    Notification, OrderHistory, Part, PaymentRecord, PayrollRecord,
    RepairOrder, RepairOrderPart, RepairOrderService, SaleOrder,
    SaleOrderItem, StockMovement, Supplier, Task, UserProfile,
)


# ─── AUTH ─────────────────────────────────────────────────────────────────────

def crm_login(request):
    if request.user.is_authenticated:
        return redirect('crm:dashboard')
    error = None
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username'),
                            password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'crm:dashboard'))
        error = 'Неверный логин или пароль'
    return render(request, 'crm/login.html', {'error': error})


@crm_required
def crm_logout(request):
    logout(request)
    return redirect('crm:login')


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@crm_required
def dashboard(request):
    now = timezone.now()
    today = now.date()
    month_start = today.replace(day=1)

    orders_qs = RepairOrder.objects.select_related('customer', 'brand', 'phone_model', 'assigned_to')

    open_statuses = ['new', 'diagnosis', 'waiting_parts', 'in_progress', 'approval']
    open_orders = orders_qs.filter(status__in=open_statuses)

    # Payments this month
    payments_month = PaymentRecord.objects.filter(
        created_at__date__gte=month_start,
        payment_type__in=['repair', 'sale'],
    )
    revenue_month = payments_month.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    profit_month = orders_qs.filter(
        status='issued', paid_at__date__gte=month_start
    ).aggregate(p=Sum('final_cost') - Sum('cost_price'))['p'] or Decimal('0')

    payments_today = PaymentRecord.objects.filter(created_at__date=today)
    revenue_today = payments_today.aggregate(t=Sum('amount'))['t'] or Decimal('0')

    avg_check = orders_qs.filter(
        status='issued', paid_at__date__gte=month_start
    ).aggregate(a=Avg('final_cost'))['a'] or Decimal('0')

    low_stock_parts = Part.objects.filter(quantity__lte=F('min_quantity')).order_by('quantity')[:8]
    low_stock_acc = Accessory.objects.filter(quantity__lte=F('min_quantity')).order_by('quantity')[:4]
    low_stock_items = list(low_stock_parts) + list(low_stock_acc)

    # Chart data: last 30 days
    days = [today - timedelta(days=i) for i in range(29, -1, -1)]
    chart_labels = [d.strftime('%d %b') for d in days]
    chart_revenue = []
    chart_profit = []
    for d in days:
        rev = PaymentRecord.objects.filter(
            created_at__date=d, payment_type__in=['repair', 'sale']
        ).aggregate(t=Sum('amount'))['t'] or 0
        prf = RepairOrder.objects.filter(
            paid_at__date=d
        ).aggregate(p=Sum('final_cost') - Sum('cost_price'))['p'] or 0
        chart_revenue.append(float(rev))
        chart_profit.append(float(prf))

    # Status breakdown
    status_colors = {
        'new': '#6b7280', 'diagnosis': '#f97316', 'waiting_parts': '#eab308',
        'in_progress': '#6366f1', 'approval': '#a855f7', 'done': '#22c55e',
        'issued': '#14b8a6', 'cancelled': '#ef4444',
    }
    status_breakdown = []
    for val, label in RepairOrder.STATUS_CHOICES:
        cnt = orders_qs.filter(status=val).count()
        if cnt:
            status_breakdown.append({'label': label, 'count': cnt, 'color': status_colors[val]})

    status_chart_data = {
        'labels': [x['label'] for x in status_breakdown],
        'values': [x['count'] for x in status_breakdown],
        'colors': [x['color'] for x in status_breakdown],
    }

    # Top masters
    top_masters = User.objects.filter(
        assigned_repairs__status='issued',
        assigned_repairs__paid_at__date__gte=month_start,
    ).annotate(
        orders_count=Count('assigned_repairs'),
        total_profit=Sum('assigned_repairs__final_cost') - Sum('assigned_repairs__cost_price'),
    ).order_by('-total_profit')[:5]

    stats = {
        'revenue_today': revenue_today,
        'profit_month': profit_month,
        'open_orders': open_orders.count(),
        'done_orders': orders_qs.filter(status='done').count(),
        'cash_today': revenue_today,
        'avg_check': avg_check,
        'low_stock': len(low_stock_items),
        'orders_month': orders_qs.filter(created_at__date__gte=month_start).count(),
        'month_name': month_start.strftime('%B %Y'),
        'status_breakdown': status_breakdown,
    }

    return render(request, 'crm/dashboard.html', {
        'stats': stats,
        'recent_orders': orders_qs[:10],
        'top_masters': top_masters,
        'low_stock_items': low_stock_items,
        'chart_labels': chart_labels,
        'chart_revenue': chart_revenue,
        'chart_profit': chart_profit,
        'status_chart_data': status_chart_data,
    })


# ─── SEARCH ───────────────────────────────────────────────────────────────────

@crm_required
def search(request):
    q = request.GET.get('q', '').strip()
    results = {'orders': [], 'customers': [], 'parts': []}
    if len(q) >= 2:
        results['orders'] = RepairOrder.objects.filter(
            Q(order_number__icontains=q) | Q(customer__name__icontains=q) |
            Q(customer__phone__icontains=q) | Q(imei__icontains=q) |
            Q(complaint__icontains=q)
        ).select_related('customer', 'brand', 'phone_model')[:10]
        results['customers'] = Customer.objects.filter(
            Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
        )[:10]
        results['parts'] = Part.objects.filter(
            Q(name__icontains=q) | Q(sku__icontains=q)
        )[:10]
    return render(request, 'crm/search.html', {'q': q, 'results': results})


# ─── CUSTOMERS ────────────────────────────────────────────────────────────────

@crm_required
def customer_list(request):
    qs = Customer.objects.annotate(
        repair_count=Count('repairs'),
    ).order_by('-created_at')
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q))
    page = Paginator(qs, 30).get_page(request.GET.get('page'))
    return render(request, 'crm/customers/list.html', {'customers': page, 'q': q})


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
        if not name or not phone:
            messages.error(request, 'Имя и телефон обязательны')
        else:
            if customer:
                customer.name = name
                customer.phone = phone
                customer.email = request.POST.get('email', '')
                customer.notes = request.POST.get('notes', '')
                customer.save()
                messages.success(request, 'Клиент обновлён')
            else:
                customer = Customer.objects.create(
                    name=name, phone=phone,
                    email=request.POST.get('email', ''),
                    notes=request.POST.get('notes', ''),
                )
                messages.success(request, 'Клиент создан')
            return redirect('crm:customer_detail', customer.pk)
    return render(request, 'crm/customers/form.html', {'customer': customer})


@crm_required
def customer_search_api(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    customers = Customer.objects.filter(
        Q(name__icontains=q) | Q(phone__icontains=q)
    ).values('id', 'name', 'phone')[:10]
    return JsonResponse(list(customers), safe=False)


# ─── REPAIRS ──────────────────────────────────────────────────────────────────

@crm_required
def repair_list(request):
    qs = RepairOrder.objects.select_related(
        'customer', 'brand', 'phone_model', 'assigned_to', 'created_by'
    )
    profile = getattr(request.user, 'profile', None)
    if profile and profile.role == 'master':
        qs = qs.filter(assigned_to=request.user)

    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(
            Q(order_number__icontains=q) | Q(customer__name__icontains=q) |
            Q(customer__phone__icontains=q) | Q(imei__icontains=q)
        )
    if request.GET.get('status'):
        qs = qs.filter(status=request.GET['status'])
    if request.GET.get('master'):
        qs = qs.filter(assigned_to_id=request.GET['master'])
    if request.GET.get('branch'):
        qs = qs.filter(branch_id=request.GET['branch'])
    if request.GET.get('date_from'):
        qs = qs.filter(created_at__date__gte=request.GET['date_from'])
    if request.GET.get('date_to'):
        qs = qs.filter(created_at__date__lte=request.GET['date_to'])

    # Status tabs counts
    status_tabs = []
    for val, label in RepairOrder.STATUS_CHOICES:
        cnt = RepairOrder.objects.filter(status=val).count()
        status_tabs.append((val, label, cnt))

    total_count = RepairOrder.objects.count()
    page = Paginator(qs, 30).get_page(request.GET.get('page'))

    return render(request, 'crm/repairs/list.html', {
        'orders': page,
        'status_choices': RepairOrder.STATUS_CHOICES,
        'status_tabs': status_tabs,
        'total_count': total_count,
        'masters': User.objects.filter(profile__role__in=['master', 'employee', 'manager']),
        'branches': Branch.objects.filter(is_active=True),
    })


@crm_required
def repair_create(request):
    if request.method == 'POST':
        with transaction.atomic():
            # Customer lookup or create
            customer_id = request.POST.get('customer_id')
            if customer_id:
                customer = get_object_or_404(Customer, pk=customer_id)
            else:
                customer_name = request.POST.get('customer_name', '').strip()
                customer_phone = request.POST.get('customer_phone', '').strip()
                if not customer_phone:
                    messages.error(request, 'Укажите телефон клиента')
                    return _repair_create_ctx(request)
                customer, _ = Customer.objects.get_or_create(
                    phone=customer_phone,
                    defaults={'name': customer_name or customer_phone},
                )

            brand_id = request.POST.get('brand')
            model_id = request.POST.get('phone_model')
            if not brand_id or not model_id:
                messages.error(request, 'Выберите бренд и модель')
                return _repair_create_ctx(request)

            branch_id = request.POST.get('branch') or None
            assigned_id = request.POST.get('assigned_to') or None
            deadline_str = request.POST.get('deadline') or None
            deadline = date.fromisoformat(deadline_str) if deadline_str else None

            order = RepairOrder.objects.create(
                customer=customer,
                brand_id=brand_id,
                phone_model_id=model_id,
                imei=request.POST.get('imei', ''),
                device_password=request.POST.get('device_password', ''),
                complaint=request.POST.get('complaint', ''),
                appearance=request.POST.get('appearance', ''),
                estimated_cost=request.POST.get('estimated_cost') or 0,
                notes=request.POST.get('notes', ''),
                warranty_days=request.POST.get('warranty_days') or 90,
                created_by=request.user,
                assigned_to_id=assigned_id,
                branch_id=branch_id,
                deadline=deadline,
            )
            OrderHistory.objects.create(
                order=order, event_type='created',
                description=f'Заказ создан. Клиент: {customer.name}, устройство: {order.phone_model}',
                user=request.user,
            )
            messages.success(request, f'Заказ {order.order_number} создан')
            return redirect('crm:repair_detail', order.pk)

    return _repair_create_ctx(request)


def _repair_create_ctx(request):
    return render(request, 'crm/repairs/create.html', {
        'brands': Brand.objects.filter(is_active=True).order_by('order', 'name'),
        'masters': User.objects.filter(
            profile__role__in=['master', 'employee'], profile__is_active=True
        ),
        'branches': Branch.objects.filter(is_active=True),
    })


@crm_required
def repair_detail(request, pk):
    repair = get_object_or_404(
        RepairOrder.objects.select_related(
            'customer', 'brand', 'phone_model', 'assigned_to', 'created_by', 'branch'
        ).prefetch_related('order_services__service', 'order_parts__part', 'history__user'),
        pk=pk,
    )
    services_total = sum(s.price for s in repair.order_services.all())
    parts_total = sum(p.total for p in repair.order_parts.all())

    available_services = RepairService.objects.filter(
        phone_model=repair.phone_model, is_active=True
    ).select_related('phone_model__brand')
    # Запчасти: сначала подходящие для модели, потом все остальные
    parts_for_model = Part.objects.filter(
        phone_model=repair.phone_model, quantity__gt=0
    ).order_by('name')
    all_parts = Part.objects.filter(quantity__gt=0).order_by('name')

    tabs = [
        ('info', 'Информация'),
        ('works', 'Работы и материалы'),
        ('comment', 'Комментарий'),
    ]

    return render(request, 'crm/repairs/detail.html', {
        'repair': repair,
        'services_total': services_total,
        'parts_total': parts_total,
        'available_services': available_services,
        'available_parts': all_parts,
        'parts_for_model': parts_for_model,
        'masters': User.objects.filter(profile__role__in=['master', 'employee', 'admin', 'manager']),
        'status_choices': RepairOrder.STATUS_CHOICES,
        'history': repair.history.order_by('created_at'),
        'tabs': tabs,
    })


@crm_required
@require_POST
def repair_update_status(request, pk):
    repair = get_object_or_404(RepairOrder, pk=pk)
    new_status = request.POST.get('status')
    valid = [v for v, _ in RepairOrder.STATUS_CHOICES]
    if new_status in valid and new_status != repair.status:
        old_label = repair.get_status_display()
        repair.status = new_status
        repair.save(update_fields=['status', 'updated_at'])
        OrderHistory.objects.create(
            order=repair, event_type='status_change',
            description=f'Статус изменён: {old_label} → {repair.get_status_display()}',
            user=request.user,
        )
        messages.success(request, f'Статус обновлён: {repair.get_status_display()}')
    return redirect('crm:repair_detail', pk)


@crm_required
@require_POST
def repair_update_assigned(request, pk):
    repair = get_object_or_404(RepairOrder, pk=pk)
    assigned_id = request.POST.get('assigned_to')
    master = get_object_or_404(User, pk=assigned_id) if assigned_id else None
    repair.assigned_to = master
    repair.save(update_fields=['assigned_to', 'updated_at'])
    name = master.get_full_name() if master else 'не назначен'
    OrderHistory.objects.create(
        order=repair, event_type='master_assigned',
        description=f'Мастер назначен: {name}',
        user=request.user,
    )
    messages.success(request, f'Мастер назначен: {name}')
    return redirect('crm:repair_detail', pk)


@crm_required
@require_POST
def repair_add_service(request, pk):
    repair = get_object_or_404(RepairOrder, pk=pk)
    service_id = request.POST.get('service_id')
    custom_name = request.POST.get('custom_name', '').strip()
    custom_price = request.POST.get('custom_price', '0') or '0'

    if service_id:
        svc = get_object_or_404(RepairService, pk=service_id)
        price = Decimal(custom_price) if custom_price and float(custom_price) > 0 else svc.price_from
        RepairOrderService.objects.create(order=repair, service=svc, name=svc.name, price=price)
        OrderHistory.objects.create(
            order=repair, event_type='service_added',
            description=f'Добавлена услуга: {svc.name} — {price} ₽',
            user=request.user,
        )
    elif custom_name:
        price = Decimal(custom_price) if custom_price else Decimal('0')
        RepairOrderService.objects.create(order=repair, name=custom_name, price=price)
        OrderHistory.objects.create(
            order=repair, event_type='service_added',
            description=f'Добавлена услуга: {custom_name} — {price} ₽',
            user=request.user,
        )
    repair.recalculate_final_cost()
    return redirect('crm:repair_detail', pk)


@crm_required
@require_POST
def repair_remove_service(request, pk, service_pk):
    repair = get_object_or_404(RepairOrder, pk=pk)
    svc = get_object_or_404(RepairOrderService, pk=service_pk, order=repair)
    name = svc.name
    svc.delete()
    repair.recalculate_final_cost()
    OrderHistory.objects.create(
        order=repair, event_type='service_removed',
        description=f'Удалена услуга: {name}',
        user=request.user,
    )
    return redirect('crm:repair_detail', pk)


@crm_required
@require_POST
def repair_add_part(request, pk):
    repair = get_object_or_404(RepairOrder, pk=pk)
    part = get_object_or_404(Part, pk=request.POST.get('part_id'))
    qty = int(request.POST.get('quantity', 1))
    price_raw = str(request.POST.get('price', '') or part.sale_price).replace(',', '.')
    price = Decimal(price_raw)

    if part.quantity < qty:
        messages.error(request, f'Недостаточно запчасти "{part.name}" на складе (есть: {part.quantity})')
        return redirect('crm:repair_detail', pk)

    RepairOrderPart.objects.create(order=repair, part=part, quantity=qty, price=price)
    repair.recalculate_final_cost()
    OrderHistory.objects.create(
        order=repair, event_type='part_added',
        description=f'Добавлена запчасть: {part.name} ×{qty} — {price * qty} ₽',
        user=request.user,
    )
    return redirect('crm:repair_detail', pk)


@crm_required
@require_POST
def repair_remove_part(request, pk, part_pk):
    repair = get_object_or_404(RepairOrder, pk=pk)
    op = get_object_or_404(RepairOrderPart, pk=part_pk, order=repair)
    name = op.part.name
    op.delete()
    repair.recalculate_final_cost()
    OrderHistory.objects.create(
        order=repair, event_type='part_removed',
        description=f'Удалена запчасть: {name}',
        user=request.user,
    )
    return redirect('crm:repair_detail', pk)


@crm_required
@require_POST
def repair_add_comment(request, pk):
    repair = get_object_or_404(RepairOrder, pk=pk)
    comment = request.POST.get('comment', '').strip()
    if comment:
        OrderHistory.objects.create(
            order=repair, event_type='comment',
            description=comment, user=request.user,
        )
        messages.success(request, 'Комментарий добавлен')
    return redirect('crm:repair_detail', pk)


@crm_required
@require_POST
def repair_pay(request, pk):
    repair = get_object_or_404(RepairOrder, pk=pk)
    if repair.is_paid:
        messages.warning(request, 'Заказ уже оплачен')
        return redirect('crm:repair_detail', pk)

    method = request.POST.get('method', 'cash')
    with transaction.atomic():
        repair.is_paid = True
        repair.paid_at = timezone.now()
        repair.status = 'issued'
        repair.save(update_fields=['is_paid', 'paid_at', 'status', 'updated_at'])

        # Списать запчасти
        for op in repair.order_parts.select_related('part').all():
            op.part.quantity -= op.quantity
            op.part.save(update_fields=['quantity'])
            StockMovement.objects.create(
                part=op.part, movement_type='repair',
                quantity=-op.quantity,
                comment=f'Списано по заказу {repair.order_number}',
                created_by=request.user,
            )

        PaymentRecord.objects.create(
            repair_order=repair,
            payment_type='repair',
            method=method,
            amount=repair.final_cost,
            branch=repair.branch,
            created_by=request.user,
        )

        # Начислить зарплату мастеру
        if repair.assigned_to:
            try:
                profile = repair.assigned_to.profile
                if profile.repair_percent > 0:
                    bonus = repair.profit * profile.repair_percent / 100
                    PayrollRecord.objects.create(
                        employee=repair.assigned_to,
                        record_type='repair_bonus',
                        amount=bonus,
                        description=f'Бонус за заказ {repair.order_number}',
                        repair_order=repair,
                        period_year=timezone.now().year,
                        period_month=timezone.now().month,
                        created_by=request.user,
                    )
            except UserProfile.DoesNotExist:
                pass

        OrderHistory.objects.create(
            order=repair, event_type='payment',
            description=f'Оплачено {repair.final_cost} ₽ ({dict(PaymentRecord.PAYMENT_METHODS)[method]})',
            user=request.user,
        )

    messages.success(request, f'Заказ {repair.order_number} оплачен и выдан')
    return redirect('crm:repair_detail', pk)


@crm_required
def repair_print(request, pk):
    repair = get_object_or_404(
        RepairOrder.objects.select_related(
            'customer', 'brand', 'phone_model', 'assigned_to', 'created_by'
        ).prefetch_related('order_services', 'order_parts__part'),
        pk=pk,
    )
    site_settings = SiteSettings.get()

    # Determine document type
    doc_type = request.GET.get('type', '')
    if not doc_type:
        # Auto-select based on status
        if repair.status in ('done', 'issued'):
            doc_type = 'work_act'
        else:
            doc_type = 'receipt'

    valid_types = {'receipt', 'work_act', 'warranty', 'refusal', 'receipt_sale'}
    if doc_type not in valid_types:
        doc_type = 'receipt'

    return render(request, 'crm/repairs/print_act.html', {
        'repair': repair,
        'site_settings': site_settings,
        'today': timezone.now().date(),
        'doc_type': doc_type,
        'services': repair.order_services.all(),
        'parts': repair.order_parts.select_related('part').all(),
        'print_date': timezone.now(),
    })


# ─── WAREHOUSE: PARTS ─────────────────────────────────────────────────────────

@crm_required
def warehouse_parts(request):
    qs = Part.objects.select_related('brand', 'phone_model', 'supplier')
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if request.GET.get('brand'):
        qs = qs.filter(brand_id=request.GET['brand'])
    if request.GET.get('stock') == 'low':
        qs = [p for p in qs if p.is_low_stock]
    elif request.GET.get('stock') == 'out':
        qs = [p for p in qs if p.is_out_of_stock]

    all_parts = Part.objects.all()
    stats = {
        'total_parts': all_parts.count(),
        'stock_value': sum(p.stock_value for p in all_parts),
        'low_stock': sum(1 for p in all_parts if p.is_low_stock),
        'out_of_stock': sum(1 for p in all_parts if p.is_out_of_stock),
    }

    page = Paginator(qs if isinstance(qs, list) else list(qs), 30).get_page(request.GET.get('page'))
    return render(request, 'crm/warehouse/parts.html', {
        'parts': page,
        'stats': stats,
        'brands': Brand.objects.filter(is_active=True),
    })


@crm_required
def part_create(request):
    if request.method == 'POST':
        Part.objects.create(
            name=request.POST['name'],
            brand_id=request.POST.get('brand') or None,
            phone_model_id=request.POST.get('phone_model') or None,
            sku=request.POST.get('sku', ''),
            quantity=int(request.POST.get('quantity', 0)),
            min_quantity=int(request.POST.get('min_quantity', 1)),
            purchase_price=Decimal(request.POST.get('purchase_price', 0)),
            sale_price=Decimal(request.POST.get('sale_price', 0)),
            supplier_id=request.POST.get('supplier') or None,
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, 'Запчасть добавлена')
        return redirect('crm:warehouse_parts')
    return render(request, 'crm/warehouse/part_form.html', {
        'brands': Brand.objects.filter(is_active=True),
        'suppliers': Supplier.objects.filter(is_active=True),
    })


@crm_required
def part_edit(request, pk):
    part = get_object_or_404(Part, pk=pk)
    if request.method == 'POST':
        part.name = request.POST['name']
        part.brand_id = request.POST.get('brand') or None
        part.phone_model_id = request.POST.get('phone_model') or None
        part.sku = request.POST.get('sku', '')
        part.min_quantity = int(request.POST.get('min_quantity', 1))
        part.purchase_price = Decimal(request.POST.get('purchase_price', 0))
        part.sale_price = Decimal(request.POST.get('sale_price', 0))
        part.supplier_id = request.POST.get('supplier') or None
        part.notes = request.POST.get('notes', '')
        part.save()
        messages.success(request, 'Запчасть обновлена')
        return redirect('crm:warehouse_parts')
    return render(request, 'crm/warehouse/part_form.html', {
        'part': part,
        'brands': Brand.objects.filter(is_active=True),
        'suppliers': Supplier.objects.filter(is_active=True),
    })


@crm_required
@require_POST
def part_stock_in(request, pk):
    part = get_object_or_404(Part, pk=pk)
    qty = int(request.POST.get('quantity', 0))
    price = Decimal(request.POST.get('price', 0))
    comment = request.POST.get('comment', '')
    if qty > 0:
        part.quantity += qty
        if price:
            part.purchase_price = price
        part.save(update_fields=['quantity', 'purchase_price'])
        StockMovement.objects.create(
            part=part, movement_type='in', quantity=qty,
            unit_price=price, comment=comment, created_by=request.user,
        )
        messages.success(request, f'Поступление {qty} шт. "{part.name}"')
    return redirect('crm:warehouse_parts')


@crm_required
@require_POST
def part_stock_out(request, pk):
    part = get_object_or_404(Part, pk=pk)
    qty = int(request.POST.get('quantity', 0))
    comment = request.POST.get('comment', '')
    if qty > 0 and part.quantity >= qty:
        part.quantity -= qty
        part.save(update_fields=['quantity'])
        StockMovement.objects.create(
            part=part, movement_type='out', quantity=-qty,
            comment=comment, created_by=request.user,
        )
        messages.success(request, f'Списано {qty} шт. "{part.name}"')
    else:
        messages.error(request, 'Недостаточно на складе')
    return redirect('crm:warehouse_parts')


@crm_required
def warehouse_accessories(request):
    qs = Accessory.objects.select_related('supplier')
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if request.GET.get('category'):
        qs = qs.filter(category=request.GET['category'])
    page = Paginator(qs, 30).get_page(request.GET.get('page'))
    return render(request, 'crm/warehouse/accessories.html', {
        'accessories': page,
        'categories': Accessory.CATEGORIES,
    })


@crm_required
def accessory_create(request):
    if request.method == 'POST':
        Accessory.objects.create(
            name=request.POST['name'],
            category=request.POST.get('category', 'other'),
            sku=request.POST.get('sku', ''),
            compatible_with=request.POST.get('compatible_with', ''),
            quantity=int(request.POST.get('quantity', 0)),
            min_quantity=int(request.POST.get('min_quantity', 2)),
            purchase_price=Decimal(request.POST.get('purchase_price', 0)),
            sale_price=Decimal(request.POST.get('sale_price', 0)),
            supplier_id=request.POST.get('supplier') or None,
        )
        messages.success(request, 'Аксессуар добавлен')
        return redirect('crm:warehouse_accessories')
    return render(request, 'crm/warehouse/accessory_form.html', {
        'categories': Accessory.CATEGORIES,
        'suppliers': Supplier.objects.filter(is_active=True),
    })


@crm_required
def accessory_edit(request, pk):
    acc = get_object_or_404(Accessory, pk=pk)
    if request.method == 'POST':
        acc.name = request.POST['name']
        acc.category = request.POST.get('category', 'other')
        acc.sku = request.POST.get('sku', '')
        acc.compatible_with = request.POST.get('compatible_with', '')
        acc.min_quantity = int(request.POST.get('min_quantity', 2))
        acc.purchase_price = Decimal(request.POST.get('purchase_price', 0))
        acc.sale_price = Decimal(request.POST.get('sale_price', 0))
        acc.supplier_id = request.POST.get('supplier') or None
        acc.save()
        messages.success(request, 'Аксессуар обновлён')
        return redirect('crm:warehouse_accessories')
    return render(request, 'crm/warehouse/accessory_form.html', {
        'accessory': acc,
        'categories': Accessory.CATEGORIES,
        'suppliers': Supplier.objects.filter(is_active=True),
    })


@crm_required
@require_POST
def accessory_stock_in(request, pk):
    acc = get_object_or_404(Accessory, pk=pk)
    qty = int(request.POST.get('quantity', 0))
    if qty > 0:
        acc.quantity += qty
        acc.save(update_fields=['quantity'])
        StockMovement.objects.create(
            accessory=acc, movement_type='in', quantity=qty,
            comment=request.POST.get('comment', ''), created_by=request.user,
        )
        messages.success(request, f'Поступление {qty} шт.')
    return redirect('crm:warehouse_accessories')


@crm_required
def stock_movements(request):
    qs = StockMovement.objects.select_related('part', 'accessory', 'created_by').order_by('-created_at')
    if request.GET.get('type'):
        qs = qs.filter(movement_type=request.GET['type'])
    page = Paginator(qs, 50).get_page(request.GET.get('page'))
    return render(request, 'crm/warehouse/movements.html', {
        'movements': page,
        'movement_types': StockMovement.MOVEMENT_TYPES,
    })


@crm_required
def supplier_list(request):
    suppliers = Supplier.objects.filter(is_active=True)
    return render(request, 'crm/warehouse/suppliers.html', {'suppliers': suppliers})


# ─── SALES ────────────────────────────────────────────────────────────────────

@crm_required
def sale_list(request):
    qs = SaleOrder.objects.select_related('created_by', 'branch').order_by('-created_at')
    page = Paginator(qs, 30).get_page(request.GET.get('page'))
    return render(request, 'crm/sales/list.html', {'sales': page})


@crm_required
def sale_create(request):
    # Создаём черновик и сразу открываем кассу
    sale = SaleOrder.objects.create(
        created_by=request.user,
        payment_method=request.POST.get('payment_method', 'cash') if request.method == 'POST' else 'cash',
    )
    return redirect('crm:sale_detail', sale.pk)


@crm_required
def sale_detail(request, pk):
    sale = get_object_or_404(
        SaleOrder.objects.prefetch_related('items__accessory').select_related('created_by'),
        pk=pk,
    )
    if request.method == 'POST' and not sale.is_finalized:
        action = request.POST.get('action')
        if action == 'add_item':
            acc_id = request.POST.get('accessory_id')
            qty = int(request.POST.get('quantity', 1))
            price = request.POST.get('price')
            if acc_id:
                try:
                    acc = Accessory.objects.get(pk=acc_id)
                    price = Decimal(price) if price else acc.sale_price
                    SaleOrderItem.objects.create(
                        order=sale, accessory=acc,
                        quantity=qty, price=price,
                    )
                    sale.recalculate_total()
                except (Accessory.DoesNotExist, Exception):
                    messages.error(request, 'Ошибка добавления товара')
        elif action == 'set_payment':
            sale.payment_method = request.POST.get('payment_method', 'cash')
            sale.save(update_fields=['payment_method'])
        return redirect('crm:sale_detail', pk)

    accessories = Accessory.objects.filter(quantity__gt=0).order_by('category', 'name')
    return render(request, 'crm/sales/detail.html', {
        'sale': sale,
        'accessories': accessories,
        'payment_methods': SaleOrder._meta.get_field('payment_method').choices,
    })


@crm_required
@require_POST
def sale_remove_item(request, pk, item_pk):
    sale = get_object_or_404(SaleOrder, pk=pk)
    get_object_or_404(SaleOrderItem, pk=item_pk, order=sale).delete()
    sale.recalculate_total()
    return redirect('crm:sale_detail', pk)


@crm_required
@require_POST
def sale_finalize(request, pk):
    sale = get_object_or_404(SaleOrder, pk=pk)
    if sale.is_finalized:
        messages.warning(request, 'Продажа уже завершена')
        return redirect('crm:sale_detail', pk)
    with transaction.atomic():
        for item in sale.items.select_related('accessory').all():
            acc = item.accessory
            if acc.quantity < item.quantity:
                messages.error(request, f'Недостаточно "{acc.name}" на складе')
                return redirect('crm:sale_detail', pk)
            acc.quantity -= item.quantity
            acc.save(update_fields=['quantity'])
            StockMovement.objects.create(
                accessory=acc, movement_type='sale',
                quantity=-item.quantity,
                comment=f'Продажа {sale.order_number}',
                created_by=request.user,
            )
        sale.is_finalized = True
        sale.save(update_fields=['is_finalized'])
        PaymentRecord.objects.create(
            sale_order=sale, payment_type='sale',
            method=sale.payment_method, amount=sale.total,
            created_by=request.user,
        )
        messages.success(request, f'Продажа {sale.order_number} завершена')
    return redirect('crm:sale_detail', pk)


# ─── FINANCE ──────────────────────────────────────────────────────────────────

@crm_required
def finance(request):
    now = timezone.now()
    month_start = now.date().replace(day=1)

    payments = PaymentRecord.objects.select_related(
        'repair_order', 'sale_order', 'created_by'
    ).order_by('-created_at')[:100]

    expenses = Expense.objects.order_by('-created_at')[:50]
    payroll_records = PayrollRecord.objects.select_related(
        'employee', 'repair_order'
    ).order_by('-created_at')[:50]

    revenue_month = PaymentRecord.objects.filter(
        created_at__date__gte=month_start,
        payment_type__in=['repair', 'sale'],
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    expenses_month = Expense.objects.filter(
        date__gte=month_start
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    profit_month = revenue_month - expenses_month

    stats = {
        'revenue_month': revenue_month,
        'profit_month': profit_month,
        'expenses_month': expenses_month,
        'cash_balance': PaymentRecord.objects.filter(
            method='cash'
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0'),
    }

    # ── Зарплата к выплате: агрегация по сотрудникам ──
    all_payroll = PayrollRecord.objects.select_related('employee').order_by(
        'employee__last_name', 'employee__first_name'
    )
    emp_map = {}
    for rec in all_payroll:
        uid = rec.employee_id
        if uid not in emp_map:
            try:
                role_display = rec.employee.profile.get_role_display()
            except Exception:
                role_display = '—'
            emp_map[uid] = {
                'employee_pk': uid,
                'name': rec.employee.get_full_name() or rec.employee.username,
                'role_display': role_display,
                'accrued': Decimal('0'),
                'penalties': Decimal('0'),
            }
        if rec.record_type == 'penalty':
            emp_map[uid]['penalties'] += rec.amount
        else:
            emp_map[uid]['accrued'] += rec.amount

    payroll_summary = []
    total_accrued = Decimal('0')
    total_penalties = Decimal('0')
    for row in emp_map.values():
        row['net'] = row['accrued'] - row['penalties']
        total_accrued += row['accrued']
        total_penalties += row['penalties']
        payroll_summary.append(row)
    payroll_total = total_accrued - total_penalties

    from crm.decorators import get_role
    current_role = get_role(request.user)

    # For admin: pass list of all employees for payroll management
    all_employees = []
    if current_role == 'admin':
        from django.contrib.auth.models import User as AuthUser
        all_employees = AuthUser.objects.filter(is_active=True).select_related('profile').order_by(
            'last_name', 'first_name'
        )

    return render(request, 'crm/finance/index.html', {
        'stats': stats,
        'payments': payments,
        'expenses': expenses,
        'payroll_records': payroll_records,
        'payroll_summary': payroll_summary,
        'payroll_total': payroll_total,
        'payroll_total_accrued': total_accrued,
        'payroll_total_penalties': total_penalties,
        'month_label': month_start.strftime('%B %Y'),
        'all_employees': all_employees,
    })


@crm_required
@require_POST
def expense_create(request):
    Expense.objects.create(
        category=request.POST.get('category', 'other'),
        description=request.POST.get('description', ''),
        amount=Decimal(request.POST.get('amount', 0)),
        date=request.POST.get('date') or timezone.now().date(),
        created_by=request.user,
    )
    messages.success(request, 'Расход добавлен')
    return redirect('crm:finance')


@crm_required
def payroll_my(request):
    now = timezone.now()
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))

    records = PayrollRecord.objects.filter(
        employee=request.user, period_year=year, period_month=month
    ).order_by('-created_at')

    total = records.aggregate(
        income=Sum('amount', filter=~Q(record_type='penalty')),
        penalty=Sum('amount', filter=Q(record_type='penalty')),
    )
    net = (total['income'] or Decimal('0')) - (total['penalty'] or Decimal('0'))

    # Build last 6 months for selector
    month_range = []
    for i in range(5, -1, -1):
        from datetime import date
        import calendar
        d = now.date().replace(day=1)
        # Go back i months
        m = d.month - i
        y = d.year
        while m <= 0:
            m += 12
            y -= 1
        month_range.append({
            'year': y, 'month': m,
            'label': date(y, m, 1).strftime('%b %Y'),
        })

    return render(request, 'crm/finance/payroll_my.html', {
        'records': records,
        'year': year, 'month': month,
        'net': net,
        'income': total['income'] or Decimal('0'),
        'penalty': total['penalty'] or Decimal('0'),
        'month_range': month_range,
    })


@crm_required
@admin_required
def payroll_employee(request, employee_pk):
    """Admin view: detailed payroll for a specific employee."""
    from django.contrib.auth.models import User as AuthUser
    from datetime import date as date_type
    emp = get_object_or_404(AuthUser, pk=employee_pk)
    now = timezone.now()
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))

    records = PayrollRecord.objects.filter(
        employee=emp, period_year=year, period_month=month
    ).order_by('-created_at')

    total = records.aggregate(
        income=Sum('amount', filter=~Q(record_type='penalty')),
        penalty=Sum('amount', filter=Q(record_type='penalty')),
    )
    net = (total['income'] or Decimal('0')) - (total['penalty'] or Decimal('0'))

    month_range = []
    for i in range(5, -1, -1):
        d = now.date().replace(day=1)
        m = d.month - i
        y = d.year
        while m <= 0:
            m += 12
            y -= 1
        month_range.append({'year': y, 'month': m, 'label': date_type(y, m, 1).strftime('%b %Y')})

    return render(request, 'crm/finance/payroll_employee.html', {
        'emp': emp,
        'records': records,
        'year': year, 'month': month,
        'net': net,
        'income': total['income'] or Decimal('0'),
        'penalty': total['penalty'] or Decimal('0'),
        'month_range': month_range,
    })


@crm_required
@admin_required
@require_POST
def payroll_add_record(request, employee_pk):
    """Admin: add a payroll record (penalty, bonus, salary) for any employee."""
    from django.contrib.auth.models import User as AuthUser
    emp = get_object_or_404(AuthUser, pk=employee_pk)
    now = timezone.now()

    record_type = request.POST.get('record_type', 'penalty')
    valid_types = {'repair_bonus', 'sale_bonus', 'base_salary', 'bonus', 'penalty'}
    if record_type not in valid_types:
        record_type = 'penalty'

    amount_raw = str(request.POST.get('amount', '0')).replace(',', '.')
    try:
        amount = Decimal(amount_raw)
    except Exception:
        amount = Decimal('0')

    description = request.POST.get('description', '').strip()
    year = int(request.POST.get('year', now.year))
    month = int(request.POST.get('month', now.month))

    PayrollRecord.objects.create(
        employee=emp,
        record_type=record_type,
        amount=amount,
        description=description,
        period_year=year,
        period_month=month,
        created_by=request.user,
    )

    # Уведомление сотруднику при штрафе
    if record_type == 'penalty':
        issuer = request.user.get_full_name() or request.user.username
        msg = description if description else 'Без комментария'
        Notification.objects.create(
            user=emp,
            notification_type='penalty',
            title=f'Штраф на {amount} ₽',
            message=f'Выписал: {issuer}. Причина: {msg}',
            link='',
        )

    type_label = dict(PayrollRecord.RECORD_TYPES).get(record_type, record_type)
    messages.success(request, f'Запись «{type_label}» на {amount} ₽ добавлена для {emp.get_full_name() or emp.username}')
    return redirect('crm:payroll_employee', employee_pk=emp.pk)


# ─── ANALYTICS ────────────────────────────────────────────────────────────────

@crm_required
def analytics(request):
    period = request.GET.get('period', '30')
    now = timezone.now().date()

    period_map = {'7': 7, '30': 30, '90': 90, '365': 365}
    days_back = period_map.get(period, 30)
    date_from = now - timedelta(days=days_back)

    orders_qs = RepairOrder.objects.filter(created_at__date__gte=date_from)
    paid_qs = RepairOrder.objects.filter(paid_at__date__gte=date_from, is_paid=True)

    revenue = paid_qs.aggregate(t=Sum('final_cost'))['t'] or Decimal('0')
    cost = paid_qs.aggregate(t=Sum('cost_price'))['t'] or Decimal('0')
    profit = revenue - cost
    count = paid_qs.count()
    avg_check = revenue / count if count else Decimal('0')
    margin = (profit / revenue * 100) if revenue else Decimal('0')

    # Chart data
    days = [now - timedelta(days=i) for i in range(days_back - 1, -1, -1)]
    if days_back > 30:
        # Weekly buckets
        chart_labels = [d.strftime('%d %b') for d in days[::7]]
        chart_revenue, chart_profit = [], []
        for i in range(0, len(days), 7):
            week = days[i:i+7]
            rev = sum(
                float(PaymentRecord.objects.filter(
                    created_at__date=d, payment_type__in=['repair', 'sale']
                ).aggregate(t=Sum('amount'))['t'] or 0) for d in week
            )
            prf = sum(
                float((RepairOrder.objects.filter(paid_at__date=d, is_paid=True)
                       .aggregate(p=Sum('final_cost') - Sum('cost_price'))['p']) or 0)
                for d in week
            )
            chart_revenue.append(rev)
            chart_profit.append(prf)
    else:
        chart_labels = [d.strftime('%d %b') for d in days]
        chart_revenue, chart_profit = [], []
        for d in days:
            rev = float(PaymentRecord.objects.filter(
                created_at__date=d, payment_type__in=['repair', 'sale']
            ).aggregate(t=Sum('amount'))['t'] or 0)
            prf = float((RepairOrder.objects.filter(paid_at__date=d, is_paid=True)
                         .aggregate(p=Sum('final_cost') - Sum('cost_price'))['p']) or 0)
            chart_revenue.append(rev)
            chart_profit.append(prf)

    # Payment methods
    method_data = []
    labels_map = dict(PaymentRecord.PAYMENT_METHODS)
    for method, label in PaymentRecord.PAYMENT_METHODS:
        amt = PaymentRecord.objects.filter(
            method=method, created_at__date__gte=date_from
        ).aggregate(t=Sum('amount'))['t'] or 0
        method_data.append({'label': label, 'amount': float(amt)})

    # Top repairs
    top_repairs = (
        RepairOrderService.objects.filter(order__paid_at__date__gte=date_from)
        .values('name')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')[:8]
    )

    # Top devices
    top_devices = (
        paid_qs.values('phone_model__name')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')[:8]
    )

    # Top masters
    top_masters = User.objects.filter(
        assigned_repairs__is_paid=True,
        assigned_repairs__paid_at__date__gte=date_from,
    ).annotate(
        orders_count=Count('assigned_repairs'),
        total_revenue=Sum('assigned_repairs__final_cost'),
        total_profit=Sum('assigned_repairs__final_cost') - Sum('assigned_repairs__cost_price'),
    ).order_by('-total_profit')[:5]

    # Accessory sales by category
    accessory_sales = []
    for val, label in Accessory.CATEGORIES:
        items = SaleOrderItem.objects.filter(
            accessory__category=val,
            order__is_finalized=True,
            order__created_at__date__gte=date_from,
        )
        total_qty = items.aggregate(t=Sum('quantity'))['t'] or 0
        total_rev = float(sum(
            (i.price * i.quantity) for i in items.select_related()
        ))
        if total_qty:
            accessory_sales.append({
                'category_label': label,
                'total_qty': total_qty,
                'total_revenue': total_rev,
                'total_profit': 0,
            })

    repair_profit = float(profit)
    acc_profit = float(SaleOrder.objects.filter(
        is_finalized=True, created_at__date__gte=date_from
    ).aggregate(t=Sum('total') - Sum('cost_price'))['t'] or 0)

    period_labels = {
        'revenue': revenue, 'profit': profit,
        'orders_count': count, 'avg_check': avg_check, 'margin': margin,
    }

    return render(request, 'crm/analytics/index.html', {
        'stats': period_labels,
        'current_period': period,
        'period_label': f'Последние {days_back} дней',
        'period_options': [('7', '7 дней'), ('30', '30 дней'), ('90', '3 месяца'), ('365', 'Год')],
        'branches': Branch.objects.filter(is_active=True),
        'current_branch': request.GET.get('branch', ''),
        'chart_labels': chart_labels,
        'chart_revenue': chart_revenue,
        'chart_profit': chart_profit,
        'payment_methods_data': method_data,
        'payment_labels': [m['label'] for m in method_data],
        'payment_values': [m['amount'] for m in method_data],
        'top_repairs_labels': [r['name'] for r in top_repairs],
        'top_repairs_values': [r['cnt'] for r in top_repairs],
        'device_labels': [d['phone_model__name'] for d in top_devices],
        'device_values': [d['cnt'] for d in top_devices],
        'top_masters': top_masters,
        'accessory_sales': accessory_sales,
        'profit_type_values': [repair_profit, acc_profit],
    })


# ─── TASKS ────────────────────────────────────────────────────────────────────

@crm_required
def task_list(request):
    qs = Task.objects.select_related('assigned_to', 'created_by', 'repair_order')
    profile = getattr(request.user, 'profile', None)
    if profile and profile.role == 'master':
        qs = qs.filter(assigned_to=request.user)
    if request.GET.get('status'):
        qs = qs.filter(status=request.GET['status'])
    page = Paginator(qs, 30).get_page(request.GET.get('page'))
    return render(request, 'crm/tasks/list.html', {
        'tasks': page,
        'status_choices': Task.STATUS_CHOICES,
    })


@crm_required
@require_POST
def task_create(request):
    Task.objects.create(
        title=request.POST['title'],
        description=request.POST.get('description', ''),
        priority=request.POST.get('priority', 'medium'),
        assigned_to_id=request.POST.get('assigned_to') or None,
        due_date=request.POST.get('due_date') or None,
        created_by=request.user,
    )
    messages.success(request, 'Задача создана')
    return redirect('crm:task_list')


@crm_required
@require_POST
def task_update_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.status = request.POST.get('status', task.status)
    task.save(update_fields=['status'])
    return redirect('crm:task_list')


# ─── EMPLOYEES ────────────────────────────────────────────────────────────────

@crm_required
@manager_required
def employee_list(request):
    users = User.objects.select_related('profile').filter(
        profile__is_active=True
    ).order_by('first_name', 'last_name')
    return render(request, 'crm/employees/list.html', {'employees': users})


@crm_required
@manager_required
def employee_create(request):
    if request.method == 'POST':
        with transaction.atomic():
            username = request.POST['username']
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Пользователь с таким логином уже существует')
                return redirect('crm:employee_create')
            user = User.objects.create_user(
                username=username,
                password=request.POST['password'],
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                email=request.POST.get('email', ''),
            )
            UserProfile.objects.create(
                user=user,
                role=request.POST.get('role', 'employee'),
                phone=request.POST.get('phone', ''),
                repair_percent=Decimal(request.POST.get('repair_percent') or '0'),
                accessory_percent=Decimal(request.POST.get('accessory_percent') or '0'),
                base_salary=Decimal(request.POST.get('base_salary') or '0'),
                branch_id=request.POST.get('branch') or None,
            )
            messages.success(request, f'Сотрудник {user.get_full_name()} создан')
            return redirect('crm:employee_list')
    return render(request, 'crm/employees/form.html', {
        'roles': UserProfile.ROLES,
        'branches': Branch.objects.filter(is_active=True),
    })


@crm_required
@manager_required
def employee_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile = getattr(user, 'profile', None)
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save(update_fields=['first_name', 'last_name', 'email'])
        if profile:
            profile.role = request.POST.get('role', 'employee')
            profile.phone = request.POST.get('phone', '')
            profile.repair_percent = Decimal(request.POST.get('repair_percent') or '0')
            profile.accessory_percent = Decimal(request.POST.get('accessory_percent') or '0')
            profile.base_salary = Decimal(request.POST.get('base_salary') or '0')
            profile.branch_id = request.POST.get('branch') or None
            profile.save()
        messages.success(request, 'Сотрудник обновлён')
        return redirect('crm:employee_list')
    return render(request, 'crm/employees/form.html', {
        'employee': user, 'profile': profile,
        'roles': UserProfile.ROLES,
        'branches': Branch.objects.filter(is_active=True),
    })


# ─── NOTIFICATIONS ────────────────────────────────────────────────────────────

@crm_required
def notifications(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    page = Paginator(notifs, 30).get_page(request.GET.get('page'))
    return render(request, 'crm/notifications/list.html', {'notifications': page})


# ─── SETTINGS ─────────────────────────────────────────────────────────────────

@crm_required
@admin_required
def settings_company(request):
    settings_obj = SiteSettings.get()
    if request.method == 'POST':
        settings_obj.company_name = request.POST.get('company_name', settings_obj.company_name)
        settings_obj.phone = request.POST.get('phone', settings_obj.phone)
        settings_obj.working_hours = request.POST.get('working_hours', settings_obj.working_hours)
        for field in ['inn', 'kpp', 'ogrn', 'director_name', 'email', 'website',
                      'telegram', 'whatsapp', 'legal_address', 'actual_address',
                      'bank_name', 'bik', 'account_number', 'corr_account',
                      'warranty_days']:
            if hasattr(settings_obj, field):
                setattr(settings_obj, field, request.POST.get(field, ''))
        if 'logo' in request.FILES:
            settings_obj.logo = request.FILES['logo']
        if 'stamp' in request.FILES:
            settings_obj.stamp = request.FILES['stamp']
        settings_obj.save()
        messages.success(request, 'Настройки сохранены')
        return redirect('crm:settings_company')

    settings_tabs = [
        ('company', 'Компания', '#'),
        ('branches', 'Филиалы', '#'),
        ('employees', 'Сотрудники', '#'),
        ('security', 'Безопасность', '#'),
        ('documents', 'Печатные формы', '#'),
        ('notifications', 'Уведомления', '#'),
    ]

    return render(request, 'crm/settings/company.html', {
        'settings': settings_obj,
        'current_tab': 'company',
        'settings_tabs': settings_tabs,
    })


# ─── DOCUMENTS ────────────────────────────────────────────────────────────────

@crm_required
def document_blank_print(request, doc_type):
    """Print a blank (empty) form template."""
    valid_types = {'receipt', 'work_act', 'warranty', 'refusal', 'receipt_sale'}
    if doc_type not in valid_types:
        doc_type = 'receipt'
    site_settings = SiteSettings.get()
    return render(request, 'crm/repairs/print_blank.html', {
        'doc_type': doc_type,
        'site_settings': site_settings,
        'today': timezone.now().date(),
        'print_date': timezone.now(),
    })


@crm_required
def document_list(request):
    repairs = RepairOrder.objects.select_related(
        'customer', 'brand', 'phone_model'
    ).order_by('-created_at')[:20]
    doc_types = [
        ('receipt', '📄', 'Акт приёма-передачи', 'indigo'),
        ('work_act', '🔧', 'Акт выполненных работ', 'blue'),
        ('warranty', '🛡', 'Гарантийный талон', 'green'),
        ('refusal', '❌', 'Акт отказа от ремонта', 'red'),
        ('receipt_sale', '🧾', 'Товарный чек', 'yellow'),
    ]
    return render(request, 'crm/documents/list.html', {
        'recent_orders': repairs,
        'doc_types': doc_types,
    })


# ─── CALL REQUESTS ────────────────────────────────────────────────────────────

@crm_required
def call_request_list(request):
    qs = CallRequest.objects.order_by('-created_at')
    if request.GET.get('status') == 'new':
        qs = qs.filter(is_processed=False)
    page = Paginator(qs, 30).get_page(request.GET.get('page'))
    return render(request, 'crm/call_requests/list.html', {'call_requests': page})


@crm_required
@require_POST
def call_request_update(request, pk):
    cr = get_object_or_404(CallRequest, pk=pk)
    cr.is_processed = True
    cr.processed_at = timezone.now()
    cr.result = request.POST.get('result', '')
    cr.save()
    messages.success(request, 'Заявка отмечена обработанной')
    return redirect('crm:call_request_list')


# ─── LEGACY ALIASES (keep old URL names working) ──────────────────────────────

part_list = warehouse_parts
user_list = employee_list
user_create = employee_create
user_edit = employee_edit
repair_update_status = repair_update_status
repair_update_assigned = repair_update_assigned


# ─── API ──────────────────────────────────────────────────────────────────────

def api_prices(request):
    services = RepairService.objects.filter(is_active=True).select_related('phone_model__brand').values(
        'id', 'name', 'price_from', 'price_to', 'phone_model__name', 'phone_model__brand__name'
    )
    return JsonResponse(list(services), safe=False)


def api_models_for_brand(request, brand_id):
    models = PhoneModel.objects.filter(brand_id=brand_id, is_active=True).values('id', 'name')
    return JsonResponse(list(models), safe=False)


# ─── Price List Editor ────────────────────────────────────────────────────────

@crm_required
@manager_required
def price_list(request):
    brands = Brand.objects.filter(is_active=True).prefetch_related(
        'phone_models__services'
    )
    selected_brand_id = request.GET.get('brand')
    try:
        selected_brand_id = int(selected_brand_id)
    except (TypeError, ValueError):
        selected_brand_id = brands.first().pk if brands.exists() else None

    selected_brand = None
    phone_models = []
    if selected_brand_id:
        selected_brand = Brand.objects.filter(pk=selected_brand_id).first()
        phone_models = PhoneModel.objects.filter(
            brand_id=selected_brand_id
        ).prefetch_related('services').order_by('order', 'name')

    return render(request, 'crm/prices/index.html', {
        'brands': brands,
        'selected_brand': selected_brand,
        'selected_brand_id': selected_brand_id,
        'phone_models': phone_models,
    })


@crm_required
@manager_required
def price_service_save(request):
    if request.method != 'POST':
        return redirect('crm:price_list')

    pk = request.POST.get('pk')
    model_id = request.POST.get('phone_model_id')
    name = request.POST.get('name', '').strip()
    price_from = request.POST.get('price_from', '').strip()
    price_to = request.POST.get('price_to', '').strip() or None
    duration = request.POST.get('duration', '1–2 часа').strip()
    is_popular = request.POST.get('is_popular') == '1'
    is_active = request.POST.get('is_active', '1') == '1'
    brand_id = request.POST.get('brand_id')

    if not name or not price_from or not model_id:
        messages.error(request, 'Заполните обязательные поля')
        return redirect(f"{request.build_absolute_uri('/crm/prices/')}?brand={brand_id}")

    try:
        price_from = int(price_from)
        price_to = int(price_to) if price_to else None
    except (ValueError, TypeError):
        messages.error(request, 'Некорректная цена')
        return redirect(f'/crm/prices/?brand={brand_id}')

    if pk:
        svc = get_object_or_404(RepairService, pk=pk)
        svc.phone_model_id = model_id
        svc.name = name
        svc.price_from = price_from
        svc.price_to = price_to
        svc.duration = duration
        svc.is_popular = is_popular
        svc.is_active = is_active
        svc.save()
        messages.success(request, f'Услуга «{name}» обновлена')
    else:
        RepairService.objects.create(
            phone_model_id=model_id,
            name=name,
            price_from=price_from,
            price_to=price_to,
            duration=duration,
            is_popular=is_popular,
            is_active=is_active,
        )
        messages.success(request, f'Услуга «{name}» добавлена')

    return redirect(f'/crm/prices/?brand={brand_id}')


@crm_required
@manager_required
def price_service_delete(request, pk):
    svc = get_object_or_404(RepairService, pk=pk)
    brand_id = request.POST.get('brand_id', '')
    svc.delete()
    messages.success(request, 'Услуга удалена')
    return redirect(f'/crm/prices/?brand={brand_id}')


@crm_required
@manager_required
def price_model_save(request):
    if request.method != 'POST':
        return redirect('crm:price_list')

    brand_id = request.POST.get('brand_id')
    name = request.POST.get('name', '').strip()
    if not name or not brand_id:
        messages.error(request, 'Укажите название модели')
        return redirect(f'/crm/prices/?brand={brand_id}')

    PhoneModel.objects.create(brand_id=brand_id, name=name)
    messages.success(request, f'Модель «{name}» добавлена')
    return redirect(f'/crm/prices/?brand={brand_id}')


@crm_required
@manager_required
def price_model_delete(request, pk):
    model = get_object_or_404(PhoneModel, pk=pk)
    brand_id = request.POST.get('brand_id', '')
    count = model.services.count()
    model.delete()
    messages.success(request, f'Модель удалена вместе с {count} услугами')
    return redirect(f'/crm/prices/?brand={brand_id}')


