from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', RedirectView.as_view(url='/invoices/'), name='home'),
    path('users/', include('users.urls')),
    path('invoices/', include('invoices.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    path('logout/', LogoutView.as_view(
        template_name='registration/logged_out.html',
        next_page=None,
        http_method_names=['get', 'post']
    ), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
