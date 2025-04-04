from math import fabs
import os
from b2sdk.v2 import InMemoryAccountInfo, B2Api, AuthInfoCache, Bucket
from b2sdk._internal.exception import FileNotPresent, B2Error, InvalidAuthToken

from downloads import DOWNLOADS_DIRECTORY
from loglib import logger


def connect_to_backblaze(account_id, app_key) -> B2Api:
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info, cache=AuthInfoCache(info))
        b2_api.authorize_account("production", account_id, app_key)
        return b2_api
    except InvalidAuthToken as e:
        logger.error("Invalid credentials provided.")
        raise e
    except B2Error as e:
        logger.error(f"Unable to connect to Backblaze.")
        raise e


def check_if_file_exists(bucket: Bucket, filename: str) -> bool:
    try:
        bucket.get_file_info_by_name(filename)
        return True
    except FileNotPresent:
        return False


def upload_files(bucket: Bucket, fpath: str):
    bucket.upload_local_file(
        local_file=fpath,
        file_name=fpath,
    )


def upload_files(dirname: str):
    account_id = os.getenv("BACKBLAZE_S3_KEY_ID")
    application_key = os.getenv("BACKBLAZE_S3_APP_KEY")
    bucket_name = os.getenv("BACKBLAZE_BUCKET_NAME")

    try:
        b2_api = connect_to_backblaze(account_id, application_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)
        print(check_if_file_exists(bucket, "nobil_art_24_11_01__24_11_30.pdf"))

        for filename in os.listdir(dirname):
            fpath = os.path.join(dirname, filename)
            # checking if it is a file
            if not os.path.isfile(fpath):
                continue
            logger.debug("local file %s", fpath)

            if check_if_file_exists(bucket, filename):
                logger.info("skipping file %s, already exists", filename)
                continue

            logger.info("uploading file %s", fpath)
            try:
                bucket.upload_local_file(
                    local_file=fpath,
                    file_name=filename,
                )
                logger.info("successfully uploaded file %s", fpath)
            except B2Error as e:
                logger.exception(f"could not upload file: {e}")

    except B2Error as e:
        logger.error(f"A backblaze error occurred: {e}")
        raise e

    except OSError as e:
        logger.error(f"An OS error occured: {e}")
        raise e


if __name__ == "__main__":
    logger.debug("debugging backblaze upload only")
    upload_files(DOWNLOADS_DIRECTORY)
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait


from loglib import logger


def close_bitwarden(driver: WebDriver):
    wait = WebDriverWait(driver, 5)
    try:
        bitwarder_header = wait.find_element(
            by=By.XPATH,
            value="//div//*[contains(text(), 'Should Bitwarden remember this password for you?')]",
        )
        close_button = bitwarder_header.find_element(by=By.ID, value="close-button")
        close_button.click()
        logger.debug("closing bitwarden")

    # No such element
    except Exception as e:
        logger.debug("skipping bitwarden close")
        return
import os

DOWNLOADS_DIRECTORY = "bills"
import logging
import sys


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("oblio_exporter_py")
    logger.setLevel(logging.DEBUG)
    fh = logging.StreamHandler(sys.stderr)
    fh_formatter = logging.Formatter("[%(levelname)s] %(message)s")
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    return logger


logger = setup_logger()
import calendar
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


import logging

logger = logging.getLogger("oblio_exporter_py")
logger.setLevel(logging.DEBUG)
fh = logging.StreamHandler(sys.stderr)
fh_formatter = logging.Formatter("[%(levelname)s] %(message)s")
fh.setFormatter(fh_formatter)
logger.addHandler(fh)


logger.debug(f"what is going on? {2}")

print("ramge", calendar.monthrange(2024, 10)[1])

exit()


def init_driver() -> WebDriver:
    # Set Firefox options to use the existing profile
    firefox_options = Options()

    driver = webdriver.Firefox(options=firefox_options)

    return driver


driver = init_driver()
driver.get("https://www.cs.ubbcluj.ro/")
time.sleep(2)

# item = driver.find_element(
#     by=By.CLASS_NAME,
#     value="post.post-box.clearfix.post-63060.type-post.status-publish.format-standard.hentry.category-anunturi-cadre-didactice.category-comunicari",
# )
# print(item)

item = driver.find_elements(
    by=By.CLASS_NAME,
    value="clearfix",
)
for i in item:
    print(i.text)
import calendar
import datetime
import sys
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.support.ui import Select

from selenium.webdriver.remote.webelement import WebElement


from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException

from downloads import DOWNLOADS_DIRECTORY
from timelib import MONTH_TO_OBLIO_CALENDAR_TEXT, get_previous_month_as_date
from loglib import logger
from backblaze import upload_files
from bitwarden import close_bitwarden
from userinput import ask_for_period, get_login_code

import os
from urllib.request import urlretrieve


SUSPEND = True


