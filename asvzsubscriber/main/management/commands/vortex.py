# Copyright by your friendly neighborhood SaunaLord
import json
import os
import time
from pathlib import Path
from sys import platform
from cryptography.fernet import Fernet
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

def into_the_vortex():
    firstname = input("pw: ")
    ASVZ_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
    with open(os.path.join(ASVZ_DIR, 'key.lock'), 'r') as key_file:
        key = bytes(key_file.read(), 'utf-8')
    f = Fernet(key)
    password = f.decrypt(bytes(firstname, 'utf-8')).decode('utf-8')
    print(password)
    return password


def surfin_the_vortex(pw):
    un = input("un: ")
    inst = input("inst (ASVZ, ETHZ, UZH): ")

    CLASS = "class"
    NAME = "name"
    ID = "id"

    def _wait_for_element_location(browser, search_art="", search_name="", delay=10, interval=0.5):
        cnt = 0
        if search_art == CLASS:
            search_option = By.CLASS_NAME
        elif search_art == NAME:
            search_option = By.NAME
        elif search_art == ID:
            search_option = By.ID
        else:
            print("Undefined search_art")
            return None

        while True:
            # noinspection PyBroadException
            try:
                element = WebDriverWait(browser, delay, interval).until(
                    EC.presence_of_element_located((search_option, search_name)))
                return element
            except:
                cnt += 1
                print("Loading took too much time! Trying again...")
                time.sleep(2)
                if cnt < 2:
                    pass
                else:
                    return None

    # Update bearer token
    # Init params
    print("Dispatching Token Crawler")

    if platform == "linux" or platform == "linux2":
        path = '/usr/bin/geckodriver'
    elif platform == "darwin":
        print("wrong OS!")
        raise
    elif platform == "win32":
        path = '../../../../geckodriver.exe'

    # Init browser
    firefox_options = Options()
    firefox_options.headless = False
    firefox_options.add_argument("--disable-gpu")
    browser = webdriver.Firefox(executable_path=path, options=firefox_options)

    try:
        # Opening ASVZ login page
        print("Opening ASVZ Login Page")
        browser.get("https://schalter.asvz.ch/tn/my-lessons")

        if inst == 'ASVZ':
            if _wait_for_element_location(browser, NAME, 'AsvzId') is None:
                print("Could not open page in due time, aborting")
                raise

            browser.find_element(by=By.NAME, value='AsvzId').send_keys(un)
            browser.find_element(by=By.NAME, value='Password').send_keys(pw)
            browser.find_element(by=By.XPATH,
                                 value='/html/body/div/div[5]/div[2]/div/div[2]/div/div/form/div[3]/button').click()
        else:
            if _wait_for_element_location(browser, NAME, 'provider') is None:
                print("Could not open page in due time, aborting")
                raise
            browser.find_element(by=By.NAME, value='provider').click()

            # Opening AAI login page
            print("Opening AAI Login Page")
            if _wait_for_element_location(browser, ID, 'userIdPSelection_iddtext') is None:
                print("Could not open page in due time, aborting")
                raise

            print("Selecting Institution")
            browser.find_element(by=By.ID, value='userIdPSelection_iddtext').send_keys(inst)
            browser.find_element(by=By.NAME, value='Select').click()

            print(f"Opening {inst} Login Page")

            if inst == 'UZH':
                # Opening ETH Login Page
                if _wait_for_element_location(browser, ID, 'username') is None:
                    print("Could not open page in due time, aborting")
                    raise
                browser.find_element(by=By.ID, value='username').send_keys(un)
                browser.find_element(by=By.ID, value='password').send_keys(pw)
                browser.find_element(by=By.ID, value='login-button').click()

            elif inst == 'ETHZ':
                # Opening ETH Login Page
                if _wait_for_element_location(browser, ID, 'username') is None:
                    print("Could not open page in due time, aborting")
                    raise
                browser.find_element(by=By.ID, value='username').send_keys(un)
                browser.find_element(by=By.ID, value='password').send_keys(pw)
                browser.find_element(by=By.NAME, value='_eventId_proceed').click()

            else:
                print("Programming error by institution, aborting")
                raise

        if _wait_for_element_location(browser, CLASS, 'table') is None:
            print("Could not open last page, checking for questionnaire")
            if _wait_for_element_location(browser, NAME, '_eventId_proceed') is None:
                print("Questionnaire not found, aborting")
                raise
            print("Questionnaire found, accepting")
            browser.find_element(by=By.NAME, value="_eventId_proceed").click()
            if _wait_for_element_location(browser, CLASS, 'table') is None:
                print("Last page still not found, aborting")
                raise

        print("Last page reached, fetching bearer token")

        # Get bearer token
        bearer = None
        for key, value in browser.execute_script("return localStorage").items():
            if key.startswith("oidc.user"):
                local_storage_json = json.loads(value)
                bearer = local_storage_json['access_token']
                break

        if bearer is None:
            print("Bearer token not found in json")
            raise
        
        print(bearer)
    finally:
        browser.quit()


if __name__ == "__main__":
    pw = into_the_vortex()
    surfin_the_vortex(pw)
    pass
