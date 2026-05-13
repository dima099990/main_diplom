from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import SiteSettings, Brand, PhoneModel, RepairService, Review, CallRequest


def home(request):
    reviews = Review.objects.filter(is_active=True)[:6]
    popular_services = RepairService.objects.filter(is_popular=True, is_active=True).select_related('phone_model__brand')[:6]
    return render(request, 'core/home.html', {'reviews': reviews, 'popular_services': popular_services})


def about(request):
    return render(request, 'core/about.html')


def prices(request):
    brands = Brand.objects.filter(is_active=True).prefetch_related('phone_models__services')
    search_q = request.GET.get('q', '').strip()
    selected_model = request.GET.get('model', '')
    
    result = []
    for brand in brands:
        brand_models = []
        for model in brand.phone_models.filter(is_active=True):
            services = model.services.filter(is_active=True)
            if search_q:
                services = services.filter(
                    Q(name__icontains=search_q) | Q(phone_model__name__icontains=search_q)
                )
                if not services.exists() and search_q.lower() not in model.name.lower() and search_q.lower() not in brand.name.lower():
                    continue
            if selected_model and str(model.id) != selected_model:
                continue
            if services.exists() or not search_q:
                brand_models.append({'model': model, 'services': list(services)})
        if brand_models:
            result.append({'brand': brand, 'models': brand_models})
    
    all_models = PhoneModel.objects.filter(is_active=True).select_related('brand').order_by('brand__order','order','name')
    return render(request, 'core/prices.html', {
        'result': result, 'search_q': search_q,
        'selected_model': selected_model, 'all_models': all_models,
    })


def about_page(request):
    return render(request, 'core/about.html')


def contacts(request):
    return render(request, 'core/contacts.html')


def contact_request(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        message = request.POST.get('message', '').strip()
        if name and phone:
            CallRequest.objects.create(name=name, phone=phone, message=message)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': True})
            messages.success(request, 'Заявка отправлена! Мы свяжемся с вами.')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': 'Заполните имя и телефон'})
            messages.error(request, 'Заполните имя и телефон.')
    return redirect(request.META.get('HTTP_REFERER', '/'))
