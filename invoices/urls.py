from django.urls import path
from . import views
from django.shortcuts import redirect
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required

app_name = 'invoices'  

urlpatterns = [
    path('', login_required(RedirectView.as_view(url='/invoices/dashboard/'))),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.invoice_create, name='create'),
    path('<int:pk>/', views.invoice_detail, name='detail'),
    path('<int:pk>/edit/', views.invoice_update, name='edit'),
    path('<int:pk>/delete/', views.invoice_delete, name='delete'),
    path('<int:pk>/send/', views.send_invoice, name='send'),
    path('view/<str:uuid>/', views.customer_invoice_view, name='customer_view'),
]
