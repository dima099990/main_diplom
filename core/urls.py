from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('prices/', views.prices, name='prices'),
    path('contacts/', views.contacts, name='contacts'),
    path('request/', views.contact_request, name='contact_request'),
]
