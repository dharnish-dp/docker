"""
conftest.py — pytest configuration and shared fixtures

This file is automatically loaded by pytest before running any tests.
Fixtures defined here are available to ALL test files without importing.
"""
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


@pytest.fixture(scope="function")
def driver():
    """
    Provides a configured Chrome WebDriver for each test.

    scope="function" = a fresh browser is created for each test function.
    Change to scope="session" to reuse one browser for all tests (faster
    but tests can affect each other).

    The fixture automatically closes the browser after each test via yield.
    """
    options = Options()

    # Required for running inside Docker (no display server)
    options.add_argument("--headless")           # no GUI window
    options.add_argument("--no-sandbox")         # required in Docker
    options.add_argument("--disable-dev-shm-usage")  # use /tmp instead of /dev/shm
    options.add_argument("--disable-gpu")        # not needed in headless mode
    options.add_argument("--window-size=1920,1080")  # consistent viewport

    # ChromeDriver is pre-installed in the selenium/standalone-chrome image
    # No need for webdriver-manager — the binary is at a known path
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    driver.implicitly_wait(10)  # wait up to 10s for elements to appear

    yield driver  # test runs here

    driver.quit()  # always close browser, even if test fails
