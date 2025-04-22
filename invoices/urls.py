from django.urls import path
from . import views
from django.shortcuts import redirect
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required

app_name = 'invoices'  

urlpatterns = [
    path('dashboard/', login_required(views.dashboard), name='dashboard'),
    path('create/', views.invoice_create, name='create'),
    path('<int:pk>/', views.invoice_detail, name='detail'),
    path('<int:pk>/edit/', views.invoice_update, name='edit'),
    path('<int:pk>/delete/', views.invoice_delete, name='delete'),
    path('<int:pk>/send/', views.send_invoice, name='send'),
    path('<int:pk>/activate/', views.invoice_profile_activate, name='invoice_profile_activate'),
    path('pdfgenerate/<str:invoice_id>/download/', views.invoice_pdf_view, name='download_invoice'),

    # PayPal Payment URL
    path('paypal_return/', views.paypal_return, name='paypal_return'),
    path('view/<str:uuid>/', views.customer_invoice_view, name='customer_view'),

    # Cashfree Payment URL
    path('cashfree-payment/<str:uuid>/', views.cashfree_payment, name='cashfree_payment'),
    path('cashfree-return/', views.cashfree_return, name='cashfree_return'),

    # Invoice Customer Url
    path('customer/', views.customer_list, name='customer_list'), 
    path('customer/<str:customer_id>/edit/', views.customer_edit, name='customer_edit'),
    path('customer/<str:customer_id>/delete/', views.customer_delete, name='customer_delete'),
    
    # Product URLs
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/edit/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
]
