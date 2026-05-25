"""
test_google.py — Example: testing Google Search

Demonstrates:
- Navigation (driver.get)
- Finding elements (By.NAME, By.CSS_SELECTOR)
- Typing and submitting forms
- Waiting for results
- Asserting page content
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def test_google_title(driver):
    """Page title should contain 'Google'"""
    driver.get("https://www.google.com")
    assert "Google" in driver.title


def test_google_search(driver):
    """Searching for 'Docker' should return results"""
    driver.get("https://www.google.com")

    # Find the search box by its name attribute
    search_box = driver.find_element(By.NAME, "q")

    # Type search query and press Enter
    search_box.send_keys("Docker containerization")
    search_box.send_keys(Keys.RETURN)

    # Wait until results appear (up to 10 seconds)
    # WebDriverWait is explicit waiting — better than time.sleep()
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, "search")))

    # Verify results page loaded
    assert "Docker" in driver.page_source


def test_google_search_suggestions(driver):
    """Typing in search box should show autocomplete suggestions"""
    driver.get("https://www.google.com")

    search_box = driver.find_element(By.NAME, "q")
    search_box.send_keys("Python Docker")

    # Wait for suggestions dropdown to appear
    wait = WebDriverWait(driver, 5)
    suggestions = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li[data-ved]"))
    )

    # At least one suggestion should appear
    assert len(suggestions) > 0
