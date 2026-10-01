# AI Career Guidance and Resume Analyzer

A Flask-based web app for generating a 30-day career plan and analyzing a resume against a target role.

## Features

- AI-powered career guidance using Gemini when configured
- Resume upload support for PDF and DOCX files
- ATS compatibility score with skill and keyword analysis
- Interview-preparation generator by role and skill set
- Career readiness score and exportable roadmap
- Role-based learning resources and job portal recommendations
- Clean orange-and-white responsive interface

## Setup

1. Create and activate a virtual environment.
2. Install Python dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
3. Add your Gemini key to a `.env` file:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
4. Start the app:
   ```bash
   python app.py
   ```
5. Open `http://127.0.0.1:5000` in the browser.

## API Endpoints

- `POST /api/career-plan`
- `POST /api/analyze-resume`

## Notes

- The app falls back to heuristic recommendations when the AI service is unavailable or misconfigured.
- The frontend never receives the Gemini API key.
