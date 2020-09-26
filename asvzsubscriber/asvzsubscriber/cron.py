from datetime import datetime, timezone
import pytz
from cryptography.fernet import Fernet
import threading

from main.models import ASVZEvent
from event_subscriber import event_subscriber


def check_time():
    print(f"========= Chron Job =========")
    current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
    event_list = ASVZEvent.objects.order_by('register_start_date')
    while event_list:
        register_time = event_list[0].register_start_date.replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone('Europe/Zurich'))
        time_delta = (register_time - current_time).total_seconds()
        if time_delta < 5*60:
            event = event_list[0]
            event_list = event_list[1:]
            if True or time_delta > 0.0:
                user = event.user
                username = user.username
                url = event.url
                with open('../key.lock', 'r') as key_file:
                    key = bytes(key_file.read(), 'utf-8')
                f = Fernet(key)
                password = f.decrypt(bytes(user.first_name, 'utf-8')).decode('utf-8')

                bot_id = f"{username}:{url[-6:]}"
                print(f"{bot_id} ==> Dispatch Bot")
                dispatch_thread = threading.Thread(target=event_subscriber(username, password, url), name=bot_id)
                dispatch_thread.start()
            event.delete()
        else:
            break
    return
