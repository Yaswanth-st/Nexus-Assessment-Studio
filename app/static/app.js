const form = document.getElementById("assessment-form");
const modeSelect = document.getElementById("mode");
const jdWrap = document.getElementById("jd-wrap");
const skillsWrap = document.getElementById("skills-wrap");
const statusChip = document.getElementById("status-chip");
const submitBtn = document.getElementById("submit-btn");
const summary = document.getElementById("summary");
const errorBox = document.getElementById("error");
const results = document.getElementById("results");
const sourceFileInput = document.getElementById("source-file");
const extractBtn = document.getElementById("extract-btn");
const generateDocBtn = document.getElementById("generate-doc-btn");
const jdInput = document.getElementById("jd");
const skillsInput = document.getElementById("skills");
const analyzeCurriculumBtn = document.getElementById("analyze-curriculum-btn");
const curriculumOptions = document.getElementById("curriculum-options");
const questionsControlsDiv = document.getElementById("question-controls");
const sortSelect = document.getElementById("sort-select");
const gamificationPanel = document.getElementById("gamification-panel");

let currentQuestions = [];
let originalQuestions = [];
let draggedElement = null;
let sessionId = null;
let analyzedCurriculumSections = [];
let sessionData = {
  totalXp: 0,
  currentLevel: 1,
  currentStreak: 0,
  maxStreak: 0,
  achievements: [],
  correctAnswers: 0,
  totalAttempts: 0,
};

function setStatus(text) {
  statusChip.textContent = text;
}

function toggleModeUI() {
  const mode = modeSelect.value;
  if (mode === "jd") {
    jdWrap.classList.remove("hidden");
    skillsWrap.classList.add("hidden");
    curriculumOptions.classList.add("hidden");
  } else {
    skillsWrap.classList.remove("hidden");
    jdWrap.classList.add("hidden");
  }
}

function getSelectedCurriculumIds() {
  return Array.from(
    document.querySelectorAll("input[name='curriculum_section']:checked")
  ).map((el) => el.value);
}

function buildScopedCurriculumText(rawText) {
  if (!analyzedCurriculumSections.length) {
    return rawText;
  }

  const selected = getSelectedCurriculumIds();
  const selectedSet = new Set(selected);

  const sectionsToUse = selected.length
    ? analyzedCurriculumSections.filter((section) => selectedSet.has(section.id))
    : analyzedCurriculumSections;

  if (!sectionsToUse.length) {
    throw new Error("Select at least one curriculum module/chapter.");
  }

  return sectionsToUse
    .map((section) => `${section.title}\n${section.content || section.preview || ""}`)
    .join("\n\n");
}

function renderCurriculumOptions(payload) {
  const overview = payload?.overview || {};
  const sections = Array.isArray(payload?.sections) ? payload.sections : [];

  analyzedCurriculumSections = sections;

  if (!sections.length) {
    curriculumOptions.classList.remove("hidden");
    curriculumOptions.innerHTML = `<p class="curriculum-empty">No modules/chapters detected. You can still generate from full curriculum text.</p>`;
    return;
  }

  const rows = sections
    .map((section) => {
      const words = section.word_count || 0;
      const category = section.category || "section";
      return `
        <label class="curriculum-option-row">
          <input type="checkbox" name="curriculum_section" value="${section.id}" checked />
          <div>
            <p class="curriculum-option-title">${section.title}</p>
            <p class="curriculum-option-meta">${category.toUpperCase()} | ${words} words</p>
            <p class="curriculum-option-preview">${section.preview || ""}</p>
          </div>
        </label>
      `;
    })
    .join("");

  const categories = Object.entries(overview.categories || {})
    .map(([name, count]) => `${name}: ${count}`)
    .join(" | ");

  curriculumOptions.innerHTML = `
    <div class="curriculum-header">
      <p><strong>${overview.total_sections || sections.length}</strong> sections detected (${categories || "mixed"})</p>
      <div class="curriculum-bulk-actions">
        <button type="button" id="select-all-sections" class="secondary-btn">Select All</button>
        <button type="button" id="clear-all-sections" class="secondary-btn">Clear All</button>
      </div>
    </div>
    <div class="curriculum-option-list">${rows}</div>
  `;

  curriculumOptions.classList.remove("hidden");

  const selectAllBtn = document.getElementById("select-all-sections");
  const clearAllBtn = document.getElementById("clear-all-sections");

  if (selectAllBtn) {
    selectAllBtn.addEventListener("click", () => {
      document
        .querySelectorAll("input[name='curriculum_section']")
        .forEach((el) => {
          el.checked = true;
        });
    });
  }

  if (clearAllBtn) {
    clearAllBtn.addEventListener("click", () => {
      document
        .querySelectorAll("input[name='curriculum_section']")
        .forEach((el) => {
          el.checked = false;
        });
    });
  }
}

