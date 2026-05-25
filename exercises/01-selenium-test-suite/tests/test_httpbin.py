"""
test_httpbin.py — Example: testing httpbin.org (a test API site)

Demonstrates:
- Testing forms
- Checking response content
- URL navigation and verification
- Screenshot on failure pattern
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def test_httpbin_homepage(driver):
    """httpbin homepage should load and show API documentation"""
    driver.get("https://httpbin.org")
    assert "httpbin" in driver.title.lower()


def test_httpbin_get_endpoint(driver):
    """Navigating to /get endpoint should return JSON response"""
    driver.get("https://httpbin.org/get")

    # The page should contain JSON with the URL we requested
    assert "httpbin.org/get" in driver.page_source
    assert '"url"' in driver.page_source


def test_httpbin_ip_endpoint(driver):
    """The /ip endpoint should return our container's IP address"""
    driver.get("https://httpbin.org/ip")

    # Should contain an IP address in the response
    assert '"origin"' in driver.page_source


def test_page_screenshot(driver):
    """
    Demonstrates taking a screenshot — useful for debugging test failures.
    Screenshot is saved to the reports/ folder which is bind-mounted to Mac.
    """
    driver.get("https://httpbin.org")

    # Take screenshot and save to reports folder
    driver.save_screenshot("/app/reports/httpbin_homepage.png")

    # Verify screenshot was created (file exists)
    import os
    assert os.path.exists("/app/reports/httpbin_homepage.png")
