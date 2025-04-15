import json
import logging
import time
import warnings
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

import paypalrestsdk
from cashfree_pg.api_client import Cashfree
from cashfree_pg.models.customer_details import CustomerDetails
from cashfree_pg.models.create_link_request import CreateLinkRequest
from cashfree_pg.models.link_notify_entity import LinkNotifyEntity

from .forms import InvoiceForm, InvoiceItemFormSet
from .models import Invoice, InvoiceItem, InvoiceCustomer, Product
from .utils import render_to_pdf
from users.models import Profile

from cashfree_pg.models.create_order_request import CreateOrderRequest

logger = logging.getLogger(__name__)


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
    profiles = Profile.objects.filter(user=request.user)
    customers = InvoiceCustomer.objects.all().values_list('customer_name', 'customer_email', 'customer_contact', 'customer_address', 'customer_country', 'customer_zip', 'customer_state', 'customer_city').distinct().order_by('customer_name')
    # print(customers)
    latest_products = Product.objects.values('item_name').annotate(max_id=Max('invoice_item_id')).order_by()
    products = Product.objects.filter(invoice_item_id__in=[p['max_id'] for p in latest_products]).values_list('item_name', 'item_price', flat=False).order_by('item_name')
    # print(products)
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
        'active_profile': active_profile,
        'profiles': profiles,
        'customers': customers,
        'products': products,
        'latest_products': latest_products,
    })

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, profile__user=request.user)

    # Calculate original subtotal (before discounts)
    original_subtotal = sum(item.quantity * item.unit_price for item in invoice.items.all())
    
    # Calculate total discount from InvoiceItem table
    total_discount_rate = sum(int(item.discount) for item in invoice.items.all())

    total_discount = sum(
        (item.quantity * item.unit_price * item.discount) / Decimal('100')
        for item in invoice.items.all()
    )
    
    # Subtotal after discounts
    subtotal = original_subtotal - total_discount or Decimal('0')
    
    # GST rate and amount
    gst_rate = invoice.gst_rate or Decimal('0')
    gst_amount = (subtotal * gst_rate) / Decimal('100')
    
    # Total amount
    total_amount = subtotal + gst_amount

    return render(request, 'invoices/invoice_detail.html', {
        'invoice': invoice,
        'original_subtotal': original_subtotal,
        'total_discount': total_discount,
        'subtotal': subtotal,
        'gst_amount': gst_amount,
        'total_amount': total_amount,
        'total_discount_rate': total_discount_rate,
        'title': f'Invoice #{invoice.invoice_id}'
    })


@login_required
def invoice_update(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, profile__user=request.user)
    profiles = Profile.objects.filter(user=request.user)
    # customers = Invoice.objects.filter(profile=invoice.profile).values_list('customer_name', flat=True).distinct().order_by('customer_name')
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
        'active_profile': invoice.profile,
        'profiles': profiles,
        # 'customers': customers
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

