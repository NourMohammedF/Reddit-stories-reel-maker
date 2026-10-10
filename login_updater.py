import os
import json
import logging
from playwright.sync_api import sync_playwright

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Path to store session storage
session_storage_path = 'C:\\Users\\Nour\\Desktop\\My Code\\tiktok_session.json'
login_url = 'https://www.tiktok.com/login'

def save_session(context):
    """Save session (cookies) from the current browser context."""
    try:
        cookies = context.cookies()  # Get all cookies from the current context

        # Create the directory if it doesn't exist
        if not os.path.exists(os.path.dirname(session_storage_path)):
            os.makedirs(os.path.dirname(session_storage_path))

        # Write the session data to the JSON file
        with open(session_storage_path, 'w') as f:
            json.dump(cookies, f, indent=4)  # Added indent for better readability
        
        logging.info(f"Session successfully saved to {session_storage_path}.")
    except Exception as e:
        logging.error(f"Error saving session: {e}")

def login_and_save_session(playwright):
    """Let user log in manually, then save session."""
    try:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()

        page = context.new_page()
        page.goto(login_url, timeout=180000)

        logging.info("Please log in to TikTok manually...")

        # Wait for the user to finish logging in
        input("Press Enter after you have logged in...")

        # Save the session after the user logs in
        save_session(context)

    except Exception as e:
        logging.error(f"Error during login or saving session: {e}")
    finally:
        # Ensure the browser is closed even if an error occurs
        if 'context' in locals() and context:
            context.close()
        if 'browser' in locals() and browser:
            browser.close()

def main():
    with sync_playwright() as playwright:
        try:
            login_and_save_session(playwright)
        except Exception as e:
            logging.error(f"Error during execution: {e}")

if __name__ == "__main__":
    main()
