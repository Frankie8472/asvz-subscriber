# Copyright by your friendly neighborhood SaunaLord
import json
import os
import pytz
import requests
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support.ui import WebDriverWait

from .models import ASVZEvent, ASVZUser


def encrypt_passphrase(passphrase):
    return _get_cryptor().encrypt(bytes(passphrase, 'utf-8')).decode('utf-8')


def _decrypt_passphrase(passphrase):
    return _get_cryptor().decrypt(bytes(passphrase, 'utf-8')).decode('utf-8')


def _get_cryptor():
    asvz_dir = Path(__file__).resolve().parent.parent.parent
    with open(os.path.join(asvz_dir, 'key.lock'), 'r') as key_file:
        key = bytes(key_file.read(), 'utf-8')
    return Fernet(key)


def _unix_time_millis(dt):
    return round((dt - datetime.utcfromtimestamp(0).replace(tzinfo=timezone.utc)).total_seconds() * 1000)


class ASVZCrawler:
    def __init__(self, obj=None):
        if (obj is None) or (not isinstance(obj, ASVZEvent) and not isinstance(obj, ASVZUser)):
            self.bot_id = f"{'ERROR'}"
            self._log("No user or event given", error=True)
            return
        self.CLASS = "class"
        self.NAME = "name"
        self.ID = "id"

        if isinstance(obj, ASVZEvent):
            self.event: ASVZEvent = obj
            self.user: ASVZUser = ASVZUser.objects.get(username=self.event.user.__str__().split(' - ')[2])
            self.request_id = self.event.url[-6:]
        else:
            self.user: ASVZUser = obj
            self.event = None
            self.request_id = ''

        self.bot_id = f"{self.user.username}:{self.request_id}"
        if self.user.username == 'admin' or self.user.username == 'test':
            return

        self._password = _decrypt_passphrase(self.user.open_password)
        self._update_bearer_token()

        if not self.user.account_verified:
            if self.user.bearer_token == '':
                self.user.delete()
                return
            self.user.account_verified = True
            self.user.save()

        self._bearer_token = _decrypt_passphrase(self.user.bearer_token)

        if self.event is not None and self.user.bearer_token != '':
            self._subscribe_to_event()
        return

    def _subscribe_to_event(self):
        if self.event is None:
            self._log('Event is None, cannot subscribe if no event given', error=True)
            return

        # Wait until 5 sec before reg opening
        self._log('Wait for registration to open')

        lesson_register_time_datetime = self.event.register_start_date.replace(tzinfo=timezone.utc).astimezone(
            tz=pytz.timezone('Europe/Zurich'))
        lesson_register_time_unix = _unix_time_millis(lesson_register_time_datetime)
        current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
        time_delta = lesson_register_time_datetime - current_time
        self._log(f'TIMEDELTA: {time_delta}')
        sleep_time_offset = 3
        if time_delta.total_seconds() > 0.0:
            time.sleep(time_delta.total_seconds())

        # Spam Post requests
        self._log('Trying to register')

        ret = 422
        cnt = 0
        while (ret != 201) and (cnt < sleep_time_offset):
            # noinspection PyBroadException
            try:
                headers = {'Authorization': f'Bearer {self._bearer_token}'}
                json_data = {}

                ret = requests.post(
                    f'https://schalter.asvz.ch/tn-api/api/Lessons/{self.request_id}/Enrollment??t={lesson_register_time_unix}',
                    headers=headers,
                    json=json_data
                ).status_code

                self._log(f"Status Code: {ret}")

            except LookupError:
                self._log(f"Request failed", error=True)
                pass

            step = 0.2
            time.sleep(step)
            cnt += step

        if ret != 201:
            self._log("Registration Failed")
        else:
            self._log("Registration Succeeded")

        # Delete Event
        self._log("Deleting Event")
        self.event.delete()
        return

    def get_enrollments(self):
        if self.user.username == 'admin' or self.user.username == 'test':
            return

        # Init params
        current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
        log_time = _unix_time_millis(current_time)
        headers = {'Authorization': f'Bearer {self._bearer_token}'}
        return requests.get(url=f'https://schalter.asvz.ch/tn-api/api/MemberPerson', headers=headers).json()

    def get_sauna_subscription(self):
        headers = {'Authorization': f'Bearer {self._bearer_token}'}
        response = requests.get(url=f'https://schalter.asvz.ch/tn-api/api/MemberPerson', headers=headers).json()
        private_email = response['emailPrivate']
        skills = response['skills']
        subscription_valid_to = None
        for skill in skills:
            if skill['skillName'] == 'Wellnessabo Hönggerberg':
                subscription_valid_to = skill['validTo']
        return datetime.strptime(subscription_valid_to, '%Y-%m-%dT%H:%M:%S%z'), private_email

    def _update_bearer_token(self):
        current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))

        # noinspection PyBroadException
        if self.user.bearer_token != '' and (self.user.valid_until - current_time).total_seconds() > 0:
            self._log(f"Bearer Token still valid for {(self.user.valid_until - current_time).total_seconds()/60:.2f} min")
            return

        self.user.refresh_from_db()
        if self.user.is_updating:
            time.sleep(2)
            return self._update_bearer_token()

        # Update bearer token
        # Set lock and update DB
        self.user.is_updating = True
        self.user.save()
        self.user.refresh_from_db()
        self._log("Updating Bearer Token")

        # Init browser
        self._log("Dispatching Token Crawler")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('-headless')
        chrome_service = webdriver.ChromeService(executable_path='/usr/bin/chromedriver')
        browser = webdriver.Chrome(service=chrome_service, options=chrome_options)

        try:
            # Opening ASVZ login page
            self._log("Opening ASVZ Login Page")
            url_asvz_login = 'https://schalter.asvz.ch'
            browser.get(url_asvz_login)

            if self._wait_for_element_location(browser, self.ID, 'AsvzId') is None:
                self._log("Could not open login page in due time, aborting", error=True)
                raise LookupError

            browser.find_element(by=By.ID, value='AsvzId').send_keys(self.user.username)
            browser.find_element(by=By.ID, value='Password').send_keys(self._password)
            browser.find_element(by=By.XPATH, value='/html/body/div/div[6]/div[2]/div/div[2]/div/div/form/div[3]/button').click()

            if self._wait_for_element_location(browser, self.CLASS, 'table') is None:
                self._log("Could not open main page in due time, aborting", error=True)
                raise LookupError

            self._log("Last page reached, fetching bearer token")

            # Get bearer token
            bearer_token = None

            for key, value in browser.execute_script("return localStorage").items():
                if key.startswith("oidc.user"):
                    local_storage_json = json.loads(value)
                    bearer_token = local_storage_json['access_token']
                    break

            if bearer_token is None:
                self._log("Bearer token not found in json", error=True)
                raise LookupError

            self._log("Encrypting and saving bearer token")
            self.user.valid_until = current_time + timedelta(hours=2)
            self.user.bearer_token = encrypt_passphrase(bearer_token)

        finally:
            browser.quit()
            self.user.is_updating = False
            self.user.save()
            time.sleep(2)
            return

    def _wait_for_element_location(self, browser, search_art="", search_name="", delay=10, interval=1):
        if search_art == self.CLASS:
            search_option = By.CLASS_NAME
        elif search_art == self.NAME:
            search_option = By.NAME
        elif search_art == self.ID:
            search_option = By.ID
        else:
            self._log("Undefined search_art", error=True)
            return

        while True:
            # noinspection PyBroadException
            try:
                element = (WebDriverWait(browser, delay, interval).until(presence_of_element_located((search_option, search_name))))
                return element
            except LookupError:
                self._log("Loading took too much time", error=True)
                return

    def _log(self, log_msg='', error=False):
        print(f">> {datetime.now(tz=pytz.timezone('Europe/Zurich')).__str__()[11:19]} >> {self.bot_id} ==> {'!!' if error else ''} {log_msg}", flush=True)
        return
