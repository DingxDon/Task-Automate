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

class APIHandler:
    def __init__(self):
        self.api_key = self.get_api_key()
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
    def __init__(self, model, log_output, progress_var):
        self.model = model
        self.log_output = log_output
        self.progress_var = progress_var

    def generate_code(self, user_input, file_path):
        prompt = f"Write a Python script/program to {user_input}. Only give code and nothing else."
        self.log_output.insert(tk.END, f"Request Sent: {prompt}\n")
        if file_path:
            self.log_output.insert(tk.END, f"File attached: {file_path}\n")
        self.log_output.see(tk.END)

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
    def __init__(self, model, log_output, progress_var, copy_button):
        self.model = model
        self.log_output = log_output
        self.progress_var = progress_var
        self.copy_button = copy_button  # Assign copy_button attribute

    def qa_mode(self, user_input, file_path):
        self.log_output.insert(tk.END, f"Question: {user_input}\n")
        if file_path:
            self.log_output.insert(tk.END, f"File attached: {file_path}\n")
        self.log_output.see(tk.END)
        
        # Ensure self.copy_button is accessed correctly
        if self.copy_button:
            self.copy_button.config(state='disabled')
        else:
            print("self.copy_button is None or not initialized properly")

        self.progress_var.set(0)

        def qa_mode_thread():
            try:
                chat = self.model.start_chat(history=[])
                
                if file_path:
                    with open(file_path, 'rb') as file:
                        file_content = file.read()
                    response = chat.send_message([user_input, file_content], stream=True)
                else:
                    response = chat.send_message(user_input, stream=True)

                answer = ""
                for chunk in response:
                    if hasattr(chunk, 'text'):
                        answer += chunk.text
                    self.progress_var.set(min(self.progress_var.get() + 10, 90))

                self.log_output.insert(tk.END, f"Answer: {answer}\n")
                self.log_output.insert(tk.END, "_" * 80 + "\n")
                self.log_output.see(tk.END)
                
                # Ensure self.copy_button is accessed correctly
                if self.copy_button:
                    self.copy_button.config(state='normal')
                else:
                    print("self.copy_button is None or not initialized properly")
                
            except Exception as e:
                self.log_output.insert(tk.END, f"An error occurred: {e}\n")
                self.log_output.see(tk.END)

            self.progress_var.set(100)

        threading.Thread(target=qa_mode_thread).start()

class ScriptManager:
    def __init__(self, log_output, saved_scripts_listbox):
        self.log_output = log_output
        self.saved_scripts_listbox = saved_scripts_listbox

    def save_code(self, script_name, generated_code):
        if not generated_code.strip():
            messagebox.showerror("Error", "No code generated to save.")
            return

        if not script_name:
            messagebox.showerror("Error", "Please enter a script name.")
            return

        script_file = os.path.join(os.path.dirname(__file__), f"{script_name}.py")

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
            script_name = self.saved_scripts_listbox.item(selected_item)['text']

            try:
                with open(os.path.join(os.path.dirname(__file__), f"{script_name}.py"), "r") as file:
                    script_code = file.read()

                self.log_output.delete("1.0", tk.END)
                self.log_output.insert(tk.END, script_code)
                self.log_output.insert(tk.END, f"Loaded saved script '{script_name}.py':\n")
                self.log_output.see(tk.END)

                exec(script_code)
            except FileNotFoundError:
                self.log_output.insert(tk.END, f"Error: '{script_name}.py' not found.\n")
                self.log_output.see(tk.END)
            except Exception as e:
                self.log_output.insert(tk.END, f"An error occurred while loading or executing '{script_name}.py': {e}\n")
                self.log_output.see(tk.END)
        else:
            messagebox.showerror("Error", "Please select a script to load.")

    def delete_saved_script(self):
        selected_item = self.saved_scripts_listbox.selection()
        if selected_item:
            script_name = self.saved_scripts_listbox.item(selected_item)['text']
            script_file = os.path.join(os.path.dirname(__file__), f"{script_name}.py")
            
            if os.path.exists(script_file):
                os.remove(script_file)
                self.saved_scripts_listbox.delete(selected_item)
                self.log_output.insert(tk.END, f"Deleted script: {script_name}.py\n")
                self.log_output.see(tk.END)
            else:
                messagebox.showerror("Error", f"Script file not found: {script_name}.py")
        else:
            messagebox.showerror("Error", "Please select a script to delete.")

