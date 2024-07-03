import tkinter as tk
from tkinter import scrolledtext, messagebox, StringVar, simpledialog, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import google.generativeai as genai
import os
import subprocess
import sys
import time
import importlib
import threading
import json
import pyperclip
from PIL import Image
import markdown2
from threading import Lock
import io

class APIHandler:
    def __init__(self, settings):
        self.settings = settings
        self.api_key = self.settings.get_setting('api_key')
        self.configure_api()
        
        
    def get_api_key(self):
        config_file = 'config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get('api_key')
        
        api_key = simpledialog.askstring("API Key", "Enter your API key:", show='*')
        if api_key:
            with open(config_file, 'w') as f:
                json.dump({'api_key': api_key}, f)
            return api_key
        else:
            messagebox.showerror("Error", "API key is required to use this application.")
            sys.exit()

    def configure_api(self):
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def change_api_key(self):
        new_api_key = simpledialog.askstring("Change API Key", "Enter new API key:", show='*')
        if new_api_key:
            with open('config.json', 'w') as f:
                json.dump({'api_key': new_api_key}, f)
            self.api_key = new_api_key
            self.configure_api()
            messagebox.showinfo("Success", "API key updated successfully.")
        else:
            messagebox.showwarning("Warning", "API key not changed.")

class CodeGenerator:
    def __init__(self, model, log_output, progress_var, api_tracker):
        self.model = model
        self.log_output = log_output
        self.progress_var = progress_var
        self.api_tracker = api_tracker
        
    def generate_web_content(self, prompt):
        chat = self.model.start_chat(history=[])
        response = chat.send_message(prompt, stream=True)

        generated_content = ""
        for chunk in response:
            if hasattr(chunk, 'text'):
                generated_content += chunk.text

        return generated_content    

    def generate_code(self, user_input, file_path):
        prompt = f"Write a Python script/program to {user_input}. Only give code and nothing else."
        self.log_output.insert(tk.END, f"Request Sent: {prompt}\n")
        if file_path:
            self.log_output.insert(tk.END, f"File attached: {file_path}\n")
        self.log_output.see(tk.END)
        self.api_tracker.add_request()
        self.progress_var.set(0)
        
        def generate_code_thread():
            try:
                chat = self.model.start_chat(history=[])
                
                if file_path:
                    with open(file_path, 'rb') as file:
                        file_content = file.read()
                    response = chat.send_message([prompt, file_content], stream=True)
                else:
                    response = chat.send_message(prompt, stream=True)

                generated_code = ""
                for chunk in response:
                    if hasattr(chunk, 'text'):
                        generated_code += chunk.text
                    self.progress_var.set(min(self.progress_var.get() + 10, 90))

                if generated_code.startswith("```") and generated_code.endswith("```"):
                    generated_code = generated_code.strip("```").strip()
                    if generated_code.startswith("python"):
                        generated_code = generated_code[6:]

                self.log_output.delete("1.0", tk.END)
                self.log_output.insert(tk.END, generated_code)
                self.log_output.insert(tk.END, "Response Received:\n")
                self.log_output.insert(tk.END, generated_code + "\n")
                self.log_output.see(tk.END)

                self.install_libraries(generated_code)
                self.execute_code(generated_code)

            except Exception as e:
                self.log_output.insert(tk.END, f"An error occurred: {e}\n")
                self.log_output.see(tk.END)

            self.progress_var.set(100)

        threading.Thread(target=generate_code_thread).start()

    def install_libraries(self, code):
        libraries = self.identify_libraries(code)
        for library in libraries:
            if not self.is_installed(library):
                self.log_output.insert(tk.END, f"Library '{library}' is not installed. Attempting to install...\n")
                self.log_output.see(tk.END)
                if self.install_package(library):
                    self.log_output.insert(tk.END, f"Successfully installed {library}.\n")
                    self.log_output.see(tk.END)
                else:
                    self.log_output.insert(tk.END, f"Failed to install {library}. Skipping script execution.\n")
                    self.log_output.see(tk.END)
                    return False
        return True

    def identify_libraries(self, code):
        libraries = []
        for line in code.splitlines():
            if line.startswith("import ") or line.startswith("from "):
                parts = line.split()
                if parts[0] == "import":
                    libraries.append(parts[1].split('.')[0])
                elif parts[0] == "from":
                    libraries.append(parts[1].split('.')[0])
        return libraries

    def is_installed(self, package_name):
        spec = importlib.util.find_spec(package_name)
        return spec is not None

    def install_package(self, package):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            return True
        except subprocess.CalledProcessError as e:
            self.log_output.insert(tk.END, f"Failed to install {package}. Error: {e}\n")
            self.log_output.see(tk.END)
            return False

    def execute_code(self, code):
        start_time = time.time()
        try:
            exec(code)
        except Exception as e:
            self.log_output.insert(tk.END, f"An error occurred during script execution: {e}\n")
            self.log_output.see(tk.END)

        end_time = time.time()
        execution_time = end_time - start_time
        self.log_output.insert(tk.END, f"Execution time: {execution_time:.2f} seconds\n")
        self.log_output.insert(tk.END, "_" * 80 + "\n")
        self.log_output.see(tk.END)

