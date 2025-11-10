"""
Basic E2E tests for the Streamlit application using Playwright.

These tests verify that the application starts correctly and basic UI elements are present.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_app_loads(page: Page) -> None:
    """
    Test that the application loads successfully.

    Args:
        page: Playwright page fixture
    """
    # Navigate to the app
    page.goto("http://localhost:8080")

    # Wait for the app to load
    page.wait_for_selector("h1", timeout=10000)

    # Check for the main title (use first since there might be multiple h1 elements)
    expect(page.locator("h1").first).to_contain_text("Trail Running Race GPX Analyzer")


@pytest.mark.e2e
def test_tabs_exist(page: Page) -> None:
    """
    Test that both tabs are present.

    Args:
        page: Playwright page fixture
    """
    page.goto("http://localhost:8080")
    page.wait_for_selector("h1", timeout=10000)

    # Check for tabs
    tabs = page.get_by_role("tab")
    expect(tabs).to_have_count(2)


@pytest.mark.e2e
def test_gpx_analysis_tab_content(page: Page) -> None:
    """
    Test that the GPX analysis tab has expected content.

    Args:
        page: Playwright page fixture
    """
    page.goto("http://localhost:8080")
    page.wait_for_selector("h1", timeout=10000)

    # Click on GPX analysis tab
    gpx_tab = page.get_by_role("tab", name="GPX分析")
    gpx_tab.click()

    # Check for upload section heading (use get_by_role for more specific selector)
    expect(page.get_by_role("heading", name="GPXファイルのアップロード")).to_be_visible()
    expect(page.get_by_text("ローカルファイル", exact=True).first).to_be_visible()
    expect(page.get_by_text("URL", exact=True).first).to_be_visible()


@pytest.mark.e2e
def test_help_tab_content(page: Page) -> None:
    """
    Test that the help tab has expected content.

    Args:
        page: Playwright page fixture
    """
    page.goto("http://localhost:8080")
    page.wait_for_selector("h1", timeout=10000)

    # Click on help tab
    help_tab = page.get_by_role("tab", name="ヘルプ")
    help_tab.click()

    # Check for help content (using headings from usage.md)
    expect(page.get_by_role("heading", name="使い方ガイド")).to_be_visible()
    expect(page.get_by_role("heading", name="概要")).to_be_visible()


@pytest.mark.e2e
def test_upload_methods_toggle(page: Page) -> None:
    """
    Test toggling between upload methods.

    Args:
        page: Playwright page fixture
    """
    page.goto("http://localhost:8080")
    page.wait_for_selector("h1", timeout=10000)

    # Should start with local file option (look for file uploader widget)
    expect(page.get_by_test_id("stFileUploader")).to_be_visible()

    # Click URL radio button - use label selector
    # Streamlit renders radio buttons as labels with clickable areas
    page.locator("label").filter(has_text="URL").click()

    # Should show URL input and button
    expect(page.get_by_placeholder("https://example.com/track.gpx")).to_be_visible()
    expect(page.get_by_role("button", name="URLから読み込み")).to_be_visible()
