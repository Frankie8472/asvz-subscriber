import json
import time

import pytz
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.expected_conditions import visibility_of_element_located
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from datetime import datetime, timezone
import ntplib
import requests


class element_located_not_disabled(object):
    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver):
        element = visibility_of_element_located(self.locator)(driver)
        if 'disabled' in element.get_attribute('class'):
            return False
        else:
            return element


def unix_time_millis(dt):
    return round((dt - datetime.utcfromtimestamp(0).replace(tzinfo=timezone.utc)).total_seconds() * 1000)


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


def event_subscriber(event=None, password=None):
    # Init params
    url = event.url
    user = event.user
    username = user.username
    event_id = url[-6:]
    bot_id = f"{username}:{event_id}"
    print(f"{bot_id} ==> Dispatch Bot")

    asvzlogin_class = "btn-default"
    aailogin_name = 'provider'
    institution_selection_id = 'userIdPSelection_iddtext'
    institution_submit_name = 'Select'
    eth_username_id = 'username'
    uzh_username_id = 'username'
    eth_password_id = 'password'
    uzh_password_id = 'password'
    eth_login_name = '_eventId_proceed'
    uzh_login_name = '_eventId_proceed'
    lesson_register_element_id = 'eventDetails'

    # Init browser
    firefox_options = Options()
    firefox_options.headless = True
    firefox_options.add_argument("--disable-gpu")
    browser = webdriver.Firefox(executable_path='/usr/bin/geckodriver', options=firefox_options)

    # Opening lesson page
    print(f"{bot_id} ==> Opening Lesson Page")
    browser.get(url)
    elem = wait_for_element_location(bot_id, browser, "class", asvzlogin_class)
    if elem is None:
        print(f"{bot_id} ==> Element not found, aborting")
        return
    elem.click()

    # Opening ASVZ login page
    print(f"{bot_id} ==> Opening ASVZ Login Page")
    time.sleep(5)
    elem = wait_for_element_location(bot_id, browser, "name", aailogin_name)
    if elem is None:
        print(f"{bot_id} ==> Element not found, aborting")
        return
    elem.click()

    # Opening AAI login page
    print(f"{bot_id} ==> Opening AAI Login Page")
    time.sleep(1)
    print(f"{bot_id} ==> Selecting Institution")
    elem = wait_for_element_location(bot_id, browser, "id", institution_selection_id)
    if elem is None:
        print(f"{bot_id} ==> Element not found, aborting")
        return

    uni = user.last_name
    elem.send_keys(uni)
    time.sleep(1)
    browser.find_element_by_name(institution_submit_name).click()


    if uni == 'ETH Zürich':
        # Opening ETH Login Page
        print(f"{bot_id} ==> Opening {uni} Login Page")
        elem = wait_for_element_location(bot_id, browser, "id", eth_username_id)
        if elem is None:
            print(f"{bot_id} ==> Element not found, aborting")
            return
        elem.send_keys(username)
        time.sleep(0.5)
        elem = browser.find_element_by_id(eth_password_id)
        try:
            elem.send_keys(password)
        except ValueError:
            print(f"{bot_id} ==> Wrong password, stupid! Aborting")
            return
        browser.find_element_by_name(eth_login_name).click()
    elif uni == 'Universität Zürich':
        # Opening ETH Login Page
        print(f"{bot_id} ==> Opening {uni} Login Page")
        elem = wait_for_element_location(bot_id, browser, "id", uzh_username_id)
        if elem is None:
            print(f"{bot_id} ==> Element not found, aborting")
            return
        elem.send_keys(username)
        time.sleep(0.5)
        browser.find_element_by_id(uzh_password_id).send_keys(password)
        browser.find_element_by_name(uzh_login_name).click()

    elem = wait_for_element_location(bot_id, browser, "id", lesson_register_element_id)
    if elem is None:
        print(f"{bot_id} ==> Element not found, aborting")
        return
    time.sleep(0.5)

    # Get bearer token and reg time
    lesson_register_time_datetime = event.register_start_date.replace(tzinfo=timezone.utc)
    logtime = unix_time_millis(lesson_register_time_datetime)
    bearer = None
    for key, value in browser.execute_script("return localStorage").items():
        if key.startswith("oidc.user"):
            j = json.loads(value)
            bearer = j['access_token']
            break

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

        except ValueError:
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
