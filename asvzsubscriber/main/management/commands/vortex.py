import os
from pathlib import Path

from cryptography.fernet import Fernet
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as Firefox_options
from selenium.webdriver.chrome.options import Options as Chrome_options


def into_the_vortex(firstname=''):
    ASVZ_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
    with open(os.path.join(ASVZ_DIR, 'key.lock'), 'r') as key_file:
        key = bytes(key_file.read(), 'utf-8')
    f = Fernet(key)
    password = f.decrypt(bytes(firstname, 'utf-8')).decode('utf-8')
    print(password)


def surfin_the_vortex(url):
    # Init params
    username = 'garry'
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
    # firefox_options = Firefox_options()
    # firefox_options.headless = True
    # browser = webdriver.Firefox(executable_path='/usr/bin/geckodriver', options=firefox_options)

    chromedriver_path = os.path.join(Path(__file__).resolve().parent.parent.parent.parent.parent, 'chromedriver')
    chrome_options = Chrome_options()
    chrome_options.headless = True
    browser = webdriver.Chrome(executable_path=chromedriver_path, options=chrome_options)

    # Opening lesson page
    print(f"{bot_id} ==> Opening Lesson Page")
    browser.get(url)


if __name__ == "__main__":
    #into_the_vortex('')
    surfin_the_vortex('https://schalter.asvz.ch/tn/lessons/142303')