import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.support.ui import Select

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

import os

SUSPEND = True


def suspend():
    if SUSPEND:
        try:
            input("press anything to continue...")
        except:  # capture everything including ctrl C
            os._exit(1)


def get_login_code() -> str:
    code = input("what is the 6 digits code? >")
    return code


def wait_for_element(driver: WebDriver, by: By, element_identifier, timeout=5):
    try:
        element_present = EC.presence_of_element_located((by, element_identifier))
        WebDriverWait(driver, timeout).until(element_present)
    except TimeoutException:
        print(f"timed out waiting for {element_identifier}", file=sys.stderr)
        return None
    return driver.find_element(by, element_identifier)


def init_driver() -> WebDriver:
    # Set Firefox options to use the existing profile
    firefox_options = Options()

    profile_path = os.getenv("OBLIO_FIREFOX_PROFILE_PATH")
    if profile_path not in [None, ""]:

        print(f"using profile path {profile_path}")

        firefox_profile = FirefoxProfile(profile_path)
        firefox_options.profile = firefox_profile

    driver = webdriver.Firefox(options=firefox_options)

    return driver


def close_bitwarden(driver: WebDriver):
    wait = WebDriverWait(driver, 5)
    try:
        bitwarder_header = driver.find_element(
            by=By.XPATH,
            value="//div//*[contains(text(), 'Should Bitwarden remember this password for you?')]",
        )
        close_button = bitwarder_header.find_element(by=By.ID, value="close-button")
        close_button.click()
        print("closing bitwarden")

    # No such element
    except Exception as e:
        print("skipping bitwarden close")
        return


