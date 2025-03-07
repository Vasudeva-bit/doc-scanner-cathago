# Document Scanner Application

A Flask-based web app for uploading text documents, matching content, and managing credits with profile and admin features.

## Prerequisites

- **Python**: 3.7+ (recommended: 3.11)
- **Git**
- **Conda** (optional) or Python `venv`
- **Text Editor/IDE** (e.g., VS Code)

## Installation

### Option 1: Using Conda
1. Install Miniconda/Anaconda: [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/products/distribution).
2. Clone repo: `git clone https://github.com/yourusername/document-scanner.git && cd document-scanner`
3. Create env: `conda create -n docscanner python=3.11`
4. Activate: `conda activate docscanner` (Windows) or `source activate docscanner` (Mac/Linux)
5. Install deps: `pip install -r requirements.txt`
6. Initialize DB: `python app.py` (creates `database.db` with default admin: username `vasudeva`, password `vasudeva`)

### Option 2: Using Python `venv`
1. Clone repo: `git clone https://github.com/yourusername/document-scanner.git && cd document-scanner`
2. Create env: `python -m venv venv`
3. Activate: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Install deps: `pip install -r requirements.txt`
5. Initialize DB: `python app.py` (sets default admin: username `vasudeva`, password `vasudeva`)

### Additional Setup
- **Google Gemini API Key** (optional): For text comparison, get a key from [Google AI Studio](https://makersuite.google.com/) and replace `"YOUR_GOOGLE_API_KEY"` in `app.py`. Skip if not using Gemini.
- **Uploads Folder**: Created on first run; manually create with `mkdir uploads` if needed.

## Running Locally
1. Activate env (Conda or `venv`).
2. Start app: `python app.py` (runs on `http://127.0.0.1:5000`).
3. Access: Open browser, log in with username `vasudeva`, password `vasudeva`, or register new users.
4. Test: Upload `.txt` files via `/upload`, check matches at `/match/<doc_id>`, view `/profile` or `/admin`.

## Troubleshooting
- **Database Locked**: Close other app instances or use a single worker (see `Procfile`).
- **Missing Packages**: Clear cache with `pip cache purge` and retry `pip install -r requirements.txt`.
- **Port Conflict**: Change `port=5000` to `port=8000` in `app.py`.

## Deployment
Configured for Render (see `Procfile`).

## Contact
open a GitHub issue.
