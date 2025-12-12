import os
import time
import datetime
import getpass
import base64
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException, TimeoutException

def book_room():
    # --- Configuration ---
    TARGET_ROOM = "464"
    START_HOUR = 15 # 3 PM
    START_MINUTE = 30
    DURATION_HOURS = 3
    
    print("--- Carleton Library Room Booker ---")
    
    # 1. Credentials
    # You can store base64 encoded strings here to avoid plain text
    # To generate: python -c "import base64; print(base64.b64encode(b'YOUR_PASSWORD').decode())"
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
    # options.add_argument("--headless") 
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
        print(f"Selecting start time {START_HOUR}:{START_MINUTE} for Room {TARGET_ROOM}...")
        
        start_time = datetime.datetime.combine(target_date, datetime.time(START_HOUR, START_MINUTE))
        time_str = start_time.strftime("%I:%M%p").lstrip("0").lower() 
        
        xpath = f"//a[contains(@title, '{time_str}') and contains(@title, '{TARGET_ROOM}') and contains(@title, 'Available')]"
        
        try:
            slot = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", slot)
            driver.execute_script("arguments[0].click();", slot)
            print(f"Clicked start time {time_str}.")
            time.sleep(2) 
        except TimeoutException:
            print(f"Could not find available slot for {time_str}.")
            return

        # 6. Select End Time from Dropdown
        print("Selecting end time 6:30pm from dropdown...")
        try:
            time.sleep(2)
            all_selects = driver.find_elements(By.TAG_NAME, "select")
            target_dropdown_found = False
            
            for select_el in all_selects:
                try:
                    if not select_el.is_displayed():
                        continue
                    select = Select(select_el)
                    for option in select.options:
                        if "6:30" in option.text or "18:30" in option.text:
                            select.select_by_visible_text(option.text)
                            target_dropdown_found = True
                            break
                    if target_dropdown_found:
                        break
                except:
                    continue
            
            if not target_dropdown_found:
                print("Could not find a dropdown with '6:30pm'. Proceeding with default duration...")
                
        except Exception as e:
            print(f"Error selecting end time: {e}")

        # 7. Submit Times
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
            print("Login page did not appear. Proceeding...")

        # 9. Continue Booking & Submit
        print("Finalizing booking...")
        time.sleep(3)
        
        try:
            continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
            continue_btn.click()
            time.sleep(2)
        except:
            pass
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
                print("Could not find 'Submit My Booking' button. Please check browser.")
                time.sleep(300)
                return

        time.sleep(5)
        print("Booking process completed.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        
    finally:
        print("Done.")

if __name__ == "__main__":
    book_room()
