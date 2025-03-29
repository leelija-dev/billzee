from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import login
from django.http import JsonResponse
import requests
from .forms import CustomUserForm, ProfileForm, CustomUserCreationForm
from .models import Profile
from .utils import get_country_choices

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('invoices:dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile_settings(request):
    if request.method == 'POST':
        form = CustomUserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('invoices:dashboard')
    else:
        form = CustomUserForm(instance=request.user)
    return render(request, 'users/profile_settings.html', {'form': form, 'title': 'Profile Settings'})

@login_required
def profile_list(request):
    profiles = Profile.objects.filter(user=request.user)
    return render(request, 'users/profile_list.html', {
        'profiles': profiles,
        'title': 'Business Profiles'
    })

@login_required
def profile_create(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            # Make active if first profile
            profile.is_active = not Profile.objects.filter(user=request.user).exists()
            profile.save()
            messages.success(request, 'Business profile created successfully!')
            return redirect('users:profile_list')
    else:
        form = ProfileForm()
    return render(request, 'users/profile_form.html', {
        'form': form,
        'title': 'Create Business Profile'
    })

@login_required
def profile_edit(request, pk):
    profile = get_object_or_404(Profile, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Business profile updated successfully!')
            return redirect('users:profile_list')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'users/profile_form.html', {
        'form': form,
        'profile': profile,
        'title': 'Edit Business Profile'
    })

@login_required
def profile_activate(request, pk):
    if request.method == 'POST':
        with transaction.atomic():
            # First, deactivate all profiles for this user
            Profile.objects.filter(user=request.user).update(is_active=False)
            # Then activate the selected profile
            profile = get_object_or_404(Profile, pk=pk, user=request.user)
            profile.is_active = True
            profile.save()
            messages.success(request, f'Business profile "{profile.company_name}" is now active!')
    return redirect('users:profile_list')

def get_states(request):
    """AJAX view to fetch states based on the selected country."""
    country_code = request.GET.get('country')
    country_name = None
    for code, name in get_country_choices():
        if code.upper() == country_code.upper():
            country_name = name
            break

    if not country_name:
        return JsonResponse({'error': 'Invalid country code'}, status=400)

    try:
        url = "https://countriesnow.space/api/v0.1/countries/states"
        payload = {"country": country_name}
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if not data.get('error'):
                states = data.get('data', {}).get('states', [])
                state_choices = sorted([state.get('name', '') for state in states if state.get('name')])
                return JsonResponse({'states': state_choices})
        return JsonResponse({'error': 'Failed to fetch states'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_cities(request):
    """AJAX view to fetch cities based on the selected state and country."""
    country_code = request.GET.get('country')
    state = request.GET.get('state')
    country_name = None
    for code, name in get_country_choices():
        if code.upper() == country_code.upper():
            country_name = name
            break

    if not country_name or not state:
        return JsonResponse({'error': 'Invalid country or state'}, status=400)

    try:
        url = "https://countriesnow.space/api/v0.1/countries/state/cities"
        payload = {"country": country_name, "state": state}
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if not data.get('error'):
                cities = data.get('data', [])
                cities = sorted([city for city in cities if city])
                return JsonResponse({'cities': cities})
        return JsonResponse({'error': 'Failed to fetch cities'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500) 

def get_location_by_zip(request):
    """
    AJAX view to fetch state and city based on a zip/pin code.
    For India, it uses the PostalPincode API.
    For the US, it uses the Zippopotam.us API.
    """
    zip_code = request.GET.get('zip')
    country = request.GET.get('country')
    if not zip_code or not country:
        return JsonResponse({'error': 'Zip code and country are required.'}, status=400)

    if country.upper() == 'IN':
        try:
            url = f"http://www.postalpincode.in/api/pincode/{zip_code}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('Status') == 'Success':
                    post_offices = data.get('PostOffice', [])
                    if post_offices:
                        first_po = post_offices[0]
                        state = first_po.get('State', '')
                        city = first_po.get('District', '')
                        print(state)
                        print(city)
                        return JsonResponse({'state': state, 'city': city})
                    else:
                        return JsonResponse({'error': 'No post offices found for this pin code.'}, status=404)
                else:
                    return JsonResponse({'error': 'Invalid PIN code.'}, status=404)
            else:
                return JsonResponse({'error': 'Error fetching location.'}, status=response.status_code)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    elif country.upper() == 'US':
        try:
            url = f"http://api.zippopotam.us/us/{zip_code}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                places = data.get('places', [])
                if places:
                    first_place = places[0]
                    state = first_place.get('state abbreviation', '')
                    city = first_place.get('place name', '')
                    return JsonResponse({'state': state, 'city': city})
                else:
                    return JsonResponse({'error': 'No places found.'}, status=404)
            else:
                return JsonResponse({'error': 'Invalid ZIP code.'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Country not supported for zip lookup.'}, status=400)