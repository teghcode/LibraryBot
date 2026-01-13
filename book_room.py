import os
import time
import datetime
import getpass
import base64
import argparse
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException, TimeoutException

def parse_arguments():
    parser = argparse.ArgumentParser(description="Carleton Library Room Booker")
    
    # Defaults can be overridden by Environment Variables
    default_room = os.environ.get("TARGET_ROOM", "464")
    default_hour = os.environ.get("START_HOUR", "3") # 12-hour format
    default_minute = os.environ.get("START_MINUTE", "30")
    default_ampm = os.environ.get("START_AMPM", "PM") # AM or PM
    default_duration = os.environ.get("DURATION_MINUTES", "180")
    
    parser.add_argument("--room", default=default_room, help="Target room number (e.g. 464)")
    parser.add_argument("--hour", default=default_hour, type=int, help="Start hour (1-12)")
    parser.add_argument("--minute", default=default_minute, type=int, help="Start minute (0-59)")
    parser.add_argument("--ampm", default=default_ampm, choices=["AM", "PM"], help="AM or PM")
    parser.add_argument("--duration", default=default_duration, type=int, help="Duration in minutes (e.g. 30, 60, 180)")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without submitting the booking")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")

    return parser.parse_args()

def book_room(args):
    print("--- Carleton Library Room Booker ---")
    print(f"Configuration: Room={args.room}, Time={args.hour}:{args.minute:02d} {args.ampm}, Duration={args.duration} mins")
    
    if args.dry_run:
        print("BS: *** DRY RUN MODE ENABLED - NO BOOKING WILL BE MAKING ***")
    
    # 1. Credentials
    encoded_user = "" 
    encoded_pass = ""
    
    username = os.environ.get('CARLETON_USER')
    password = os.environ.get('CARLETON_PASS')
    
    if not username and encoded_user:
        try:
            username = base64.b64decode(encoded_user).decode()
        except:
            pass
            
    if not password and encoded_pass:
        try:
            password = base64.b64decode(encoded_pass).decode()
        except:
            pass
    
    if not username:
        username = input("Enter your MyCarletonOne Username: ")
    if not password:
        password = getpass.getpass("Enter your Password: ")
    
    # 2. Setup Browser
    options = webdriver.ChromeOptions()
    # Check for CI environment variable to run headless
    is_ci = os.environ.get('CI') == 'true'
    if is_ci or args.headless:
        print("Running in headless mode")
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 10)
    
    try:
        # 3. Navigate to Study Rooms page
        print("Navigating to library website...")
        driver.get("https://library.carleton.ca/services/study-rooms")
        
        # Handle Cookie Consent
        try:
            cookie_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Ok. Got it.')]")))
            driver.execute_script("arguments[0].click();", cookie_btn)
            time.sleep(1)
        except:
            pass
        
        # Click "Book a Study Room"
        book_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='carletonu.libcal.com'] button")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", book_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", book_btn)
        
        # Switch to new tab
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[1])
            
        # 4. Select Date (One week from now)
        today = datetime.date.today()
        # logic: book for 7 days ahead
        target_date = today + datetime.timedelta(days=7)
        target_day_str = str(target_date.day)
        print(f"Target Date: {target_date.strftime('%A, %B %d, %Y')}")
        
        # Click "Go To Date"
        go_to_date_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.fc-goToDate-button")))
        go_to_date_btn.click()
        time.sleep(1) 
        
        if target_date.month > today.month:
             try:
                 next_month_btn = driver.find_element(By.CSS_SELECTOR, "button.fc-next-button")
                 next_month_btn.click()
                 time.sleep(0.5)
             except:
                 pass 

        # Click the day
        driver.execute_script(f"""
        document.querySelectorAll('td').forEach(el => {{
            if (el.innerText.trim() === '{target_day_str}' && !el.classList.contains('old') && !el.classList.contains('new')) {{
                el.click();
            }}
        }});
        """)
        
        time.sleep(2) 
        
        # 5. Select Start Time
        print(f"Selecting start time {args.hour}:{args.minute:02d} {args.ampm}...")
        
        # Convert 12h to 24h for datetime logic
        hour_24 = args.hour
        if args.ampm == "PM" and args.hour != 12:
            hour_24 += 12
        elif args.ampm == "AM" and args.hour == 12:
            hour_24 = 0
            
        start_time = datetime.datetime.combine(target_date, datetime.time(hour_24, args.minute))
        time_str = start_time.strftime("%I:%M%p").lstrip("0").lower() # e.g. "3:30pm"
        
        # Construct XPath based on strategy
        # Strategy: "Any Room" (Try preferred, then fallback)
        
        slot = None
        
        print(f"Looking for preferred Room {args.room} at {time_str}")
        xpath_specific = f"//a[contains(@title, '{time_str}') and contains(@title, '{args.room}') and contains(@title, 'Available')]"
        try:
            slot = driver.find_element(By.XPATH, xpath_specific)
            print(f"Found preferred Room {args.room}!")
        except NoSuchElementException:
            print(f"Preferred Room {args.room} unavailable. searching for ANY available room at {time_str}...")
            xpath_any = f"//a[contains(@title, '{time_str}') and contains(@title, 'Available')]"
            try:
                # Get all available slots at that time
                slots = driver.find_elements(By.XPATH, xpath_any)
                if slots:
                    slot = slots[0] # Pick the first one
                    # Extract room number from title for logging if possible
                    title = slot.get_attribute("title")
                    print(f"Found alternative slot: {title}")
                else:
                    print(f"No rooms available at all at {time_str}.")
                    return
            except Exception as e:
                print(f"Error finding alternative room: {e}")
                return

        if slot:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", slot)
            driver.execute_script("arguments[0].click();", slot)
            print(f"Clicked start time slot.")
            time.sleep(2)
        else:
            print("Failed to select a slot.")
            return

        # 6. Select End Time from Dropdown
        # Calculate expected end time
        end_time = start_time + datetime.timedelta(minutes=args.duration)
        end_time_str = end_time.strftime("%I:%M%p").lstrip("0").lower() 
        
        print(f"Selecting end time {end_time_str} from dropdown...")
        try:
            time.sleep(2)
            all_selects = driver.find_elements(By.TAG_NAME, "select")
            target_dropdown_found = False
            
            for index, select_el in enumerate(all_selects):
                try:
                    # Check visibility
                    if not select_el.is_displayed():
                        continue
                        
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", select_el)
                    select = Select(select_el)
                    
                    found_option = None
                    for option in select.options:
                        if end_time_str in option.text.lower():
                             found_option = option
                             break
                    
                    if found_option:
                        select.select_by_visible_text(found_option.text)
                        target_dropdown_found = True
                        print(f"Success: Selected '{found_option.text}'")
                        break
                    
                except Exception:
                    continue
            
            if not target_dropdown_found:
                print(f"WARNING: Could not find a dropdown option containing '{end_time_str}'.")
                
        except Exception as e:
            print(f"Error selecting end time: {e}")

        # 7. Submit Times
        print("Waiting for selection to register...")
        time.sleep(2) 
        submit_btn = driver.find_element(By.ID, "submit_times")
        driver.execute_script("arguments[0].click();", submit_btn)
        
        # 8. SSO Login
        print("Waiting for SSO Login...")
        try:
            wait.until(EC.presence_of_element_located((By.ID, "userNameInput")))
            driver.find_element(By.ID, "userNameInput").send_keys(username)
            driver.find_element(By.ID, "passwordInput").send_keys(password)
            driver.find_element(By.ID, "submitButton").click()
            print("Logged in.")
        except TimeoutException:
            print("Login page did not appear (already logged in?). Proceeding...")
            # If we are already logged in, we might be on the next page already.

        # 9. Continue Booking & Submit
        print("Finalizing booking...")
        time.sleep(3)
        
        try:
            continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
            continue_btn.click()
            time.sleep(2)
        except:
            pass
            
        if args.dry_run:
            print("[DRY RUN] Skipping final 'Submit My Booking' click.")
            print("[DRY RUN] Process would have completed successfully here.")
            return

        try:
            final_submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-form-submit")))
            final_submit_btn.click()
            print("Clicked 'Submit My Booking'.")
        except TimeoutException:
            try:
                final_submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Submit My Booking')]")
                final_submit_btn.click()
                print("Clicked 'Submit My Booking'.")
            except:
                print("Could not find 'Submit My Booking' button.")
                return

        time.sleep(5)
        print("Booking process completed.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        # Take screenshot if headless
        if is_ci or args.headless:
             driver.save_screenshot("error_screenshot.png")
             print("Saved error_screenshot.png")
        
    finally:
        print("Done.")
        driver.quit()

if __name__ == "__main__":
    args = parse_arguments()
    book_room(args)
