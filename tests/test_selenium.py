import socket
import threading
import time

import pytest
import uvicorn

selenium = pytest.importorskip("selenium")
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from amazon_bot import api


class FakeWorkflow:
    def invoke(self, state):
        return {
            "final_response": {
                "status": "completed",
                "answer": "Your package is on the way.",
            },
            "intent": "delivery_issue",
            "confidence": 0.93,
            "reranked_conversations": [],
            "review_result": {
                "approved": True,
                "score": 0.95,
                "issues": [],
                "suggestions": [],
                "requires_human": False,
            },
        }


def _free_port():
    with socket.socket() as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        return server_socket.getsockname()[1]


@pytest.fixture
def browser_server(monkeypatch):
    monkeypatch.setattr(api, "workflow", FakeWorkflow())
    port = _free_port()
    config = uvicorn.Config(
        api.app,
        host="127.0.0.1",
        port=port,
        log_level="error",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        pytest.fail("Test server did not start")
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.fixture
def chrome():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    try:
        driver = webdriver.Chrome(options=options)
    except WebDriverException as error:
        pytest.skip(f"Chrome WebDriver is unavailable: {error}")
    yield driver
    driver.quit()


def _wait_for_result(chrome):
    return WebDriverWait(chrome, 5).until(
        EC.visibility_of_element_located((By.ID, "result"))
    )


@pytest.mark.selenium
def test_chat_form_displays_workflow_response(browser_server, chrome):
    chrome.get(f"{browser_server}/")

    assert chrome.title == "Amazon Bot Assistant"
    chrome.find_element(By.ID, "user-id").clear()
    chrome.find_element(By.ID, "user-id").send_keys("demo_user_001")
    chrome.find_element(By.ID, "query").send_keys("Where is my package?")
    chrome.find_element(By.ID, "send").click()

    result = _wait_for_result(chrome)
    answer = chrome.find_element(By.ID, "answer")
    assert result.is_displayed()
    assert chrome.find_element(By.ID, "result-status").text == "completed"
    assert chrome.find_element(By.ID, "intent").text == "delivery_issue"
    assert chrome.find_element(By.ID, "confidence").text == "93.0%"
    assert answer.text == "Your package is on the way."


@pytest.mark.selenium
def test_chat_form_requires_a_query(browser_server, chrome):
    chrome.get(f"{browser_server}/")

    query = chrome.find_element(By.ID, "query")
    assert query.get_attribute("required") == "true"
    assert query.get_attribute("validationMessage")
    assert chrome.find_element(By.ID, "result").get_attribute("hidden") == "true"


@pytest.mark.selenium
def test_new_conversation_replaces_session(browser_server, chrome):
    chrome.get(f"{browser_server}/")
    session_field = chrome.find_element(By.ID, "session-id")
    original_session = session_field.get_attribute("value")

    chrome.find_element(By.ID, "new-session").click()
    WebDriverWait(chrome, 5).until(EC.staleness_of(session_field))
    WebDriverWait(chrome, 5).until(
        lambda driver: driver.find_element(By.ID, "session-id").get_attribute("value")
        != original_session
    )

    assert chrome.find_element(By.ID, "result").get_attribute("hidden") == "true"


@pytest.mark.selenium
def test_chat_error_is_rendered(browser_server, chrome):
    chrome.get(f"{browser_server}/")
    chrome.execute_script(
        "window.fetch = () => Promise.reject(new Error('network failure'));"
    )
    chrome.find_element(By.ID, "query").send_keys("Will fail")
    chrome.find_element(By.ID, "send").click()

    WebDriverWait(chrome, 5).until(
        EC.text_to_be_present_in_element((By.ID, "error"), "network failure")
    )
    assert chrome.find_element(By.ID, "result").get_attribute("hidden") == "true"
