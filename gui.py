import tkinter as tk
from tkinter import ttk, messagebox
import sys
import webbrowser
import os

class BookingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Library Bot Config Editor")
        self.root.geometry("500x600")
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Header
        header_frame = ttk.Frame(root, padding=10)
        header_frame.pack(fill="x")
        ttk.Label(header_frame, text="GitHub Actions Configuration", font=("Helvetica", 14, "bold")).pack()
        ttk.Label(header_frame, text="Use this tool to update your bot's automated schedule and defaults.", foreground="gray").pack()

        # --- Preferences Frame ---
        pref_frame = ttk.LabelFrame(root, text="Booking Preferences (Defaults)", padding=10)
        pref_frame.pack(fill="x", padx=10, pady=5)
        
        # --- GitHub Schedule Frame ---
        sch_frame = ttk.LabelFrame(root, text="Daily Schedule (Cloud Run)", padding=10)
        sch_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(sch_frame, text="Run Time (EST):").grid(row=0, column=0, sticky="w")
        
        # Initialize variables
        self.room_var = tk.StringVar(value="464")
        self.hour_var = tk.StringVar(value="3")
        self.min_var = tk.StringVar(value="30")
        self.ampm_var = tk.StringVar(value="PM")
        self.dur_var = tk.StringVar(value="180")
        
        self.sch_hour_var = tk.StringVar(value="12")
        self.sch_min_var = tk.StringVar(value="01")
        self.sch_ampm_var = tk.StringVar(value="AM")

        # Load from file immediately to overwrite defaults if file exists
        self.load_current_config()

        # Room UI
        ttk.Label(pref_frame, text="Target Room:").grid(row=0, column=0, sticky="w")
        ttk.Entry(pref_frame, textvariable=self.room_var, width=10).grid(row=0, column=1, sticky="w", padx=5)
        
        # Time UI
        ttk.Label(pref_frame, text="Start Time:").grid(row=1, column=0, sticky="w")
        time_frame = ttk.Frame(pref_frame)
        time_frame.grid(row=1, column=1, sticky="w", padx=5)
        
        ttk.Spinbox(time_frame, from_=1, to=12, textvariable=self.hour_var, width=3).pack(side="left")
        ttk.Label(time_frame, text=":").pack(side="left")
        # Constrain to 0 or 30
        ttk.Combobox(time_frame, values=["00", "30"], textvariable=self.min_var, width=3, state="readonly").pack(side="left")
        ttk.Combobox(time_frame, values=["AM", "PM"], textvariable=self.ampm_var, width=4, state="readonly").pack(side="left", padx=2)
        
        # Duration UI
        ttk.Label(pref_frame, text="Duration (minutes):").grid(row=3, column=0, sticky="w")
        minutes_options = ["30", "60", "90", "120", "150", "180"]
        ttk.Combobox(pref_frame, values=minutes_options, textvariable=self.dur_var, width=5).grid(row=3, column=1, sticky="w", padx=5)
        
        # Schedule UI
        ttk.Spinbox(sch_frame, from_=1, to=12, textvariable=self.sch_hour_var, width=3).grid(row=0, column=1, sticky="w", padx=2)
        ttk.Label(sch_frame, text=":").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(sch_frame, from_=0, to=59, textvariable=self.sch_min_var, width=3, format="%02.0f").grid(row=0, column=3, sticky="w", padx=2)
        ttk.Combobox(sch_frame, values=["AM", "PM"], textvariable=self.sch_ampm_var, width=4, state="readonly").grid(row=0, column=4, sticky="w", padx=2)
        ttk.Label(sch_frame, text="(Daily)").grid(row=0, column=5, sticky="w", padx=5)


        # --- Credentials Frame ---
        cred_frame = ttk.LabelFrame(root, text="GitHub Secrets (Credentials)", padding=10)
        cred_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(cred_frame, text="Set these secrets in GitHub for the bot to work:", foreground="black").pack(anchor="w")
        ttk.Label(cred_frame, text="1. CARLETON_USER\n2. CARLETON_PASS", font=("Consolas", 10)).pack(anchor="w", padx=20, pady=2)
        
        self.secrets_btn = ttk.Button(cred_frame, text="Open GitHub Secrets Page ↗", command=self.open_secrets_page)
        self.secrets_btn.pack(fill="x", pady=5)

        # --- Actions ---
        btn_frame = ttk.Frame(root, padding=20)
        btn_frame.pack(fill="x", padx=10)
        
        self.save_yml_btn = ttk.Button(btn_frame, text="Update GitHub Config (YML)", command=self.update_yaml_config)
        self.save_yml_btn.pack(fill="x", pady=10)
        
        ttk.Label(btn_frame, text="After updating, remember to 'git commit' and 'git push'!", foreground="red").pack()

    def update_yaml_config(self):
        """Updates the default values and schedule in the GitHub Actions YAML file."""
        import ruamel.yaml
        
        yaml_path = os.path.join(os.path.dirname(__file__), ".github", "workflows", "schedule_booking.yml")
        if not os.path.exists(yaml_path):
            messagebox.showerror("Error", f"Could not find workflow file at:\n{yaml_path}")
            return
            
        try:
            yaml = ruamel.yaml.YAML()
            yaml.preserve_quotes = True
            
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.load(f)
            
            # 1. Update Inputs Defaults
            inputs = data.get('on', {}).get('workflow_dispatch', {}).get('inputs', {})
            if inputs:
                if 'target_room' in inputs:
                    inputs['target_room']['default'] = self.room_var.get()
                if 'start_hour' in inputs:
                    inputs['start_hour']['default'] = self.hour_var.get()
                if 'start_minute' in inputs:
                    inputs['start_minute']['default'] = self.min_var.get()
                if 'start_ampm' in inputs:
                    inputs['start_ampm']['default'] = self.ampm_var.get()
                if 'duration_minutes' in inputs:
                    inputs['duration_minutes']['default'] = self.dur_var.get()

            # 2. Update Cron Schedule (Convert 12h EST to UTC)
            schedules = data.get('on', {}).get('schedule', [])
            if schedules:
                try:
                    est_h_12 = int(self.sch_hour_var.get())
                    est_m = int(self.sch_min_var.get())
                    est_ampm = self.sch_ampm_var.get()
                    
                    # Convert to 24h EST
                    est_h_24 = est_h_12
                    if est_ampm == "PM" and est_h_12 != 12:
                        est_h_24 += 12
                    elif est_ampm == "AM" and est_h_12 == 12:
                        est_h_24 = 0
                        
                    # UTC = EST + 5
                    utc_h = (est_h_24 + 5) % 24
                    
                    new_cron = f"{est_m} {utc_h} * * *"
                    schedules[0]['cron'] = new_cron
                except Exception as ex:
                    print(f"Skipping schedule update (invalid time): {ex}")

            # Write back
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f)
                
            messagebox.showinfo("Success", "Updated GitHub workflow config!\n\n1. Check '.github/workflows/schedule_booking.yml' to verify.\n2. Run 'git add .'\n3. Run 'git commit -m \"update config\"'\n4. Run 'git push'")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_current_config(self):
        """Loads default values from the existing YAML file into the GUI variables."""
        import ruamel.yaml
        yaml_path = os.path.join(os.path.dirname(__file__), ".github", "workflows", "schedule_booking.yml")
        
        if not os.path.exists(yaml_path):
            return # Just use defaults
            
        try:
            yaml = ruamel.yaml.YAML()
            yaml.preserve_quotes = True
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.load(f)
            
            # 1. Load Input Defaults
            inputs = data.get('on', {}).get('workflow_dispatch', {}).get('inputs', {})
            
            # Helper to safely get default string
            def get_default(key, fallback):
                if key in inputs and 'default' in inputs[key]:
                    return str(inputs[key]['default'])
                return fallback

            self.room_var.set(get_default('target_room', "464"))
            self.hour_var.set(get_default('start_hour', "3"))
            self.min_var.set(get_default('start_minute', "30")) # Default 30
            self.ampm_var.set(get_default('start_ampm', "PM"))
            self.dur_var.set(get_default('duration_minutes', "180"))
            
            # Minute isn't in inputs (it's hardcoded to 30 in the script usually, unless we add it to inputs)
            # Checking if the user has a custom minute variable isn't standard in previous steps, 
            # but we can leave it as 30 or check if they added one.
            # For now, we'll leave it at 30 as per the script default.
            
            # 2. Load Schedule (Cron)
            # Expecting format: 'MIN HOUR * * *' (UTC)
            schedules = data.get('on', {}).get('schedule', [])
            if schedules and 'cron' in schedules[0]:
                cron_parts = schedules[0]['cron'].split()
                if len(cron_parts) >= 2:
                    utc_min = int(cron_parts[0])
                    utc_hour = int(cron_parts[1])
                    
                    # Convert UTC to EST (approximate: UTC-5)
                    # Note: Dealing with daylight savings is complex, this is a simple static offset 
                    # consistent with the write logic (EST = UTC - 5)
                     
                    est_hour_24 = (utc_hour - 5) % 24
                    
                    # Convert 24h to 12h
                    est_ampm = "AM"
                    est_hour_12 = est_hour_24
                    
                    if est_hour_24 >= 12:
                        est_ampm = "PM"
                        if est_hour_24 > 12:
                            est_hour_12 -= 12
                    elif est_hour_24 == 0:
                        est_hour_12 = 12
                        
                    self.sch_hour_var.set(str(est_hour_12))
                    self.sch_min_var.set(f"{utc_min:02d}")
                    self.sch_ampm_var.set(est_ampm)
                    
        except Exception as e:
            print(f"Failed to load existing config: {e}")

    def open_secrets_page(self):
        """Opens the GitHub Secrets settings page in the default browser."""
        # specific for this repo
        url = "https://github.com/teghcode/LibraryBot/settings/secrets/actions"
        webbrowser.open(url)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = BookingGUI(root)
        root.mainloop()
    except Exception as e:
        with open("gui_error.log", "w") as f:
            f.write(str(e))
