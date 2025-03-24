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
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_sent = models.BooleanField(default=False, help_text='Indicates if the invoice has been sent to the customer')

    def __str__(self):
        return f"Invoice #{self.invoice_id} - {self.customer_name}"

    def calculate_total(self):
        return sum(item.total_price for item in self.items.all())

    def update_total(self):
        """Update total without triggering recursive saves"""
        self.total_amount = self.calculate_total()
        super().save(update_fields=['total_amount'])

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