@login_required
def customer_invoice_view(request, uuid):
    invoice = get_object_or_404(Invoice, invoice_id=uuid)

    # Auto-trigger payment if parameter exists
    if request.GET.get('initiate_payment') and request.method == 'GET':
        return render(request, 'invoices/customer_invoice_view.html', {
            'invoice': invoice,
            'auto_pay': True, 
        })
    
    original_subtotal = sum(item.quantity * item.unit_price for item in invoice.items.all())
    total_discount_rate = sum(int(item.discount) for item in invoice.items.all())
    total_discount = sum(
        (item.quantity * item.unit_price * item.discount) / Decimal('100')
        for item in invoice.items.all()
    )
    subtotal = original_subtotal - total_discount or Decimal('0')
    gst_rate = invoice.gst_rate or Decimal('0')
    gst_amount = (subtotal * gst_rate) / Decimal('100')
    total_amount = subtotal + gst_amount

    if request.method == 'POST' and 'mark_paid' in request.POST:

        # Configure PayPal SDK
        paypalrestsdk.configure({
            "mode": settings.PAYPAL_MODE,
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_SECRET
        })

        # Create PayPal payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": request.build_absolute_uri(
                    reverse('invoices:paypal_return') + f'?invoice_id={invoice.invoice_id}'
                ),
                "cancel_url": request.build_absolute_uri(
                    reverse('invoices:customer_view', kwargs={'uuid': invoice.invoice_id}) + '?cancelled=true'
                )
            },
            "transactions": [{
                "amount": {
                    "total": str(total_amount.quantize(Decimal('0.01'))),
                    # "currency": "USD"
                    "currency": invoice.currency
                },
                "description": f"Payment for Invoice #{invoice.invoice_id}"
            }]
        })

        if payment.create():
            invoice.paypal_payment_id = payment.id
            invoice.save()
            for link in payment.links:
                if link.rel == "approval_url":
                    return redirect(link.href)
        else:
            messages.error(request, f"Failed to create PayPal payment: {payment.error}")
            return render(request, 'invoices/customer_invoice_view.html', {
                'invoice': invoice,
                'original_subtotal': original_subtotal,
                'total_discount': total_discount,
                'subtotal': subtotal,
                'gst_amount': gst_amount,
                'total_amount': total_amount,
                'total_discount_rate': total_discount_rate,
                'title': f'Invoice #{invoice.invoice_id}',
                'PAYPAL_CLIENT_ID': settings.PAYPAL_CLIENT_ID,
                'currency': invoice.currency
            })

    if 'cancelled' in request.GET:
        messages.info(request, "Payment was cancelled.")

    return render(request, 'invoices/customer_invoice_view.html', {
        'invoice': invoice,
        'original_subtotal': original_subtotal,
        'total_discount': total_discount,
        'subtotal': subtotal,
        'gst_amount': gst_amount,
        'total_amount': total_amount,
        'total_discount_rate': total_discount_rate,
        'title': f'Invoice #{invoice.invoice_id}',
        'PAYPAL_CLIENT_ID': settings.PAYPAL_CLIENT_ID,
        'currency': invoice.currency
    })

def paypal_return(request):
    invoice_id = request.GET.get('invoice_id')
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')

    invoice = get_object_or_404(Invoice, invoice_id=invoice_id)

    # If required PayPal parameters are missing, treat it as a cancelled payment.
    if not payment_id or not payer_id:
        messages.info(request, "Payment was not completed.")
        return redirect('invoices:customer_view', uuid=invoice.invoice_id)

    if invoice.paypal_payment_id != payment_id:
        messages.error(request, "Invalid payment ID.")
        return redirect('invoices:customer_view', uuid=invoice.invoice_id)

    # Configure PayPal SDK
    paypalrestsdk.configure({
        "mode": settings.PAYPAL_MODE,
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_SECRET
    })

    payment = paypalrestsdk.Payment.find(payment_id)
    if payment.execute({"payer_id": payer_id}):
        if payment.state == "approved":
            invoice.status = 'completed'
            invoice.save()

            # Generate PDF and send emails (as before)
            original_subtotal = sum(item.quantity * item.unit_price for item in invoice.items.all())
            total_discount = sum(
                (item.quantity * item.unit_price * item.discount) / Decimal('100')
                for item in invoice.items.all()
            )
            subtotal = original_subtotal - total_discount or Decimal('0')
            gst_amount = (subtotal * invoice.gst_rate) / Decimal('100') if invoice.gst_rate else Decimal('0')
            total_amount = subtotal + gst_amount

            context = {
                'invoice': invoice,
                'original_subtotal': original_subtotal,
                'total_discount': total_discount,
                'total_discount_rate': sum(int(item.discount) for item in invoice.items.all()),
                'gst_amount': gst_amount,
                'total_amount': total_amount,
            }
            pdf = render_to_pdf('pdfgenerate/pdf_generate.html', context)

            if not pdf:
                messages.error(request, "PDF generation failed.")
                return redirect('invoices:customer_view', uuid=invoice.invoice_id)

            connection = get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=invoice.profile.company_email,
                password=invoice.profile.password,
                use_tls=settings.EMAIL_USE_TLS,
            )
            payment_date = timezone.now().date()
            subject = f'Payment Confirmation for Invoice #{invoice.invoice_id}'
            filename = f"Invoice_{invoice.invoice_id}.pdf"
            email_html = render_to_string('invoices/payment_confirmation.html', {
                'invoice': invoice,
                'total_amount': total_amount,
                'payment_date': payment_date,
            })

            # Send to customer
            customer_email = EmailMultiAlternatives(
                subject=subject,
                body=strip_tags(email_html),
                from_email=invoice.profile.company_email,
                to=[invoice.customer_email],
                connection=connection,
            )
            customer_email.attach_alternative(email_html, "text/html")
            customer_email.attach(filename, pdf, 'application/pdf')
            customer_email.send(fail_silently=False)

            # Send to profile
            merchant_email = EmailMultiAlternatives(
                subject=f'Payment Received - {subject}',
                body=strip_tags(email_html),
                from_email=invoice.profile.company_email,
                to=[invoice.profile.company_email],
                connection=connection,
            )
            merchant_email.attach_alternative(email_html, "text/html")
            merchant_email.attach(filename, pdf, 'application/pdf')
            merchant_email.send(fail_silently=False)

            messages.success(request, "Payment completed successfully.")
            redirect_url = reverse('invoices:customer_view', kwargs={'uuid': invoice.invoice_id}) + '?from_popup=1&success=1'
            return redirect(redirect_url)
        else:
            messages.error(request, "Payment not approved.")
    else:
        messages.error(request, "Payment execution failed.")

    return redirect('invoices:customer_view', uuid=invoice.invoice_id) 
    
