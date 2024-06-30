# Task Automate

Task Automate is a Python-based GUI application that allows users to input natural language commands and automatically generates and executes Python scripts. 
It leverages the Gemini AI API to create scripts based on user input and handles library installations as needed.

## Features

- **Natural Language Input**: Enter commands in plain English, and the application generates the corresponding Python script.
- **Automatic Library Installation**: Identifies required libraries from the generated script and installs them if not already present.
- **Execution Logging**: Displays logs of requests sent to the AI model, responses received, and script execution details.
- **Modern GUI**: Built with Tkinter and ttk for a clean and modern interface.

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/DingxDon/task-automate.git
   cd task-automate

    Set Up Virtual Environment:

    bash

python -m venv env
source env/bin/activate  # On Windows use `env\Scripts\activate`

Install Required Packages:

bash

pip install -r requirements.txt

Set Up Gemini AI API Key:

    Obtain your API key from your Gemini AI account.
    Set it as an environment variable:

    bash

    export API_KEY='your_api_key'  # On Windows use `set API_KEY=your_api_key`

Run the Application:

bash

    python Task-Automate.py

Usage

    Launch the application.
    Enter a command such as "open Word" or "search for Python tutorials".
    Click the "Run" button.
    The application will generate a script, install any required libraries, and execute the script. Logs will be displayed in the application window.

Contributing

    Fork the repository.
    Create a new branch (git checkout -b feature/YourFeature).
    Commit your changes (git commit -am 'Add a feature').
    Push to the branch (git push origin feature/YourFeature).
    Open a pull request.

License

This project is licensed under the MIT License. See the LICENSE file for details.
Acknowledgments

    Gemini AI for the API.
    Tkinter for the GUI framework.
