# Smart Spreadsheet for Job Search

This repository houses a PyQt6 application ("Smart Spreadsheet") designed to help you track and manage your job search. It allows you to:

* Create, load, and save job-tracking spreadsheets (CSV, Excel).
* Apply various transformations and automated data-enrichment steps to your rows (e.g., web scraping, LinkedIn enrichment, and email follow-ups).
* Compose and keep track of emails directly from within the spreadsheet.

---

## Table of Contents

1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation (Conda)](#installation-conda)
4. [Usage Instructions](#usage-instructions)
5. [How to Use for Job Search](#how-to-use-for-job-search)
6. [Project Structure](#project-structure)
7. [Troubleshooting](#troubleshooting)
8. [License](#license)

---

## Features

* Open or create new spreadsheet-like files (CSV/XLS/XLSX).
* Automatically scrape data from job postings or company websites.
* Generate and manage follow-up emails.
* Store multiple job entries, hiring manager info, and relevant notes.
* Easily rename columns, add columns, or remove columns.
* Quickly duplicate a row to track a new job or new hiring manager for the same company.
* Auto-save changes on data editing.
* Automatically load the most recently used file on application start.
* Mark columns as input or output columns, reflecting transformations applied in real-time.

---

## Requirements

You will find the required Python packages listed in [smart_spreadsheet/requirements.txt](https://chatgpt.com/c/smart_spreadsheet/requirements.txt). Key dependencies:

* PyQt6
* pandas
* openai / anthropic (for AI-based transformations)
* playwright, playwright-stealth (stealth web scraping)
* google-api-python-client (some optional integrations for Google services)
* cryptography
* python-dotenv

---

## Installation (Conda)

Follow these steps to configure a Conda environment and install all dependencies:

1. Make sure you have Conda or Miniconda/Anaconda installed.
2. Create and activate a new environment:
   ```bash
   conda create --name smart_spreadsheet python=3.10
   conda activate smart_spreadsheet
   ```
3. Once your environment is active, install dependencies with pip (within the Conda environment):
   ```bash
   pip install -r smart_spreadsheet/requirements.txt
   ```
4. (Optional) If you plan to use PyInstaller to package the application, ensure you have it installed (it is also pinned in requirements.txt).

---

## Usage Instructions

1. Activate your Conda environment:
   ```bash
   conda activate smart_spreadsheet
   ```
2. Run the application:
   ```bash
   python smart_spreadsheet/app.py
   ```
3. The PyQt6-based GUI will launch. From there, you can:
   * Create a new spreadsheet by clicking "Create New."
   * Load a spreadsheet from CSV/XLS/XLSX by clicking "Load File."
   * Once a file is open/created, you can begin editing rows, columns, and exploring transformations.

### Important Notes

* By default, the application auto-saves whenever you make edits to the data.
* The last used file location will be remembered (in a small file named lastfile.txt).
* You can open the "Preferences" dialog to configure email settings (sender information) so that you can compose and send emails directly from the interface.

---

## How to Use for Job Search

1. **Create or Load a Spreadsheet**

   Start by creating a new CSV or loading an existing file where you track companies, jobs, hiring managers, etc.
2. **Populate Basic Columns**

   Columns like "CompanyName," "JobURL," "Job_Description," "Hiring_Manager_LinkedIn," and "Email" will help drive the built-in transformations.
3. **Discover & Apply Transformations**

   * In the UI, you’ll see a “Transformation” dropdown. Select a transformation (e.g., “Stealth Browser Web Scraper”) and specify input and output columns.
   * Transformations can automate tasks like scraping the job website, analyzing the job description, or generating personalized emails.
4. **Use the Built-in Email Composition**

   * If you have the “Email” column set for a row, you can right-click on a follow-up column (e.g., “FollowUp_Email_1”) to open a compose dialog.
   * The system inserts templates or AI-generated text for you to send to the hiring manager.
5. **Track Communication & Responses**

   * The tool can detect incoming replies from your email account (through the integrated email service, if configured).
   * Use the built-in context menus to log new follow-ups, set statuses, or keep notes.
6. **Add or Rename Columns**

   * Right-click on the table header to dynamically add, rename, or remove columns.
   * This allows you to adapt the spreadsheet for your specific job search strategy.
7. **Save & Reuse**

   * Your data is saved automatically. As you close and reopen the application, it loads your last used file so you can pick up right where you left off.

---

## Project Structure

Below is a broad outline of the key files/folders:

* `smart_spreadsheet/app.py`
  * Launches the main PyQt6 GUI and sets up the MainWindow.
* `smart_spreadsheet/ui/main_window.py`
  * Contains the MainWindow class with the spreadsheet view, transformations, and all UI logic.
* `smart_spreadsheet/ui/`
  * Various PyQt UI components (dialogs, delegates, data models).
* `smart_spreadsheet/services/`
  * Logic for file I/O, email handling, settings management.
* `smart_spreadsheet/transformations/`
  * Implementation of specific transformations (e.g., scraping, generating email content, etc.).
* `smart_spreadsheet/requirements.txt`
  * Lists all required Python packages.

---

## Troubleshooting

1. **Missing dependencies**
   * Ensure you are in the correct Conda environment. If you see errors about missing modules, run:
     ```bash
     pip install -r smart_spreadsheet/requirements.txt
     ```
2. **Playwright Setup**
   * Some scraping transformations require Playwright. If you face issues, run:
     ```bash
     playwright install
     ```
   * Then retry.
3. **Email Sending Errors**
   * Check that your email credentials are configured correctly in the Preferences dialog.
   * Make sure any required environment variables (if using .env) are set properly.
4. **GUI Not Launching**
   * Validate your Python version and environment. PyQt6 requires Python 3.7+ (ideally 3.10 here).

---

## License

This project is distributed under MIT Licence.

Feel free to fork and adapt to your job search workflow!

---

Happy job hunting, and best of luck! If you have questions or feature requests, feel free to open an issue or pull request.
