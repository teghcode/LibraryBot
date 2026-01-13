# 📚 Library Room Booker

This tool automates booking study rooms at the Carleton University Library. It is designed to run **automatically in the cloud** using GitHub Actions, but can also be run locally for testing.

---

## ☁️ Automatic Cloud Booking (Recommended)

The cloud version runs daily using GitHub Actions. The easiest way to set it up is using the included configuration tool.

### Setup Instructions
1.  **Fork and Clone:**
    *   **Fork** this repository to your own GitHub account (click the "Fork" button at the top right).
    *   **Clone** it to your local machine:
        ```bash
        git clone https://github.com/YOUR_USERNAME/LibraryBot.git
        cd LibraryBot
        pip install -r requirements.txt
        ```

2.  **Launch the Configuration Tool:**
    ```bash
    python gui.py
    ```

3.  **Set Your Preferences:**
    *   Choose your desired **Target Room**, **Start Time**, and **Duration**.
    *   Click **"Update GitHub Config (YML)"** to save these settings to your project. 

> Advanced: The GUI updates the GitHub Actions workflow file directly.
> If you prefer, you can also edit `.github/workflows/schedule_booking.yml` by hand.
> If the target room is unavailable, the bot will still attempt to book any available room for the requested time.

4.  **Set Your Credentials:**
    *   In the tool, click **"Open GitHub Secrets Page ↗"**.
    *   This will open your browser to the correct GitHub settings page.
    *   Add two new repository secrets:
        *   `CARLETON_USER` : Your username
        *   `CARLETON_PASS` : Your password
> If you prefer, you can also directly edit the secrets in GitHub, under Settings > Secrets and variables > Actions > New repository secret.
5.  **Save Changes:**
    Commit and push your updated configuration to GitHub:
    ```bash
    git add .
    git commit -m "update bot config"
    git push
    ```

No further action is required unless you want to change your booking preferences.
> Note: The bot may start slightly later than scheduled due to GitHub Actions runner availability.

---

## 💻 Local Mode (Brief)
You can run the bot manually on your own computer for testing or one-off bookings.

1.  **Install:** `pip install -r requirements.txt`
2.  **Run:**
    ```bash
    python book_room.py
    ```
    *(You will be prompted to enter your username and password securely)*
    *Tip: Run `python book_room.py --help` to see all available options.*

3.  **Custom Run:**
    ```bash
    python book_room.py --room 468 --hour 5 --minute 30 --ampm PM --duration 180
    ```
    > The example above aims to book room 468 from 5:30 PM to 7:30 PM (180 minutes); all parameters are adjustable.
