# Copyright by your friendly neighborhood SaunaLord
import time
import pytz
from datetime import datetime, timezone
from pathos.multiprocessing import ProcessPool
from django.core.management import BaseCommand
from main.asvz_crawler import ASVZCrawler
from main.models import ASVZEvent


class Command(BaseCommand):
    help = 'Checks for events to register'

    def handle(self, *args, **kwargs):
        check_time()


def check_time():
    print(f"========= Chron Job - Registration =========", flush=True)
    current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
    event_list = ASVZEvent.objects.order_by('register_start_date')

    pool_event = []
    while event_list:
        register_time = event_list[0].register_start_date.replace(tzinfo=timezone.utc).astimezone(
            tz=pytz.timezone('Europe/Zurich'))
        time_delta = (register_time - current_time).total_seconds()
        if time_delta < 5 * 60:
            event = event_list[0]
            event_list = event_list[1:]
            pool_event.append(event)
        else:
            break

    if pool_event:
        pool = ProcessPool(nodes=8)
        res = pool.amap(ASVZCrawler, pool_event)
        while not res.ready():
            time.sleep(5)

    print(f"========= Finished - Registration  =========", flush=True)
    return