# @login_required
def cashfree_payment(request, uuid):
    invoice = get_object_or_404(Invoice, invoice_id=uuid)
    
    # Calculate totals
    original_subtotal = sum(item.quantity * item.unit_price for item in invoice.items.all())
    total_discount = sum(
        (item.quantity * item.unit_price * item.discount) / Decimal('100')
        for item in invoice.items.all()
    )
    subtotal = original_subtotal - total_discount or Decimal('0')
    gst_amount = (subtotal * invoice.gst_rate) / Decimal('100') if invoice.gst_rate else Decimal('0')
    total_amount = subtotal + gst_amount

    # Configure Cashfree SDK
    Cashfree.XClientId = settings.CASHFREE_APP_ID
    Cashfree.XClientSecret = settings.CASHFREE_SECRET_KEY
    Cashfree.XEnvironment = Cashfree.SANDBOX  
    x_api_version = settings.CASHFREE_API_VERSION

    try:
        # Create unique order ID
        order_id = f"order_{uuid}_{int(time.time())}"
        
        # Create order request
        order_request = CreateOrderRequest(
            order_id=order_id,
            order_amount=float(total_amount.quantize(Decimal('0.01'))),
            order_currency=invoice.currency,
            customer_details=CustomerDetails(
                customer_id=str(uuid),
                customer_email=invoice.customer_email,
                customer_phone=invoice.customer_contact
            ),
            order_meta={
                "return_url": request.build_absolute_uri(
                    reverse('invoices:cashfree_return') + f'?invoice_id={uuid}'
                )
            }
        )

        # Create order
        order_response = Cashfree().PGCreateOrder(x_api_version, order_request)
        
        if order_response.status_code == 200:
            invoice.cashfree_order_id = order_id
            invoice.save()
            
            return JsonResponse({
                'payment_session_id': order_response.data.payment_session_id,
                'cashfree_mode': 'sandbox'  # Change to 'production' for live
            })
        
        return JsonResponse({'error': order_response.data.message}, status=400)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def cashfree_return(request):
    invoice_id = request.GET.get('invoice_id')
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id)

    Cashfree.XClientId = settings.CASHFREE_APP_ID
    Cashfree.XClientSecret = settings.CASHFREE_SECRET_KEY
    Cashfree.XEnvironment = Cashfree.SANDBOX  # Use PRODUCTION for live
    x_api_version = settings.CASHFREE_API_VERSION

    order_id = invoice.cashfree_order_id
    if not order_id:
        messages.error(request, "Invalid payment reference.")
        return redirect('invoices:customer_view', uuid=invoice_id)

    try:
        resp = Cashfree().PGFetchOrder(x_api_version, order_id)
        if resp.status_code != 200:
            logger.error("FetchOrder failed for %s: %s", order_id, resp.data)
            messages.error(request, "Could not verify payment status.")
            return redirect('invoices:customer_view', uuid=invoice_id)

        status = (getattr(resp.data, 'order_status', '') or '').upper()
        logger.info("Cashfree order %s status: %s", order_id, status)

        if status not in ('PAID', 'SUCCESS'):
            messages.error(request, f"Payment not successful (status: {status}).")
            return redirect('invoices:customer_view', uuid=invoice_id)

        invoice.status = 'completed'
        invoice.save(update_fields=['status'])
        messages.success(request, "Payment completed successfully!")

    except Exception as e:
        logger.exception("Exception while fetching Cashfree order %s: %s", order_id, str(e))
        messages.error(request, "An error occurred while verifying payment.")
        return redirect('invoices:customer_view', uuid=invoice_id)

    original_subtotal = sum(item.quantity * item.unit_price for item in invoice.items.all())
    total_discount = sum(
        (item.quantity * item.unit_price * item.discount) / Decimal('100')
        for item in invoice.items.all()
    )
    subtotal = original_subtotal - total_discount
    gst_amount = (subtotal * invoice.gst_rate) / Decimal('100') if invoice.gst_rate else Decimal('0')
    total_amount = subtotal + gst_amount

    pdf_context = {
        'invoice': invoice,
        'original_subtotal': original_subtotal,
        'total_discount': total_discount,
        'total_discount_rate': sum(item.discount for item in invoice.items.all()),
        'gst_amount': gst_amount,
        'total_amount': total_amount,
    }
    pdf_file = render_to_pdf('pdfgenerate/pdf_generate.html', pdf_context)
    if not pdf_file:
        messages.warning(request, "Payment succeeded but PDF generation failed.")
        return redirect('invoices:customer_view', uuid=invoice_id)

    try:
        connection = get_connection(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=invoice.profile.company_email,
            password=invoice.profile.password,
            use_tls=settings.EMAIL_USE_TLS,
        )
        payment_date = timezone.now().date()
        subject = f'Payment Confirmation for Invoice #{invoice.invoice_id}'
        filename = f"Invoice_{invoice.invoice_id}.pdf"
        email_html = render_to_string('invoices/payment_confirmation.html', {
            'invoice': invoice,
            'total_amount': total_amount,
            'payment_date': payment_date,
        })

        # Send to customer
        customer_email = EmailMultiAlternatives(
            subject=subject,
            body=strip_tags(email_html),
            from_email=invoice.profile.company_email,
            to=[invoice.customer_email],
            connection=connection,
        )
        customer_email.attach_alternative(email_html, "text/html")
        customer_email.attach(filename, pdf_file, 'application/pdf')  
        customer_email.send(fail_silently=False)

        # Send to merchant
        merchant_email = EmailMultiAlternatives(
            subject=f'Payment Received - {subject}',
            body=strip_tags(email_html),
            from_email=invoice.profile.company_email,
            to=[invoice.profile.company_email],
            connection=connection,
        )
        merchant_email.attach_alternative(email_html, "text/html")
        merchant_email.attach(filename, pdf_file, 'application/pdf')  
        merchant_email.send(fail_silently=False)

        messages.success(request, "Confirmation emails sent successfully.")
    except Exception as e:
        logger.exception(
            "Failed to send confirmation emails for invoice %s. "
            "SMTP Host: %s, Port: %s, Username: %s. Error: %s",
            invoice_id,
            settings.EMAIL_HOST,
            settings.EMAIL_PORT,
            invoice.profile.company_email,
            str(e)
        )
        messages.warning(
            request,
            "Payment succeeded, but failed to send confirmation emails. "
            "Please check your email settings in the profile."
        )

    return redirect('invoices:customer_view', uuid=invoice_id)


