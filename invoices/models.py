from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
from django.contrib.auth.models import User
from django.conf import settings
from users.models import Profile
from .utils import generate_custom_invoice_id

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]

    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('INR', 'INR'),
        ('EUR', 'EUR'),
        ('GBP', 'GBP'),
        ('JPY', 'JPY'),
        ('AUD', 'AUD'),
        ('CAD', 'CAD'),
    ]

    invoice_id = models.CharField(max_length=19, editable=False, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.PROTECT, related_name='invoices', null=True, blank=True)
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    billing_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # stores total of items
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)         # GST percentage
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)    # final total including GST
    is_sent = models.BooleanField(default=False, help_text='Indicates if the invoice has been sent to the customer')

    def __str__(self):
        return f"Invoice #{self.invoice_id} - {self.customer_name}"

    def calculate_total(self):
        # return sum(item.total_price for item in self.items.all())
        return sum(item.total_price for item in self.items.all())

    def update_total(self):
        # """Update total without triggering recursive saves"""
        # self.total_amount = self.calculate_total()
        # super().save(update_fields=['total_amount'])
        total = self.calculate_total()
        self.subtotal_amount = total

        # Calculate GST amount if gst_rate is greater than 0
        gst_amount = (total * self.gst_rate) / 100 if self.gst_rate > 0 else 0

        final_total = total + gst_amount
        self.total_amount = final_total

        # Save only the updated fields to avoid recursive calls
        super().save(update_fields=['subtotal_amount', 'total_amount', 'gst_rate'])

    def save(self, *args, **kwargs):
        if not self.invoice_id:
            while True:
                new_id = generate_custom_invoice_id()
                if not Invoice.objects.filter(invoice_id=new_id).exists():
                    self.invoice_id = new_id
                    break
                    
        if not self.pk and not self.profile:  # Only for new invoices without profile
            try:
                self.profile = Profile.objects.get(user=self.user, is_active=True)
            except Profile.DoesNotExist:
                pass  # Allow creation without profile for now
        super().save(*args, **kwargs)

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    item = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        self.invoice.update_total()  # Use the new method to update invoice total

    def __str__(self):
        return f"{self.item} - {self.invoice.invoice_id}"