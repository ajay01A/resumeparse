# Resume Parser

## First-time setup on Windows

From this folder, create and activate a virtual environment, install the Python
dependencies, install the spaCy English model, and start the Flask app:

```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

If PowerShell prevents virtual-environment activation, run the commands using
the environment's interpreter directly:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m spacy download en_core_web_sm
```

## Start the app

After setup, double-click `start_app.bat` whenever you want to use the app. It
starts the server and opens <http://127.0.0.1:5000> in your browser. Keep the
server window open while using the app; close that window to stop it.

The app stores candidate records in `resume_db.sqlite` and uploaded resumes in
`uploads` beside `app.py`.
