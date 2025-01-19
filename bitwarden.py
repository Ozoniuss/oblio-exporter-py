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
