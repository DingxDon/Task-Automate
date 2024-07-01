import tkinter as tk
from tkinter import scrolledtext, Listbox, messagebox, StringVar
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import google.generativeai as genai
import os
import subprocess
import sys
import time
import importlib
from shutil import which
import threading

# Function to configure and install packages
def install_package(package, progress_var):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        progress_var.set(100)
        return True
    except subprocess.CalledProcessError as e:
        log_output.insert(tk.END, f"Failed to install {package}. Error: {e}\n")
        log_output.see(tk.END)
        progress_var.set(0)
        return False

# Function to check if a library is installed
def is_installed(package_name):
    spec = importlib.util.find_spec(package_name)
    return spec is not None

# Function to handle user input and generate code
def generate_code():
    user_input = entry.get()
    prompt = f"Write a Python script/program to {user_input}. Only give code and nothing else."

    log_output.insert(tk.END, f"Request Sent: {prompt}\n")
    log_output.see(tk.END)

    progress_var.set(0)
    progress_bar.pack(fill=X, pady=(10, 0))

    def generate_code_thread():
        try:
            chat = model.start_chat(history=[])
            response = chat.send_message(prompt, stream=True)

            generated_code = ""
            for chunk in response:
                if hasattr(chunk, 'text'):
                    generated_code += chunk.text
                progress_var.set(min(progress_var.get() + 10, 90))

            if generated_code.startswith("```") and generated_code.endswith("```"):
                generated_code = generated_code.strip("```").strip()
                if generated_code.startswith("python"):
                    generated_code = generated_code[6:]

            log_output.delete("1.0", tk.END)
            log_output.insert(tk.END, generated_code)

            log_output.insert(tk.END, "Response Received:\n")
            log_output.insert(tk.END, generated_code + "\n")
            log_output.see(tk.END)

            libraries = identify_libraries(generated_code)
            for library in libraries:
                if not is_installed(library):
                    log_output.insert(tk.END, f"Library '{library}' is not installed. Attempting to install...\n")
                    log_output.see(tk.END)
                    if install_package(library, progress_var):
                        log_output.insert(tk.END, f"Successfully installed {library}.\n")
                        log_output.see(tk.END)
                    else:
                        log_output.insert(tk.END, f"Failed to install {library}. Skipping script execution.\n")
                        log_output.see(tk.END)
                        progress_bar.pack_forget()
                        return

            start_time = time.time()
            try:
                exec(generated_code)
            except Exception as e:
                log_output.insert(tk.END, f"An error occurred during script execution: {e}\n")
                log_output.see(tk.END)

            end_time = time.time()
            execution_time = end_time - start_time
            log_output.insert(tk.END, f"Execution time: {execution_time:.2f} seconds\n")
            log_output.insert(tk.END, "_" * 80 + "\n")
            log_output.see(tk.END)

        except Exception as e:
            log_output.insert(tk.END, f"An error occurred: {e}\n")
            log_output.see(tk.END)

        progress_var.set(100)
        root.after(1000, progress_bar.pack_forget)

    threading.Thread(target=generate_code_thread).start()

# Function to parse and identify required libraries from the generated code
def identify_libraries(code):
    libraries = []
    for line in code.splitlines():
        if line.startswith("import ") or line.startswith("from "):
            parts = line.split()
            if parts[0] == "import":
                libraries.append(parts[1].split('.')[0])
            elif parts[0] == "from":
                libraries.append(parts[1].split('.')[0])
    return libraries

# Function to save the generated code to a file with a given name
def save_code():
    generated_code = get_generated_code()

    if not generated_code.strip():
        messagebox.showerror("Error", "No code generated to save.")
        return

    script_name = script_name_entry.get().strip()

    if not script_name:
        messagebox.showerror("Error", "Please enter a script name.")
        return

    script_file = os.path.join(os.path.dirname(__file__), f"{script_name}.py")

    progress_var.set(0)
    progress_bar.pack(fill=X, pady=(10, 0))

    def save_code_thread():
        with open(script_file, "w") as file:
            file.write(generated_code)
        
        saved_scripts_listbox.insert("", "end", text=script_name)

        log_output.insert(tk.END, f"Script saved as '{script_file}'\n")
        log_output.see(tk.END)

        progress_var.set(100)
        root.after(1000, progress_bar.pack_forget)

    threading.Thread(target=save_code_thread).start()

