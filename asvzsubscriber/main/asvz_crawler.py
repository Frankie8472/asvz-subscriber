import json
import os
import pytz
import requests
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from .models import ASVZEvent, BearerToken


def subscribe_to_event(event: ASVZEvent = None):
    # Init params
    event_id = event.url[-6:]
    user = User.objects.get(username=event.user)
    bearer = get_bearer_token(user=user, request_id=event_id)

    bot_id = f"{user.username}:{event_id}"

    # Get reg time
    lesson_register_time_datetime = event.register_start_date.replace(tzinfo=timezone.utc)
    logtime = unix_time_millis(lesson_register_time_datetime)

    # Wait until 5 sec before reg opening
    print(f"{bot_id} ==> Wait for register start")
    sleeptimeoffset = 2
    current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
    timedelta = lesson_register_time_datetime - current_time
    if timedelta.total_seconds() > 0.0:
        time.sleep(timedelta.total_seconds() - sleeptimeoffset)

    # Spam Post requests
    print(f"{bot_id} ==> Registering")
    ret = 422
    cnt = 0
    while (ret != 201) and (cnt < 2 * sleeptimeoffset):
        try:
            ret = requests.post(
                url=f'https://schalter.asvz.ch/tn-api/api/Lessons/{event_id}/enroll?%3Ft={logtime}',
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en,en-US;q=0.7,de;q=0.3',
                    'Authorization': f'Bearer {bearer}',
                    'Content-Type': 'application/json',
                    'Origin': 'https://schalter.asvz.ch',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Referer': f'https://schalter.asvz.ch/tn/lessons/{event_id}',
                }
            ).status_code
            print(f"{bot_id} ==> {ret}")

        except:
            pass

        step = 0.1
        time.sleep(step)
        cnt += step

    if ret == 422:
        print(f"{bot_id} ==> Registering Failed")
    else:
        print(f"{bot_id} ==> You are registered!")

    # Delete Event
    if not (event is None):
        print(f"{bot_id} ==> Deleting Event")
        event.delete()

    return


def get_enrollments(user: User = None):
    if user.username == 'admin':
        return None

    # Init params
    bearer = get_bearer_token(user=user)
    current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
    logtime = unix_time_millis(current_time)

    ret = requests.get(
        url=f'https://schalter.asvz.ch/tn-api/api/Enrollments??t={logtime}',
        headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en,en-US;q=0.7,de;q=0.3',
            'Authorization': f'Bearer {bearer}',
            'Content-Type': 'application/json',
            'Origin': 'https://schalter.asvz.ch',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': f'https://schalter.asvz.ch/tn/my-lessons',
        }
    ).json()

    return ret


def get_bearer_token(user: User = None, request_id=''):
    if user.username == 'admin':
        return None

    return decrypt_passphrase(update_bearer_token(user, request_id).bearerToken)


