import os
from datetime import datetime, timezone
from pathlib import Path
import pytz
from cryptography.fernet import Fernet
from django.core.management import BaseCommand
from main.event_subscriber import event_subscriber
from main.models import ASVZEvent
from pathos.multiprocessing import ProcessPool


class Command(BaseCommand):
    help = 'Checks for events to register'

    def handle(self, *args, **kwargs):
        check_time()


def check_time():
    print(f"========= Chron Job =========")
    current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
    event_list = ASVZEvent.objects.order_by('register_start_date')

    pool_event = []
    pool_username = []
    pool_pw = []
    while event_list:
        register_time = event_list[0].register_start_date.replace(tzinfo=timezone.utc).astimezone(
            tz=pytz.timezone('Europe/Zurich'))
        time_delta = (register_time - current_time).total_seconds()
        if time_delta < 5 * 60:
            event = event_list[0]
            event_list = event_list[1:]

            user = event.user
            username = user.username
            url = event.url
            ASVZ_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
            with open(os.path.join(ASVZ_DIR, 'key.lock'), 'r') as key_file:
                key = bytes(key_file.read(), 'utf-8')
            f = Fernet(key)
            password = f.decrypt(bytes(user.first_name, 'utf-8')).decode('utf-8')
            pool_event.append(event)
            pool_username.append(username)
            pool_pw.append(password)
        else:
            break

    pool = ProcessPool(nodes=10)
    pool.map(event_subscriber, pool_event, pool_username, pool_pw)
    return
