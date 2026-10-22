import os
import re
import sqlite3
import pdfplumber
import docx
import spacy
from spacy.matcher import PhraseMatcher
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "super_secret_ats_key"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DB_NAME = os.path.join(BASE_DIR, "resume_db.sqlite")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 1. SQLite Database Connection (No external server required!)
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the candidates table automatically on startup."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            name TEXT,
            email TEXT,
            phone TEXT,
            skills TEXT,
            education TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    conn.close()

init_db()

# 2. Load spaCy Model & Setup Skills Matcher
try:
    nlp = spacy.load("en_core_web_sm")
except OSError as exc:
    raise RuntimeError(
        "The spaCy model 'en_core_web_sm' is missing. Install it with "
        "'python -m spacy download en_core_web_sm'."
    ) from exc
matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

SKILL_LIST = [
    "Python", "Java", "C++", "JavaScript", "TypeScript", "SQL", "PostgreSQL",
    "MongoDB", "MySQL", "Flask", "Django", "FastAPI", "React", "Node.js",
    "Machine Learning", "Deep Learning", "NLP", "spaCy", "TensorFlow", "PyTorch",
    "AWS", "Docker", "Kubernetes", "Git", "HTML", "CSS", "Pandas", "Data Analysis"
]
patterns = [nlp.make_doc(skill) for skill in SKILL_LIST]
matcher.add("SKILLS", patterns)

# 3. File Text Extraction (PDF & DOCX)
def extract_text_from_file(filepath):
    text = ""
    if filepath.lower().endswith(".pdf"):
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    elif filepath.lower().endswith(".docx"):
        doc = docx.Document(filepath)
        for para in doc.paragraphs:
            text += para.text + "\n"
    return text.strip()

# 4. NLP Information Extraction Pipeline
def parse_resume(text):
    doc = nlp(text)

    # A. Extract Name
    name = "Unknown Candidate"
    for ent in doc.ents:
        if ent.label_ == "PERSON" and len(ent.text.split()) >= 2:
            name = ent.text.strip()
            break

    # B. Extract Email
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    email = email_match.group(0) if email_match else "Not Found"

    # C. Extract Phone Number
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    phone = phone_match.group(0) if phone_match else "Not Found"

    # D. Extract Skills
    matches = matcher(doc)
    found_skills = set()
    for match_id, start, end in matches:
        span = doc[start:end]
        for s in SKILL_LIST:
            if s.lower() == span.text.lower():
                found_skills.add(s)
    skills = sorted(list(found_skills))

    # E. Extract Education
    edu_keywords = [
        r'\bB\.?Tech\b', r'\bM\.?Tech\b', r'\bB\.?E\b', r'\bB\.?Sc\b',
        r'\bM\.?Sc\b', r'\bBCA\b', r'\bMCA\b', r'\bMBA\b', r'\bBachelor\b', r'\bMaster\b', r'\bPh\.?D\b'
    ]
    found_degrees = set()
    for kw in edu_keywords:
        for m in re.finditer(kw, text, re.IGNORECASE):
            found_degrees.add(m.group(0).upper())
    education = ", ".join(sorted(found_degrees)) if found_degrees else "Not Specified"

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "skills": skills,
        "education": education
    }

# 5. Flask Routes
@app.route("/", methods=["GET"])
def index():
    search_query = request.args.get("search", "").strip()
    conn = get_db_connection()
    cur = conn.cursor()

    if search_query:
        like_val = f"%{search_query}%"
        cur.execute('''
            SELECT * FROM candidates
            WHERE skills LIKE ? OR name LIKE ? OR education LIKE ?
            ORDER BY uploaded_at DESC;
        ''', (like_val, like_val, like_val))
    else:
        cur.execute("SELECT * FROM candidates ORDER BY uploaded_at DESC;")

    rows = cur.fetchall()
    conn.close()

    # Format skills string back into a Python list for the HTML template
    candidates = []
    for row in rows:
        c = dict(row)
        c["skills"] = [s.strip() for s in c["skills"].split(",") if s.strip()]
        candidates.append(c)

    return render_template("index.html", candidates=candidates, search_query=search_query)

@app.route("/upload", methods=["POST"])
def upload_resume():
    if "resume" not in request.files:
        flash("No file selected!")
        return redirect(url_for("index"))

    files = request.files.getlist("resume")
    conn = get_db_connection()
    cur = conn.cursor()

    parsed_count = 0
    for file in files:
        filename = secure_filename(file.filename or "")
        if file and filename.lower().endswith((".pdf", ".docx")):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            raw_text = extract_text_from_file(filepath)
            parsed_data = parse_resume(raw_text)

            skills_str = ", ".join(parsed_data["skills"])

            cur.execute('''
                INSERT INTO candidates (filename, name, email, phone, skills, education)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                filename,
                parsed_data["name"],
                parsed_data["email"],
                parsed_data["phone"],
                skills_str,
                parsed_data["education"]
            ))
            parsed_count += 1

    conn.commit()
    conn.close()

    flash(f"Successfully parsed and saved {parsed_count} resume(s)!")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)