async function analyzeCurriculumFromText(text) {
  const response = await fetch("/assessment/curriculum/options", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ curriculum_text: text }),
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch (_) {
      // Ignore non-JSON error body.
    }
    throw new Error(message);
  }

  return await response.json();
}

async function analyzeCurriculumFromDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/assessment/curriculum/options-from-document", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch (_) {
      // Ignore non-JSON error body.
    }
    throw new Error(message);
  }

  return await response.json();
}

function parseSkills(rawText) {
  const lines = rawText
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const parsed = lines.map((line) => {
    const [namePart, weightPart] = line.split(":");
    const name = (namePart || "").trim();
    const parsedWeight = Number((weightPart || "").trim());
    const weight = Number.isFinite(parsedWeight) && parsedWeight >= 0 ? parsedWeight : 0;
    return { name, weight };
  }).filter((item) => item.name.length > 0);

  const total = parsed.reduce((acc, x) => acc + x.weight, 0);
  if (total > 0) {
    return parsed.map((item) => ({
      name: item.name,
      weight: Number((item.weight / total).toFixed(4))
    }));
  }

  if (parsed.length > 0) {
    const equal = Number((1 / parsed.length).toFixed(4));
    return parsed.map((item) => ({ name: item.name, weight: equal }));
  }

  return [];
}

function inferSkillsFromText(rawText) {
  const segments = rawText
    .split(/\n|,|;|\||\t/g)
    .map((x) => x.trim())
    .filter((x) => x.length > 0 && x.length <= 60);

  const unique = [];
  const seen = new Set();

  for (const segment of segments) {
    const normalized = segment.toLowerCase();
    if (!seen.has(normalized)) {
      seen.add(normalized);
      unique.push(segment);
    }
    if (unique.length >= 15) {
      break;
    }
  }

  if (unique.length === 0) {
    return [];
  }

  const equalWeight = Number((1 / unique.length).toFixed(4));
  return unique.map((name) => ({ name, weight: equalWeight }));
}

function getCheckedTypes() {
  const checkboxes = Array.from(document.querySelectorAll("input[name='question_type']:checked"));
  return checkboxes.map((el) => el.value);
}

function buildPayload() {
  const mode = modeSelect.value;
  const numQuestionsRaw = Number(document.getElementById("num_questions").value || 10);
  const numQuestions = Math.max(1, Math.min(50, numQuestionsRaw));
  const questionTypes = getCheckedTypes();

  if (questionTypes.length === 0) {
    throw new Error("Pick at least one question type.");
  }

  const base = {
    type: mode,
    difficulty: document.getElementById("difficulty").value,
    num_questions: numQuestions,
    question_types: questionTypes,
  };

  if (mode === "jd") {
    const jd = document.getElementById("jd").value.trim();
    if (!jd) {
      throw new Error("Please provide a job description.");
    }
    return { ...base, jd };
  }

  const skills = parseSkills(document.getElementById("skills").value);
  const rawCurriculum = document.getElementById("skills").value.trim();

  if (!rawCurriculum) {
    throw new Error("Add curriculum content or weighted skills.");
  }

  const scopedCurriculum = buildScopedCurriculumText(rawCurriculum);
  const fallbackSkills = skills.length === 0 ? inferSkillsFromText(scopedCurriculum) : skills;

  if (fallbackSkills.length === 0) {
    return {
      ...base,
      curriculum_text: scopedCurriculum,
    };
  }

  return {
    ...base,
    skills: fallbackSkills,
    curriculum_text: scopedCurriculum,
  };
}

