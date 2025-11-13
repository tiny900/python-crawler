#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Crawler - Automated Version
Collects all tweets from specified accounts
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import json
import os
from datetime import datetime, timedelta
import re
import pickle
import sys

# Twitter accounts to crawl
TWITTER_ACCOUNTS = {
    'garyblack00': 'https://x.com/garyblack00',
    'SeekingAlpha': 'https://x.com/SeekingAlpha',
    'Tesla': 'https://x.com/Tesla',
    'FinanceNews': 'https://x.com/ftfinancenews',
    'Reuters': 'https://x.com/Reuters'
}


def setup_driver(headless=True):
    """Setup Chrome browser driver"""
    chrome_options = Options()

    if headless:
        chrome_options.add_argument('--headless')

    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    # Disable image loading for faster performance
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)

    # Create local user data directory
    user_data_dir = os.path.join(os.getcwd(), "chrome_user_data")
    chrome_options.add_argument(f'--user-data-dir={user_data_dir}')

    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Browser driver startup failed: {e}")
        print("Please ensure Chrome browser and ChromeDriver are installed")
        return None


def load_cookies(driver, filename="twitter_cookies.pkl"):
    """Load cookies from file"""
    try:
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                cookies = pickle.load(f)

            # Visit website first
            driver.get("https://x.com")
            time.sleep(2)

            # Add cookies
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except:
                    pass

            print("[OK] Cookies loaded successfully")
            return True
    except Exception as e:
        print(f"[ERROR] Failed to load cookies: {e}")
    return False


def check_login_status(driver):
    """Check if logged in"""
    try:
        driver.get("https://x.com/home")
        time.sleep(3)

        # Check if redirected to login page
        if "login" in driver.current_url or "flow" in driver.current_url:
            return False

        # Check for compose tweet button
        compose_button = driver.find_elements(By.CSS_SELECTOR, '[data-testid="SideNav_NewTweet_Button"]')
        return len(compose_button) > 0

    except:
        return False


def extract_tweet_data(tweet_element, index):
    """Extract tweet data"""
    tweet_data = {
        'index': index,
        'text': '',
        'time': '',
        'date': '',
        'author': '',
        'url': '',
        'engagement': {}
    }

    try:
        # Check if pinned tweet
        try:
            pinned_indicators = [
                '[data-testid="socialContext"]',
                '[aria-label*="Pinned"]',
                'svg[aria-label*="Pinned"]'
            ]

            for indicator in pinned_indicators:
                try:
                    pinned_element = tweet_element.find_element(By.CSS_SELECTOR, indicator)
                    if pinned_element:
                        tweet_data['is_pinned'] = True
                        break
                except:
                    continue

        except Exception as e:
            pass

        # Get tweet text
        try:
            tweet_text_elem = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
            tweet_data['text'] = tweet_text_elem.text.strip()
        except:
            # Backup method
            try:
                tweet_data['text'] = tweet_element.text.split('\\n')[2]
            except:
                pass

        # Get tweet time
        try:
            time_elem = tweet_element.find_element(By.CSS_SELECTOR, 'time')
            tweet_data['date'] = time_elem.get_attribute('datetime')
            tweet_data['time'] = time_elem.text
            tweet_data['timestamp'] = tweet_data['date']
        except:
            # Backup method for time
            try:
                status_links = tweet_element.find_elements(By.CSS_SELECTOR, 'a[href*="/status/"]')
                for link in status_links:
                    aria_label = link.get_attribute('aria-label')
                    if aria_label and any(t in aria_label.lower() for t in ['ago', 'h', 'm', 'd']):
                        tweet_data['time'] = aria_label
                        break
            except:
                tweet_data['time'] = "Unknown time"

        # Get author
        try:
            author_elem = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"]')
            tweet_data['author'] = author_elem.text.strip()
        except:
            pass

        # Get tweet link
        try:
            link_elem = tweet_element.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
            tweet_data['url'] = link_elem.get_attribute('href')
        except:
            pass

        # Get engagement data
        try:
            stats = tweet_element.find_elements(By.CSS_SELECTOR, '[role="group"] span')
            if len(stats) >= 3:
                tweet_data['engagement']['replies'] = stats[0].text
                tweet_data['engagement']['retweets'] = stats[1].text
                tweet_data['engagement']['likes'] = stats[2].text
        except:
            pass

    except Exception as e:
        print(f"Error extracting tweet data: {e}")

    return tweet_data


