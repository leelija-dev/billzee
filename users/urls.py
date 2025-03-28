from django.urls import path
from . import views

app_name = 'users'  # Add namespace to match the existing pattern

urlpatterns = [
    path('register/', views.register, name='register'),
    path('settings/', views.profile_settings, name='profile_settings'),
    path('profiles/', views.profile_list, name='profile_list'),
    path('profiles/create/', views.profile_create, name='profile_create'),
    path('profiles/<int:pk>/edit/', views.profile_edit, name='profile_edit'),
    path('profiles/<int:pk>/activate/', views.profile_activate, name='profile_activate'),
    path('get-states/', views.get_states, name='get_states'),
    path('get-cities/', views.get_cities, name='get_cities'),
    path('get-location-by-zip/', views.get_location_by_zip, name='get_location_by_zip'),
]