async function extractDocumentText() {
  const file = sourceFileInput.files && sourceFileInput.files[0];
  if (!file) {
    throw new Error("Please choose a document first.");
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/assessment/extract-text", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch (_) {
      // Ignore non-JSON error body.
    }
    throw new Error(message);
  }

  const data = await response.json();
  if (data.extraction_method) {
    setStatus(`Text Ready (${String(data.extraction_method).toUpperCase()})`);
  }
  return data.text || "";
}

async function generateFromDocument() {
  const file = sourceFileInput.files && sourceFileInput.files[0];
  if (!file) {
    throw new Error("Please choose a document first.");
  }

  const numQuestionsRaw = Number(document.getElementById("num_questions").value || 10);
  const numQuestions = Math.max(1, Math.min(50, numQuestionsRaw));
  const questionTypes = getCheckedTypes();
  if (questionTypes.length === 0) {
    throw new Error("Pick at least one question type.");
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("input_type", modeSelect.value);
  formData.append("difficulty", document.getElementById("difficulty").value);
  formData.append("num_questions", String(numQuestions));
  formData.append("question_types", questionTypes.join(","));

  if (modeSelect.value === "curriculum" && analyzedCurriculumSections.length > 0) {
    const selectedIds = getSelectedCurriculumIds();
    if (selectedIds.length > 0) {
      formData.append("selected_sections", selectedIds.join(","));
    }
  }

  const response = await fetch("/assessment/generate-from-document", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch (_) {
      // Ignore non-JSON error body.
    }
    throw new Error(message);
  }

  return await response.json();
}

function renderSummary(report, metadata) {
  summary.classList.remove("hidden");
  const extraction = metadata?.extraction_method ? ` | <strong>Extraction:</strong> ${metadata.extraction_method.toUpperCase()}` : "";
  summary.innerHTML = `
    <strong>Total Questions:</strong> ${metadata?.total_questions ?? report?.total_questions ?? 0}
    | <strong>Skills Covered:</strong> ${report?.skills_covered ?? 0}/${report?.total_skills ?? 0}
    | <strong>Priority Aligned:</strong> ${report?.priority_aligned ? "Yes" : "Partial"}
    ${extraction}
  `;
}

function renderQuestions(questions) {
  if (!questions || questions.length === 0) {
    results.innerHTML = "<p>No questions returned.</p>";
    questionsControlsDiv.classList.add("hidden");
    return;
  }

  originalQuestions = JSON.parse(JSON.stringify(questions));
  currentQuestions = JSON.parse(JSON.stringify(questions));

  questionsControlsDiv.classList.remove("hidden");
  gamificationPanel.classList.remove("hidden");

  results.innerHTML = questions
    .map((q, idx) => {
      const optionsHtml =
        Array.isArray(q.options) && q.options.length
          ? `<div class="option-choices" data-question-id="${idx}">${q.options
              .map(
                (opt) =>
                  `<button type="button" class="option-choice" data-question-id="${idx}" data-option="${String(opt).replace(/\"/g, "&quot;")}">${opt}</button>`
              )
              .join("")}</div>`
          : "";

      const answerControl =
        Array.isArray(q.options) && q.options.length
          ? `
            <input
              type="text"
              class="user-answer-input"
              placeholder="Click an option above or type your answer"
              data-question-id="${idx}"
              style="font-size: 0.95rem;"
            />
          `
          : `
            <textarea
              class="user-answer-input"
              placeholder="Type your answer here..."
              data-question-id="${idx}"
              rows="3"
              style="font-size: 0.95rem;"
            ></textarea>
          `;

      const difficultyClass = q.difficulty
        ? `difficulty-${q.difficulty.toLowerCase()}`
        : "";
      const difficultyTag = q.difficulty
        ? q.difficulty.charAt(0).toUpperCase() + q.difficulty.slice(1)
        : "Medium";

      return `
        <article class="question" data-index="${idx}" style="animation-delay:${Math.min(
          idx * 20,
          300
        )}ms">
          <div class="meta">
            <span class="tag">${q.type || "Q"}</span>
            <span class="tag skill">${q.skill || "Unknown Skill"}</span>
            <span class="tag ${difficultyClass}">${difficultyTag}</span>
            ${
              q.priority_rank
                ? `<span class="tag priority">Priority ${q.priority_rank}</span>`
                : ""
            }
          </div>
          <p class="qtext"><strong class="qnumber">${idx + 1}.</strong> ${
            q.question || "(No question text)"
          }</p>
          ${optionsHtml}
          
          <!-- Answer Input Section -->
          <div class="answer-input-group" data-question-id="${idx}">
            <label style="color: var(--text-secondary); font-size: 0.9rem; margin: 0 0 8px 0;">
              Your Answer:
            </label>
            ${answerControl}
            
            <div class="answer-controls">
              <button class="submit-answer-button" data-question-id="${idx}" style="cursor: pointer;">
                Submit Answer
              </button>
              <button class="hint-button" data-question-id="${idx}" disabled style="cursor: pointer;">
                💡 Hint (0/3)
              </button>
              <button class="reveal-button" data-question-id="${idx}" disabled style="cursor: pointer;">
                👁️ Reveal
              </button>
            </div>
            
            <div class="hints-container" data-question-id="${idx}"></div>
            <div class="feedback-container" data-question-id="${idx}"></div>
          </div>
        </article>
      `;
    })
    .join("");

  attachEventListeners();
  attachDragListeners();
}

function attachEventListeners() {
  document.querySelectorAll(".option-choice").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const questionId = parseInt(e.target.dataset.questionId, 10);
      const option = e.target.dataset.option || "";
      const input = document.querySelector(
        `.user-answer-input[data-question-id="${questionId}"]`
      );
      if (!input) return;

      input.value = option;

      document
        .querySelectorAll(`.option-choice[data-question-id="${questionId}"]`)
        .forEach((optionBtn) => optionBtn.classList.remove("selected"));
      e.target.classList.add("selected");
    });
  });

  // Submit Answer buttons
  document.querySelectorAll(".submit-answer-button").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const questionId = parseInt(e.target.dataset.questionId);
      const input = document.querySelector(
        `.user-answer-input[data-question-id="${questionId}"]`
      );
      const userAnswer = input.value.trim();

      if (!userAnswer) {
        alert("Please enter an answer");
        return;
      }

      await submitAnswer(questionId, userAnswer);
    });
  });

  // Enter key to submit answer
  document.querySelectorAll(".user-answer-input").forEach((input) => {
    input.addEventListener("keypress", async (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const questionId = parseInt(e.target.dataset.questionId);
        const userAnswer = input.value.trim();

        if (userAnswer) {
          await submitAnswer(questionId, userAnswer);
        }
      }
    });
  });

  // Hint buttons
  document.querySelectorAll(".hint-button").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const questionId = parseInt(e.target.dataset.questionId);
      await getHint(questionId, e.target);
    });
  });

  // Reveal buttons
  document.querySelectorAll(".reveal-button").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const questionId = parseInt(e.target.dataset.questionId);
      await revealAnswer(questionId, e.target);
    });
  });
}