def format_company_name(name: str) -> str:
    parts = name.split(" ")
    if len(parts) == 1:
        parts.append("co")
    return f"{parts[0].lower()}_{parts[1].lower()}"


def format_filename(company: str, billing_period: datetime.date, download_format: str):
    extension = None
    if download_format == "pdf":
        extension = "pdf"
    elif download_format == "xml":
        extension = "zip"
    else:
        raise Exception("invalid format")
    prefix = format_company_name(company)
    number_of_days = calendar.monthrange(billing_period.year, billing_period.month)[1]
    return f"{prefix}_{billing_period.year % 100}_{billing_period.month}_01__{billing_period.year % 100}_{billing_period.month}_{number_of_days}.{extension}"


def suspend():
    if SUSPEND:
        try:
            input("press anything to continue...")
        except:  # capture everything including ctrl C
            os._exit(1)


def wait_for_element(driver: WebDriver, by: By, element_identifier, timeout=5):
    try:
        element_present = EC.presence_of_element_located((by, element_identifier))
        WebDriverWait(driver, timeout).until(element_present)
    except TimeoutException:
        logger.error("timed out waiting for %s", element_identifier)
        return None
    return driver.find_element(by, element_identifier)


def init_driver() -> WebDriver:
    # Set Firefox options to use the existing profile
    firefox_options = Options()

    profile_path = os.getenv("OBLIO_FIREFOX_PROFILE_PATH")
    if profile_path not in [None, ""]:

        logger.debug("using profile path %s", profile_path)

        firefox_profile = FirefoxProfile(profile_path)
        firefox_options.profile = firefox_profile

    driver = webdriver.Firefox(options=firefox_options)

    return driver


def download_data_for_current_company(
    driver: WebDriver,
    wait: WebDriverWait,
    company_name: str,
    billing_period: datetime.date,
    download_format: str,
    download_directory: str,
):
    logger.info("exporting data for company %s", company_name)

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

    if (
        month_select.first_selected_option.text
        != MONTH_TO_OBLIO_CALENDAR_TEXT[billing_period.month]
    ):
        month_select.select_by_visible_text(
            MONTH_TO_OBLIO_CALENDAR_TEXT[billing_period.month]
        )
    time.sleep(1)

    # I got an error like the following:
    # selenium.common.exceptions.StaleElementReferenceException: Message: The element with the reference be055f0a-476f-4363-8e0e-0fe853f7cb4a is stale; either its node document is not the active document, or it is no longer connected to the DOM;
    # I believe when you change the month the Select item rerenders. Creating it
    # here fixes it.
    year_select = Select(calendar_div.find_element(By.CSS_SELECTOR, ".yearselect"))
    if year_select.first_selected_option.text != str(billing_period.year):
        year_select.select_by_value(str(billing_period.year))

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
        logger.debug("calendar selector %s %s", idx, date.text)
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
        logger.debug("calendar selector again %s %s", idx, date.text)
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

    if download_format == "pdf":
        pdf_radio_button = export_div.find_element(by=By.ID, value="efct2-format1")
        pdf_radio_button.click()
    elif download_format == "xml":
        xml_radio_button = export_div.find_element(by=By.ID, value="efct2-format2")
        xml_radio_button.click()

    export_button = export_div.find_element(
        by=By.XPATH, value='.//button[contains(text(), "Exporta")]'
    )
    export_button.click()

    notifications_div = wait.until(
        EC.visibility_of_element_located((By.ID, "notifications"))
    )
    notifications_div_wait = WebDriverWait(notifications_div, 60)
    document_link = notifications_div_wait.until(first_document_is_no_longer_loading())
    document_href = document_link.get_attribute("href")

    output_filename = format_filename(company_name, billing_period, download_format)
    urlretrieve(document_href, os.path.join(download_directory, output_filename))

    logger.info("finished downloading file %s", output_filename)

    time.sleep(1)

    # suspend()