class QAHandler:
    def __init__(self, model, log_output, progress_var, copy_button, api_tracker):
        self.model = model
        self.log_output = log_output
        self.progress_var = progress_var
        self.copy_button = copy_button  # Assign copy_button attribute
        self.api_tracker = api_tracker

    def qa_mode(self, user_input, file_path):
        self.log_output.insert(tk.END, f"Question: {user_input}\n")
        if file_path:
            self.log_output.insert(tk.END, f"File attached: {file_path}\n")
        self.log_output.see(tk.END)
        
        if self.copy_button:
            self.copy_button.config(state='disabled')
        else:
            print("self.copy_button is None or not initialized properly")
        self.api_tracker.add_request()
        self.progress_var.set(0)

        def qa_mode_thread():
            try:
                chat = self.model.start_chat(history=[])
                
                if file_path:
                    with open(file_path, 'rb') as file:
                        file_content = file.read()
                    image = Image.open(io.BytesIO(file_content))  # Convert bytes to PIL Image
                    response = chat.send_message([user_input, image], stream=True)
                else:
                    response = chat.send_message(user_input, stream=True)

                answer = ""
                for chunk in response:
                    if hasattr(chunk, 'text'):
                        answer += chunk.text
                    self.progress_var.set(min(self.progress_var.get() + 10, 90))

                answer = self.process_markdown(answer)  # Process Markdown in the answer
                self.log_output.insert(tk.END, f"Answer: {answer}\n")
                self.log_output.insert(tk.END, "_" * 80 + "\n")
                self.log_output.see(tk.END)
                
                if self.copy_button:
                    self.copy_button.config(state='normal')
                else:
                    print("self.copy_button is None or not initialized properly")
                
            except Exception as e:
                self.log_output.insert(tk.END, f"An error occurred: {e}\n")
                self.log_output.see(tk.END)

            self.progress_var.set(100)

        threading.Thread(target=qa_mode_thread).start()

    def process_markdown(self, text):
        # Convert markdown to HTML
        html = markdown2.markdown(text)
        
        # Basic HTML to text conversion (you might want to expand this)
        html = html.replace('<p>', '').replace('</p>', '\n')
        html = html.replace('<strong>', '').replace('</strong>', '')
        html = html.replace('<em>', '').replace('</em>', '')
        html = html.replace('<code>', '`').replace('</code>', '`')
        
        # Handle code blocks
        lines = html.split('\n')
        in_code_block = False
        processed_lines = []
        for line in lines:
            if line.strip() == '<pre><code>':
                in_code_block = True
                processed_lines.append('```')
            elif line.strip() == '</code></pre>':
                in_code_block = False
                processed_lines.append('```')
            elif in_code_block:
                processed_lines.append(line)
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
class ScriptManager:
    def __init__(self, log_output, saved_scripts_listbox, settings):
        self.log_output = log_output
        self.saved_scripts_listbox = saved_scripts_listbox
        self.settings = settings
        self.scripts_folder = self.settings.get_setting('script_save_location')

        # Ensure the folder exists
        if not os.path.exists(self.scripts_folder):
            os.makedirs(self.scripts_folder)

    def save_code(self, script_name, generated_code):
        if not generated_code.strip():
            messagebox.showerror("Error", "No code generated to save.")
            return

        if not script_name:
            messagebox.showerror("Error", "Please enter a script name.")
            return

        script_file = os.path.join(self.scripts_folder, f"{script_name}.py")

        def save_code_thread():
            with open(script_file, "w") as file:
                file.write(generated_code)
            
            self.saved_scripts_listbox.insert("", "end", text=script_name)

            self.log_output.insert(tk.END, f"Script saved as '{script_file}'\n")
            self.log_output.see(tk.END)

        threading.Thread(target=save_code_thread).start()

    def load_saved_script(self):
        selected_item = self.saved_scripts_listbox.selection()
        if selected_item:
            script_name = self.saved_scripts_listbox.item(selected_item, 'text')
            script_file = os.path.join(self.scripts_folder, f"{script_name}.py")

            try:
                with open(script_file, "r") as file:
                    script_code = file.read()

                self.log_output.delete("1.0", tk.END)
                self.log_output.insert(tk.END, script_code)
                self.log_output.insert(tk.END, f"Loaded saved script '{script_name}.py':\n")
                self.log_output.see(tk.END)

                exec(script_code)
            except FileNotFoundError:
                self.log_output.insert(tk.END, f"Error: '{script_name}.py' not found at '{script_file}'.\n")
                self.log_output.see(tk.END)
            except Exception as e:
                self.log_output.insert(tk.END, f"An error occurred while loading or executing '{script_name}.py': {e}\n")
                self.log_output.see(tk.END)
        else:
            messagebox.showerror("Error", "Please select a script to load.")

    def delete_saved_script(self):
        selected_item = self.saved_scripts_listbox.selection()
        if selected_item:
            script_name = self.saved_scripts_listbox.item(selected_item, 'text')
            script_file = os.path.join(self.scripts_folder, f"{script_name}.py")
            
            if os.path.exists(script_file):
                os.remove(script_file)
                self.saved_scripts_listbox.delete(selected_item)
                self.log_output.insert(tk.END, f"Deleted script: {script_name}.py\n")
                self.log_output.see(tk.END)
            else:
                messagebox.showerror("Error", f"Script file not found: {script_name}.py")
        else:
            messagebox.showerror("Error", "Please select a script to delete.")

