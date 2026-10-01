document.addEventListener("DOMContentLoaded", async () => {
  const careerForm = document.getElementById("career-form");
  const resumeForm = document.getElementById("resume-form");
  const interviewForm = document.getElementById("interview-form");

  await loadRoleSuggestions();
  renderRecentActivity();

  careerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(careerForm);
    const payload = {
      name: formData.get("name"),
      target_role: formData.get("target_role"),
      skills: (formData.get("skills") || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    };

    renderLoading("career-result", "Generating your 30-day roadmap...");

    try {
      const response = await fetch("/api/career-plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
        throw new Error(result.error || "Unable to generate the career plan.");
      }
      renderCareerPlan(result, "career-result");
      saveRecentActivity({
        type: "career",
        label: `${result.target_role || "Career"} roadmap`,
        detail: `${result.current_skills?.length || 0} current skills · ${result.plan?.length || 0} day plan`,
      });
    } catch (error) {
      renderError("career-result", error.message || "Unable to generate the career plan right now.");
    }
  });

  resumeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(resumeForm);
    const file = formData.get("resume");

    if (!file || !file.name) {
      renderError("resume-result", "Please choose a resume file to upload.");
      return;
    }

    renderLoading("resume-result", "Analyzing your resume and scoring ATS fit...");

    try {
      const requestData = new FormData();
      requestData.append("resume", file);
      requestData.append("target_role", formData.get("target_role"));

      const response = await fetch("/api/analyze-resume", {
        method: "POST",
        body: requestData,
      });

      const result = await response.json();
      if (!response.ok || !result.success) {
        throw new Error(result.error || "Unable to analyze the resume right now.");
      }
      renderResumeAnalysis(result, "resume-result");
      saveRecentActivity({
        type: "resume",
        label: `${result.target_role || "Resume"} ATS score`,
        detail: `${result.ats_score || 0}/100 ATS compatibility`,
      });
    } catch (error) {
      renderError("resume-result", error.message || "Unable to analyze the resume right now.");
    }
  });

  interviewForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(interviewForm);
    const payload = {
      target_role: formData.get("target_role"),
      skills: (formData.get("skills") || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    };

    renderLoading("interview-result", "Generating interview questions for your target role...");

    try {
      const response = await fetch("/api/interview-prep", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
        throw new Error(result.error || "Unable to generate interview prep.");
      }
      renderInterviewPrep(result, "interview-result");
      saveRecentActivity({
        type: "interview",
        label: `${result.target_role || "Interview"} prep`,
        detail: `${result.readiness_score || 0}% readiness score`,
      });
    } catch (error) {
      renderError("interview-result", error.message || "Unable to generate interview prep right now.");
    }
  });
});

async function loadRoleSuggestions() {
  try {
    const response = await fetch("/api/roles");
    const data = await response.json();
    const roles = Array.isArray(data.roles) ? data.roles : [];
    const datalist = document.getElementById("role-options");
    datalist.innerHTML = roles.map((role) => `<option value="${escapeAttribute(role)}"></option>`).join("");
  } catch (error) {
    console.warn("Could not load role suggestions.", error);
  }
}

function saveRecentActivity(entry) {
  try {
    const history = JSON.parse(localStorage.getItem("career-app-history") || "[]");
    const next = [
      {
        ...entry,
        timestamp: new Date().toLocaleString([], { dateStyle: "medium", timeStyle: "short" }),
      },
      ...history,
    ].slice(0, 4);
    localStorage.setItem("career-app-history", JSON.stringify(next));
  } catch (error) {
    console.warn("Unable to save activity history.", error);
  }
  renderRecentActivity();
}