async function submitAnswer(questionId, userAnswer) {
  if (!sessionId) {
    alert("Session not initialized. Please regenerate the assessment and try again.");
    console.error("No session ID. Initialize session first.");
    return false;
  }

  try {
    const question = currentQuestions[questionId] || originalQuestions[questionId] || {};

    const response = await fetch(
      `/assessment/session/${sessionId}/answer`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          question_id: questionId,
          question,
          user_answer: userAnswer,
        }),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    // Update session data
    sessionData.totalXp = data.total_xp;
    sessionData.currentLevel = data.current_level;
    sessionData.currentStreak = data.current_streak;
    sessionData.totalAttempts = (sessionData.totalAttempts || 0) + 1;
    if (data.is_correct) {
      sessionData.correctAnswers = (sessionData.correctAnswers || 0) + 1;
    }

    // Show feedback
    const feedbackContainer = document.querySelector(
      `.feedback-container[data-question-id="${questionId}"]`
    );
    const feedbackClass = data.is_correct ? "feedback-correct" : "feedback-incorrect";
    const feedbackText = data.is_correct
      ? `✓ Correct! +${data.xp_earned} XP`
      : `✗ Not quite right. Try again or use hints!`;

    feedbackContainer.innerHTML = `<div class="feedback-message ${feedbackClass}">${feedbackText}</div>`;

    // Disable input and submit button if correct
    if (data.is_correct) {
      const input = document.querySelector(
        `.user-answer-input[data-question-id="${questionId}"]`
      );
      const submitBtn = document.querySelector(
        `.submit-answer-button[data-question-id="${questionId}"]`
      );
      input.disabled = true;
      submitBtn.disabled = true;
    }

    // Update hint button state
    updateHintButton(questionId, data.hints_used || 0);

    // Check for achievements
    if (data.achievements_unlocked && data.achievements_unlocked.length > 0) {
      displayAchievements(data.achievements_unlocked);
    }

    // Display behavioral signals if any
    if (data.behavioral_signals && data.behavioral_signals.length > 0) {
      displayBehavioralSignals(data.behavioral_signals);
    }

    // Update gamification display
    updateGamificationDisplay();

    return data.is_correct;
  } catch (err) {
    console.error("Error submitting answer:", err);
    alert("Error submitting answer. Check console for details.");
    return false;
  }
}

