from django import forms
from django.forms import formset_factory, modelformset_factory
from .models import Invoice, InvoiceItem

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['customer_name', 'customer_email', 'billing_date', 'due_date', 'notes','status','gst_rate', 'currency']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'customer_email': forms.EmailInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'billing_date': forms.DateInput(attrs={'type': 'date', 'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'notes': forms.Textarea(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm', 'rows': 4}),
            'status': forms.HiddenInput(),
            'gst_rate': forms.HiddenInput(),
            'currency': forms.HiddenInput(),
        }

    def clean_status(self):
        status = self.cleaned_data.get('status')
        if not status:
            raise forms.ValidationError("Please select a status.")
        return status

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['item', 'quantity', 'unit_price']
        widgets = {
            'item': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm', 'placeholder': 'Item Name'}),
            'quantity': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm', 'min': '1', 'placeholder': 'Quantity'}),
            'unit_price': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm', 'min': '0', 'step': '0.01', 'placeholder': 'Unit price'})
        }

class BaseInvoiceItemFormSet(forms.BaseModelFormSet):
    def clean(self):
        if any(self.errors):
            return

        if not any(form.cleaned_data and not form.cleaned_data.get('DELETE', False)
                  for form in self.forms):
            raise forms.ValidationError('At least one item is required.')

InvoiceItemFormSet = modelformset_factory(
    InvoiceItem,
    form=InvoiceItemForm,
    formset=BaseInvoiceItemFormSet,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True
)