def get_generated_code():
    return log_output.get("1.0", tk.END).split("Response Received:")[0].strip()

# Function to load and execute a selected saved script
def load_saved_script():
    selected_item = saved_scripts_listbox.selection()
    if selected_item:
        script_name = saved_scripts_listbox.item(selected_item)['text']

        try:
            with open(os.path.join(os.path.dirname(__file__), f"{script_name}.py"), "r") as file:
                script_code = file.read()

            log_output.delete("1.0", tk.END)
            log_output.insert(tk.END, script_code)
            log_output.insert(tk.END, f"Loaded saved script '{script_name}.py':\n")
            log_output.see(tk.END)

            exec(script_code)
        except FileNotFoundError:
            log_output.insert(tk.END, f"Error: '{script_name}.py' not found.\n")
            log_output.see(tk.END)
        except Exception as e:
            log_output.insert(tk.END, f"An error occurred while loading or executing '{script_name}.py': {e}\n")
            log_output.see(tk.END)
    else:
        messagebox.showerror("Error", "Please select a script to load.")

# Function to delete selected saved script
def delete_saved_script():
    selected_item = saved_scripts_listbox.selection()
    if selected_item:
        script_name = saved_scripts_listbox.item(selected_item)['text']
        script_file = os.path.join(os.path.dirname(__file__), f"{script_name}.py")
        
        if os.path.exists(script_file):
            os.remove(script_file)
            saved_scripts_listbox.delete(selected_item)
            log_output.insert(tk.END, f"Deleted script: {script_name}.py\n")
            log_output.see(tk.END)
        else:
            messagebox.showerror("Error", f"Script file not found: {script_name}.py")
    else:
        messagebox.showerror("Error", "Please select a script to delete.")

# New function to handle Q/A mode
def qa_mode():
    user_input = entry.get()
    
    log_output.insert(tk.END, f"Question: {user_input}\n")
    log_output.see(tk.END)

    progress_var.set(0)
    progress_bar.pack(fill=X, pady=(10, 0))

    def qa_mode_thread():
        try:
            chat = model.start_chat(history=[])
            response = chat.send_message(user_input, stream=True)

            answer = ""
            for chunk in response:
                if hasattr(chunk, 'text'):
                    answer += chunk.text
                progress_var.set(min(progress_var.get() + 10, 90))

            log_output.insert(tk.END, f"Answer: {answer}\n")
            log_output.insert(tk.END, "_" * 80 + "\n")
            log_output.see(tk.END)

        except Exception as e:
            log_output.insert(tk.END, f"An error occurred: {e}\n")
            log_output.see(tk.END)

        progress_var.set(100)
        root.after(1000, progress_bar.pack_forget)

    threading.Thread(target=qa_mode_thread).start()

# Modified function to handle user input based on selected mode
def process_input():
    mode = mode_var.get()
    if mode == "Automation":
        generate_code()
    elif mode == "Q/A":
        qa_mode()

# GUI setup
root = ttk.Window(themename="cosmo")
root.title("Task Automate")
root.geometry("1200x800")