async function getHint(questionId, btn) {
  if (!sessionId) {
    alert("Session not initialized. Please regenerate the assessment and try again.");
    console.error("No session ID.");
    return;
  }

  try {
    const question = currentQuestions[questionId] || originalQuestions[questionId] || {};

    const response = await fetch(
      `/assessment/session/${sessionId}/hint`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          question_id: questionId,
          question,
        }),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    if (data.error) {
      alert(data.error);
      return;
    }

    // Append hint to hints container
    const hintsContainer = document.querySelector(
      `.hints-container[data-question-id="${questionId}"]`
    );
    const hintBox = document.createElement("div");
    hintBox.className = "hint-display";
    hintBox.textContent = `💡 Hint ${data.hints_used}: ${data.hint}`;
    hintsContainer.appendChild(hintBox);

    // Update button state
    updateHintButton(questionId, data.hints_used);

    // Enable reveal button if 3 hints used
    if (data.hints_used >= 3) {
      const revealBtn = document.querySelector(
        `.reveal-button[data-question-id="${questionId}"]`
      );
      revealBtn.disabled = false;
      revealBtn.title = "Answer revealed after 3 hints";
    }
  } catch (err) {
    console.error("Error getting hint:", err);
    alert("Error retrieving hint. Check console for details.");
  }
}

async function revealAnswer(questionId, btn) {
  if (!sessionId) {
    alert("Session not initialized. Please regenerate the assessment and try again.");
    console.error("No session ID.");
    return;
  }

  try {
    const question = currentQuestions[questionId] || originalQuestions[questionId] || {};

    const response = await fetch(
      `/assessment/session/${sessionId}/reveal`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          question_id: questionId,
          question,
        }),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    // Show answer and explanation
    const feedbackContainer = document.querySelector(
      `.feedback-container[data-question-id="${questionId}"]`
    );
    const revealBox = document.createElement("div");
    revealBox.className = "feedback-message";
    revealBox.style.borderTop = "2px solid var(--border)";
    revealBox.style.marginTop = "12px";
    revealBox.innerHTML = `
      <strong>Answer Revealed:</strong> ${data.answer}
      ${data.explanation ? `<br/><em>${data.explanation}</em>` : ""}
    `;
    feedbackContainer.appendChild(revealBox);

    // Disable reveal button
    btn.disabled = true;
    btn.style.opacity = "0.5";

    // Disable input and submit button
    const input = document.querySelector(
      `.user-answer-input[data-question-id="${questionId}"]`
    );
    const submitBtn = document.querySelector(
      `.submit-answer-button[data-question-id="${questionId}"]`
    );
    input.disabled = true;
    submitBtn.disabled = true;
  } catch (err) {
    console.error("Error revealing answer:", err);
    alert("Error revealing answer. Check console for details.");
  }
}

function updateHintButton(questionId, hintsUsed) {
  const hintBtn = document.querySelector(
    `.hint-button[data-question-id="${questionId}"]`
  );
  if (!hintBtn) return;

  hintBtn.textContent = `💡 Hint (${hintsUsed}/3)`;

  if (hintsUsed >= 3) {
    hintBtn.disabled = true;
    hintBtn.title = "Maximum hints reached";
  } else {
    hintBtn.disabled = false;
  }
}