def update_bearer_token(user: User = None, request_id=''):
    if user.username == 'admin':
        return None

    current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
    try:
        bearerToken = BearerToken.objects.get(user=user)
    except BearerToken.DoesNotExist:
        bearerToken = BearerToken.objects.create(
            user=user,
            bearerToken='',
            valid_until=current_time - timedelta(hours=3),
            is_updating=False
        )

    if bearerToken.is_updating:
        time.sleep(2)
        return update_bearer_token(user, request_id)

    elif (bearerToken.valid_until - current_time).total_seconds() > 0:
        return bearerToken

    else:
        bearerToken.valid_until = current_time + timedelta(hours=2)
        bearerToken.is_updating = True
        bearerToken.save()

    # Update bearer token
    # Init params
    url = "https://schalter.asvz.ch/tn/my-lessons"
    username = user.username
    university = user.last_name
    bot_id = f"{username}:{request_id}"

    password = decrypt_passphrase(user.first_name)

    print(f"{bot_id} ==> Dispatch Bot")

    aailogin_name = 'provider'
    institution_selection_id = 'userIdPSelection_iddtext'
    institution_submit_name = 'Select'
    eth_username_id = 'username'
    uzh_username_id = 'username'
    eth_password_id = 'password'
    uzh_password_id = 'password'
    eth_login_name = '_eventId_proceed'
    uzh_login_name = '_eventId_proceed'
    final_page_identifier_class = 'table'

    # Init browser
    firefox_options = Options()
    firefox_options.headless = True
    firefox_options.add_argument("--disable-gpu")
    browser = webdriver.Firefox(executable_path='/usr/bin/geckodriver', options=firefox_options)

    # Opening ASVZ login page
    print(f"{bot_id} ==> Opening ASVZ Login Page")
    browser.get(url)
    elem = wait_for_element_location(bot_id, browser, "name", aailogin_name)
    if elem is None:
        print(f"{bot_id} ==> Element not found, aborting")
        return
    elem.click()

    # Opening AAI login page
    print(f"{bot_id} ==> Opening AAI Login Page")
    elem = wait_for_element_location(bot_id, browser, "id", institution_selection_id)

    print(f"{bot_id} ==> Selecting Institution")
    if elem is None:
        print(f"{bot_id} ==> Element not found, aborting")
        return

    elem.send_keys(university)
    browser.find_element_by_name(institution_submit_name).click()

    print(f"{bot_id} ==> Opening {university} Login Page")
    if university == 'ETH Zürich':
        # Opening ETH Login Page
        elem = wait_for_element_location(bot_id, browser, "id", eth_username_id)
        if elem is None:
            print(f"{bot_id} ==> Element not found, aborting")
            return
        elem.send_keys(username)
        browser.find_element_by_id(eth_password_id).send_keys(password)
        browser.find_element_by_name(eth_login_name).click()
        elem = wait_for_element_location(bot_id, browser, "id", "corp")
        if elem is not None:
            browser.find_element_by_name("_eventId_proceed").click()

    elif university == 'Universität Zürich':
        # Opening ETH Login Page
        elem = wait_for_element_location(bot_id, browser, "id", uzh_username_id)
        if elem is None:
            print(f"{bot_id} ==> Element not found, aborting")
            return
        elem.send_keys(username)
        browser.find_element_by_id(uzh_password_id).send_keys(password)
        browser.find_element_by_name(uzh_login_name).click()

    elem = wait_for_element_location(bot_id, browser, "class", final_page_identifier_class)
    if elem is None:
        print(f"{bot_id} ==> Element not found, aborting")
        return

    # Get bearer token
    bearer = None
    for key, value in browser.execute_script("return localStorage").items():
        if key.startswith("oidc.user"):
            localStorage_json = json.loads(value)
            bearer = localStorage_json['access_token']
            break

    browser.quit()
    bearerToken.bearerToken = encrypt_passphrase(bearer)
    bearerToken.is_updating = False
    bearerToken.save()
    return bearerToken


def wait_for_element_location(bot_id, browser, search_art="class", search_name="", delay=10, interval=0.5):
    cnt = 0
    if search_art == "class":
        search_option = By.CLASS_NAME
    elif search_art == "name":
        search_option = By.NAME
    elif search_art == "xpath":
        search_option = By.XPATH
    else:  # id
        search_option = By.ID
    while True:
        try:
            element = WebDriverWait(browser, delay, interval).until(
                EC.presence_of_element_located((search_option, search_name)))
            return element
        except TimeoutException:
            cnt += 1
            print(f"{bot_id} !! Loading took too much time! Trying again...")
            time.sleep(5)
            if cnt < 5:
                pass
            else:
                return None


def unix_time_millis(dt):
    return round((dt - datetime.utcfromtimestamp(0).replace(tzinfo=timezone.utc)).total_seconds() * 1000)


def get_cryptor():
    ASVZ_DIR = Path(__file__).resolve().parent.parent.parent
    with open(os.path.join(ASVZ_DIR, 'key.lock'), 'r') as key_file:
        key = bytes(key_file.read(), 'utf-8')
    return Fernet(key)


def decrypt_passphrase(passphrase):
    return get_cryptor().decrypt(bytes(passphrase, 'utf-8')).decode('utf-8')


def encrypt_passphrase(passphrase):
    return get_cryptor().encrypt(bytes(passphrase, 'utf-8')).decode('utf-8')
