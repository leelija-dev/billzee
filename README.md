# Invoice Application

A modern invoicing application built with Django and Tailwind CSS that allows businesses to create, manage, and send invoices to customers.

## Features

- Create and manage invoices with unique IDs
- Add multiple products/services to each invoice
- Track invoice status (pending, completed, canceled)
- Send invoices via email
- Share unique invoice links with customers
- Customer portal for marking payments as complete
- Responsive design using Tailwind CSS

## Setup Instructions

1. Create a virtual environment and activate it:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations:
```bash
python manage.py makemigrations users invoices
python manage.py migrate
```

4. Create a superuser:
```bash
python manage.py createsuperuser
```

5. Run the development server:
```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000/ to access the application.

## Project Structure

```
invoice_app/
├── invoice_project/     # Main project settings
├── invoices/           # Invoice management app
├── users/             # Custom user management
├── templates/         # HTML templates
└── static/           # Static files (CSS, JS)
```

## Usage

1. Log in with your credentials
2. Create a new invoice from the dashboard
3. Add items to the invoice
4. Send the invoice to customers via email
5. Track payment status and manage invoices

## Email Configuration

By default, the application uses Django's console email backend for development. To send real emails, update the email settings in `settings.py` with your email provider's configuration.