function updateGamificationDisplay() {
  // Update XP
  const xpEl = document.querySelector("#xp-display");
  if (xpEl) xpEl.textContent = sessionData.totalXp || 0;

  // Update Level
  const levelEl = document.querySelector("#level-display");
  if (levelEl) levelEl.textContent = sessionData.currentLevel || 1;

  // Update Streak
  const streakEl = document.querySelector("#streak-display");
  if (streakEl) streakEl.textContent = sessionData.currentStreak || 0;

  // Update Accuracy
  const accuracyEl = document.querySelector("#accuracy-display");
  if (accuracyEl) {
    const accuracy = sessionData.totalAttempts
      ? Math.round((sessionData.correctAnswers / sessionData.totalAttempts) * 100)
      : 0;
    accuracyEl.textContent = accuracy + "%";
  }
}

function displayAchievements(achievements) {
  const badgesContainer = document.querySelector("#achievements-badges");
  if (!badgesContainer) return;

  achievements.forEach((achievement) => {
    const badge = document.createElement("div");
    badge.className = "achievement-badge";
    badge.innerHTML = `<span>${achievement.icon || "🏆"}</span> <strong>${achievement.name}</strong>`;
    badge.title = achievement.description;
    badgesContainer.appendChild(badge);

    // Trigger animation
    setTimeout(() => {
      badge.style.animation = "bounce-in 0.4s ease-out";
    }, 10);
  });
}

function displayBehavioralSignals(signals) {
  const signalsContainer = document.querySelector("#behavioral-signals");
  if (!signalsContainer) return;

  signals.forEach((signal) => {
    const signalBox = document.createElement("div");
    signalBox.className = `signal-box ${signal.intervention_level || "info"}`;
    signalBox.innerHTML = `<strong>${signal.signal_type}:</strong> ${signal.recommendation}`;
    signalsContainer.appendChild(signalBox);

    // Auto-remove after 5 seconds
    setTimeout(() => signalBox.remove(), 5000);
  });
}

function attachDragListeners() {
  const questions = document.querySelectorAll(".question");
  
  questions.forEach((q) => {
    q.addEventListener("dragstart", (e) => {
      draggedElement = q;
      q.classList.add("dragging");
    });

    q.addEventListener("dragend", () => {
      q.classList.remove("dragging");
    });

    q.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (draggedElement && draggedElement !== q) {
        const rect = q.getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;
        if (e.clientY < midpoint) {
          q.parentNode.insertBefore(draggedElement, q);
        } else {
          q.parentNode.insertBefore(draggedElement, q.nextSibling);
        }
      }
    });
  });
}

function sortQuestions(sortBy) {
  const questions = JSON.parse(JSON.stringify(currentQuestions.length > 0 ? currentQuestions : originalQuestions));

  if (sortBy === "original") {
    currentQuestions = originalQuestions;
  } else if (sortBy === "priority") {
    currentQuestions = questions.sort((a, b) => {
      const priorityA = a.priority_rank || 999;
      const priorityB = b.priority_rank || 999;
      return priorityA - priorityB;
    });
  } else if (sortBy === "difficulty-asc") {
    const diffOrder = { easy: 1, medium: 2, hard: 3 };
    currentQuestions = questions.sort((a, b) => {
      const diffA = diffOrder[a.difficulty?.toLowerCase()] || 2;
      const diffB = diffOrder[b.difficulty?.toLowerCase()] || 2;
      return diffA - diffB;
    });
  } else if (sortBy === "difficulty-desc") {
    const diffOrder = { easy: 1, medium: 2, hard: 3 };
    currentQuestions = questions.sort((a, b) => {
      const diffA = diffOrder[a.difficulty?.toLowerCase()] || 2;
      const diffB = diffOrder[b.difficulty?.toLowerCase()] || 2;
      return diffB - diffA;
    });
  }

  renderQuestions(currentQuestions);
}

modeSelect.addEventListener("change", toggleModeUI);

extractBtn.addEventListener("click", async () => {
  errorBox.classList.add("hidden");

  try {
    setStatus("Extracting...");
    extractBtn.disabled = true;

    const extractedText = await extractDocumentText();
    if (!extractedText.trim()) {
      throw new Error("No readable text found in the uploaded file.");
    }

    if (modeSelect.value === "jd") {
      jdInput.value = extractedText;
    } else {
      skillsInput.value = extractedText;
      const analysis = await analyzeCurriculumFromText(extractedText);
      renderCurriculumOptions(analysis);
    }

    if (!statusChip.textContent.startsWith("Text Ready")) {
      setStatus("Text Ready");
    }
  } catch (error) {
    setStatus("Error");
    errorBox.classList.remove("hidden");
    errorBox.textContent = error.message || "Failed to extract text";
  } finally {
    extractBtn.disabled = false;
  }
});

