import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from urllib.parse import urljoin, urlparse
import os
import time

# Hard-coded list of Wiktionary URLs
URLS = [
    "https://en.wiktionary.org/wiki/dinde#French",
    # Add more URLs here as needed
]


def download_pronunciation(url):
    """
    Downloads the first pronunciation audio file from a Wiktionary URL.
    Uses Selenium to execute JavaScript and get the actual audio source.

    Args:
        url: Wiktionary URL with language anchor (e.g., https://en.wiktionary.org/wiki/dinde#French)

    Returns:
        Path to downloaded file or None if not found
    """
    # Parse the URL to extract the language section
    parsed = urlparse(url)
    language = parsed.fragment if parsed.fragment else None
    word = parsed.path.split('/')[-1]

    if not language:
        print(f"Error: URL must include a language anchor (e.g., #French)")
        return None

    print(f"\n{'=' * 60}")
    print(f"Processing: {word} ({language})")
    print(f"{'=' * 60}")

    # Set up Selenium with headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"Error initializing Chrome driver: {e}")
        print("Make sure you have Chrome and chromedriver installed.")
        return None

    try:
        # Load the page
        print(f"Loading page...")
        driver.get(url)

        # Wait for page to load
        time.sleep(2)

        # Find the language section
        try:
            language_header = driver.find_element(By.ID, language)
            print(f"✓ Found {language} section")
        except:
            print(f"✗ Could not find {language} section on page")
            driver.quit()
            return None

        # Scroll to the language section
        driver.execute_script("arguments[0].scrollIntoView();", language_header)
        time.sleep(1)

        # Find the first pronunciation link (a.mw-tmh-play)
        # Search within a reasonable scope after the language header
        try:
            # Get all audio play buttons
            play_buttons = driver.find_elements(By.CSS_SELECTOR, "a.mw-tmh-play")

            if not play_buttons:
                print("✗ Could not find any pronunciation audio buttons")
                driver.quit()
                return None

            # Get the href from the first play button
            first_button = play_buttons[0]
            file_href = first_button.get_property("href")

            if not file_href:
                print("✗ Could not extract href from audio button")
                driver.quit()
                return None

            print(f"✓ Found first pronunciation link: {file_href}")

        except Exception as e:
            print(f"✗ Error finding pronunciation button: {e}")
            driver.quit()
            return None

        driver.quit()

        # Now we have the file page URL, get the actual audio file
        print(f"Fetching audio file page...")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            file_response = requests.get(file_href, headers=headers)
            file_response.raise_for_status()
        except requests.RequestException as e:
            print(f"✗ Error fetching file page: {e}")
            return None

        # Parse the file page to find the actual download link
        file_soup = BeautifulSoup(file_response.content, 'html.parser')

        download_link = None
        for link in file_soup.find_all('a'):
            href = link.get('href', '')
            if (href.endswith('.ogg') or href.endswith('.wav')) and href.count("upload.wikimedia.org") > 0:
                download_link = href
                print(href)
                break

        if not download_link:
            print("✗ Could not find audio file download link")
            return None

        # Make sure we have absolute URL
        if not download_link.startswith('http'):
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            download_link = urljoin(base_url, download_link)

        print(f"✓ Found download link: {download_link}")

        # Download the audio file
        print(f"Downloading audio file...")

        try:
            audio_response = requests.get(download_link, headers=headers)
            audio_response.raise_for_status()
        except requests.RequestException as e:
            print(f"✗ Error downloading audio file: {e}")
            return None

        # Create filename: word_language.extension
        extension = os.path.splitext(urlparse(download_link).path)[1]
        filename = f"{word}_{language.lower()}{extension}"

        # Save the file
        with open(filename, 'wb') as f:
            f.write(audio_response.content)

        print(f"✓ Successfully saved: {filename}")
        return filename

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        driver.quit()
        return None


if __name__ == "__main__":
    print("Starting Wiktionary pronunciation downloader...")
    print(f"Processing {len(URLS)} URL(s)\n")

    results = []

    for url in URLS:
        result = download_pronunciation(url)
        results.append((url, result))

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")

    successful = sum(1 for _, r in results if r is not None)
    failed = len(results) - successful

    print(f"Total: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if successful > 0:
        print(f"\nDownloaded files:")
        for url, filename in results:
            if filename:
                print(f"  - {filename}")