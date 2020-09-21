from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash

import urllib.request
import json


# Create your views here.
def home(request):
    if not request.user.is_authenticated:
        return redirect('main:login')

    url = 'https://asvz.ch/asvz_api/event_search?_format=json&limit=60'

    with urllib.request.urlopen(url) as url:
        data = json.loads(url.read().decode())
        print(data['results'][0]['title'])
    return render(
        request,
        'main/home.html',
        {'data': data}
    )


def register(request):
    user = request.user
    if user.is_authenticated:
        return redirect('main:home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.first_name = form.cleaned_data.get('password1')
            user.save()
            user.refresh_from_db()
            username = form.cleaned_data.get('username')
            messages.success(request, f"New Account Created for {username}")
            login(request, user)
            messages.info(request, f"You are now logged in as {username}")
            return redirect("main:home")
        else:
            for msg in form.error_messages:
                messages.error(request, f"{msg}: {form.error_messages[msg]}")

    form = UserCreationForm()
    return render(
        request,
        'main/register.html',
        {'form': form}
    )


def login_request(request):
    user = request.user
    if user.is_authenticated:
        return redirect('main:home')

    if request.method == 'POST':
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}")
                return redirect('main:home')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")

    form = AuthenticationForm()
    return render(
        request,
        'main/login.html',
        {'form': form}
    )


def logout_request(request):
    if not request.user.is_authenticated:
        return redirect('main:home')

    logout(request)
    messages.info(request, "Logged out successfully!")
    return redirect('main:home')


def account(request):
    if not request.user.is_authenticated:
        return redirect('main:home')

    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            user = User.objects.get(request.user['username'])
            user.first_name = form.cleaned_data.get('new_password1')
            user.save()
            user.refresh_from_db()
            update_session_auth_hash(request, form.user)
            messages.info(request, f"Your password has been Updated.")
            return redirect('main:home')
        else:
            for msg in form.error_messages:
                messages.error(request, f"{msg}: {form.error_messages[msg]}")

    form = PasswordChangeForm(request.user)
    return render(
        request,
        'main/account.html',
        {'form': form}
    )
