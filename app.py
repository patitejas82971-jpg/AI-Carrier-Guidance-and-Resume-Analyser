import json
import os
import re
from typing import Any, Dict, List, Tuple

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from PyPDF2 import PdfReader
from docx import Document

from backend.config import Config
from backend.services.gemini_service import GeminiService

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_UPLOAD_SIZE

ROLE_DATA = []
LEARNING_RESOURCES = []
JOB_PORTALS = []
CERTIFICATIONS = []


def load_json_file(filename: str) -> List[Dict[str, Any]]:
    path = Config.DATA_DIR / filename
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, list) else []


ROLE_DATA = load_json_file("career_roles.json")
LEARNING_RESOURCES = load_json_file("learning_resources.json")
JOB_PORTALS = load_json_file("job_portals.json")
CERTIFICATIONS = load_json_file("certifications.json")


def sanitize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("\x00", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def get_role_metadata(target_role: str) -> Dict[str, Any]:
    normalized = target_role.lower().strip()
    for item in ROLE_DATA:
        if item.get("role", "").lower() == normalized:
            skills = item.get("required_skills") or item.get("skills") or []
            return {
                **item,
                "skills": skills,
                "required_skills": skills,
            }
    return {
        "role": target_role,
        "skills": [],
        "required_skills": [],
        "certifications": [],
        "recommended_projects": [],
        "learning_path": []
    }


def extract_resume_text(uploaded_file) -> str:
    if uploaded_file is None:
        raise ValueError("Resume file is required.")

    filename = secure_filename(uploaded_file.filename or "resume")
    extension = os.path.splitext(filename)[1].lower()
    if extension not in Config.ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported resume format. Please upload a PDF or DOCX file.")

    content = uploaded_file.read()
    if not content or len(content) > Config.MAX_UPLOAD_SIZE:
        raise ValueError("Resume file is too large or empty.")

    text_parts: List[str] = []
    if extension == ".pdf":
        pdf_reader = PdfReader(__import__('io').BytesIO(content))
        for page in pdf_reader.pages:
            text_parts.append(page.extract_text() or "")
    elif extension == ".docx":
        document = Document(__import__('io').BytesIO(content))
        for paragraph in document.paragraphs:
            text_parts.append(paragraph.text)

    resume_text = "\n".join(text_parts)
    return sanitize_text(resume_text)


def normalize_list(values: Any) -> List[str]:
    if not values:
        return []
    if isinstance(values, str):
        return [values]
    return [str(item).strip() for item in values if str(item).strip()]


def safe_isin(value: str, item_list: List[str]) -> bool:
    if not value:
        return False
    target = value.strip().lower()
    return any(item.strip().lower() == target for item in item_list)


def build_career_plan(name: str, target_role: str, skills: List[str]) -> Dict[str, Any]:
    role_details = get_role_metadata(target_role)
    known_skills = [skill.strip() for skill in skills if skill.strip()]
    target_skills = role_details.get("required_skills") or role_details.get("skills", [])
    missing_skills = [skill for skill in target_skills if not any(s.lower() == skill.lower() for s in known_skills)]

    readiness_score = min(100, max(45, 55 + (len(known_skills) * 5) - (len(missing_skills) * 3)))
    plan = {
        "summary": f"{name} is preparing for a {target_role} role with a strong foundation in {', '.join(known_skills) if known_skills else 'core technical skills'}. The plan emphasizes role-specific learning and practical skill building.",
        "current_skills": known_skills or ["Foundational skills"],
        "skills_to_learn": missing_skills[:8] or ["Role-specific fundamentals", "Portfolio projects", "Interview readiness"],
        "readiness_score": readiness_score,
        "thirty_day_plan": [],
        "resources": []
    }

    week_map = [
        {"label": "Foundation", "start": 1, "end": 7},
        {"label": "Core Skills", "start": 8, "end": 15},
        {"label": "Projects and Practical Skills", "start": 16, "end": 23},
        {"label": "Interview and Job Preparation", "start": 24, "end": 30},
    ]

    topics = [
        ("Python Fundamentals", "Strengthen the basics of Python and problem solving.", ["Variables", "Data types", "Loops", "Functions", "Conditionals"], "2-3 hours", "Solve 5 Python coding problems."),
        ("SQL Essentials", "Build confidence in querying, filtering, and joins.", ["SELECT statements", "WHERE clauses", "GROUP BY", "JOINs", "CASE expressions"], "2-3 hours", "Write 3 SQL practice queries."),
        ("Analytics and Visualization", "Practice turning data into actionable insights.", ["Charts", "Dashboard structure", "Data cleaning", "Storytelling", "Insights"], "3 hours", "Create one dashboard summary."),
        ("Project Work", "Apply skills on a realistic mini project.", ["Data collection", "Cleaning", "Modeling", "Reporting", "Presentation"], "4 hours", "Complete a mini capstone project."),
        ("Interview Preparation", "Prepare for role-specific interviews and case questions.", ["Resume review", "Behavioral questions", "Technical explanation", "Portfolio walkthrough"], "2-3 hours", "Practice one mock interview."),
    ]

    for idx, (topic, objective, tasks, hours, practice) in enumerate(topics):
        for day in range(1, 31):
            if day in range(1, 8):
                section = 0
            elif day in range(8, 16):
                section = 1
            elif day in range(16, 24):
                section = 2
            else:
                section = 3
            if idx == section:
                plan["thirty_day_plan"].append({
                    "day": day,
                    "topic": topic,
                    "objective": objective,
                    "tasks": tasks,
                    "estimated_hours": hours,
                    "practice_activity": practice,
                    "resources": ["Python docs: official documentation", "Kaggle: practical exercises", "Coursera: beginner learning modules"]
                })
                break

    resources_for_role = []
    for item in LEARNING_RESOURCES:
        if item.get("topic") in set(target_skills + ["Python", "SQL", "Data Visualization", "Machine Learning", "Interview Preparation"]):
            resources_for_role.append(item)

    plan["resources"] = resources_for_role[:6]
    return plan


def generate_fallback_career_plan(name: str, target_role: str, skills: List[str]) -> Dict[str, Any]:
    return build_career_plan(name, target_role, skills)


def generate_fallback_resume_analysis(target_role: str, resume_text: str) -> Dict[str, Any]:
    role_details = get_role_metadata(target_role)
    role_skills = role_details.get("required_skills") or role_details.get("skills", [])
    detected = []
    lower_text = resume_text.lower()
    for skill in role_skills:
        if skill.lower() in lower_text:
            detected.append(skill)
    missing = [skill for skill in role_skills if skill not in detected][:8]
    score = 78
    if not detected:
        score = 62
    elif len(missing) <= 3:
        score = 82
    elif len(missing) <= 5:
        score = 74

    certification_suggestions = role_details.get("certifications", []) or [
        "Google Data Analytics Professional Certificate",
        "Microsoft Certified: Power BI Data Analyst Associate"
    ]
    projects = role_details.get("recommended_projects", []) or [
        "Customer churn prediction dashboard",
        "Sales performance analysis project",
        "Project portfolio case study"
    ]
    portals = []
    for portal in JOB_PORTALS:
        if not portal.get("roles"):
            continue
        if target_role.lower() in [role.lower() for role in portal.get("roles", [])]:
            portals.append(portal)
    if not portals:
        portals = JOB_PORTALS[:5]

    return {
        "ats_score": score,
        "summary": f"The resume is a reasonable match for the {target_role} role, but it would benefit from stronger keyword alignment and more measurable outcomes.",
        "skills_found": detected or ["Python", "SQL", "Communication"],
        "missing_skills": missing or ["Advanced SQL", "Statistics", "Data Visualization"],
        "keyword_gaps": ["Result metrics", "Project outcomes", "Role-specific keywords", "Technology stack"],
        "certifications": certification_suggestions[:3],
        "projects": projects[:3],
        "resume_improvements": [
            "Add measurable achievements with numeric impact.",
            "Strengthen the professional summary around the target role.",
            "Add relevant keywords for the job description.",
            "Include GitHub, portfolio, or dashboard links.",
            "Use ATS-friendly sections and consistent formatting."
        ],
        "job_portals": portals[:5]
    }


def generate_interview_prep(target_role: str, skills: List[str]) -> Dict[str, Any]:
    role = target_role.strip() or "General Career"
    current_skills = [skill.strip() for skill in skills if skill.strip()]
    role_skills = get_role_metadata(role).get("skills", [])
    technical = [
        f"Explain how you would use {skill} in a real project for a {role} role." for skill in (current_skills[:3] or role_skills[:3])
    ]
    role_specific = {
        "Data Scientist": [
            "How would you detect and handle outliers in a dataset?",
            "Explain the difference between overfitting and underfitting.",
            "How do you evaluate a classification model in production?"
        ],
        "Data Analyst": [
            "How would you clean messy sales data before building a dashboard?",
            "What metrics would you use to measure campaign performance?",
            "How do you explain a KPI drop to a business stakeholder?"
        ],
        "Software Developer": [
            "How do you debug a bug in a production application?",
            "What is the difference between synchronous and asynchronous processing?",
            "How would you design a scalable REST API?"
        ],
        "UX Designer": [
            "How do you validate a design with users before building it?",
            "What makes a user flow intuitive?",
            "How do you measure the success of a UX design improvement?"
        ],
    }
    behavioral = [
        "Tell me about a project where you handled ambiguity or uncertainty.",
        "Describe a time you solved a difficult problem with limited information.",
        "What would you do if a teammate disagreed with your approach?",
        "How do you prioritize tasks when multiple deadlines overlap?"
    ]
    fallback_skill = current_skills[0] if current_skills else "problem-solving"
    technical.extend(role_specific.get(role, [
        f"Describe a project where you used {fallback_skill} to create measurable value.",
        "How do you validate whether a solution meets the user or business need?",
        "What trade-offs matter when choosing a technical approach?"
    ]))

    readiness = min(100, max(45, 65 + (len(current_skills) * 5)))
    return {
        "success": True,
        "target_role": role,
        "readiness_score": readiness,
        "technical_questions": technical[:5],
        "behavioral_questions": behavioral[:4],
        "mock_prompt": f"Prepare me for a {role} interview. Ask me 3 technical questions and 2 behavioral questions, then provide feedback on my answers."
    }


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health_check():
    return jsonify({"status": "ok"})


@app.get("/api/roles")
def roles_list():
    role_names = [item.get("role", "") for item in ROLE_DATA if item.get("role")]
    return jsonify({"success": True, "roles": sorted(role_names)})


@app.post("/api/career-plan")
def career_plan():
    try:
        payload = request.get_json(silent=True) or {}
        name = str(payload.get("name", "")).strip()
        target_role = str(payload.get("target_role", "")).strip()
        skills = payload.get("skills", [])
        if not name or not target_role:
            return jsonify({"success": False, "error": "Name and target role are required."}), 400
        if not isinstance(skills, list):
            return jsonify({"success": False, "error": "Skills must be a list of strings."}), 400

        gemini = GeminiService()
        generated = None
        try:
            generated = gemini.generate_career_plan(name, target_role, skills)
        except ValueError as exc:
            generated = generate_fallback_career_plan(name, target_role, skills)
        except Exception:
            generated = generate_fallback_career_plan(name, target_role, skills)

        normalized = generated if isinstance(generated, dict) else generate_fallback_career_plan(name, target_role, skills)
        if "thirty_day_plan" not in normalized:
            normalized = generate_fallback_career_plan(name, target_role, skills)
        if "readiness_score" not in normalized:
            normalized["readiness_score"] = min(100, max(45, 55 + (len(skills) * 5)))

        response = {
            "success": True,
            "name": name,
            "target_role": target_role,
            "summary": normalized.get("summary", ""),
            "current_skills": normalized.get("current_skills", []),
            "skills_to_learn": normalized.get("skills_to_learn", []),
            "readiness_score": int(normalized.get("readiness_score", 0)),
            "plan": normalized.get("thirty_day_plan", []),
            "resources": normalized.get("resources", [])
        }
        return jsonify(response)
    except Exception as exc:
        return jsonify({"success": False, "error": "Unable to generate the career plan right now."}), 500


@app.post("/api/analyze-resume")
def analyze_resume():
    try:
        if "resume" not in request.files:
            return jsonify({"success": False, "error": "Resume file is required."}), 400
        target_role = request.form.get("target_role", "").strip()
        if not target_role:
            return jsonify({"success": False, "error": "Target role is required."}), 400

        uploaded = request.files["resume"]
        if uploaded.filename == "":
            return jsonify({"success": False, "error": "Please choose a resume file to upload."}), 400

        try:
            resume_text = extract_resume_text(uploaded)
        except ValueError as exc:
            return jsonify({"success": False, "error": str(exc)}), 400

        gemini = GeminiService()
        generated = None
        try:
            generated = gemini.generate_resume_analysis(target_role, resume_text)
        except ValueError:
            generated = generate_fallback_resume_analysis(target_role, resume_text)
        except Exception:
            generated = generate_fallback_resume_analysis(target_role, resume_text)

        normalized = generated if isinstance(generated, dict) else generate_fallback_resume_analysis(target_role, resume_text)
        if "ats_score" not in normalized:
            normalized = generate_fallback_resume_analysis(target_role, resume_text)

        response = {
            "success": True,
            "target_role": target_role,
            "ats_score": int(normalized.get("ats_score", 0)),
            "summary": normalized.get("summary", ""),
            "skills_found": normalized.get("skills_found", []),
            "missing_skills": normalized.get("missing_skills", []),
            "keyword_gaps": normalized.get("keyword_gaps", []),
            "certifications": normalized.get("certifications", []),
            "projects": normalized.get("projects", []),
            "resume_improvements": normalized.get("resume_improvements", []),
            "job_portals": normalized.get("job_portals", []),
        }
        return jsonify(response)
    except Exception as exc:
        return jsonify({"success": False, "error": "The resume could not be analyzed right now."}), 500


@app.post("/api/interview-prep")
def interview_prep():
    try:
        payload = request.get_json(silent=True) or {}
        target_role = str(payload.get("target_role", "")).strip()
        skills = payload.get("skills", [])
        if not isinstance(skills, list):
            return jsonify({"success": False, "error": "Skills must be a list of strings."}), 400
        if not target_role:
            return jsonify({"success": False, "error": "Target role is required."}), 400

        prep = generate_interview_prep(target_role, skills)
        return jsonify(prep)
    except Exception:
        return jsonify({"success": False, "error": "Interview preparation could not be generated right now."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
