# Copyright by your friendly neighborhood SaunaLord
import pytz
import urllib.request
import json
from pathos.multiprocessing import ProcessPool
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.utils.safestring import mark_safe
from django.utils import timezone

from .asvz_crawler import ASVZCrawler
from .forms import ASVZEventForm, ASVZUserCreationForm, ASVZUserChangeForm
from .models import ASVZEvent, ASVZUser


def validation(request):
    user: ASVZUser = request.user
    if not user.is_authenticated or (user.account_approved and user.account_verified):
        return redirect('main:home')

    return render(
        request,
        'main/validation.html'
    )


def enrollments(request):
    user: ASVZUser = request.user
    if not request.user.is_authenticated or not user.account_approved or not user.account_verified:
        return redirect('main:home')

    json_obj = ASVZCrawler(user).get_enrollments()  # is already updating bearer token
    valid_to, _ = ASVZCrawler(user).get_sauna_subscription()

    if valid_to > timezone.datetime.now(tz=pytz.timezone('Europe/Zurich')):
        valid_to = valid_to.strftime('%d.%m.%Y')
    else:
        valid_to = '--- No active sauna subscription ---'

    new_list = list()

    if json_obj is not None:
        for obj in json_obj:
            new_list.append({
                "lessonName": obj['lessonName'],
                "sportName": obj['sportName'],
                "lessonTime": f"{obj['lessonStart'][8:10]}.{obj['lessonStart'][5:7]}.{obj['lessonStart'][0:4]} {obj['lessonStart'][11:16]} - {obj['lessonEnd'][11:16]}",
                "location": obj['location'],
                "room": obj['room'],
                "placeNumber": obj['placeNumber']
            })
        new_list = sorted(new_list, key=lambda i: i['lessonTime'])

    return render(
        request,
        'main/enrollments.html',
        {'json_obj': new_list, 'valid_to': valid_to}
    )


# Create your views here.
def home(request):
    user: ASVZUser = request.user
    if not user.is_authenticated:
        return redirect('main:login')
    if not user.account_approved or not user.account_verified:
        return redirect('main:validation')

    update_bearer_token(user, asyncron=True)

    selected_sporttypes = []
    selected_facilities = []
    tomorrow = timezone.datetime.now(tz=pytz.timezone('Europe/Zurich')) + timezone.timedelta(days=1)
    selected_date = tomorrow.strftime('%Y-%m-%d')
    selected_time = tomorrow.strftime('%H:%M')
    selected_limit = '15'
    selected_sauna = ''

    if request.method == 'POST':
        # Read selection
        selected_sporttypes = request.POST.getlist('sporttype')
        selected_facilities = request.POST.getlist('facility')
        selected_date = request.POST.get('date')
        selected_time = request.POST.get('time')
        selected_limit = request.POST.get('limit')
        selected_sauna = 'checked' if request.POST.get('sauna') == 'on' else ''

        if selected_sauna == 'checked':
            selected_limit = 50
            selected_sporttypes = ['Wellness / Sauna']
            selected_facilities = ['Sport Center Hönggerberg']

    data, default_data = update_url(
        show_results=selected_limit,
        sporttypes=selected_sporttypes,
        facilities=selected_facilities,
        date=selected_date,
        time=selected_time
    )

    events, events_scheduled, events_scheduled_mod = load_events(data, user)

    if request.method == 'POST' and not ('show_results' in request.POST):
        if 'schedule' in request.POST:
            form = ASVZEventForm(request.POST)
            form.set_choices(events=events)

            if form.is_valid():
                for selected_event in form.cleaned_data.get('Events'):
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
                                niveau_short_name=event['niveau_short_name'],
                            )
                            break
        elif 'deschedule' in request.POST:
            form_scheduled = ASVZEventForm(request.POST)
            form_scheduled.set_choices(events=events_scheduled_mod)

            if form_scheduled.is_valid():
                for selected_event in form_scheduled.cleaned_data.get('Events'):
                    for event in events_scheduled:
                        if selected_event == event.url:
                            record = ASVZEvent.objects.get(url=event.url, user=user)
                            record.delete()
                            break

        events, events_scheduled, events_scheduled_mod = load_events(data, user)

    form = ASVZEventForm()
    form.set_choices(events=events)

    form_scheduled = ASVZEventForm()
    form_scheduled.set_choices(events=events_scheduled_mod)

    sporttypes = [t['label'] for t in default_data['facets'][7]['terms']]
    facilities = [f['label'] for f in default_data['facets'][1]['terms']]
    sporttypes.sort()
    facilities.sort()

    return render(
        request,
        'main/home.html',
        {'form': form,
         'form_scheduled': form_scheduled,
         'sporttypes': sporttypes,
         'facilities': facilities,
         'selected_sporttypes': selected_sporttypes,
         'selected_facilities': selected_facilities,
         'selected_date': selected_date,
         'selected_time': selected_time,
         'selected_limit': selected_limit,
         'selected_sauna': mark_safe(selected_sauna),
         }
    )


