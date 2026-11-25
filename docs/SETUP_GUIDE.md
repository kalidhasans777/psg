# MEDORA — Setup & Deployment Guide

## Option A: PostgreSQL + Full Stack via Docker Compose (Recommended for Production / PostgreSQL)
1. Copy `.env.example` to `.env` and set a strong `SECRET_KEY` (and optional `GEMINI_API_KEY`).
2. Start PostgreSQL, FastAPI backend, and React frontend:
   ```bash
   docker compose up --build
   ```
3. Open `http://localhost:5173`.

## Option B: Local Development (Windows / macOS / Linux)
### 1. Database Setup
- **PostgreSQL (Recommended)**: Create database `medora` and set `DATABASE_URL=postgresql+psycopg://medora:medora_password@localhost:5432/medora` in `backend/.env`.
- **Zero-Config Local Dev Fallback**: If PostgreSQL is not installed locally, `backend/app/config.py` defaults to `sqlite:///backend/medora_dev.db` so you can run and test immediately.

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate  |  Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
On startup, MEDORA initializes tables and seeds 5 synthetic patients (including `MED-2026-00125`), 4 doctors, 8 departments, sample PDFs, and medical knowledge documents.

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`.