# Configure OpenAI API
genai.configure(api_key=os.environ["API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# Create main frame
main_frame = ttk.Frame(root, padding="20 20 20 0")
main_frame.pack(fill=BOTH, expand=YES)

# Create left and right panes
left_pane = ttk.Frame(main_frame, padding="0 0 10 0")
left_pane.pack(side=LEFT, fill=BOTH, expand=YES)

right_pane = ttk.Frame(main_frame, padding="10 0 0 0")
right_pane.pack(side=RIGHT, fill=BOTH, expand=YES)

# Input section (left pane)
input_frame = ttk.Frame(left_pane)
input_frame.pack(fill=X, pady=(0, 10))

label = ttk.Label(input_frame, text="Enter your command/question:", font=('Helvetica', 12, 'bold'))
label.pack(anchor=W, pady=(0, 5))

entry = ttk.Entry(input_frame, width=50, font=('Helvetica', 12))
entry.pack(fill=X, expand=YES)

mode_frame = ttk.Frame(left_pane)
mode_frame.pack(fill=X, pady=(0, 10))

mode_var = StringVar(root)
mode_var.set("Automation")
mode_label = ttk.Label(mode_frame, text="Mode:", font=('Helvetica', 12))
mode_label.pack(side=LEFT, padx=(0, 10))
mode_dropdown = ttk.Combobox(mode_frame, textvariable=mode_var, values=["Automation", "Q/A"], state="readonly", width=15, font=('Helvetica', 12))
mode_dropdown.pack(side=LEFT)

process_button = ttk.Button(left_pane, text="Process", command=process_input, style='success.TButton')
process_button.pack(fill=X, pady=(0, 20))

# Script name entry (only visible in Automation mode)
script_name_frame = ttk.Frame(left_pane)

script_name_label = ttk.Label(script_name_frame, text="Enter script name:", font=('Helvetica', 12))
script_name_label.pack(anchor=W, pady=(0, 5))

script_name_entry = ttk.Entry(script_name_frame, font=('Helvetica', 12))
script_name_entry.pack(fill=X, expand=YES, side=LEFT)

save_button = ttk.Button(script_name_frame, text="Save", command=save_code, style='info.TButton', width=10)
save_button.pack(side=RIGHT, padx=(10, 0))

# Function to toggle script name frame visibility
def toggle_script_name_frame(*args):
    if mode_var.get() == "Automation":
        script_name_frame.pack(fill=X, pady=(0, 20))
    else:
        script_name_frame.pack_forget()

mode_var.trace('w', toggle_script_name_frame)

# Log output
log_frame = ttk.LabelFrame(left_pane, text="Output", padding=10)
log_frame.pack(fill=BOTH, expand=YES)

log_output = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=('Consolas', 11))
log_output.pack(fill=BOTH, expand=YES)

# Progress bar
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(left_pane, variable=progress_var, maximum=100)

# Saved scripts section (right pane)
saved_scripts_frame = ttk.LabelFrame(right_pane, text="Saved Scripts", padding=10)
saved_scripts_frame.pack(fill=BOTH, expand=YES)

saved_scripts_listbox = ttk.Treeview(saved_scripts_frame, selectmode="browse", show="tree", style='info.Treeview')
saved_scripts_listbox.pack(side=LEFT, fill=BOTH, expand=YES)

listbox_scrollbar = ttk.Scrollbar(saved_scripts_frame, orient=VERTICAL, command=saved_scripts_listbox.yview)
listbox_scrollbar.pack(side=RIGHT, fill=Y)
saved_scripts_listbox.config(yscrollcommand=listbox_scrollbar.set)

button_frame = ttk.Frame(right_pane)
button_frame.pack(pady=(10, 0), fill=X)

load_button = ttk.Button(button_frame, text="Load Selected Script", command=load_saved_script, style='info.TButton')
load_button.pack(side=LEFT, fill=X, expand=YES)

delete_button = ttk.Button(button_frame, text="Delete Selected Script", command=delete_saved_script, style='danger.TButton')
delete_button.pack(side=RIGHT, fill=X, expand=YES, padx=(10, 0))

# Populate initial list of saved scripts
for script_file in os.listdir(os.path.dirname(__file__)):
    if script_file.endswith(".py") and script_file != os.path.basename(__file__):
        script_name = os.path.splitext(script_file)[0]
        saved_scripts_listbox.insert("", "end", text=script_name)

# Status bar
status_bar = ttk.Label(root, text="Ready", relief=tk.SUNKEN, anchor=W, font=('Helvetica', 10))
status_bar.pack(side=BOTTOM, fill=X)

# Function to update status bar
def update_status(message):
    status_bar.config(text=message)
    root.update_idletasks()

# Modify process_input function to update status
def process_input():
    mode = mode_var.get()
    update_status("Processing...")
    if mode == "Automation":
        generate_code()
    elif mode == "Q/A":
        qa_mode()
    update_status("Ready")

# Start GUI main loop
root.mainloop()