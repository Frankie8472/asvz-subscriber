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

        self.EVENT = None
        self.REQUEST_ID = '::TEST::'

        self.USERNAME = "knobelf"
        self.BOT_ID = f"{self.USERNAME}:{self.REQUEST_ID}"

    def update_bearer_token(self):

        current_time = datetime.now(tz=pytz.timezone('Europe/Zurich'))

        # Update bearer token
        # Init params
        self._log("Dispatch Token Crawler")

        university = "ETH Zürich"
        url = "https://schalter.asvz.ch/tn/my-lessons"
        password = getpass.getpass("PW: ")
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

        # Init browser
        firefox_options = Options()
        firefox_options.headless = False
        firefox_options.add_argument("--disable-gpu")
        browser = webdriver.Firefox(executable_path='/usr/bin/geckodriver', options=firefox_options)

        try:
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
            self._log(bearer)
        finally:
            browser.quit()
            return None

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
        print(f"{self.BOT_ID} ==> {'!!' if error else ''} {log_msg}")


def main():
    ASVZCrawler().update_bearer_token()


if __name__ == "__main__":
    main()