def register(request):
    user: ASVZUser = request.user
    if user.is_authenticated:
        return redirect('main:home')

    if request.method == 'POST':
        form = ASVZUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"New Account Created for {user.username}")
            login(request, user)
            messages.info(request, f"You are now logged in as {user.username}")
            update_bearer_token(user, asyncron=True)
            return redirect("main:home")
        else:
            for msg in form.error_messages:
                messages.error(request, f"{msg}: {form.error_messages[msg]}")

    form = ASVZUserCreationForm()
    return render(
        request,
        'main/register.html',
        {'form': form}
    )


def login_request(request):
    user: ASVZUser = request.user
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
                messages.info(request, f"You are now logged in as {user.username}")
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
    user: ASVZUser = request.user
    if not user.is_authenticated:
        return redirect('main:home')

    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('main:home')


def account(request):
    user: ASVZUser = request.user
    if not user.is_authenticated or not user.account_approved or not user.account_verified:
        return redirect('main:home')

    update_bearer_token(user, asyncron=True)

    if request.method == 'POST':
        if 'delete' in request.POST:
            logout(request)
            user.delete()
            messages.success(request, "Your account has been deleted")
            return redirect('main:home')

        form = ASVZUserChangeForm(user=user, data=request.POST)
        if form.is_valid():
            form.save()
            user.save()
            user.refresh_from_db()
            update_session_auth_hash(request, form.user)
            messages.success(request, f"Your account has been Updated.")
            update_bearer_token(user, asyncron=True)
            return redirect('main:home')
        else:
            for msg in form.error_messages:
                messages.error(request, f"{msg}: {form.error_messages[msg]}")

    form = ASVZUserChangeForm(request.user)
    return render(
        request,
        'main/account.html',
        {'form': form}
    )


def load_events(data, user):
    events_scheduled = [event for event in ASVZEvent.objects.order_by('register_start_date').filter(user=user)]
    events_scheduled_url = [event.url for event in ASVZEvent.objects.filter(user=user)]

    events = [(
        event['url'],
        mark_safe(
            f"<span>{timezone.datetime.strptime(event['from_date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.timezone.utc).astimezone(tz=pytz.timezone('Europe/Zurich')).strftime('%d.%m %H:%M')} | {event['sport_name']} | {event['niveau_short_name']} | {event['title']} | {event['location']}</span>")
    ) for event in data['results'] if event['url'] not in events_scheduled_url]

    events_scheduled_mod = [(
        event.url,
        mark_safe(
            f"<span>{event.event_start_date.replace(tzinfo=timezone.timezone.utc).astimezone(tz=pytz.timezone('Europe/Zurich')).strftime('%d.%m %H:%M')} | {event.sport_name} | {event.niveau_short_name} | {event.title} | {event.location}</span>")
    ) for event in events_scheduled]
    return events, events_scheduled, events_scheduled_mod


def update_url(show_results=15, sporttypes=None, facilities=None, date=None, time=None):
    default_url = f'https://asvz.ch/asvz_api/event_search?_format=json&limit={show_results}'
    with urllib.request.urlopen(default_url) as url:
        default_data = json.loads(url.read().decode())

    sporttype_string = ''
    facility_string = ''
    i = 0
    for sporttype in sporttypes:
        for fulltype in default_data['facets'][7]['terms']:
            if fulltype['label'] == sporttype:
                sporttype_string = sporttype_string + f"&f[{i}]=sport:{fulltype['tid']}"
                break
        i += 1

    for facility in facilities:
        for fulltype in default_data['facets'][1]['terms']:
            if fulltype['label'] == facility:
                sporttype_string = sporttype_string + f"&f[{i}]=facility:{fulltype['tid']}"
                break
        i += 1

    f_appendix = ''
    for cnt in range(0, i):
        f_appendix = f_appendix + f":f[{cnt}]"

    url = f"https://asvz.ch/asvz_api/event_search?_format=json&limit={show_results}&date={date}%20{time}{sporttype_string}{facility_string}&selected=date{f_appendix}"

    # print(f"\nDEBUG ====> {url}\n")

    with urllib.request.urlopen(url) as url:
        data = json.loads(url.read().decode())

    # Remove already open events
    events_to_be_removed = []
    for event in data['results']:
        current_time = timezone.datetime.now(pytz.timezone('Europe/Zurich'))
        registration_start = current_time
        if 'oe_from_date' in event:
            registration_start = timezone.datetime.strptime(event['oe_from_date'], '%Y-%m-%dT%H:%M:%SZ').replace(
                tzinfo=timezone.timezone.utc).astimezone(tz=current_time.tzinfo)
        time_delta = (registration_start - current_time).total_seconds()
        if time_delta < 0.0:
            events_to_be_removed.append(event)
    for event in events_to_be_removed:
        data['results'].remove(event)

    return data, default_data


def update_bearer_token(user: ASVZUser, asyncron=False):
    if asyncron:
        pool = ProcessPool(nodes=1)
        pool.amap(ASVZCrawler, [user])
    else:
        ASVZCrawler(user)
    return