class GUI:
    def __init__(self, root, api_handler, code_generator, qa_handler, script_manager):
        self.root = root
        self.api_handler = api_handler
        self.code_generator = code_generator
        self.qa_handler = qa_handler
        self.script_manager = script_manager
        self.copy_button = None
        self.setup_gui()

    def setup_gui(self):
        self.root.title("Task Automate")
        self.root.geometry("1200x800")

        main_frame = ttk.Frame(self.root, padding="20 20 20 0")
        main_frame.pack(fill=BOTH, expand=YES)

        left_pane = ttk.Frame(main_frame, padding="0 0 10 0")
        left_pane.pack(side=LEFT, fill=BOTH, expand=YES)

        right_pane = ttk.Frame(main_frame, padding="10 0 0 0")
        right_pane.pack(side=RIGHT, fill=BOTH, expand=YES)

        self.setup_input_section(left_pane)
        self.setup_log_output(left_pane)
        self.setup_saved_scripts_section(right_pane)
        self.setup_status_bar()

    def setup_input_section(self, parent):
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=X, pady=(0, 10))

        label = ttk.Label(input_frame, text="Enter your command/question:", font=('Helvetica', 12, 'bold'))
        label.pack(anchor=W, pady=(0, 5))

        self.entry = ttk.Entry(input_frame, width=50, font=('Helvetica', 12))
        self.entry.pack(fill=X, expand=YES)

        file_frame = ttk.Frame(parent)
        file_frame.pack(fill=X, pady=(0, 10))

        self.file_path_var = StringVar()
        file_button = ttk.Button(file_frame, text="Select File", command=self.select_file, style='info.TButton')
        file_button.pack(side=LEFT)

        self.file_label = ttk.Label(file_frame, text="No file selected", font=('Helvetica', 10))
        self.file_label.pack(side=LEFT, padx=(10, 0))

        mode_frame = ttk.Frame(parent)
        mode_frame.pack(fill=X, pady=(0, 10))

        self.mode_var = StringVar(self.root)
        self.mode_var.set("Automation")
        mode_label = ttk.Label(mode_frame, text="Mode:", font=('Helvetica', 12))
        mode_label.pack(side=LEFT, padx=(0, 10))
        mode_dropdown = ttk.Combobox(mode_frame, textvariable=self.mode_var, values=["Automation", "Q/A"], state="readonly", width=15, font=('Helvetica', 12))
        mode_dropdown.pack(side=LEFT)

        process_button = ttk.Button(parent, text="Process", command=self.process_input, style='success.TButton')
        process_button.pack(fill=X, pady=(0, 20))

        self.script_name_frame = ttk.Frame(parent)
        script_name_label = ttk.Label(self.script_name_frame, text="Enter script name:", font=('Helvetica', 12))
        script_name_label.pack(anchor=W, pady=(0, 5))

        self.script_name_entry = ttk.Entry(self.script_name_frame, font=('Helvetica', 12))
        self.script_name_entry.pack(fill=X, expand=YES, side=LEFT)

        save_button = ttk.Button(self.script_name_frame, text="Save", command=self.save_code, style='info.TButton', width=10)
        save_button.pack(side=RIGHT, padx=(10, 0))

        self.mode_var.trace('w', self.toggle_script_name_frame)

        api_key_button = ttk.Button(parent, text="Change API Key", command=self.api_handler.change_api_key, style='secondary.TButton')
        api_key_button.pack(fill=X, pady=(0, 10))

    def setup_copy_button(self, parent):
        self.copy_button = ttk.Button(parent, text="Copy Answer", command=self.copy_answer, state='disabled', style='info.TButton')
        self.copy_button.pack(fill=X, pady=(10, 0))

    def copy_answer(self):
        answer = self.log_output.get("1.0", tk.END).split("Answer: ")[-1].split("_" * 80)[0].strip()
        pyperclip.copy(answer)
        self.update_status("Answer copied to clipboard")
        
    def setup_log_output(self, parent):
        log_frame = ttk.LabelFrame(parent, text="Output", padding=10)
        log_frame.pack(fill=BOTH, expand=YES)

        self.log_output = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=('Consolas', 11))
        self.log_output.pack(fill=BOTH, expand=YES)

        self.setup_copy_button(parent)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(parent, variable=self.progress_var, maximum=100)

    def setup_saved_scripts_section(self, parent):
        saved_scripts_frame = ttk.LabelFrame(parent, text="Saved Scripts", padding=10)
        saved_scripts_frame.pack(fill=BOTH, expand=YES)

        self.saved_scripts_listbox = ttk.Treeview(saved_scripts_frame, selectmode="browse", show="tree", style='info.Treeview')
        self.saved_scripts_listbox.pack(side=LEFT, fill=BOTH, expand=YES)

        listbox_scrollbar = ttk.Scrollbar(saved_scripts_frame, orient=VERTICAL, command=self.saved_scripts_listbox.yview)
        listbox_scrollbar.pack(side=RIGHT, fill=Y)
        self.saved_scripts_listbox.config(yscrollcommand=listbox_scrollbar.set)

        button_frame = ttk.Frame(parent)
        button_frame.pack(pady=(10, 0), fill=X)

        load_button = ttk.Button(button_frame, text="Load Selected Script", command=self.script_manager.load_saved_script, style='info.TButton')
        load_button.pack(side=LEFT, fill=X, expand=YES)

        delete_button = ttk.Button(button_frame, text="Delete Selected Script", command=self.script_manager.delete_saved_script, style='danger.TButton')
        delete_button.pack(side=RIGHT, fill=X, expand=YES, padx=(10, 0))

        self.populate_saved_scripts()

    def setup_status_bar(self):
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=W, font=('Helvetica', 10))
        self.status_bar.pack(side=BOTTOM, fill=X)

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("All files", "*.*")])
        if file_path:
            self.file_path_var.set(file_path)
            self.file_label.config(text=f"Selected file: {os.path.basename(file_path)}")
        else:
            self.file_path_var.set("")
            self.file_label.config(text="No file selected")

    def toggle_script_name_frame(self, *args):
        if self.mode_var.get() == "Automation":
            self.script_name_frame.pack(fill=X, pady=(0, 20))
        else:
            self.script_name_frame.pack_forget()

    def process_input(self):
        mode = self.mode_var.get()
        self.update_status("Processing...")
        if mode == "Automation":
            self.code_generator.generate_code(self.entry.get(), self.file_path_var.get())
        elif mode == "Q/A":
            self.qa_handler.qa_mode(self.entry.get(), self.file_path_var.get())
        self.update_status("Ready")
        
    def save_code(self):
        generated_code = self.get_generated_code()
        script_name = self.script_name_entry.get().strip()
        self.script_manager.save_code(script_name, generated_code)

    def get_generated_code(self):
        return self.log_output.get("1.0", tk.END).split("Response Received:")[0].strip()

    def update_status(self, message):
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def populate_saved_scripts(self):
        for script_file in os.listdir(os.path.dirname(__file__)):
            if script_file.endswith(".py") and script_file != os.path.basename(__file__):
                script_name = os.path.splitext(script_file)[0]
                self.saved_scripts_listbox.insert("", "end", text=script_name)

class App:
    def __init__(self):
        self.root = ttk.Window(themename="cosmo")
        self.api_handler = APIHandler()
        
        # Initialize instances before assigning them to attributes
        self.code_generator = CodeGenerator(self.api_handler.model, None, None)
        self.qa_handler = QAHandler(self.api_handler.model, None, None, None)  # Pass None for copy_button initially
        self.script_manager = ScriptManager(None, None)
        
        # Initialize GUI after initializing dependencies
        self.gui = GUI(self.root, self.api_handler, self.code_generator, self.qa_handler, self.script_manager)
        
        # Now that GUI is initialized, we can set the missing attributes
        self.code_generator.log_output = self.gui.log_output
        self.code_generator.progress_var = self.gui.progress_var
        self.qa_handler.log_output = self.gui.log_output
        self.qa_handler.progress_var = self.gui.progress_var
        self.qa_handler.copy_button = self.gui.copy_button  # Assign copy_button to QAHandler
        self.script_manager.log_output = self.gui.log_output
        self.script_manager.saved_scripts_listbox = self.gui.saved_scripts_listbox
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = App()
    app.run()
