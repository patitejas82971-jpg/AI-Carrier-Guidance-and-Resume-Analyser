import json
import re
from typing import Any, Dict, Optional

import google.generativeai as genai

from backend.config import Config


class GeminiService:
    def __init__(self) -> None:
        self.api_key = Config.GEMINI_API_KEY
        self.model = None
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")

    def is_configured(self) -> bool:
        return bool(self.api_key) and self.model is not None

    def _translate_error(self, exc: Exception) -> str:
        message = str(exc).lower()
        if "api key" in message or "authentication" in message or "forbidden" in message:
            return "The AI service could not authenticate the request. Please verify your Gemini API key."
        if "429" in message or "rate limit" in message:
            return "The AI service has temporarily reached its request limit. Please try again later."
        if "timeout" in message or "timed out" in message:
            return "Unable to connect to the AI service. Please check your internet connection and try again."
        if "network" in message or "connection" in message:
            return "Unable to connect to the AI service. Please check your internet connection and try again."
        if "not configured" in message or "missing" in message:
            return "AI service is not configured. Please check the GEMINI_API_KEY in the .env file."
        return "The AI service is temporarily unavailable. Please try again in a few moments."

    def _safe_parse_json(self, raw: Any) -> Optional[Dict[str, Any]]:
        if raw is None:
            return None
        text = raw.text if hasattr(raw, "text") else str(raw)
        if not text:
            return None
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text, flags=re.IGNORECASE)
        text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

    def _generate(self, prompt: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise ValueError("AI service is not configured. Please check the GEMINI_API_KEY in the .env file.")

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            parsed = self._safe_parse_json(response)
            if not isinstance(parsed, dict):
                raise ValueError("The AI returned an unexpected response. Please try again.")
            return parsed
        except Exception as exc:
            raise ValueError(self._translate_error(exc)) from exc

    def generate_career_plan(self, name: str, target_role: str, skills: list[str]) -> Dict[str, Any]:
        prompt = f"""
        You are a senior career coach and resume strategist.
        Create a personalized 30-day learning plan for {name} targeting the role of {target_role}.
        The person currently knows these skills: {', '.join(skills) if skills else 'No explicit skills provided'}.

        Return valid JSON with the following keys only:
        {{
          "summary": "",
          "current_skills": ["..."],
          "skills_to_learn": ["..."],
          "thirty_day_plan": [
            {{
              "day": 1,
              "topic": "",
              "objective": "",
              "tasks": ["..."],
              "estimated_hours": "2-3 hours",
              "practice_activity": "",
              "resources": ["Resource name: platform - URL or description"]
            }}
          ],
          "resources": [
            {{
              "resource_name": "",
              "topic": "",
              "platform": "",
              "description": "",
              "open_resource": ""
            }}
          ]
        }}

        Keep recommendations practical for early-career learners.
        Generate a 30-day plan with 30 entries, divided across foundation, core skills, project skills, and interview readiness.
        Use realistic, reliable learning resources, and do not invent false URLs.
        No extra commentary outside JSON.
        """
        return self._generate(prompt)

    def generate_resume_analysis(self, target_role: str, resume_text: str) -> Dict[str, Any]:
        prompt = f"""
        You are an expert ATS and hiring coach. Analyze this resume text for a target role of {target_role}.

        Resume text:
        {resume_text[:12000]}

        Return valid JSON with exactly these keys:
        {{
          "ats_score": 0,
          "summary": "",
          "skills_found": ["..."],
          "missing_skills": ["..."],
          "keyword_gaps": ["..."],
          "certifications": ["..."],
          "projects": ["..."],
          "resume_improvements": ["..."],
          "job_portals": ["LinkedIn", "Indeed"]
        }}

        Provide an estimated ATS compatibility score out of 100.
        Keep results accurate and honest. Do not invent job titles, employers, certifications, or years of experience.
        If details are missing, say that they should be added.
        No extra commentary outside JSON.
        """
        return self._generate(prompt)