def get_oblio_data(driver: WebDriver):

    close_bitwarden(driver)
    suspend()

    wait = WebDriverWait(driver, 2)  # waits up to 10 seconds

    driver.get("https://www.oblio.eu/account")

    try:
        close_initial_popup_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".btn.btn-sm.btn-square.btn-outline-warning")
            )
        )
        close_initial_popup_button.click()
    except TimeoutException:
        print("starting popup did not show")

    wait = WebDriverWait(driver, 10)

    # Wait for modal-backdrop fade and modal-backdrop show to dissapear because
    # it's an animation that fucking blocks the button from being clickable.
    element_to_wait_for = (By.CSS_SELECTOR, ".modal-backdrop.fade")
    wait.until(EC.invisibility_of_element_located(element_to_wait_for))
    element_to_wait_for = (By.CSS_SELECTOR, ".modal-backdrop.show")
    wait.until(EC.invisibility_of_element_located(element_to_wait_for))

    close_initial_popup_button = wait.until(
        EC.element_to_be_clickable((By.ID, "switch-company-menu"))
    )
    close_initial_popup_button.click()

    # Get companies list
    dropdown_items = wait.until(
        EC.visibility_of_all_elements_located(
            (By.CSS_SELECTOR, ".dropdown-item.leave-confirm.comp-list")
        )
    )

    dropdown_items[0].click()

    # go to the import/export page for the company
    driver.get("https://www.oblio.eu/account/import_export")

    export_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//div[contains(h6, 'e-Facturi Furnizori (XML+PDF)')]/following-sibling::div//button[text()='Exporta']",
            )
        )
    )

    # firefox bug:(
    # https://stackoverflow.com/questions/44777053/selenium-movetargetoutofboundsexception-with-firefox
    driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
    time.sleep(1)

    export_button.click()

    date_selection = wait.until(
        EC.element_to_be_clickable((By.ID, "daterange-interval-export-efct2"))
    )
    date_selection.click()

    big_calendar_frame = driver.find_element(
        by=By.CLASS_NAME,
        value="daterangepicker.ltr.show-ranges.show-calendar.openscenter.custom-scroll",
    )
    big_calendar_wait = WebDriverWait(big_calendar_frame, 10)

    calendar_element = big_calendar_wait.until(
        EC.visibility_of_any_elements_located((By.CLASS_NAME, "drp-calendar.left"))
    )
    calendar_div = calendar_element[0]

    # # Select the month if it's not already set to August 2024
    month_select = Select(calendar_div.find_element(By.CSS_SELECTOR, ".monthselect"))

    if month_select.first_selected_option.text != "August":
        month_select.select_by_visible_text("August")
    time.sleep(1)

    # I got an error like the following:
    # selenium.common.exceptions.StaleElementReferenceException: Message: The element with the reference be055f0a-476f-4363-8e0e-0fe853f7cb4a is stale; either its node document is not the active document, or it is no longer connected to the DOM;
    # I believe when you change the month the Select item rerenders. Creating it
    # here fixes it.
    year_select = Select(calendar_div.find_element(By.CSS_SELECTOR, ".yearselect"))
    if year_select.first_selected_option.text != "2024":
        year_select.select_by_value("2024")

    # Wait until the calendar is loaded and available dates are visible

    calendar_table = WebDriverWait(calendar_div, 10).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "calendar-table"))
    )

    available_dates = calendar_table.find_elements(
        By.XPATH, ".//td[contains(@class, 'available')]"
    )
    first_date_idx = second_date_idx = None

    # calendar will always contain days from previous and next month. It's okay
    # to find first 1 and last 1.
    for idx, date in enumerate(available_dates):
        print(idx, date.text)
        if date.text == "1":
            if first_date_idx is None:
                first_date_idx = idx
            else:
                second_date_idx = idx - 1
                break

    available_dates[first_date_idx].click()

    calendar_table = WebDriverWait(calendar_div, 10).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "calendar-table"))
    )

    available_dates = calendar_table.find_elements(
        By.XPATH, ".//td[contains(@class, 'available')]"
    )
    first_date_idx = second_date_idx = None

    # classes change upon click... :(
    for idx, date in enumerate(available_dates):
        print(idx, date.text)
        if date.text == "1":
            if first_date_idx is None:
                first_date_idx = idx
            else:
                second_date_idx = idx - 1
                break

    available_dates[second_date_idx].click()

    apply_button = big_calendar_wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, './/button[contains(text(), "Aplica")]')
        )
    )
    apply_button.click()
    export_div = wait.until(
        EC.visibility_of_element_located((By.ID, "modal-export-efct2"))
    )
    pdf_radio_button = export_div.find_element(by=By.ID, value="efct2-format1")
    pdf_radio_button.click()

    export_button = export_div.find_element(
        by=By.XPATH, value='.//button[contains(text(), "Exporta")]'
    )
    export_button.click()

    suspend()


def login(driver: WebDriver):

    oblio_email = os.getenv("OBLIO_EMAIL")
    oblio_password = os.getenv("OBLIO_PASSWORD")

    if oblio_email in [None, ""] or oblio_password in [None, ""]:
        print("email or password not set", file=sys.stderr)
        os._exit(1)

    driver.get("https://www.oblio.eu/account")

    # sometimes you may be already logged in and don't need to do this
    if "login" not in driver.current_url:
        return

    # title = driver.title

    username = driver.find_element(by=By.ID, value="username")
    username.send_keys(oblio_email)
    password = driver.find_element(by=By.ID, value="password")
    password.send_keys(oblio_password)

    submit_button = driver.find_element(
        by=By.XPATH,
        value="""//button[@type="submit" and .//span[contains(text(), "Intra in cont")]]""",
    )
    submit_button.click()

    # need an additional check that we get to this page
    login_code = get_login_code()

    # did not require a code
    # todo: automatize
    if login_code == "ok":
        return


driver = init_driver()
print("driver initialized")

login(driver=driver)

get_oblio_data(driver=driver)
suspend()

# text_box.send_keys("Selenium")
# submit_button.click()

# message = driver.find_element(by=By.ID, value="message")
# text = message.text

# suspend()

driver.quit()
