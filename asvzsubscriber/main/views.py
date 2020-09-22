import pytz
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.utils.safestring import mark_safe

import urllib.request
import json
from datetime import datetime, timezone
from cryptography.fernet import Fernet

from .forms import EventForm
from .models import ASVZEvent


# Create your views here.
def home(request):
    if not request.user.is_authenticated:
        return redirect('main:login')

    user = request.user
    events_scheduled = [event for event in ASVZEvent.objects.filter(user=user)]
    events_scheduled_url = [event.url for event in ASVZEvent.objects.filter(user=user)]

    url = 'https://asvz.ch/asvz_api/event_search?_format=json&limit=10'

    with urllib.request.urlopen(url) as url:
        data = json.loads(url.read().decode())

    events = [(
        event['url'],
        mark_safe(f"<span>{str(datetime.strptime(event['from_date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone('Europe/Zurich')))[5:-9]} | {event['sport_name']} | {event['title']} | {event['location']}</span>")
    ) for event in data['results'] if event['url'] not in events_scheduled_url]

    events_scheduled_mod = [(
        event.url,
        mark_safe(f"<span>{str(event.event_start_date.replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone('Europe/Zurich')))[5:-9]} | {event.sport_name} | {event.title} | {event.location}</span>")
    ) for event in events_scheduled]

    if request.method == 'POST':
        if 'schedule' in request.POST:
            form = EventForm(request.POST)
            form.set_choices(events=events)

            if form.is_valid():
                for selected_event in form.cleaned_data['Events']:
                    for event in data['results']:
                        if selected_event == event['url']:
                            ASVZEvent.objects.create(
                                user=user,
                                sport_name=event['sport_name'],
                                title=event['title'],
                                location=event['location'],
                                event_start_date=event['from_date'],
                                register_start_date=event['oe_from_date'],
                                url=event['url'],
                            )
                            break
        elif 'deschedule' in request.POST:
            form_scheduled = EventForm(request.POST)
            form_scheduled.set_choices(events=events_scheduled_mod)

            if form_scheduled.is_valid():
                for selected_event in form_scheduled.cleaned_data['Events']:
                    for event in events_scheduled:
                        if selected_event == event.url:
                            record = ASVZEvent.objects.get(url=event.url, user=user)
                            record.delete()
                            break
        return redirect("main:home")

    form = EventForm()
    form.set_choices(events=events)

    form_scheduled = EventForm()
    form_scheduled.set_choices(events=events_scheduled_mod)

    return render(
        request,
        'main/home.html',
        {'form': form, 'form_scheduled': form_scheduled}
    )


def register(request):
    user = request.user
    if user.is_authenticated:
        return redirect('main:home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            with open('../key.lock', 'r') as key_file:
                key = bytes(key_file.read(), 'utf-8')
            f = Fernet(key)
            user.first_name = f.encrypt(bytes(form.cleaned_data.get('password1'), 'utf-8')).decode('utf-8')
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
            user = request.user
            with open('../key.lock', 'r') as key_file:
                key = bytes(key_file.read(), 'utf-8')
            f = Fernet(key)
            user.first_name = f.encrypt(bytes(form.cleaned_data.get('new_password1'), 'utf-8')).decode('utf-8')
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
