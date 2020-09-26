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


class element_located_not_disabled(object):
    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver):
        element = visibility_of_element_located(self.locator)(driver)
        if 'disabled' in element.get_attribute('class'):
            return False
        else:
            return element


def wait_for_element_location(bot_id, browser, xpath, delay=5, interval=0.5):
    try:
        element = WebDriverWait(browser, delay, interval).until(EC.presence_of_element_located((By.XPATH, xpath)))
        return element
    except TimeoutException:
        print(f"{bot_id} !! Loading took too much time!")


def event_subscriber(username, password, url):
    bot_id = f"{username}:{url[-6:]}"
    lesson_url = url
    asvzlogin_xpath = '/html/body/app-root/div/div[2]/app-lesson-details/div/div/app-lessons-enrollment-button/button'
    aailogin_xpath = '/html/body/div/div[5]/div[2]/div/div[2]/div/form/div/p/button'
    institution_selection_xpath = '//*[@id="userIdPSelection_iddtext"]'
    institution_submit_xpath = '/html/body/div/div/div[2]/form/div/div[1]/input'
    eth_username_xpath = '//*[@id="username"]'
    eth_password_xpath = '//*[@id="password"]'
    eth_login_xpath = '/html/body/div[2]/main/section/div[2]/div[2]/form/div[5]/button'
    lesson_register_xpath = '//*[@id="btnRegister"]'
    lesson_register_time_xpath = '/html/body/app-root/div/div[2]/app-lesson-details/div/div/tabset/div/tab/div/div/div/div[1]/div/div[2]/app-lesson-properties-display/dl[10]/dd'
    lesson_confirm_xpath = '/html/body/app-root/div/div[2]/app-lesson-details/div/div/app-lessons-enrollment-button/div[1]/div/alert/div'

    firefox_options = Options()
    firefox_options.headless = True
    browser = webdriver.Firefox(firefox_binary='/usr/bin/geckodriver', options=firefox_options)
    print(f"{bot_id} ==> Opening Lesson Page")
    browser.get(lesson_url)
    wait_for_element_location(bot_id, browser, asvzlogin_xpath).click()
    print(f"{bot_id} ==> Opening ASVZ Login Page")
    time.sleep(0.5)
    wait_for_element_location(bot_id, browser, aailogin_xpath).click()
    print(f"{bot_id} ==> Opening AAI Login Page")
    time.sleep(1)
    print(f"{bot_id} ==> Selecting Institution")
    dropdown_field = wait_for_element_location(bot_id, browser, institution_selection_xpath)
    # dropdown_field.clear()
    dropdown_field.send_keys('ETH Zürich')
    time.sleep(1)
    browser.find_element_by_xpath(institution_submit_xpath).click()
    print(f"{bot_id} ==> Opening ETH Login Page")
    wait_for_element_location(bot_id, browser, eth_username_xpath).send_keys(username)
    time.sleep(0.5)
    browser.find_element_by_xpath(eth_password_xpath).send_keys(password)
    browser.find_element_by_xpath(eth_login_xpath).click()
    wait_for_element_location(bot_id, browser, lesson_register_xpath)
    time.sleep(0.5)
    print(f"{bot_id} ==> Wait for register start")
    lesson_register_time_str = browser.find_element_by_xpath(lesson_register_time_xpath).text[4:20]
    timezone = datetime.now(pytz.timezone('Europe/Zurich')).tzinfo
    lesson_register_time_datetime = datetime.strptime(lesson_register_time_str, '%d.%m.%Y %H:%M').replace(tzinfo=timezone)
    current_time = datetime.fromtimestamp(ntplib.NTPClient().request('ch.pool.ntp.org', version=3).tx_time, timezone)
    timedelta = lesson_register_time_datetime - current_time
    if timedelta.total_seconds() > 0.0:
        time.sleep(timedelta.total_seconds())
    print(f"{bot_id} ==> Registering")
    browser.find_element_by_xpath('//*[@id="btnRegister"]').click()
    elem = wait_for_element_location(bot_id, browser, lesson_confirm_xpath)
    print(f"{bot_id} ==> " + str.split(elem.text, '\n')[-1])
    browser.quit()
    return


# For test purposes
if __name__ == '__main__':
    event_subscriber(username="knobelf", password="", url="")
