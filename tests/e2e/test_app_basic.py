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


@pytest.mark.e2e
def test_add_marker_with_coordinates(page: Page, sample_gpx_file) -> None:
    """
    Test adding a marker using coordinate input.

    Args:
        page: Playwright page fixture
        sample_gpx_file: Path to sample GPX file
    """
    page.goto("http://localhost:8080")
    page.wait_for_selector("h1", timeout=10000)

    # Upload GPX file
    file_input = page.locator("input[type='file']")
    file_input.set_input_files(str(sample_gpx_file))

    # Check that marker section is visible
    expect(page.get_by_role("heading", name="マーカー設定")).to_be_visible()

    # Initially should have 2 auto-added markers (スタート and ゴール)
    expect(page.get_by_text("登録済みマーカー:")).to_be_visible()

    # Select coordinate input method
    page.locator("label").filter(has_text="緯度経度入力").click()
    page.wait_for_timeout(500)  # Wait for UI to update

    # Enter marker name
    marker_name_input = page.get_by_placeholder("例: CP1, エイドステーション")
    marker_name_input.fill("テストマーカー")

    # Enter coordinates (use coordinates from sample GPX)
    # Streamlit number_input requires special handling
    # We need to trigger Streamlit's rerun by blurring the input field
    lat_input = page.locator("input[aria-label='緯度']")
    lon_input = page.locator("input[aria-label='経度']")

    # Clear existing values and type new ones
    # Select all, delete, type new value, then blur to trigger Streamlit rerun
    lat_input.click()
    lat_input.press("Control+a")  # Select all (Command+a on Mac, but Control works on both)
    lat_input.type("35.37", delay=50)
    # Blur the input to trigger Streamlit's change detection
    marker_name_input.click()  # Click elsewhere to blur
    page.wait_for_timeout(500)  # Wait for Streamlit to process the change and rerun

    lon_input.click()
    lon_input.press("Control+a")  # Select all
    lon_input.type("138.735", delay=50)
    # Blur the input to trigger Streamlit's change detection
    marker_name_input.click()  # Click elsewhere to blur
    page.wait_for_timeout(500)  # Wait for Streamlit to process the change and rerun

    # Verify no error messages are shown before adding marker
    error_messages = page.locator("text=座標を指定してください")
    expect(error_messages).not_to_be_visible()

    # Click add marker button
    add_button = page.get_by_role("button", name="マーカーを追加")
    add_button.click()

    # Wait for Streamlit rerun to complete
    # First check if marker count increased (more reliable)
    page.wait_for_timeout(1000)  # Wait for rerun to start

    # Wait for marker count to update (should go from 2 to 3)
    # Check for "登録済みマーカー: 3個" text
    marker_count_text = page.get_by_text("登録済みマーカー: 3個", exact=False)
    expect(marker_count_text.first).to_be_visible(timeout=10000)

    # Then check for the marker in the list
    marker_text = page.get_by_text("2. テストマーカー", exact=False)
    expect(marker_text.first).to_be_visible(timeout=5000)

    # Check success message appeared (after marker is confirmed to be added)
    success_message = page.locator("text=マーカー 'テストマーカー' を追加しました").first
    expect(success_message).to_be_visible(timeout=5000)


@pytest.mark.e2e
def test_clear_all_markers(page: Page, sample_gpx_file) -> None:
    """
    Test clearing all markers.

    Args:
        page: Playwright page fixture
        sample_gpx_file: Path to sample GPX file
    """
    page.goto("http://localhost:8080")
    page.wait_for_selector("h1", timeout=10000)

    # Upload GPX file
    file_input = page.locator("input[type='file']")
    file_input.set_input_files(str(sample_gpx_file))

    # Verify markers exist in marker list (at least the auto-added ones)
    # Marker list format: "1. スタート (35.360600, 138.727400) - 0.00km"
    # Use get_by_text with partial match to find markers in the list
    start_marker = page.get_by_text("1. スタート", exact=False)
    goal_marker = page.get_by_text("ゴール", exact=False).filter(has_text="km")
    expect(start_marker.first).to_be_visible()
    expect(goal_marker.first).to_be_visible()

    # Click clear all markers button
    clear_button = page.get_by_role("button", name="すべてのマーカーをクリア")
    clear_button.click()

    # Wait for clearing and page rerender
    page.wait_for_timeout(100)

    # Verify all markers were removed from marker list
    expect(page.get_by_text("マーカーが登録されていません")).to_be_visible()
    expect(start_marker).not_to_be_visible()
    expect(goal_marker).not_to_be_visible()