def parse_tweet_time_to_timestamp(time_str):
    """Convert tweet time to timestamp"""
    if not time_str:
        return 0

    try:
        current_time = time.time()

        # ISO format timestamp
        if 'T' in time_str and ('Z' in time_str or '+' in time_str):
            try:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                return dt.timestamp()
            except:
                pass

        # Relative time (e.g., "6h", "2m", "1d")
        if any(unit in time_str.lower() for unit in ['s', 'm', 'h', 'd', 'w']):
            numbers = re.findall(r'\\d+', time_str)
            if numbers:
                num = int(numbers[0])

                if 's' in time_str.lower():
                    seconds_ago = num
                elif 'm' in time_str.lower() and 'month' not in time_str.lower():
                    seconds_ago = num * 60
                elif 'h' in time_str.lower():
                    seconds_ago = num * 3600
                elif 'd' in time_str.lower():
                    seconds_ago = num * 86400
                elif 'w' in time_str.lower():
                    seconds_ago = num * 604800
                else:
                    seconds_ago = 0

                return current_time - seconds_ago

        return 0

    except Exception as e:
        return 0


def scroll_and_collect_tweets(driver, account_name, max_tweets=5000, days_back=7):
    """Scroll page and collect all tweets"""
    tweets_data = []
    processed_tweet_ids = set()
    scroll_attempts = 0
    no_new_tweets_count = 0

    cutoff_date = datetime.now() - timedelta(days=days_back) if days_back > 0 else None

    if days_back > 0:
        print(f"\\n[INFO] Starting to collect @{account_name} tweets from past {days_back} days...")
        print(f"[INFO] Target: Collect tweets after {cutoff_date.strftime('%Y-%m-%d')}")
    else:
        print(f"\\n[INFO] Collecting all tweets from @{account_name} (no time limit)...")

    # Track time progress
    oldest_tweet_timestamp = time.time()

    while len(tweets_data) < max_tweets and scroll_attempts < 3000:
        # Get all tweets on current page
        tweet_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')

        new_tweets_found = False

        for tweet_elem in tweet_elements:
            try:
                # Create unique ID
                tweet_html = tweet_elem.get_attribute('innerHTML')
                tweet_id = hash(tweet_html)

                # Skip processed tweets
                if tweet_id in processed_tweet_ids:
                    continue

                processed_tweet_ids.add(tweet_id)
                new_tweets_found = True

                # Extract tweet data
                tweet_data = extract_tweet_data(tweet_elem, len(tweets_data) + 1)

                # Check time range
                should_include = True
                tweet_time_str = tweet_data.get('date') or tweet_data.get('time', '')
                is_pinned = tweet_data.get('is_pinned', False)

                if days_back > 0 and not is_pinned:  # Pinned tweets not subject to time limit
                    if tweet_time_str:
                        tweet_timestamp = parse_tweet_time_to_timestamp(tweet_time_str)

                        if tweet_timestamp > 0:
                            oldest_tweet_timestamp = min(oldest_tweet_timestamp, tweet_timestamp)

                            # Check if outside time range
                            if tweet_timestamp < cutoff_date.timestamp():
                                print(f"[INFO] Tweet outside time range")
                                should_include = False

                                # Stop if collected enough tweets and found old tweet
                                if len(tweets_data) >= 10:
                                    print(f"[INFO] Reached time limit ({cutoff_date.strftime('%Y-%m-%d')})")
                                    return tweets_data
                        else:
                            # Cannot parse time, decide based on collected count
                            if len(tweets_data) < 5:
                                should_include = True
                            else:
                                should_include = False
                                print(f"[WARNING] Cannot parse tweet time: {tweet_time_str}")
                    else:
                        # No time info
                        if len(tweets_data) < 5:
                            should_include = True
                        else:
                            should_include = False

                if should_include:
                    tweets_data.append(tweet_data)
                    print(f"[FOUND] Tweet #{len(tweets_data)}: {tweet_data['text'][:60]}...")
                    if tweet_time_str:
                        print(f"   Time: {tweet_time_str}")

            except Exception as e:
                continue

        # Check for new tweets
        if not new_tweets_found:
            no_new_tweets_count += 1
            if no_new_tweets_count >= 5:
                print("[INFO] No more new tweets")
                break
        else:
            no_new_tweets_count = 0

        # Scroll page
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(2)

        scroll_attempts += 1

        # Show progress
        if scroll_attempts % 10 == 0:
            print(f"[INFO] Scrolled {scroll_attempts} times, collected {len(tweets_data)} tweets")

            # Show time progress if time limit set
            if days_back > 0 and oldest_tweet_timestamp < time.time():
                days_loaded = (time.time() - oldest_tweet_timestamp) / 86400
                print(f"[INFO] Loaded about {days_loaded:.1f} days of content")

        # Stop if too many scrolls with few tweets
        if scroll_attempts >= 5000 or (scroll_attempts >= 3000 and len(tweets_data) < 5):
            print("[INFO] Max scroll attempts reached or too few tweets")
            break

    return tweets_data