class APITracker:
    def __init__(self, rpm_limit=15):
        self.rpm_limit = rpm_limit
        self.requests = []
        self.total_requests = 0
        self.lock = Lock()

    def add_request(self):
        with self.lock:
            current_time = time.time()
            self.requests = [t for t in self.requests if current_time - t < 60]
            self.requests.append(current_time)
            self.total_requests += 1

    def get_current_rpm(self):
        with self.lock:
            current_time = time.time()
            self.requests = [t for t in self.requests if current_time - t < 60]
            return len(self.requests)

    def get_total_requests(self):
        return self.total_requests


class Settings:
    def __init__(self):
        self.config_file = 'config.json'
        self.default_settings = {
            'api_key': '',
            'script_save_location': os.path.join(os.path.dirname(__file__), "automated_scripts"),
            'shortcuts': {
                'save_script': '<Control-s>',
                'copy_output': '<Control-c>',
                'process_input': '<Return>',
                'select_automation': '<Control-Key-1>',
                'select_qa': '<Control-Key-2>',
                'select_first_script': '<Control-Key-3>',
            }
        }
        self.settings = self.load_settings()

    def load_settings(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return self.default_settings

    def save_settings(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def get_setting(self, key):
        return self.settings.get(key, self.default_settings.get(key))

    def set_setting(self, key, value):
        self.settings[key] = value
        self.save_settings()

    def reset_to_default(self):
        self.settings = self.default_settings.copy()
        self.save_settings()

class GUI:
    def __init__(self, root, api_handler, code_generator, qa_handler, script_manager):
        self.root = root
        self.api_tracker = APITracker()
        self.api_handler = api_handler
        self.code_generator = code_generator
        self.qa_handler = qa_handler
        self.script_manager = script_manager
        self.settings = Settings()
        self.setup_gui()
        self.setup_keyboard_shortcuts()
        self.update_api_tracker()

    def setup_gui(self):
        self.root.title("Task Automate")
        self.root.geometry("1200x1000")

        settings_button = ttk.Button(self.root, text="Settings", command=self.open_settings, style='info.TButton')
        settings_button.pack(side=TOP, anchor=NE, padx=20, pady=10)

        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=BOTH, expand=YES)

        left_pane = ttk.Frame(main_frame)
        left_pane.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 10))

        right_pane = ttk.Frame(main_frame)
        right_pane.pack(side=RIGHT, fill=BOTH, expand=YES, padx=(10, 0))

        

        self.setup_input_section(left_pane)
        self.setup_output_section(left_pane)
        self.setup_saved_scripts_section(right_pane)
        self.setup_api_tracker_display(self.root)
        self.setup_status_bar()

    def open_settings(self):
        settings_window = ttk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("600x400")

        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # Shortcuts tab
        shortcuts_frame = ttk.Frame(notebook)
        notebook.add(shortcuts_frame, text="Shortcuts")
        self.setup_shortcuts_tab(shortcuts_frame)

        # API Key tab
        api_key_frame = ttk.Frame(notebook)
        notebook.add(api_key_frame, text="API Key")
        self.setup_api_key_tab(api_key_frame)

        # Script Save Location tab
        save_location_frame = ttk.Frame(notebook)
        notebook.add(save_location_frame, text="Save Location")
        self.setup_save_location_tab(save_location_frame)

    def setup_shortcuts_tab(self, parent):
        for i, (action, shortcut) in enumerate(self.settings.get_setting('shortcuts').items()):
            ttk.Label(parent, text=f"{action.replace('_', ' ').title()}:").grid(row=i, column=0, padx=5, pady=5, sticky=W)
            shortcut_var = StringVar(value=shortcut)
            shortcut_entry = ttk.Entry(parent, textvariable=shortcut_var)
            shortcut_entry.grid(row=i, column=1, padx=5, pady=5, sticky=W)
            ttk.Button(parent, text="Change", command=lambda a=action, sv=shortcut_var: self.change_shortcut(a, sv)).grid(row=i, column=2, padx=5, pady=5)

        ttk.Button(parent, text="Reset to Default", command=self.reset_shortcuts).grid(row=i+1, column=0, columnspan=3, pady=20)

    def setup_api_key_tab(self, parent):
        ttk.Label(parent, text="API Key:").pack(anchor=W, padx=10, pady=10)
        api_key_var = StringVar(value=self.settings.get_setting('api_key'))
        api_key_entry = ttk.Entry(parent, textvariable=api_key_var, show='*', width=50)
        api_key_entry.pack(anchor=W, padx=10, pady=5)
        ttk.Button(parent, text="Update API Key", command=lambda: self.update_api_key(api_key_var.get())).pack(anchor=W, padx=10, pady=10)

    def setup_save_location_tab(self, parent):
        ttk.Label(parent, text="Script Save Location:").pack(anchor=W, padx=10, pady=10)
        save_location_var = StringVar(value=self.settings.get_setting('script_save_location'))
        save_location_entry = ttk.Entry(parent, textvariable=save_location_var, width=50)
        save_location_entry.pack(anchor=W, padx=10, pady=5)
        ttk.Button(parent, text="Browse", command=lambda: self.browse_save_location(save_location_var)).pack(anchor=W, padx=10, pady=5)
        ttk.Button(parent, text="Update Save Location", command=lambda: self.update_save_location(save_location_var.get())).pack(anchor=W, padx=10, pady=10)

    def change_shortcut(self, action, shortcut_var):
        new_shortcut = simpledialog.askstring("Change Shortcut", f"Enter new shortcut for {action}:", parent=self.root)
        if new_shortcut:
            shortcut_var.set(new_shortcut)
            shortcuts = self.settings.get_setting('shortcuts')
            shortcuts[action] = new_shortcut
            self.settings.set_setting('shortcuts', shortcuts)
            self.setup_keyboard_shortcuts()

    def reset_shortcuts(self):
        self.settings.reset_to_default()
        self.setup_keyboard_shortcuts()
        messagebox.showinfo("Reset Shortcuts", "Shortcuts have been reset to default values.")

    def update_api_key(self, new_api_key):
        self.settings.set_setting('api_key', new_api_key)
        self.api_handler.api_key = new_api_key
        self.api_handler.configure_api()
        messagebox.showinfo("API Key Updated", "API Key has been updated successfully.")

    def browse_save_location(self, save_location_var):
        new_location = filedialog.askdirectory()
        if new_location:
            save_location_var.set(new_location)

    def update_save_location(self, new_location):
        if os.path.exists(new_location):
            self.settings.set_setting('script_save_location', new_location)
            self.script_manager.scripts_folder = new_location
            messagebox.showinfo("Save Location Updated", "Script save location has been updated successfully.")
        else:
            messagebox.showerror("Invalid Location", "The specified location does not exist.")


    def setup_input_section(self, parent):
        input_frame = ttk.LabelFrame(parent, text="Input", padding="10")
        input_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(input_frame, text="Enter your command/question:").pack(anchor=W, pady=(0, 5))
        self.entry = ttk.Entry(input_frame, width=50, font=('Helvetica', 12))
        self.entry.pack(fill=X, expand=YES, pady=(0, 10))

        file_frame = ttk.Frame(input_frame)
        file_frame.pack(fill=X)

        self.file_path_var = StringVar()
        ttk.Button(file_frame, text="Select File", command=self.select_file, style='info.TButton').pack(side=LEFT)
        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.pack(side=LEFT, padx=(10, 0))

        mode_frame = ttk.Frame(input_frame)
        mode_frame.pack(fill=X, pady=(10, 0))

        self.mode_var = StringVar(value="Q/A")
        ttk.Label(mode_frame, text="Mode:").pack(side=LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="Automation", variable=self.mode_var, value="Automation").pack(side=LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="Q/A", variable=self.mode_var, value="Q/A").pack(side=LEFT)
        ttk.Radiobutton(mode_frame, text="Web Development", variable=self.mode_var, value="Web Development").pack(side=LEFT)

        ttk.Button(input_frame, text="Process", command=self.process_input, style='success.TButton').pack(fill=X, pady=(10, 0))

    def setup_output_section(self, parent):
        output_frame = ttk.LabelFrame(parent, text="Output", padding="10")
        output_frame.pack(fill=BOTH, expand=YES, pady=(10, 0))

        self.log_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, font=('Consolas', 11))
        self.log_output.pack(fill=BOTH, expand=YES)

        button_frame = ttk.Frame(output_frame)
        button_frame.pack(fill=X, pady=(10, 0))

        self.copy_button = ttk.Button(button_frame, text="Copy Output", command=self.copy_output, style='info.TButton')
        self.copy_button.pack(side=LEFT, fill=X, expand=YES)

        self.save_button = ttk.Button(button_frame, text="Save Script", command=self.save_code, style='info.TButton')
        self.save_button.pack(side=RIGHT, fill=X, expand=YES, padx=(10, 0))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(parent, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=X, pady=(10, 0))

    def setup_saved_scripts_section(self, parent):
        scripts_frame = ttk.LabelFrame(parent, text="Saved Scripts", padding="10")
        scripts_frame.pack(fill=BOTH, expand=YES)

        self.saved_scripts_listbox = ttk.Treeview(scripts_frame, selectmode="browse", show="tree", style='info.Treeview')
        self.saved_scripts_listbox.pack(side=LEFT, fill=BOTH, expand=YES)

        scrollbar = ttk.Scrollbar(scripts_frame, orient=VERTICAL, command=self.saved_scripts_listbox.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.saved_scripts_listbox.config(yscrollcommand=scrollbar.set)

        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=X, pady=(10, 0))

        ttk.Button(button_frame, text="Load Selected Script", command=self.load_saved_script, style='info.TButton').pack(side=LEFT, fill=X, expand=YES, padx=(0, 5))
        ttk.Button(button_frame, text="Delete Selected Script", command=self.delete_saved_script, style='danger.TButton').pack(side=RIGHT, fill=X, expand=YES, padx=(5, 0))

        self.populate_saved_scripts()

    def setup_api_tracker_display(self, parent):
        tracker_frame = ttk.LabelFrame(parent, text="API Usage", padding="10")
        tracker_frame.pack(fill=X, pady=(10, 0))

        self.rpm_var = tk.IntVar()
        self.total_requests_var = tk.IntVar()

        ttk.Label(tracker_frame, text="Requests per minute:").pack(side=LEFT, padx=(0, 5))
        self.rpm_progress = ttk.Progressbar(tracker_frame, variable=self.rpm_var, maximum=15, length=200, mode='determinate', style='info.Horizontal.TProgressbar')
        self.rpm_progress.pack(side=LEFT, padx=(0, 10))

        ttk.Label(tracker_frame, text="Total requests:").pack(side=LEFT, padx=(10, 5))
        ttk.Label(tracker_frame, textvariable=self.total_requests_var, font=('Helvetica', 10, 'bold')).pack(side=LEFT)

    def setup_status_bar(self):
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=W, padding=(5, 2))
        self.status_bar.pack(side=BOTTOM, fill=X)

    def setup_keyboard_shortcuts(self):
        shortcuts = self.settings.get_setting('shortcuts')
        self.root.bind(shortcuts['save_script'], lambda e: self.save_code())
        self.root.bind(shortcuts['copy_output'], lambda e: self.copy_output())
        self.root.bind(shortcuts['process_input'], lambda e: self.process_input())
        self.root.bind(shortcuts['select_automation'], lambda e: self.select_mode("Automation"))
        self.root.bind(shortcuts['select_qa'], lambda e: self.select_mode("Q/A"))
        self.root.bind(shortcuts['select_first_script'], lambda e: self.select_first_saved_script())

    def select_mode(self, mode):
        self.mode_var.set(mode)
        self.update_status(f"Mode changed to {mode}")
        
    def select_first_saved_script(self):
        first_item = self.saved_scripts_listbox.get_children('')
        if first_item:
            self.saved_scripts_listbox.selection_set(first_item[0])
            self.saved_scripts_listbox.focus(first_item[0])
            self.update_status("First saved script selected")
        else:
            self.update_status("No saved scripts available")    
    
    def focus_next_widget(self, event):
        event.widget.tk_focusNext().focus()
        return "break"

    def focus_prev_widget(self, event):
        event.widget.tk_focusPrev().focus()
        return "break"

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("All files", "*.*")])
        if file_path:
            self.file_path_var.set(file_path)
            self.file_label.config(text=f"Selected: {file_path.split('/')[-1]}")
        else:
            self.file_path_var.set("")
            self.file_label.config(text="No file selected")

    def process_input(self):
        mode = self.mode_var.get()
        self.update_status("Processing...")
        if mode == "Automation":
            self.code_generator.generate_code(self.entry.get(), self.file_path_var.get())
        elif mode == "Q/A":
            self.qa_handler.qa_mode(self.entry.get(), self.file_path_var.get())
        elif mode == "Web Development":
            self.generate_web_files(self.entry.get())
        self.update_status("Ready")
        self.api_tracker.add_request()

    def generate_web_files(self, user_input):
        prompt = f"Generate HTML, CSS, and JavaScript files for a web page that {user_input}. Provide the content for each file separately."
        self.log_output.insert(tk.END, f"Request Sent: {prompt}\n")
        self.log_output.see(tk.END)
        self.api_tracker.add_request()
        self.progress_var.set(0)

        def generate_web_files_thread():
            try:
                chat = self.code_generator.model.start_chat(history=[])
                response = chat.send_message(prompt, stream=True)

                generated_content = ""
                for chunk in response:
                    if hasattr(chunk, 'text'):
                        generated_content += chunk.text
                    self.progress_var.set(min(self.progress_var.get() + 10, 90))

                # Parse the generated content to separate HTML, CSS, and JS
                html_content = self.extract_content(generated_content, "HTML")
                css_content = self.extract_content(generated_content, "CSS")
                js_content = self.extract_content(generated_content, "JavaScript")

                # Create a new folder for the web files
                folder_name = simpledialog.askstring("Folder Name", "Enter a name for the web project folder:")
                if folder_name:
                    folder_path = os.path.join(self.script_manager.scripts_folder, folder_name)
                    os.makedirs(folder_path, exist_ok=True)

                    # Save the files
                    self.save_web_file(folder_path, "index.html", html_content)
                    self.save_web_file(folder_path, "styles.css", css_content)
                    self.save_web_file(folder_path, "script.js", js_content)

                    self.log_output.insert(tk.END, f"Web files generated and saved in folder: {folder_path}\n")
                else:
                    self.log_output.insert(tk.END, "Web file generation cancelled.\n")

                self.log_output.see(tk.END)

            except Exception as e:
                self.log_output.insert(tk.END, f"An error occurred: {e}\n")
                self.log_output.see(tk.END)

            self.progress_var.set(100)

        threading.Thread(target=generate_web_files_thread).start()
    
    def extract_content(self, content, file_type):
        start_marker = f"```{file_type.lower()}"
        end_marker = "```"
        start_index = content.find(start_marker)
        if start_index != -1:
            start_index += len(start_marker)
            end_index = content.find(end_marker, start_index)
            if end_index != -1:
                return content[start_index:end_index].strip()
        return ""

    def save_web_file(self, folder_path, file_name, content):
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, 'w') as f:
            f.write(content)
        self.log_output.insert(tk.END, f"Saved {file_name}\n")
        
    def copy_output(self):
        output_content = self.log_output.get("1.0", tk.END)
        pyperclip.copy(output_content)
        self.update_status("Output copied to clipboard")

    def save_code(self):
        if self.mode_var.get() == "Automation":
            script_name = simpledialog.askstring("Save Script", "Enter script name:")
            if script_name:
                # Get the content from the log output
                content = self.log_output.get("1.0", tk.END).strip()
                
                # Extract only the generated code
                generated_code = self.extract_generated_code(content)
                
                if generated_code:
                    # Show the code to be saved and ask for confirmation
                    confirm = messagebox.askyesno("Confirm Save", f"The following code will be saved:\n\n{generated_code}\n\nDo you want to proceed?")
                    if confirm:
                        # Save the code
                        self.script_manager.save_code(script_name, generated_code)
                        self.populate_saved_scripts()
                        self.update_status(f"Script '{script_name}' saved successfully")
                    else:
                        self.update_status("Save operation cancelled")
                else:
                    messagebox.showwarning("No Code Found", "No valid Python code found to save. Please generate some code first.")
        else:
            self.update_status("Script saving is only available in Automation mode")

    def extract_generated_code(self, content):
        # Split the content by lines
        lines = content.split('\n')
        
        # Find the start and end of the generated code
        code_lines = []
        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith("import ") or stripped_line.startswith("from "):
                code_lines = [line]  # Start collecting code from this line
            elif code_lines:
                if stripped_line.startswith("Response Received:") or stripped_line.startswith("_"):
                    break  # Stop collecting code when we hit "Response Received:" or a line of underscores
                if stripped_line and not stripped_line.startswith("Execution time:"):
                    code_lines.append(line)
        
        return "\n".join(code_lines).strip() if code_lines else None

    def load_saved_script(self):
        self.script_manager.load_saved_script()

    def delete_saved_script(self):
        self.script_manager.delete_saved_script()
        self.populate_saved_scripts()

    def update_status(self, message):
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def populate_saved_scripts(self):
        self.saved_scripts_listbox.delete(*self.saved_scripts_listbox.get_children())
        scripts_folder = self.script_manager.scripts_folder
        for script_file in os.listdir(scripts_folder):
            if script_file.endswith(".py"):
                script_name = os.path.splitext(script_file)[0]
                self.saved_scripts_listbox.insert("", "end", text=script_name)

    def update_api_tracker(self):
        current_rpm = self.api_tracker.get_current_rpm()
        total_requests = self.api_tracker.get_total_requests()

        self.rpm_var.set(current_rpm)
        self.total_requests_var.set(total_requests)

        if current_rpm >= 13:
            self.rpm_progress.configure(style='danger.Horizontal.TProgressbar')
        elif current_rpm >= 10:
            self.rpm_progress.configure(style='warning.Horizontal.TProgressbar')
        else:
            self.rpm_progress.configure(style='info.Horizontal.TProgressbar')

        self.root.after(1000, self.update_api_tracker)


class App:
    def __init__(self):
        self.root = ttk.Window(themename="cosmo")
        self.settings = Settings()
        self.api_handler = APIHandler(self.settings)
        self.api_tracker = APITracker()
        
        self.code_generator = CodeGenerator(self.api_handler.model, None, None, self.api_tracker)
        self.qa_handler = QAHandler(self.api_handler.model, None, None, None, self.api_tracker)
        self.script_manager = ScriptManager(None, None, self.settings)
        
        self.gui = GUI(self.root, self.api_handler, self.code_generator, self.qa_handler, self.script_manager)
        
        # Now that GUI is initialized, we can set the missing attributes
        self.code_generator.log_output = self.gui.log_output
        self.code_generator.progress_var = self.gui.progress_var
        self.qa_handler.log_output = self.gui.log_output
        self.qa_handler.progress_var = self.gui.progress_var
        self.qa_handler.copy_button = self.gui.copy_button
        self.script_manager.log_output = self.gui.log_output
        self.script_manager.saved_scripts_listbox = self.gui.saved_scripts_listbox

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = App()
    app.run()