analyzeCurriculumBtn.addEventListener("click", async () => {
  errorBox.classList.add("hidden");

  try {
    setStatus("Analyzing Curriculum...");
    analyzeCurriculumBtn.disabled = true;

    const file = sourceFileInput.files && sourceFileInput.files[0];
    let analysis;

    if (file) {
      analysis = await analyzeCurriculumFromDocument(file);
      skillsInput.value = analysis.curriculum_text || skillsInput.value;
      if (analysis.extraction_method) {
        setStatus(`Curriculum Analyzed (${String(analysis.extraction_method).toUpperCase()})`);
      }
    } else {
      const text = skillsInput.value.trim();
      if (!text) {
        throw new Error("Paste curriculum text or upload a file before analysis.");
      }
      analysis = await analyzeCurriculumFromText(text);
      setStatus("Curriculum Analyzed");
    }

    renderCurriculumOptions(analysis);
  } catch (error) {
    setStatus("Error");
    errorBox.classList.remove("hidden");
    errorBox.textContent = error.message || "Failed to analyze curriculum";
  } finally {
    analyzeCurriculumBtn.disabled = false;
  }
});

generateDocBtn.addEventListener("click", async () => {
  errorBox.classList.add("hidden");
  summary.classList.add("hidden");
  results.innerHTML = "";

  try {
    setStatus("Generating...");
    generateDocBtn.disabled = true;
    submitBtn.disabled = true;

    const data = await generateFromDocument();
    renderSummary(data.report, data.metadata);

    // Initialize gamification session for document-based generation too.
    const sessionReady = await initializeGameSession();
    if (!sessionReady) {
      throw new Error("Could not start assessment session. Please try again.");
    }

    renderQuestions(data.assessment);
    setStatus("Done");
  } catch (error) {
    setStatus("Error");
    errorBox.classList.remove("hidden");
    errorBox.textContent = error.message || "Failed to generate from document";
  } finally {
    generateDocBtn.disabled = false;
    submitBtn.disabled = false;
  }
});

toggleModeUI();
setStatus("Idle");

// Sort select listener
sortSelect.addEventListener("change", (e) => {
  sortQuestions(e.target.value);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  errorBox.classList.add("hidden");
  summary.classList.add("hidden");
  results.innerHTML = "";

  try {
    const payload = buildPayload();

    setStatus("Generating...");
    submitBtn.disabled = true;

    const response = await fetch("/assessment/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Request failed (${response.status}): ${text}`);
    }

    const data = await response.json();
    renderSummary(data.report, data.metadata);
    
    // Initialize gamification session
    const sessionReady = await initializeGameSession();
    if (!sessionReady) {
      throw new Error("Could not start assessment session. Please try generating again.");
    }
    
    renderQuestions(data.assessment);
    setStatus("Done");
  } catch (error) {
    setStatus("Error");
    errorBox.classList.remove("hidden");
    errorBox.textContent = error.message || "Unexpected error";
  } finally {
    submitBtn.disabled = false;
  }
});

async function initializeGameSession() {
  try {
    const response = await fetch("/assessment/session/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      throw new Error(`Failed to start session: ${response.status}`);
    }

    const data = await response.json();
    sessionId = data.session_id;
    
    // Reset session data
    sessionData = {
      totalXp: 0,
      currentLevel: 1,
      currentStreak: 0,
      maxStreak: 0,
      achievements: [],
      correctAnswers: 0,
      totalAttempts: 0,
    };
    
    // Clear achievement badges
    const badgesContainer = document.querySelector("#achievements-badges");
    if (badgesContainer) {
      badgesContainer.innerHTML = "";
    }

    // Clear behavioral signals
    const signalsContainer = document.querySelector("#behavioral-signals");
    if (signalsContainer) {
      signalsContainer.innerHTML = "";
    }

    console.log("Gamification session started:", sessionId);
    return true;
  } catch (err) {
    console.error("Error initializing session:", err);
    return false;
  }
}
