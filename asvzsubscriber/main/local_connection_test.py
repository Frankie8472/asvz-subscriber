# Copyright by your friendly neighborhood SaunaLord
import json
import urllib
import pytz
import requests
import time
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


def _unix_time_millis(dt):
    return round((dt - datetime.utcfromtimestamp(0).replace(tzinfo=timezone.utc)).total_seconds() * 1000)


class ASVZCrawler:
    def __init__(self):
        self.CLASS = "class"
        self.NAME = "name"
        self.ID = "id"
        self.headless = False
        self.bot_id = 'LOCAL'

        self.event_id = ""
        self.username = "FILL"
        self._password = "FILL"
        self._bearer_token = None

        self._update_bearer_token()

        self._log(self._bearer_token)
        return

    def get_enrollments(self):
        # Init params
        current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
        log_time = _unix_time_millis(current_time)

        headers = {'Authorization': f'Bearer {self._bearer_token}'}
        ret = requests.get(url=f'https://schalter.asvz.ch/tn-api/api/Enrollments??t={log_time}', headers=headers).json()
        return ret

    def _update_bearer_token(self):
        # Update bearer token
        # Set lock and update DB
        self._log("Updating Bearer Token")

        # Init browser
        self._log("Dispatching Token Crawler")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("-headless")
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

            browser.find_element(by=By.ID, value='AsvzId').send_keys(self.username)
            browser.find_element(by=By.ID, value='Password').send_keys(self._password)
            time.sleep(1)
            browser.find_element(by=By.XPATH, value=".//html//body//*//form//div[3]//button").click()

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
                raise

            self._log("Encrypting and saving bearer token")
            self._bearer_token = bearer_token

        finally:
            browser.quit()
            return

    def subscribe_to_event(self):
        request_id = ''
        lesson_register_time_unix = datetime.now(tz=pytz.timezone('Europe/Zurich'))
        sleep_time_offset = 3
        ret = 422
        cnt = 0
        while (ret != 201) and (cnt < sleep_time_offset):
            # noinspection PyBroadException
            try:

                headers = {'Authorization': f'Bearer {self._bearer_token}'}
                json_data = {}
                ret = requests.post(
                    url=f'https://schalter.asvz.ch/tn-api/api/Lessons/{request_id}/Enrollment??t={lesson_register_time_unix}',
                    headers=headers,
                    json=json_data
                ).status_code

                self._log(f"Status Code: {ret}")

            except:
                self._log(f"Request failed", error=True)
                pass

            step = 0.2
            time.sleep(step)
            cnt += step

        if ret != 201:
            self._log("Registration Failed")
        else:
            self._log("Registration Succeeded")

        return

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
                    ec.presence_of_element_located((search_option, search_name)))
                return element
            except:
                cnt += 1
                self._log("Loading took too much time! Trying again...", error=True)
                time.sleep(2)
                if cnt < 2:
                    pass
                else:
                    return None

    def get_sauna_subscription(self):
        headers = {'Authorization': f'Bearer {self._bearer_token}'}
        response = requests.get(url=f'https://schalter.asvz.ch/tn-api/api/MemberPerson', headers=headers).json()
        private_email = response['emailPrivate']
        skills = response['skills']
        subscription_valid_to = None
        for skill in skills:
            if skill['skillName'] == 'Wellnessabo Hönggerberg':
                subscription_valid_to = skill['validTo']
        return subscription_valid_to, private_email

    def _log(self, log_msg='', error=False):
        print(
            f">> {datetime.now(tz=pytz.timezone('Europe/Zurich')).__str__()[11:19]} >> {self.bot_id} ==> {'!!' if error else ''} {log_msg}",
            flush=True)


def asvz_api():
    default_url = 'https://asvz.ch/asvz_api/event_search?_format=json'
    with urllib.request.urlopen(default_url) as url:
        default_data = json.loads(url.read().decode())
    print(default_data)


def main():
    obj = ASVZCrawler()
    enrollments = obj.get_enrollments()
    for objs in enrollments:
        print(objs)
    print(obj.get_sauna_subscription())
    #obj.subscribe_to_event()


if __name__ == "__main__":
    main()
    #asvz_api()
