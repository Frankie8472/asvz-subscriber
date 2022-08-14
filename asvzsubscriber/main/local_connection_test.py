import json
import pytz
import requests
import time
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import getpass

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
        self.username = "knobelf"
        self.institution_name = 'ETHZ'
        self._password = "***REMOVED***"
        self._bearer_token = None

        self._update_bearer_token()

        self._log(str(self._bearer_token))

        if self._bearer_token is not None and self.event_id is not None and self.event_id is not "":
            self._subscribe_to_event()
        return

    def _subscribe_to_event(self):
        current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
        lesson_register_time_unix = _unix_time_millis(current_time)
        # Wait until 5 sec before reg opening
        self._log('Wait for registration to open')
        sleep_time_offset = 3

        # Spam Post requests
        self._log('Trying to register')

        ret = 422
        cnt = 0
        while (ret != 201) and (cnt < 2 * sleep_time_offset):
            # noinspection PyBroadException
            try:
                cookies = {
                    'cookie-agreed': '0',
                }

                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en,en-US;q=0.7,de;q=0.3',
                    # 'Accept-Encoding': 'gzip, deflate, br',
                    'Authorization': f'Bearer {self._bearer_token}',
                    # Already added when you pass json=
                    # 'Content-Type': 'application/json',
                    'Origin': 'https://schalter.asvz.ch',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Referer': f'https://schalter.asvz.ch/tn/lessons/{self.event_id}',
                    # 'Cookie': 'cookie-agreed=0',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                }

                json_data = {}

                response = requests.post(
                    f'https://schalter.asvz.ch/tn-api/api/Lessons/{self.event_id}/Enrollment??t={lesson_register_time_unix}', cookies=cookies,
                    headers=headers, json=json_data)
                ret = response.status_code
                self._log(f"Status Code: {ret}")
                self._log(f"Status Code: {response}")

            except:
                self._log(f"Request failed", error=True)
                pass

            step = 0.1
            time.sleep(step)
            cnt += step

        if ret != 201:
            self._log("Registration Failed")
        else:
            self._log("Registration Succeeded")

        return


    def get_enrollments(self):
        # Init params
        current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))
        log_time = _unix_time_millis(current_time)

        cookies = {
            'cookie-agreed': '0',
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en,en-US;q=0.7,de;q=0.3',
            # 'Accept-Encoding': 'gzip, deflate, br',
            'Authorization': f'Bearer {self._bearer_token}',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': 'https://schalter.asvz.ch/tn/my-lessons',
            # 'Cookie': 'cookie-agreed=0',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            # Requests doesn't support trailers
            # 'TE': 'trailers',
        }

        ret = requests.get(
            f'https://schalter.asvz.ch/tn-api/api/Enrollments??t={log_time}',
            cookies=cookies,
            headers=headers
        ).json()

        return ret

    def _update_bearer_token(self):
        self._log("Dispatching Token Crawler")

        # Init browser
        firefox_options = Options()
        firefox_options.headless = self.headless
        firefox_options.add_argument("--disable-gpu")
        browser = webdriver.Firefox(executable_path='/usr/bin/geckodriver', options=firefox_options)

        try:
            # Opening ASVZ login page
            self._log("Opening ASVZ Login Page")
            browser.get("https://schalter.asvz.ch/tn/my-lessons")

            if self.institution_name == 'ASVZ':
                if self._wait_for_element_location(browser, self.ID, 'AsvzId') is None:
                    self._log("Could not open page in due time, aborting", error=True)
                    raise
                print("reached")
                browser.find_element(by=By.NAME, value='AsvzId').send_keys(self.username)
                print("reached")
                browser.find_element(by=By.NAME, value='Password').send_keys(self._password)
                print("reached")
                #browser.find_element(by=By.CLASS_NAME, value='btn btn-primary btn-block').click()
                browser.find_element(by=By.XPATH, value='/html/body/div/div[5]/div[2]/div/div[2]/div/div/form/div[3]/button').click()
                print("reached")
            else:
                if self._wait_for_element_location(browser, self.NAME, 'provider') is None:
                    self._log("Could not open page in due time, aborting", error=True)
                    raise
                browser.find_element(by=By.NAME, value='provider').click()

                # Opening AAI login page
                self._log("Opening AAI Login Page")
                if self._wait_for_element_location(browser, self.ID, 'userIdPSelection_iddtext') is None:
                    self._log("Could not open page in due time, aborting", error=True)
                    raise

                self._log("Selecting Institution")
                browser.find_element(by=By.ID, value='userIdPSelection_iddtext').send_keys(self.institution_name)
                browser.find_element(by=By.NAME, value='Select').click()

                self._log(f"Opening {self.institution_name} Login Page")

                if self.institution_name == 'ETHZ' or self.institution_name == 'UZH':
                    # Opening ETH Login Page
                    if self._wait_for_element_location(browser, self.ID, 'username') is None:
                        self._log("Could not open page in due time, aborting", error=True)
                        raise
                    browser.find_element(by=By.ID, value='username').send_keys(self.username)
                    browser.find_element(by=By.ID, value='password').send_keys(self._password)
                    browser.find_element(by=By.NAME, value='_eventId_proceed').click()
                else:
                    self._log("Programming error by institution, aborting", error=True)
                    raise

            if self._wait_for_element_location(browser, self.CLASS, 'table') is None:
                self._log("Could not open last page, checking for questionnaire")
                if self._wait_for_element_location(browser, self.NAME, '_eventId_proceed') is None:
                    self._log("Questionnaire not found, aborting", error=True)
                    raise
                self._log("Questionnaire found, accepting")
                browser.find_element(by=By.NAME, value="_eventId_proceed").click()
                if self._wait_for_element_location(browser, self.CLASS, 'table') is None:
                    self._log("Last page still not found, aborting", error=True)
                    raise

            self._log("Last page reached, fetching bearer token")

            # Get bearer token
            bearer = None
            for key, value in browser.execute_script("return localStorage").items():
                if key.startswith("oidc.user"):
                    local_storage_json = json.loads(value)
                    bearer = local_storage_json['access_token']
                    break

            if bearer is None:
                self._log("Bearer token not found in json", error=True)
                raise

            self._log("Encrypting and saving bearer token")
            self._bearer_token = bearer
        finally:
            browser.quit()
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
        print(f">> {datetime.now(tz=pytz.timezone('Europe/Zurich')).__str__()[11:19]} >> {self.bot_id} ==> {'!!' if error else ''} {log_msg}", flush=True)



def main():
    obj = ASVZCrawler()
    json = obj.get_enrollments()
    print(json)
    for obj in json:
        print(obj)


if __name__ == "__main__":
    main()