def invoice_profile_activate(request, pk):
    if request.method == 'POST':
        with transaction.atomic():
            # First, deactivate all profiles for this user
            Profile.objects.filter(user=request.user).update(is_active=False)
            # Then activate the selected profile
            profile = get_object_or_404(Profile, pk=pk, user=request.user)
            profile.is_active = True
            profile.save()
            messages.success(request, f'Business profile "{profile.company_name}" is now active!')
    # return redirect('templates/invoices/invoice_form')
    return redirect(request.META.get('HTTP_REFERER', 'invoices:dashboard'))

def invoice_pdf_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id)
    
    # Calculate original subtotal (before discount)
    original_subtotal = sum(item.quantity * item.unit_price for item in invoice.items.all())
    
    # Calculate total discount rate and discount amount from items
    total_discount_rate = sum(int(item.discount) for item in invoice.items.all())
    total_discount = sum(
        (item.quantity * item.unit_price * item.discount) / Decimal('100')
        for item in invoice.items.all()
    )
    
    # Calculate subtotal after discount
    subtotal = original_subtotal - total_discount
    
    # Calculate GST amount
    gst_rate = invoice.gst_rate or Decimal('0')
    gst_amount = (subtotal * gst_rate) / Decimal('100')
    
    # Calculate total amount
    total_amount = subtotal + gst_amount

    context = {
        'invoice': invoice,
        'original_subtotal': original_subtotal,
        'total_discount': total_discount,
        'total_discount_rate': total_discount_rate,
        'gst_amount': gst_amount,
        'total_amount': total_amount,
    }
    
    # return render(request, 'pdfgenerate/pdf_generate.html', context)
    pdf = render_to_pdf('pdfgenerate/pdf_generate.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Invoice_{invoice.invoice_id}.pdf"
        content = f"attachment; filename={filename}"
        response['Content-Disposition'] = content
        return response
    return HttpResponse("PDF generation failed")

# ---------- for invoice all customer ----------- #
@login_required
def customer_list(request):
    customers = InvoiceCustomer.objects.all()
    return render(request, 'customer/customer_list.html', {'customers': customers, 'title': 'Customer List'})

@login_required
def customer_edit(request, customer_id):
    customer = get_object_or_404(InvoiceCustomer, pk=customer_id)
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # Update customer fields; ensure the keys match those sent from the modal
            customer.customer_name = data.get('customer_name', customer.customer_name)
            customer.customer_email = data.get('customer_email', customer.customer_email)
            customer.customer_contact = data.get('customer_contact', customer.customer_contact)
            customer.customer_address = data.get('customer_address', customer.customer_address)
            customer.customer_country = data.get('customer_country', customer.customer_country)
            customer.customer_zip = data.get('customer_zip', customer.customer_zip)
            customer.customer_state = data.get('customer_state', customer.customer_state)
            customer.customer_city = data.get('customer_city', customer.customer_city)
            customer.save()
            messages.success(request, 'Product update successfully.')
            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'fail', 'message': 'Invalid JSON data.'})
    else:
        # Optionally, return current customer data for GET requests if needed
        return JsonResponse({
            'customer_name': customer.customer_name,
            'customer_email': customer.customer_email,
            'customer_contact': customer.customer_contact,
            'customer_address': customer.customer_address,
            'customer_country': customer.customer_country,
            'customer_zip': customer.customer_zip,
            'customer_state': customer.customer_state,
            'customer_city': customer.customer_city,
        })

@login_required
def customer_delete(request, customer_id):
    customer = get_object_or_404(InvoiceCustomer, pk=customer_id)
    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'Customer deleted successfully.')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


# --------- for product ------------ #
@login_required
def product_list(request):
    products = Product.objects.all()
    return render(request, 'products/product_list.html', {'products': products, 'title': 'Products'})

@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            product.item_name = data.get('item_name', product.item_name)
            product.item_price = data.get('item_price', product.item_price)
            product.save()
            messages.success(request, 'Product update successfully.')
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully.')
        return redirect('invoices:product_list')
    return JsonResponse({'status': 'error'}, status=400)