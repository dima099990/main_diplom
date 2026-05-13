from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from crm.views import api_prices, api_models_for_brand

urlpatterns = [
    path('admin/', admin.site.urls),
    path('crm/', include('crm.urls')),
    path('', include('core.urls')),
    path('api/prices/', api_prices, name='api_prices'),
    path('api/models/<int:brand_id>/', api_models_for_brand, name='api_models'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
