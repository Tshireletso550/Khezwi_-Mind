# Khwezi Mine Monitor

A Python and Streamlit prototype for monitoring mining worker safety, incidents, equipment, maintenance, and risk assessments.

## Project files

- `app.py` — Streamlit user interface.
- `core.py` — application logic, permissions, validation, and SQLite storage.
- `branding.py` — optional homepage image payload. The supplied placeholder leaves the homepage without its original photo.
- `requirements.txt` — Python packages required by the app.

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Start the dashboard:

   ```bash
   python -m streamlit run app.py
   ```

## Deploy with Streamlit Community Cloud

Upload the project files to a GitHub repository, then create an app at https://share.streamlit.io/ and select `app.py` as the main file.

## Important

This is an educational prototype. Use fictional/demo records only; do not upload passwords, secrets, or confidential worker information. Do not use the demo thresholds or outputs to make real mine-safety decisions without qualified review.

The original homepage photograph was not included in the files available for this package. `branding.py` therefore contains an empty image value, which allows the app to import but does not restore that photograph.
