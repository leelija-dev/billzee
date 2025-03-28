from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail,  get_connection
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.utils.html import strip_tags
from .models import Invoice, InvoiceItem
from .forms import InvoiceForm, InvoiceItemFormSet
from users.models import Profile
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Q

@login_required
def dashboard(request):
    active_profile = Profile.objects.filter(user=request.user, is_active=True).first()
    if active_profile:
        invoices = Invoice.objects.filter(profile=active_profile)
        
        # Handle search
        search_query = request.GET.get('search', '')
        if search_query:
            invoices = invoices.filter(
                Q(invoice_id__icontains=search_query) |
                Q(customer_name__icontains=search_query)
            )
        
        # Handle sorting
        allowed_sort_fields = ['invoice_id', 'customer_name', 'total_amount', 'status', 'due_date']
        sort_by = request.GET.get('sort_by')
        order = request.GET.get('order', 'asc')
        if sort_by in allowed_sort_fields:
            ordering = sort_by if order == 'asc' else f"-{sort_by}"
        else:
            ordering = '-created_at'
        invoices = invoices.order_by(ordering)
    else:
        invoices = Invoice.objects.none()
    
    return render(request, 'invoices/dashboard.html', {
        'invoices': invoices,
        'active_profile': active_profile,
        'title': 'Dashboard'
    })

@login_required
def invoice_create(request):
    active_profile = Profile.objects.filter(user=request.user, is_active=True).first()
    if not active_profile:
        messages.warning(request, 'Please set up and activate a business profile before creating invoices.')
        return redirect('users:profile_list')

    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        # print(form)
        # return JsonResponse({'data': form.data})
        formset = InvoiceItemFormSet(request.POST, queryset=InvoiceItem.objects.none())
        # print(formset)
        # return JsonResponse({'data': formset.data})
        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.user = request.user
            invoice.profile = active_profile
            invoice.save()
            
            instances = formset.save(commit=False)
            for instance in instances:
                instance.invoice = invoice
                instance.save()
            
            messages.success(request, 'Invoice created successfully.')
            return redirect('invoices:detail', pk=invoice.pk)
    else:
        form = InvoiceForm()
        formset = InvoiceItemFormSet(queryset=InvoiceItem.objects.none())
    
    return render(request, 'invoices/invoice_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Create Invoice',
        'active_profile': active_profile
    })

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, profile__user=request.user)

    subtotal = invoice.subtotal_amount or 0
    gst_rate = invoice.gst_rate or 0

    gst_amount = (subtotal * gst_rate) / 100

    total_amount = subtotal + gst_amount

    return render(request, 'invoices/invoice_detail.html', {
        'invoice': invoice,
        'gst_amount': gst_amount,
        'total_amount': total_amount,
        'title': f'Invoice #{invoice.invoice_id}'
    })


@login_required
def invoice_update(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, profile__user=request.user)
    if request.method == 'POST':
        # return JsonResponse({'data':request.POST})
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, queryset=InvoiceItem.objects.filter(invoice=invoice))
        if form.is_valid() and formset.is_valid():
            form.save()
            instances = formset.save(commit=False)
            
            # Delete any removed items
            for obj in formset.deleted_objects:
                obj.delete()
            
            # Save new/updated items
            for instance in instances:
                instance.invoice = invoice
                instance.save()
            
            messages.success(request, 'Invoice updated successfully.')
            return redirect('invoices:detail', pk=pk)
    else:
        form = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(queryset=InvoiceItem.objects.filter(invoice=invoice))
    
    return render(request, 'invoices/invoice_form.html', {
        'form': form,
        'formset': formset,
        'invoice': invoice,
        'title': f'Edit Invoice #{invoice.invoice_id}',
        'active_profile': invoice.profile
    })

@login_required
def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, profile__user=request.user)
    if request.method == 'POST':
        invoice.delete()
        messages.success(request, 'Invoice deleted successfully.')
        return redirect('invoices:dashboard')
    return render(request, 'invoices/invoice_confirm_delete.html', {
        'invoice': invoice,
        'title': f'Delete Invoice #{invoice.invoice_id}'
    })

@login_required
def send_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, profile__user=request.user)
    if request.method == 'POST':
        # Generate customer view URL
        customer_url = request.build_absolute_uri(
            reverse('invoices:customer_view', kwargs={'uuid': invoice.invoice_id})
        )
        # Render email template
        email_html = render_to_string('invoices/email_invoice.html', {
            'invoice': invoice,
            'view_url': customer_url
        })
        # return JsonResponse({'data': invoice.profile.password})
        connection = get_connection(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=invoice.profile.company_email,
            password=invoice.profile.password,
            use_tls=settings.EMAIL_USE_TLS,
            # DEFAULT_FROM_EMAIL= 'jbleelija@gmail.com'
        )
        # return JsonResponse({'data': invoice.profile.company_email})
        # Send email
        send_mail(
            subject=f'Invoice #{invoice.invoice_id} from {invoice.profile.company_name}',
            message=strip_tags(email_html),
            # from_email=settings.DEFAULT_FROM_EMAIL,
            from_email=invoice.profile.company_email,
            recipient_list=[invoice.customer_email],
            html_message=email_html,
            fail_silently=False,
            connection=connection
        )
        
        messages.success(request, f'Invoice sent to {invoice.customer_email}')
    return redirect('invoices:detail', pk=pk)

def customer_invoice_view(request, uuid):
    invoice = get_object_or_404(Invoice, invoice_id=uuid)
    # if not invoice.is_sent:
    #     invoice.is_sent = True
    #     invoice.save()
    subtotal = invoice.subtotal_amount or 0
    gst_rate = invoice.gst_rate or 0
    gst_amount = (subtotal * gst_rate) / 100
    total_amount = subtotal + gst_amount

    if request.method == 'POST' and 'mark_paid' in request.POST:
        # Mark the invoice as paid
        invoice.status = 'completed'
        invoice.save()
        messages.success(request, 'Invoice marked as paid successfully.')
        # return redirect('invoices:detail', pk=invoice.pk)
        return render(request, 'invoices/customer_invoice_view.html', {
            'invoice': invoice,
            'gst_amount': gst_amount,
            'total_amount': total_amount,
            'title': f'Invoice #{invoice.invoice_id}'
        })
    return render(request, 'invoices/customer_invoice_view.html', {
        'invoice': invoice,
        'gst_amount': gst_amount,
        'total_amount': total_amount,
        'title': f'Invoice #{invoice.invoice_id}'
    })