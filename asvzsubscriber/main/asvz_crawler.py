# Copyright by your friendly neighborhood SaunaLord

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
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from .models import ASVZEvent, BearerToken


def encrypt_passphrase(passphrase):
    return _get_cryptor().encrypt(bytes(passphrase, 'utf-8')).decode('utf-8')


def _decrypt_passphrase(passphrase):
    return _get_cryptor().decrypt(bytes(passphrase, 'utf-8')).decode('utf-8')


def _get_cryptor():
    ASVZ_DIR = Path(__file__).resolve().parent.parent.parent
    with open(os.path.join(ASVZ_DIR, 'key.lock'), 'r') as key_file:
        key = bytes(key_file.read(), 'utf-8')
    return Fernet(key)


def _unix_time_millis(dt):
    return round((dt - datetime.utcfromtimestamp(0).replace(tzinfo=timezone.utc)).total_seconds() * 1000)


class ASVZCrawler:
    def __init__(self, obj=None):
        if (obj is None) or (not isinstance(obj, ASVZEvent) and not isinstance(obj, User)):
            self.BOT_ID = f"{'ERROR'}"
            self._log("No user or no event given", error=True)
            return

        self.CLASS = "class"
        self.NAME = "name"
        self.ID = "id"

        self.EVENT = None
        self.USER = obj
        self.REQUEST_ID = ''

        if isinstance(obj, ASVZEvent):
            self.EVENT: ASVZEvent = obj
            self.USER = User.objects.get(username=self.EVENT.user)
            self.REQUEST_ID = self.EVENT.url[-6:]

        self.USERNAME = self.USER.username
        self.BOT_ID = f"{self.USERNAME}:{self.REQUEST_ID}"
        self.BEARER = self._get_bearer_token()

        if self.EVENT is not None:
            self._subscribe_to_event()

    def _subscribe_to_event(self):
        if self.EVENT is None:
            self._log('Event is None, cannot subscribe if no event given', error=True)
            return

        # Wait until 5 sec before reg opening
        self._log('Wait for registration to open')

        lesson_register_time_datetime = self.EVENT.register_start_date.replace(tzinfo=timezone.utc)
        lesson_register_time_unix = _unix_time_millis(lesson_register_time_datetime)
        current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
        time_delta = lesson_register_time_datetime - current_time
        sleep_time_offset = 3
        if time_delta.total_seconds() > 0.0:
            time.sleep(time_delta.total_seconds() - sleep_time_offset)

        # Spam Post requests
        self._log('Trying to register')

        ret = 422
        cnt = 0
        while (ret != 201) and (cnt < 2 * sleep_time_offset):
            # noinspection PyBroadException
            try:
                ret = requests.post(
                    url=f'https://schalter.asvz.ch/tn-api/api/Lessons/{self.REQUEST_ID}/enroll?%3Ft={lesson_register_time_unix}',
                    headers={
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0',
                        'Accept': 'application/json, text/plain, */*',
                        'Accept-Language': 'en,en-US;q=0.7,de;q=0.3',
                        'Authorization': f'Bearer {self.BEARER}',
                        'Content-Type': 'application/json',
                        'Origin': 'https://schalter.asvz.ch',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Referer': f'https://schalter.asvz.ch/tn/lessons/{self.REQUEST_ID}',
                    }
                ).status_code
                self._log(f"Status Code: {ret}")

            except:
                self._log(f"Request failed", error=True)
                pass

            step = 0.01
            time.sleep(step)
            cnt += step

        if ret == 422:
            self._log("Registration Failed")
        else:
            self._log("Registration Succeeded")

        # Delete Event
        self._log("Deleting Event")
        self.EVENT.delete()

        return

    def get_enrollments(self):
        if self.USERNAME == 'admin' or self.USERNAME == 'test':
            return None

        # Init params
        current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
        log_time = _unix_time_millis(current_time)

        ret = requests.get(
            url=f'https://schalter.asvz.ch/tn-api/api/Enrollments??t={log_time}',
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en,en-US;q=0.7,de;q=0.3',
                'Authorization': f'Bearer {self.BEARER}',
                'Content-Type': 'application/json',
                'Origin': 'https://schalter.asvz.ch',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Referer': f'https://schalter.asvz.ch/tn/my-lessons',
            }
        ).json()

        return ret

    def _get_bearer_token(self):
        if self.USERNAME == 'admin' or self.USERNAME == 'test':
            return None

        return _decrypt_passphrase(self.update_bearer_token().bearerToken)

    def update_bearer_token(self):
        if self.USERNAME == 'admin' or self.USERNAME == 'test':
            return None

        current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))

        # noinspection PyBroadException
        try:
            bearerToken = BearerToken.objects.get(user=self.USER)
        except:
            self._log("Create new BearerToken")
            bearerToken = BearerToken.objects.create(
                user=self.USER,
                bearerToken='',
                valid_until=current_time - timedelta(hours=2),
                is_updating=False
            )

        if bearerToken.is_updating:
            time.sleep(2)
            return self.update_bearer_token()
        elif bearerToken.bearerToken != '' and (bearerToken.valid_until - current_time).total_seconds() > 0:
            return bearerToken
        else:
            bearerToken.is_updating = True
            bearerToken.save()

        # Update bearer token
        # Init params
        self._log("Dispatch Token Crawler")

        university = self.USER.last_name
        url = "https://schalter.asvz.ch/tn/my-lessons"
        password = _decrypt_passphrase(self.USER.first_name)
        aailogin_name = 'provider'
        institution_selection_id = 'userIdPSelection_iddtext'
        institution_submit_name = 'Select'
        eth_username_id = 'username'
        uzh_username_id = 'username'
        eth_password_id = 'password'
        uzh_password_id = 'password'
        eth_login_name = '_eventId_proceed'
        uzh_login_name = '_eventId_proceed'
        questionnaire_name = '_eventId_proceed'
        final_page_identifier_class = 'table'

        try:
            # Init browser
            firefox_options = Options()
            firefox_options.headless = True
            firefox_options.add_argument("--disable-gpu")
            browser = webdriver.Firefox(executable_path='/usr/bin/geckodriver', options=firefox_options)

            # Opening ASVZ login page
            self._log("Opening ASVZ Login Page")
            browser.get(url)

            if self._wait_for_element_location(browser, self.NAME, aailogin_name) is None:
                self._log("Could not open page in due time, aborting", error=True)
                raise
            browser.find_element_by_name(aailogin_name).click()

            # Opening AAI login page
            self._log("Opening AAI Login Page")
            if self._wait_for_element_location(browser, self.ID, institution_selection_id) is None:
                self._log("Could not open page in due time, aborting", error=True)
                raise

            self._log("Selecting Institution")
            browser.find_element_by_id(institution_selection_id).send_keys(university)
            browser.find_element_by_name(institution_submit_name).click()

            self._log(f"Opening {university} Login Page")
            if university == 'ETH Zürich':
                # Opening ETH Login Page
                if self._wait_for_element_location(browser, self.ID, eth_username_id) is None:
                    self._log("Could not open page in due time, aborting", error=True)
                    raise
                browser.find_element_by_id(eth_username_id).send_keys(self.USERNAME)
                browser.find_element_by_id(eth_password_id).send_keys(password)
                browser.find_element_by_name(eth_login_name).click()

            elif university == 'Universität Zürich':
                # Opening ETH Login Page
                if self._wait_for_element_location(browser, self.ID, uzh_username_id) is None:
                    self._log("Could not open page in due time, aborting", error=True)
                    raise
                browser.find_element_by_id(uzh_username_id).send_keys(self.USERNAME)
                browser.find_element_by_id(uzh_password_id).send_keys(password)
                browser.find_element_by_name(uzh_login_name).click()
            else:
                self._log("Corrupt university", error=True)
                raise

            if self._wait_for_element_location(browser, self.CLASS, final_page_identifier_class) is None:
                self._log("Could not open last page, checking for questionnaire")
                if self._wait_for_element_location(browser, self.NAME, questionnaire_name) is None:
                    self._log("Questionnaire not found, aborting", error=True)
                    raise
                self._log("Questionnaire found, accepting")
                browser.find_element_by_name("_eventId_proceed").click()
                if self._wait_for_element_location(browser, self.CLASS, final_page_identifier_class) is None:
                    self._log("Last page still not found, aborting", error=True)
                    raise

            self._log("Last page reached, fetching bearer token")

            # Get bearer token
            bearer = None
            for key, value in browser.execute_script("return localStorage").items():
                if key.startswith("oidc.user"):
                    localStorage_json = json.loads(value)
                    bearer = localStorage_json['access_token']
                    break

            if bearer is None:
                self._log("BearerToken Not found in json", error=True)
                raise

            self._log("Encrypting and saving bearer token")
            bearerToken.valid_until = current_time + timedelta(hours=2)
            bearerToken.bearerToken = encrypt_passphrase(bearer)
        finally:
            browser.quit()
            bearerToken.is_updating = False
            bearerToken.save()
            return bearerToken

    def _wait_for_element_location(self, browser, search_art="", search_name="", delay=10, interval=0.5):
        cnt = 0
        if search_art == self.CLASS:
            search_option = By.CLASS_NAME
        elif search_art == self.NAME:
            search_option = By.NAME
        elif search_art == self.ID:
            search_option = By.ID
        else:
            self._log("Undefined search_art", error=True)
            return None

        while True:
            # noinspection PyBroadException
            try:
                element = WebDriverWait(browser, delay, interval).until(
                    EC.presence_of_element_located((search_option, search_name)))
                return element
            except:
                cnt += 1
                self._log("Loading took too much time! Trying again...", error=True)
                time.sleep(2)
                if cnt < 2:
                    pass
                else:
                    return None

    def _log(self, log_msg='', error=False):
        print(f">> {datetime.now(tz=pytz.timezone('Europe/Zurich')).__str__()[11:19]} >> {self.BOT_ID} ==> {'!!' if error else ''} {log_msg}", flush=True)