function renderRecentActivity() {
  const panel = document.getElementById("recent-activity");
  if (!panel) return;

  let history = [];
  try {
    history = JSON.parse(localStorage.getItem("career-app-history") || "[]");
  } catch (error) {
    history = [];
  }

  if (!history.length) {
    panel.innerHTML = `
      <h3>Recent Activity</h3>
      <p>No saved career activities yet. Generate a plan or analyze a resume to get started.</p>
    `;
    return;
  }

  panel.innerHTML = `
    <h3>Recent Activity</h3>
    <div class="activity-list">
      ${history
        .map(
          (item) => `
            <div class="activity-item ${escapeHtml(item.type || "general")}">
              <strong>${escapeHtml(item.label || "Activity")}</strong>
              <span>${escapeHtml(item.detail || "")}</span>
              <small>${escapeHtml(item.timestamp || "Recent")}</small>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function renderLoading(targetId, message) {
  const container = document.getElementById(targetId);
  container.innerHTML = `
    <div class="empty-state">
      <div>
        <h3>Processing...</h3>
        <p>${message}</p>
      </div>
    </div>
  `;
}

function renderError(targetId, message) {
  const container = document.getElementById(targetId);
  container.innerHTML = `
    <div class="empty-state">
      <div>
        <h3>Something went wrong</h3>
        <p>${message}</p>
      </div>
    </div>
  `;
}

function renderCareerPlan(result, targetId) {
  const container = document.getElementById(targetId);
  const plan = Array.isArray(result.plan) ? result.plan : [];
  const skillsToLearn = Array.isArray(result.skills_to_learn) ? result.skills_to_learn : [];
  const currentSkills = Array.isArray(result.current_skills) ? result.current_skills : [];
  const resources = Array.isArray(result.resources) ? result.resources : [];

  window.latestCareerPlan = result;
  const readinessScore = Number(result.readiness_score || 0);
  container.innerHTML = `
    <div class="result-header">
      <h3>Career Analysis</h3>
      <button class="btn btn-secondary small" type="button" onclick="downloadCareerPlan(window.latestCareerPlan)">Export Plan</button>
    </div>
    <div class="result-section">
      <h4>Career Readiness</h4>
      <div class="ready-meter">
        <div class="ready-meter-fill" style="width: ${Math.min(100, readinessScore)}%"></div>
      </div>
      <p>${readinessScore}% readiness for ${escapeHtml(result.target_role || "the target role")}</p>
    </div>
    <div class="result-section">
      <h4>Target Role</h4>
      <p>${escapeHtml(result.target_role || "Not specified")}</p>
    </div>
    <div class="result-section">
      <h4>Current Skills</h4>
      <ul class="skill-list">${currentSkills.map((skill) => `<li>${escapeHtml(skill)}</li>`).join("") || "<li>No skills listed</li>"}</ul>
    </div>
    <div class="result-section">
      <h4>Skills To Develop</h4>
      <ul class="skill-list">${skillsToLearn.map((skill) => `<li>${escapeHtml(skill)}</li>`).join("") || "<li>None identified yet</li>"}</ul>
    </div>
    <div class="result-section">
      <h4>Summary</h4>
      <p>${escapeHtml(result.summary || "No summary available.")}</p>
    </div>
    <div class="result-section">
      <h4>30-Day Plan</h4>
      <div class="list-stack">
        ${plan
          .slice(0, 6)
          .map(
            (entry) => `
              <div class="plan-item">
                <div class="plan-meta">
                  <span>Day ${escapeHtml(entry.day ?? "")}</span>
                  <span>${escapeHtml(entry.estimated_hours ?? "")}</span>
                </div>
                <h5>${escapeHtml(entry.topic ?? "Topic")}</h5>
                <p><strong>Objective:</strong> ${escapeHtml(entry.objective ?? "")}</p>
                <p><strong>Tasks:</strong> ${escapeHtml((entry.tasks || []).join(", "))}</p>
                <p><strong>Practice:</strong> ${escapeHtml(entry.practice_activity ?? "")}</p>
              </div>
            `
          )
          .join("") || "<p>No daily plan available.</p>"}
      </div>
    </div>
    <div class="result-section">
      <h4>Learning Resources</h4>
      <div class="list-stack">
        ${resources
          .slice(0, 4)
          .map(
            (item) => `
              <div class="resource-item">
                <h5>${escapeHtml(item.resource_name || "Resource")}</h5>
                <p>${escapeHtml(item.platform || "")}</p>
                <p>${escapeHtml(item.description || "")}</p>
              </div>
            `
          )
          .join("") || "<p>No learning resources available.</p>"}
      </div>
    </div>
  `;
}

function renderResumeAnalysis(result, targetId) {
  const container = document.getElementById(targetId);
  const atsScore = Number(result.ats_score || 0);
  const skillsFound = Array.isArray(result.skills_found) ? result.skills_found : [];
  const missingSkills = Array.isArray(result.missing_skills) ? result.missing_skills : [];
  const certifications = Array.isArray(result.certifications) ? result.certifications : [];
  const jobs = Array.isArray(result.job_portals) ? result.job_portals : [];
  const improvements = Array.isArray(result.resume_improvements) ? result.resume_improvements : [];
  const keywordGaps = Array.isArray(result.keyword_gaps) ? result.keyword_gaps : [];
  const projects = Array.isArray(result.projects) ? result.projects : [];

  const scoreBreakdown = [
    { label: "Keyword Match", value: Math.min(100, Math.max(50, atsScore + 2)) },
    { label: "Skills Match", value: Math.min(100, Math.max(50, atsScore)) },
    { label: "Formatting", value: Math.min(100, Math.max(60, atsScore - 4)) },
    { label: "Experience Match", value: Math.min(100, Math.max(55, atsScore - 8)) },
    { label: "Education Match", value: Math.min(100, Math.max(70, atsScore + 5)) },
    { label: "Projects", value: Math.min(100, Math.max(50, atsScore - 6)) },
  ];

  container.innerHTML = `
    <div class="result-header">
      <h3>Resume Match</h3>
      <div class="score-box">${atsScore}/100</div>
    </div>
    <p><strong>AI-generated estimated ATS compatibility score</strong> and not an official ATS vendor score.</p>
    <div class="result-section">
      <h4>ATS Compatibility</h4>
      <div class="score-grid">
        ${scoreBreakdown
          .map(
            (metric) => `
              <div class="metric-box">
                <strong>${metric.value}%</strong>
                <small>${metric.label}</small>
              </div>
            `
          )
          .join("")}
      </div>
    </div>
    <div class="result-section">
      <h4>Skills You Have</h4>
      <ul class="skill-list">${skillsFound.map((skill) => `<li>${escapeHtml(skill)}</li>`).join("") || "<li>No major skills detected</li>"}</ul>
    </div>
    <div class="result-section">
      <h4>Skills To Improve/Add</h4>
      <ul class="skill-list">${missingSkills.map((skill) => `<li>${escapeHtml(skill)}</li>`).join("") || "<li>Good alignment</li>"}</ul>
    </div>
    <div class="result-section">
      <h4>Keyword Gaps</h4>
      <ul class="tag-list">${keywordGaps.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>No major keyword gaps found</li>"}</ul>
    </div>
    <div class="result-section">
      <h4>Recommended Resume Updates</h4>
      <ul class="bullet-list">
        ${improvements.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>No improvement suggestions yet.</li>"}
      </ul>
    </div>
    <div class="result-section">
      <h4>Recommended Certifications</h4>
      <ul class="tag-list">${certifications.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>No certification suggestions yet</li>"}</ul>
    </div>
    <div class="result-section">
      <h4>Projects To Consider</h4>
      <ul class="tag-list">${projects.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>No project suggestions yet</li>"}</ul>
    </div>
    <div class="result-section">
      <h4>Recommended Job Platforms</h4>
      <div class="list-stack">
        ${jobs
          .map(
            (portal) => `
              <div class="portal-item">
                <div class="portal-meta">
                  <strong>${escapeHtml(portal.name || "Portal")}</strong>
                  <a href="${escapeAttribute(portal.url || "#")}" target="_blank" rel="noreferrer">Open</a>
                </div>
                <p>${escapeHtml((portal.roles || []).join(", "))}</p>
              </div>
            `
          )
          .join("") || "<p>No job portals available.</p>"}
      </div>
    </div>
  `;
}

function renderInterviewPrep(result, targetId) {
  const container = document.getElementById(targetId);
  const readiness = Number(result.readiness_score || 0);
  const technical = Array.isArray(result.technical_questions) ? result.technical_questions : [];
  const behavioral = Array.isArray(result.behavioral_questions) ? result.behavioral_questions : [];

  container.innerHTML = `
    <div class="result-header">
      <h3>Interview Prep</h3>
      <div class="score-box">${readiness}%</div>
    </div>
    <div class="result-section">
      <h4>Interview Readiness</h4>
      <div class="ready-meter">
        <div class="ready-meter-fill" style="width: ${Math.min(100, readiness)}%"></div>
      </div>
      <p>Target role: <strong>${escapeHtml(result.target_role || "Career")}</strong></p>
    </div>
    <div class="result-section">
      <h4>Technical Questions</h4>
      <ul class="interview-list">
        ${technical.map((question) => `<li>${escapeHtml(question)}</li>`).join("") || "<li>No technical questions available.</li>"}
      </ul>
    </div>
    <div class="result-section">
      <h4>Behavioral Questions</h4>
      <ul class="interview-list">
        ${behavioral.map((question) => `<li>${escapeHtml(question)}</li>`).join("") || "<li>No behavioral questions available.</li>"}
      </ul>
    </div>
    <div class="result-section">
      <h4>Mock Prompt</h4>
      <p>${escapeHtml(result.mock_prompt || "Prepare me for the next interview round.")}</p>
    </div>
  `;
}

function downloadCareerPlan(result) {
  const content = JSON.stringify(result, null, 2);
  const blob = new Blob([content], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${(result.target_role || "career-plan").toLowerCase().replace(/\s+/g, "-")}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