def crawl_twitter_account(account_name, url, driver, days_back=7):
    """Crawl tweets from a Twitter account"""
    print(f"\\n{'=' * 60}")
    print(f"[START] Crawling @{account_name}")
    print(f"[URL] {url}")

    try:
        driver.get(url)
        print("[INFO] Waiting for page to load...")
        time.sleep(5)

        # Check if login needed
        if "log in" in driver.title.lower() or "login" in driver.current_url.lower():
            print("[ERROR] Need to login to Twitter to view content")
            return []

        # Collect tweets
        tweets = scroll_and_collect_tweets(driver, account_name, max_tweets=3000, days_back=days_back)

        print(f"\\n[RESULT] Collected {len(tweets)} tweets from @{account_name}")

        return tweets

    except Exception as e:
        print(f"[ERROR] Error crawling {account_name}: {e}")
        return []


def save_tweets_to_json(tweets, account_name):
    """Save tweets to JSON file"""
    # Create main directory
    base_dir = "twitter_data"

    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    # 添加：先删除该账号的旧文件
    from pathlib import Path
    pattern = f"{account_name}_*.json"
    old_files = list(Path(base_dir).glob(pattern))

    for old_file in old_files:
        try:
            os.remove(old_file)
            print(f"[DELETED] Old file: {old_file.name}")
        except Exception as e:
            print(f"[WARNING] Could not delete {old_file.name}: {e}")

    # Generate filename: account_YYYYMMDD_HHMMSS.json
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{base_dir}/{account_name}_{timestamp}.json"

    # Prepare data
    data = {
        'account': account_name,
        'account_url': TWITTER_ACCOUNTS.get(account_name, ''),
        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'tweet_count': len(tweets),
        'tweets': tweets
    }

    # Save file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[SAVED] Tweets saved to: {filename}")

    return filename


def main():
    """Main function - Automated version"""
    start_time = time.time()  # Record start time

    print("Twitter Crawler - Automated Version")
    print("=" * 60)
    print(f"[START] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[CONFIG] Target accounts: {', '.join(['@' + acc for acc in TWITTER_ACCOUNTS.keys()])}")
    print(f"[CONFIG] Time range: Past 7 days")
    print(f"[CONFIG] Mode: Automated (headless browser)")

    # Create main directory
    if not os.path.exists("twitter_data"):
        os.makedirs("twitter_data")

    # Setup browser
    print("\\n[INFO] Starting browser (headless mode)...")
    driver = setup_driver(headless=True)
    if not driver:
        return False

    all_results = []
    success = False

    try:
        # Load cookies
        print("\\n[INFO] Loading saved cookies...")
        cookies_loaded = load_cookies(driver)

        if cookies_loaded and check_login_status(driver):
            print("[OK] Login successful with cookies!")
        else:
            print("[ERROR] Cookies invalid or expired")
            print("[INFO] Please run manual login script to update cookies")
            print("   Command: python twitter_crawler_manual_login.py")
            driver.quit()
            return False

        # Crawl each account
        for account_name, url in TWITTER_ACCOUNTS.items():
            tweets = crawl_twitter_account(account_name, url, driver, days_back=7)

            if tweets:
                # Save to local
                filename = save_tweets_to_json(tweets, account_name)

                all_results.append({
                    'account': account_name,
                    'tweet_count': len(tweets),
                    'tweets': tweets,
                    'file': filename
                })
            else:
                print(f"[WARNING] No tweets found from @{account_name}")

            # Pause between accounts
            if account_name != list(TWITTER_ACCOUNTS.keys())[-1]:
                print("\\n[INFO] Pausing 10 seconds before next account...")
                time.sleep(10)

        # Summary
        print("\\n" + "=" * 60)
        print("[COMPLETE] Crawling finished!")
        print(f"[STATS] Accounts crawled: {len(all_results)}")
        print(f"[STATS] Total tweets: {sum(result['tweet_count'] for result in all_results)}")
        print(f"[STATS] Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Calculate and display execution time
        end_time = time.time()
        duration = end_time - start_time
        print(f"[TIME] Total execution time: {duration:.1f} seconds ({duration / 60:.1f} minutes)")

        if duration > 300:  # More than 5 minutes
            print("[WARNING] Crawler took longer than 5 minutes!")

        print(f"\\n[INFO] All data saved in 'twitter_data' folder")

        success = True

    except Exception as e:
        print(f"\\n[ERROR] Error during crawling: {e}")
        success = False

    finally:
        driver.quit()
        print("[INFO] Browser closed")

    return success


if __name__ == "__main__":
    # Return status for scheduler
    success = main()
    sys.exit(0 if success else 1)