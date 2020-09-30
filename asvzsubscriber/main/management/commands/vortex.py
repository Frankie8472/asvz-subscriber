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


def surfin_the_vortex():
    pass

if __name__ == "__main__":
    # into_the_vortex('')
    surfin_the_vortex('https://schalter.asvz.ch/tn/lessons/142303')
