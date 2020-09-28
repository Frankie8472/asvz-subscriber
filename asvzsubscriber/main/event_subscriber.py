import time
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.expected_conditions import visibility_of_element_located
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import pytz
from datetime import datetime
import ntplib

from main.models import ASVZEvent


class element_located_not_disabled(object):
    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver):
        element = visibility_of_element_located(self.locator)(driver)
        if 'disabled' in element.get_attribute('class'):
            return False
        else:
            return element


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
            element = WebDriverWait(browser, delay, interval).until(EC.presence_of_element_located((search_option, search_name)))
            return element
        except TimeoutException:
            cnt += 1
            print(f"{bot_id} !! Loading took too much time! Trying again...")
            time.sleep(5)
            if cnt < 5:
                pass
            else:
                return browser.find_element(search_option, search_name)


def event_subscriber(event: ASVZEvent, username, password, url):
    bot_id = f"{username}:{url[-6:]}"
    lesson_url = url
    sleeptimeoffset = 0.0

    asvzlogin_class = "btn-default"
    aailogin_name = 'provider'
    institution_selection_id = 'userIdPSelection_iddtext'
    institution_submit_name = 'Select'
    eth_username_id = 'username'
    eth_password_id = 'password'
    eth_login_name = '_eventId_proceed'
    lesson_register_id = 'btnRegister'
    lesson_confirm_xpath = '/html/body/app-root/div/div[2]/app-lesson-details/div/div/app-lessons-enrollment-button/div[1]/div/alert/div'

    firefox_options = Options()
    firefox_options.headless = True
    browser = webdriver.Firefox(executable_path='/usr/bin/geckodriver', options=firefox_options)
    print(f"{bot_id} ==> Opening Lesson Page")
    browser.get(lesson_url)
    wait_for_element_location(bot_id, browser, "class", asvzlogin_class).click()
    print(f"{bot_id} ==> Opening ASVZ Login Page")
    time.sleep(5)
    wait_for_element_location(bot_id, browser, "name", aailogin_name).click()

    print(f"{bot_id} ==> Opening AAI Login Page")
    time.sleep(1)
    print(f"{bot_id} ==> Selecting Institution")
    dropdown_field = wait_for_element_location(bot_id, browser, "id", institution_selection_id)
    # dropdown_field.clear()
    dropdown_field.send_keys('ETH Zürich')
    time.sleep(1)
    browser.find_element_by_name(institution_submit_name).click()
    print(f"{bot_id} ==> Opening ETH Login Page")
    wait_for_element_location(bot_id, browser, "id", eth_username_id).send_keys(username)
    time.sleep(0.5)
    browser.find_element_by_id(eth_password_id).send_keys(password)
    browser.find_element_by_name(eth_login_name).click()
    wait_for_element_location(bot_id, browser, "id", lesson_register_id)
    time.sleep(0.5)

    print(f"{bot_id} ==> Wait for register start")
    timezone = datetime.now(pytz.timezone('Europe/Zurich')).tzinfo
    lesson_register_time_datetime = event.register_start_date.replace(tzinfo=timezone)

    cnt = 0
    while True:
        try:
            current_time = datetime.fromtimestamp(ntplib.NTPClient().request('ch.pool.ntp.org', version=3).tx_time, timezone)
            break
        except ValueError:
            print(f"{bot_id} ==> NTP Error, trying again in 10 seconds")
            cnt += 1
            time.sleep(10)
            if cnt < 10:
                pass

    timedelta = lesson_register_time_datetime - current_time
    if timedelta.total_seconds() > 0.0:
        time.sleep(timedelta.total_seconds() - sleeptimeoffset)

    print(f"{bot_id} ==> Registering")
    browser.find_element_by_id('btnRegister').click()
    elem = wait_for_element_location(bot_id, browser, "xpath", lesson_confirm_xpath, delay=30)
    print(f"{bot_id} ==> " + str.split(elem.text, '\n')[-1])
    browser.quit()
    print(f"{bot_id} ==> Deleting Event")
    event.delete()
    return


# For test purposes
if __name__ == '__main__':
    event_subscriber(username="knobelf", password="", url="https://schalter.asvz.ch/tn/lessons/142133")
