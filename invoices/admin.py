from django.contrib import admin
from .models import Invoice, InvoiceItem

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_id', 'customer_name', 'customer_email', 'billing_date', 'due_date', 'status', 'total_amount', 'is_sent')
    list_filter = ('status', 'is_sent', 'billing_date', 'due_date')
    search_fields = ('invoice_id', 'customer_name', 'customer_email')
    readonly_fields = ('invoice_id', 'created_at', 'updated_at')
    date_hierarchy = 'billing_date'
    ordering = ('-created_at',)

@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'item', 'quantity', 'unit_price', 'total_price')
    list_filter = ('invoice__status',)
    search_fields = ('item', 'invoice__invoice_id')
    readonly_fields = ('total_price',) 