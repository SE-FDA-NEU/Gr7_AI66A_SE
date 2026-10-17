# Installation & Setup Guide

This document provides step-by-step instructions to install, configure, and run the **MiniLMS** application on a fresh machine. This guide includes environment setup, SQLite database initialization, and instructions to verify the **Walking Skeleton** route.

---

## 1. Prerequisites

Ensure your system meets the following minimum requirements before proceeding:

* **Git:** `v2.30+` (Verify with: `git --version`)
* **Python:** `v3.11+` (Verify with: `python --version` or `python3 --version`)
* **Web Browser:** Latest version of Google Chrome, Mozilla Firefox, or Microsoft Edge.

---

## 2. Copy-Paste Installation Commands

Open your Terminal (macOS/Linux) or PowerShell/CMD (Windows) and execute the following commands in order:

### Step 2.1: Clone the Repository & Navigate to Project Directory
```bash
git clone https://github.com/SE-FDA-NEU/Gr7_AI66A_SE.git
cd Gr7_AI66A_SE
```

### Step 2.2: Create and Activate Virtual Environment

- **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

- **Windows (PowerShell / CMD):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\activate
  ```

### Step 2.3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Configuration

The system uses an `.env` file to manage environment-specific variables without committing secrets to Git.

- **macOS / Linux:**
  ```bash
  cp .env.example .env
  ```

- **Windows:**
  ```cmd
  copy .env.example .env
  ```

> **Note:** Set `SECRET_KEY` in `.env` to a private random value before running
> the application. Generate one with
> `python -c "import secrets; print(secrets.token_hex(32))"`. Keep it out of Git.
> `DATABASE_PATH` defaults to `data/minilms.db`; the Flask development server
> uses port 5000.

---

## 4. Database Creation & Seeding

Initialize the SQLite database schema and seed sample data using a single command:

```bash
python src/init_db.py
```
*(On macOS if `.venv` is not activated, run: `python3 src/init_db.py`)*

**Expected Terminal Output:**
```text
[INFO] Database: data/minilms.db
[INFO] Created 6 tables: user, quiz, question, choice, attempt, answer
[INFO] Seeded user: 7
[INFO] Seeded quiz: 15
[INFO] Seeded question: 15
[INFO] Seeded choice: 60
[DONE] 97 rows in total
```

### Test accounts

The checked-in seed data contains demo-only accounts for local testing:

| Role | Email | Password |
| --- | --- | --- |
| Lecturer | `ngan.lecturer@example.edu` | `MiniLMS2026!` |
| Student | `duc.student@example.edu` | `MiniLMS2026!` |

These credentials are only for the local sample database. Do not reuse this
password for a real account.

---

## 5. Verification: How to Know It Worked (Walking Skeleton)

### Step 5.1: Start the Web Server
```bash
python src/app.py
```

The server will run locally at: `http://localhost:5000`

### Step 5.2: Test the Walking Skeleton Route
Open your web browser and navigate to: `http://127.0.0.1:5000/login`. Sign in
with the student test account above; successful login redirects to the student
dashboard.

- **Verification Criteria:**
  - The webpage displays a table containing **at least 12 quizzes** fetched directly from `data/minilms.db`.
  - Each row clearly displays: *Quiz ID, Title, Lecturer Name, Duration (mins), Closes at*.
  - Data is dynamically queried via SQL (not hardcoded arrays).

---

## 6. Troubleshooting

### Issue 1: `ModuleNotFoundError: No module named 'flask'`
- **Cause:** The virtual environment (`.venv`) is not activated, or `pip install` was not executed.
- **Resolution:**
  1. Re-activate the virtual environment (refer to Step 2.2).
  2. Ensure `(.venv)` appears in your terminal prompt, then rerun `pip install -r requirements.txt`.

### Issue 2: `Address already in use` or `Port 5000 is in use`
- **Cause:** Port 5000 is occupied by another service.
- **Resolution:**
  1. Open `.env` and change the port configuration to `PORT=5001`.
  2. Restart the application server (`python src/app.py`) and visit `127.0.0.1:5000/student/dashboard`.

### Issue 3: `sqlite3.OperationalError: no such table: quizzes`
- **Cause:** The database initialization script has not been executed.
- **Resolution:** Rerun `python src/init_db.py` (or `python3 src/init_db.py`) from Step 4.

---

## 7. Verification Record

This setup guide has been independently tested on a clean machine not owned by the primary author:

- **Tested by:** `@khangtrannf` (Team Member 7)
- **Tested on:** Clean Laptop (macOS / Clean Python Environment)
- **Date of test:** 03/10/2026
- **Total time taken:** 8 minutes 30 seconds.