def download_oblio_data_locally(
    driver: WebDriver, download_directory: str
) -> list[str]:

    billing_period = ask_for_period()
    logger.info(
        "using billing period %d %s", billing_period.year, billing_period.strftime("%b")
    )

    close_bitwarden(driver)

    wait = WebDriverWait(driver, 2)  # waits up to 10 seconds

    driver.get("https://www.oblio.eu/account")

    try:
        companies_list = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".btn.btn-sm.btn-square.btn-outline-warning")
            )
        )
        companies_list.click()
    except TimeoutException:
        logger.debug("starting popup did not show")

    wait = WebDriverWait(driver, 10)

    # Wait for modal-backdrop fade and modal-backdrop show to dissapear because
    # it's an animation that fucking blocks the button from being clickable.
    element_to_wait_for = (By.CSS_SELECTOR, ".modal-backdrop.fade")
    wait.until(EC.invisibility_of_element_located(element_to_wait_for))
    element_to_wait_for = (By.CSS_SELECTOR, ".modal-backdrop.show")
    wait.until(EC.invisibility_of_element_located(element_to_wait_for))

    current_company_idx = 0
    while True:
        companies_list = wait.until(
            EC.element_to_be_clickable((By.ID, "switch-company-menu"))
        )
        companies_list.click()

        # Get companies list
        dropdown_items = wait.until(
            EC.visibility_of_all_elements_located(
                (By.CSS_SELECTOR, ".dropdown-item.leave-confirm.comp-list")
            )
        )
        if current_company_idx >= len(dropdown_items):
            logger.info("finished downloading all companies")
            break

        company_names = [el.get_attribute("title") for el in dropdown_items]
        logger.info(
            "found %d companies: %s",
            len(company_names),
            "; ".join(map(str, company_names)),
        )

        dropdown_items[current_company_idx].click()
        download_data_for_current_company(
            driver,
            wait,
            company_names[current_company_idx],
            billing_period,
            "xml",
            download_directory,
        )
        download_data_for_current_company(
            driver,
            wait,
            company_names[current_company_idx],
            billing_period,
            "pdf",
            download_directory,
        )
        current_company_idx += 1


class first_document_is_no_longer_loading(object):
    """The document will no longer be loading when it has a link element.

    locator - used to find the element
    returns the WebElement once it has the particular css class
    """

    def __call__(self, driver) -> WebElement:
        try:

            # documents list will refresh once this is done
            ready_documents_list = driver.find_element(
                By.CSS_SELECTOR, "div.list-group.list-group-flush.notifications-list"
            )

            ready_documents = ready_documents_list.find_elements(By.XPATH, "./div")
            logger.debug(
                "polling for loading export (%d available)", len(ready_documents)
            )
            result = ready_documents[0].find_element(
                by=By.CSS_SELECTOR, value="a.btn.btn-sm.btn-success.px-2.py-1.text-xs"
            )
            # result = ready_document.find_element(
            #     By.XPATH, "//a[descendant::*[contains(text(), 'Descarca')]]"
            # )
            return result
        except NoSuchElementException as e:
            return False
        except Exception as e:
            logger.error("unknown error waiting for document to be ready: %s", str(e))
            return False


def login(driver: WebDriver):

    oblio_email = os.getenv("OBLIO_EMAIL")
    oblio_password = os.getenv("OBLIO_PASSWORD")

    if oblio_email in [None, ""] or oblio_password in [None, ""]:
        logger.error("email or password not set")
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
    else:
        code_form = driver.find_element(by=By.ID, value="email_code")
        code_form.send_keys(login_code)
        login_button = driver.find_element(
            by=By.XPATH,
            value='//button[@type="button" and .//span[contains(text(), "Intra in cont")]]',
        )
        login_button.click()


def main():
    try:
        driver = init_driver()
        logger.info("driver initialized")
        login(driver=driver)
        download_oblio_data_locally(
            driver=driver, download_directory=DOWNLOADS_DIRECTORY
        )
        upload_files(DOWNLOADS_DIRECTORY)

    except WebDriverException as e:
        logger.error(f"got webdriver error: {e}")
    except KeyboardInterrupt:
        logger.info("exiting program")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
import datetime

MONTH_TO_OBLIO_CALENDAR_TEXT = {
    1: "Ianuarie",
    2: "Februarie",
    3: "Martie",
    4: "Aprilie",
    5: "Mai",
    6: "Iunie",
    7: "Iulie",
    8: "August",
    9: "Septembrie",
    10: "Octombrie",
    11: "Noiembrie",
    12: "Decembrie",
}


def get_previous_month_as_date() -> datetime.date:
    now = datetime.datetime.now()
    year = now.year
    month = now.month - 1

    if month == 0:
        month = 12
        year -= 1

    return datetime.date(year, month, 1)
import datetime
import os
import sys

from loglib import logger
from timelib import get_previous_month_as_date


def get_login_code() -> str:
    code = input("what is the 6 digits code? >")
    if len(code) != 6:
        logger.debug("using ok as code")
        return "ok"
    if not code.isnumeric():
        logger.debug("using ok as code")
        return "ok"
    return code


def ask_for_period() -> datetime.date:
    try:
        period = get_previous_month_as_date()
        cyear = period.year
        cmonth = period.month

        billing_period = os.getenv("BILLING_PERIOD")
        if "," in billing_period:
            logger.debug("billing period set via env var %s", billing_period)
            parts = billing_period.split(",")
            cyear = int(parts[0])
            cmonth = int(parts[1])
        else:
            year = input(f"what is the year of the bill? ({period.year}) > ")
            if year != "":
                cyear = int(year)
            month = input(f"what is the month of the bill? ({period.month}) > ")
            if month != "":
                cmonth = int(month)

        return datetime.date(cyear, cmonth, 1)
    except ValueError:
        logger.error("failed to supply a proper value for year or month")
        sys.exit()
