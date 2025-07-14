import calendar
import datetime
import shutil
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
from pathlib import Path
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

    monthstr = str(billing_period.month)
    if len(monthstr) == 1:
        monthstr = "0" + monthstr

    return f"{prefix}_{billing_period.year % 100}_{monthstr}_01__{billing_period.year % 100}_{monthstr}_{number_of_days}.{extension}"


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


def init_driver(run_headless: bool) -> tuple[WebDriver, str]:
    try:
        tmp_profile = None
        # Set Firefox options to use the existing profile
        firefox_options = Options()

        if run_headless:
            firefox_options.add_argument("--headless")

        profile_path = os.getenv("OBLIO_FIREFOX_PROFILE_PATH")
        if profile_path not in [None, ""]:

            logger.debug("using profile path %s", profile_path)

            firefox_profile = FirefoxProfile(profile_path)
            firefox_options.profile = firefox_profile
            tmp_profile = firefox_profile._profile_dir
            logger.debug(f"creating temp profile {firefox_profile._profile_dir}")


        driver = webdriver.Firefox(options=firefox_options)

        return driver

    # avoid buildup of profile copies during debugging
    except KeyboardInterrupt as e:
        if tmp_profile:
            try:
                to_clean = Path(tmp_profile).parent
                logger.debug(f"attempting to clean up temporary profile {to_clean}")
                shutil.rmtree(tmp_profile)
                os.rmdir(to_clean)
                logger.debug("temp profile cleaned")
            except Exception as ex:
                logger.exception(f"could not delete temp profile: {ex}")
        raise e

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

    wait = WebDriverWait(driver, 5)

    # Removing this as it looks like it's no longer necessary? but I know I added
    # it with a purpose so keeping it as a reference.
    # driver.get("https://www.oblio.eu/account")

    try:
        companies_list = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".btn.btn-sm.btn-square.btn-outline-warning")
            )
        )
        logger.debug("closing initial companies popup")
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
        logger.info("does not attempt login")
        return

    # title = driver.title
    logger.info("attempting login...")

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
    upload_to_b2 = os.getenv("OBLIO_UPLOAD_TO_B2")
    run_headless = os.getenv("OBLIO_RUN_HEADLESS")

    if upload_to_b2 == "true":
        upload_to_b2 = True
        logger.debug("will upload files to b2")
    else:
        upload_to_b2 = False
        logger.debug("will only download locally")

    if run_headless == "true":
        run_headless = True
        logger.debug("will run in headless mode")
    else:
        run_headless = False
        logger.debug("will not run in headless mode")

    try:
        driver = init_driver(run_headless)
        logger.info("driver initialized")
        login(driver=driver)
        download_oblio_data_locally(
            driver=driver, download_directory=DOWNLOADS_DIRECTORY
        )
        if upload_to_b2 is True:
            upload_files(DOWNLOADS_DIRECTORY)

    except WebDriverException as e:
        logger.error(f"got webdriver error: {str(e)}")
    except KeyboardInterrupt:
        logger.info("exiting program")

    finally:
        logger.info("closing driver")
        driver.quit()


if __name__ == "__main__":
    main()
