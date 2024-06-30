import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
import google.generativeai as genai
import os
import subprocess
import sys
import time
import importlib
from shutil import which

# Function to configure and install packages
def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError as e:
        log_output.insert(tk.END, f"Failed to install {package}. Error: {e}\n")
        log_output.see(tk.END)
        return False

# Function to check if a library is installed
def is_installed(package_name):
    spec = importlib.util.find_spec(package_name)
    return spec is not None

# Function to handle user input and generate code
def generate_code():
    user_input = entry.get()
    prompt = f"Write a Python script to {user_input}. Only give code and nothing else."

    # Log request sent to AI model
    log_output.insert(tk.END, f"Request Sent: {prompt}\n")
    log_output.see(tk.END)

    try:
        # Text Request and Response
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt, stream=True)

        generated_code = ""
        for chunk in response:
            if hasattr(chunk, 'text'):
                generated_code += chunk.text

        # Extract code from markdown
        if generated_code.startswith("```") and generated_code.endswith("```"):
            generated_code = generated_code.strip("```").strip()
            if generated_code.startswith("python"):
                generated_code = generated_code[6:]

        log_output.delete("1.0", tk.END)
        log_output.insert(tk.END, generated_code)

        # Log response from AI model
        log_output.insert(tk.END, "Response Received:\n")
        log_output.insert(tk.END, generated_code + "\n")
        log_output.see(tk.END)

        # Identify and install required libraries
        libraries = identify_libraries(generated_code)
        for library in libraries:
            if not is_installed(library):
                log_output.insert(tk.END, f"Library '{library}' is not installed. Attempting to install...\n")
                log_output.see(tk.END)
                if install_package(library):
                    log_output.insert(tk.END, f"Successfully installed {library}.\n")
                    log_output.see(tk.END)
                else:
                    log_output.insert(tk.END, f"Failed to install {library}. Skipping script execution.\n")
                    log_output.see(tk.END)
                    return

        # Execute the generated code
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

    except ValueError as e:
        log_output.insert(tk.END, f"ValueError: {e}\n")
        log_output.see(tk.END)

    except Exception as e:
        log_output.insert(tk.END, f"An error occurred: {e}\n")
        log_output.see(tk.END)

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

# GUI setup
root = tk.Tk()
root.title("Task Automate")
root.geometry("800x600")

# Configure OpenAI API
genai.configure(api_key=os.environ["API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# Style configuration for a more modern look
style = ttk.Style()
style.theme_use('clam')

# Custom colors for a more modern appearance
root.configure(bg='#f0f0f0')
style.configure('TLabel', background='#f0f0f0')
style.configure('TButton', background='#4CAF50', foreground='#ffffff')

# User input entry
label = ttk.Label(root, text="Enter your command:", font=('Arial', 14))
label.pack(pady=20)

entry = ttk.Entry(root, width=70, font=('Arial', 12))
entry.pack()

# Generate button
generate_button = ttk.Button(root, text="Run", command=generate_code, width=20)
generate_button.pack(pady=20)

# Log output text area
log_output = scrolledtext.ScrolledText(root, height=20, width=100, wrap=tk.WORD, font=('Arial', 12))
log_output.pack(pady=20)

# Start GUI main loop
root.mainloop()