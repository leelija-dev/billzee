from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .forms import CustomUserForm, ProfileForm
from .models import Profile

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
