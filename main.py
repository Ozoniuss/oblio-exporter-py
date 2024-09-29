from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
import os

SUSPEND = True
PROFILE_PATH = r"path-to-firexoz"


def suspend():
    if SUSPEND:
        try:
            input("press anything to continue...")
        except:  # capture everything including ctrl C
            os._exit(1)


# Set Firefox options to use the existing profile
firefox_options = Options()
firefox_profile = FirefoxProfile(PROFILE_PATH)
firefox_options.profile = firefox_profile


driver = webdriver.Firefox(options=firefox_options)

driver.implicitly_wait(0.5)

driver.get("https://www.oblio.eu/account")
# driver.get("https://www.selenium.dev/selenium/web/web-form.html")

# title = driver.title
suspend()

username = driver.find_element(by=By.ID, value="username")
username.send_keys("")
suspend()
password = driver.find_element(by=By.ID, value="password")
password.send_keys("")
suspend()

submit_button = driver.find_element(
    by=By.XPATH,
    value="""//button[@type="submit" and .//span[contains(text(), "Intra in cont")]]""",
)
submit_button.click()

suspend()

# text_box.send_keys("Selenium")
# submit_button.click()

# message = driver.find_element(by=By.ID, value="message")
# text = message.text

# suspend()

driver.quit()
