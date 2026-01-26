const sampleText = `"Focus is the art of knowing what to ignore," wrote a thinker. RSVP reading keeps your gaze anchored while words flow through a fixed window. Punctuation slows the pace. Long words take a breath. Try adjusting the speed and jumping ahead or back by ten words.`;

const inputText = document.getElementById("inputText");
const loadSample = document.getElementById("loadSample");
const epubFile = document.getElementById("epubFile");
const loadEpub = document.getElementById("loadEpub");
const pdfFile = document.getElementById("pdfFile");
const loadPdf = document.getElementById("loadPdf");
const parseStatus = document.getElementById("parseStatus");
const parseSpinner = document.getElementById("parseSpinner");
const chapterList = document.getElementById("chapterList");
const chapterStatus = document.getElementById("chapterStatus");
const chapterLabel = document.getElementById("chapterLabel");
const chaptersPanel = document.querySelector(".chapters-panel");
const chapterDivider = document.querySelector(".panel-divider");
const shortcutsButton = document.getElementById("shortcuts");
const shortcutsDialog = document.getElementById("shortcutsDialog");
const shortcutsClose = document.getElementById("shortcutsClose");
const wpmSlider = document.getElementById("wpm");
const wpmValue = document.getElementById("wpmValue");
const playButton = document.getElementById("play");
const pauseButton = document.getElementById("pause");
const resumeButton = document.getElementById("resume");
const restartButton = document.getElementById("restart");
const stableButton = document.getElementById("stable");
const back10Button = document.getElementById("back10");
const forward10Button = document.getElementById("forward10");
const leftEl = document.getElementById("left");
const pivotEl = document.getElementById("pivot");
const rightEl = document.getElementById("right");
const wordIndexEl = document.getElementById("wordIndex");
const metaToggle = document.getElementById("metaToggle");
const playStateEl = document.getElementById("playState");

let tokens = [];
let currentIndex = 0;
let timerId = null;
let isPlaying = false;
let inputSegments = [];
let inputRawText = "";
let activeWordEl = null;
let rampTimerId = null;
let rampEnabled = true;
let metaMode = "words";
let chapters = [];
let activeChapterIndex = null;
let inputDebounceId = null;
let chapterMode = "none";

const INPUT_DEBOUNCE_MS = 150;

const RAMP_INTERVAL_MS = 10000;
const RAMP_STEP = 20;
const RAMP_MAX_WPM = 800;
const WORDS_PER_PAGE = 300;
const CHAPTER_LABEL_MAX = 52;

function setStatus(message) {
  parseStatus.textContent = message;
}

function setLoading(isLoading, message) {
  if (message) {
    setStatus(message);
  }
  if (parseSpinner) {
    parseSpinner.classList.toggle("is-hidden", !isLoading);
  }
  [loadEpub, loadPdf, loadSample].forEach((button) => {
    if (button) {
      button.disabled = isLoading;
    }
  });
  [epubFile, pdfFile].forEach((input) => {
    if (input) {
      input.disabled = isLoading;
    }
  });
}

function setPlayState(message) {
  playStateEl.textContent = message;
}

function updateWpmLabel() {
  wpmValue.textContent = `${wpmSlider.value} WPM`;
}

function setChapterStatus(message) {
  if (chapterStatus) {
    chapterStatus.textContent = message;
  }
}

function capChapterLabel(text) {
  if (!text) {
    return "";
  }
  if (text.length <= CHAPTER_LABEL_MAX) {
    return text;
  }
  return `${text.slice(0, CHAPTER_LABEL_MAX - 3).trimEnd()}...`;
}

function setChapterPanelMode(mode, message) {
  if (!chaptersPanel) {
    return;
  }
  const showList = mode === "epub";
  if (chapterList) {
    chapterList.classList.toggle("is-hidden", !showList);
  }
  if (chapterLabel) {
    chapterLabel.textContent = mode === "pdf" ? "Pages" : "Chapters";
  }
  chaptersPanel.classList.toggle("is-hidden", mode === "none");
  if (chapterDivider) {
    chapterDivider.classList.toggle("is-hidden", mode === "none");
  }
  if (message) {
    setChapterStatus(message);
  }
}

function isEditableTarget(target) {
  if (!target) {
    return false;
  }
  if (target === inputText || inputText.contains(target)) {
    return true;
  }
  return (
    target.isContentEditable ||
    ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
  );
}

function openShortcuts() {
  if (shortcutsDialog && !shortcutsDialog.open) {
    shortcutsDialog.showModal();
  }
}

function closeShortcuts() {
  if (shortcutsDialog && shortcutsDialog.open) {
    shortcutsDialog.close();
  }
}

function clearChapters() {
  chapters = [];
  activeChapterIndex = null;
  chapterMode = "none";
  if (chapterList) {
    chapterList.innerHTML = "";
  }
  setChapterPanelMode("none", "No chapters loaded.");
}

function setActiveChapter(index) {
  if (!chapterList) {
    return;
  }
  const items = chapterList.querySelectorAll(".chapter-item");
  items.forEach((item, itemIndex) => {
    item.classList.toggle("active", itemIndex === index);
  });
  activeChapterIndex = index;
}

function renderChapters() {
  if (!chapterList) {
    return;
  }
  chapterList.innerHTML = "";
  if (!chapters.length) {
    setChapterPanelMode("none", "No chapters loaded.");
    return;
  }
  const label = `${chapters.length} chapters`;
  setChapterPanelMode("epub", label);
  chapters.forEach((chapter, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chapter-item";
    const rawTitle = chapter.title || `Chapter ${index + 1}`;
    button.textContent = capChapterLabel(rawTitle);
    button.title = rawTitle;
    if (Number.isFinite(chapter.level) && chapter.level > 0) {
      button.style.paddingLeft = `${12 + chapter.level * 16}px`;
    }
    button.addEventListener("click", () => jumpToChapter(index));
    chapterList.appendChild(button);
  });
}

function showToken(token) {
  if (!token) {
    leftEl.textContent = "";
    pivotEl.textContent = "";
    rightEl.textContent = "";
    return;
  }

  const core = token.core || "";
  const index = Math.min(token.orp_index ?? 0, Math.max(core.length - 1, 0));
  const left = core.slice(0, index);
  const pivot = core.charAt(index) || "";
  const right = core.slice(index + 1);

  leftEl.textContent = `${token.prefix || ""}${left}`;
  pivotEl.textContent = pivot;
  rightEl.textContent = `${right}${token.suffix || ""}`;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function buildInputSegments(rawText) {
  const parts = rawText.match(/\s+|\S+/g) || [];
  let wordIndex = 0;
  inputSegments = parts.map((part) => {
    const hasCore = /[\p{L}\p{N}]/u.test(part);
    const segment = {
      text: part,
      isWord: hasCore,
      wordIndex: hasCore ? wordIndex : null,
    };
    if (hasCore) {
      wordIndex += 1;
    }
    return segment;
  });
}

function renderInputContent() {
  if (!inputSegments.length) {
    inputText.innerText = inputRawText;
    activeWordEl = null;
    return;
  }
  const html = inputSegments
    .map((segment) => {
      const escaped = escapeHtml(segment.text).replace(/\n/g, "<br>");
      if (segment.isWord) {
        return `<span class=\"input-word\" data-index=\"${segment.wordIndex}\">${escaped}</span>`;
      }
      return escaped;
    })
    .join("");
  inputText.innerHTML = html;
  activeWordEl = null;
}

function highlightInputWord(activeIndex) {
  if (!inputSegments.length) {
    return;
  }
  if (activeWordEl) {
    activeWordEl.classList.remove("input-highlight");
  }
  const next = inputText.querySelector(`[data-index=\"${activeIndex}\"]`);
  if (next) {
    next.classList.add("input-highlight");
    activeWordEl = next;
    next.scrollIntoView({ block: "center", inline: "nearest", behavior: "auto" });
  }
}

function updateMeta() {
  const total = tokens.length;
  const displayIndex = total === 0 ? 0 : Math.min(currentIndex + 1, total);
  if (metaMode === "words") {
    wordIndexEl.textContent = `${displayIndex} / ${total}`;
    metaToggle.textContent = "Words";
    return;
  }

  if (total === 0) {
    wordIndexEl.textContent = "0% / 0 pages";
    metaToggle.textContent = "% / pages";
    return;
  }

  const percent = Math.round((displayIndex / total) * 100);
  const totalPages = Math.max(1, Math.ceil(total / WORDS_PER_PAGE));
  const currentPage = Math.min(totalPages, Math.max(1, Math.ceil(displayIndex / WORDS_PER_PAGE)));
  wordIndexEl.textContent = `${percent}% / ${currentPage} / ${totalPages} pages`;
  metaToggle.textContent = "% / pages";
}

function computeDelay(token) {
  const base = 60000 / Number(wpmSlider.value || 300);
  const mult = token?.pause_mult ?? 1.0;
  return Math.max(40, base * mult);
}

function clampWpm(value) {
  return Math.min(RAMP_MAX_WPM, Math.max(100, value));
}

function startRamp() {
  if (!rampEnabled || rampTimerId) {
    return;
  }
  rampTimerId = window.setInterval(() => {
    const next = clampWpm(Number(wpmSlider.value || 300) + RAMP_STEP);
    if (next === Number(wpmSlider.value)) {
      stopRamp();
      return;
    }
    wpmSlider.value = String(next);
    updateWpmLabel();
  }, RAMP_INTERVAL_MS);
}

function stopRamp() {
  if (rampTimerId) {
    window.clearInterval(rampTimerId);
    rampTimerId = null;
  }
}

function scheduleNext() {
  if (!isPlaying) {
    return;
  }
  if (currentIndex >= tokens.length) {
    isPlaying = false;
    setPlayState("Finished");
    return;
  }

  const token = tokens[currentIndex];
  showToken(token);
  updateMeta();
  setPlayState("Playing");
  highlightInputWord(currentIndex);

  // Chain timeouts so the delay can change per word and with WPM updates.
  const delay = computeDelay(token);
  timerId = window.setTimeout(() => {
    currentIndex += 1;
    scheduleNext();
  }, delay);
}

function stopPlayback() {
  if (timerId) {
    window.clearTimeout(timerId);
    timerId = null;
  }
  isPlaying = false;
  inputText.contentEditable = "true";
  stopRamp();
}

async function parseText() {
  const text = inputText.innerText.trim();
  if (!text) {
    tokens = [];
    currentIndex = 0;
    showToken(null);
    updateMeta();
    renderInputContent();
    setStatus("Please enter some text.");
    setPlayState("Idle");
    return false;
  }

  setStatus("Parsing...");
  try {
    const response = await fetch("/api/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      throw new Error("Parse failed");
    }

    const data = await response.json();
    tokens = data.tokens || [];
    currentIndex = 0;
    showToken(tokens[0]);
    updateMeta();
    inputRawText = inputText.innerText;
    buildInputSegments(inputRawText);
    renderInputContent();
    highlightInputWord(0);
    setStatus(`Loaded ${tokens.length} words.`);
    setPlayState("Ready");
    return tokens.length > 0;
  } catch (error) {
    console.error(error);
    setStatus("Could not parse text. See console for details.");
    return false;
  }
}

function jumpWords(delta) {
  if (tokens.length === 0) {
    return;
  }
  currentIndex = Math.min(Math.max(0, currentIndex + delta), tokens.length - 1);
  showToken(tokens[currentIndex]);
  updateMeta();
  highlightInputWord(currentIndex);
  if (isPlaying) {
    stopPlayback();
    isPlaying = true;
    inputText.contentEditable = "false";
    scheduleNext();
  }
}

function jumpToChapter(index) {
  if (!chapters.length || tokens.length === 0) {
    return;
  }
  const chapter = chapters[index];
  if (!chapter) {
    return;
  }
  const startIndex = Math.min(Math.max(0, chapter.start_index ?? 0), tokens.length - 1);
  currentIndex = startIndex;
  showToken(tokens[currentIndex]);
  updateMeta();
  highlightInputWord(currentIndex);
  setActiveChapter(index);
  if (isPlaying) {
    stopPlayback();
    isPlaying = true;
    inputText.contentEditable = "false";
    scheduleNext();
  }
}

loadSample.addEventListener("click", () => {
  inputText.innerText = sampleText;
  clearChapters();
  setStatus("Sample loaded.");
  inputText.dispatchEvent(new Event("input"));
});

if (shortcutsButton && shortcutsDialog && shortcutsClose) {
  shortcutsButton.addEventListener("click", openShortcuts);
  shortcutsClose.addEventListener("click", closeShortcuts);
  shortcutsDialog.addEventListener("click", (event) => {
    if (event.target === shortcutsDialog) {
      closeShortcuts();
    }
  });
}

loadEpub.addEventListener("click", async () => {
  const file = epubFile.files[0];
  if (!file) {
    setStatus("Choose an EPUB file first.");
    return;
  }
  rampEnabled = true;
  stopRamp();
  setLoading(true, "Importing EPUB...");
  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch("/api/epub", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const errorPayload = await response.json();
      throw new Error(errorPayload.detail || "EPUB import failed");
    }
    const data = await response.json();
    chapters = Array.isArray(data.chapters) ? data.chapters : [];
    chapterMode = "epub";
    inputText.innerText = data.text || "";
    const parsed = await parseText();
    renderChapters();
    if (parsed && chapters.length) {
      setActiveChapter(0);
    }
    setLoading(false);
  } catch (error) {
    console.error(error);
    setLoading(false, `Could not import EPUB: ${error.message}`);
  }
});

if (loadPdf && pdfFile) {
  loadPdf.addEventListener("click", async () => {
    const file = pdfFile.files[0];
    if (!file) {
      setStatus("Choose a PDF file first.");
      return;
    }
    rampEnabled = true;
    stopRamp();
    setLoading(true, "Importing PDF...");
    clearChapters();
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch("/api/pdf", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const errorPayload = await response.json();
        throw new Error(errorPayload.detail || "PDF import failed");
      }
    const data = await response.json();
    inputText.innerText = data.text || "";
    const parsed = await parseText();
    const sections = Array.isArray(data.chapters) ? data.chapters : [];
    if (sections.length) {
      chapters = sections;
      chapterMode = "epub";
      renderChapters();
      if (parsed) {
        setActiveChapter(0);
      }
    } else if (Number.isFinite(data.pages)) {
      chapterMode = "pdf";
      setChapterPanelMode("pdf", `PDF pages: ${data.pages}`);
    }
    setLoading(false);
  } catch (error) {
    console.error(error);
    setLoading(false, `Could not import PDF: ${error.message}`);
  }
  });
}

inputText.addEventListener("input", () => {
  stopPlayback();
  tokens = [];
  currentIndex = 0;
  showToken(null);
  updateMeta();
  clearChapters();
  inputRawText = inputText.innerText;
  rampEnabled = true;
  setPlayState("Idle");
  if (inputDebounceId) {
    window.clearTimeout(inputDebounceId);
  }
  inputDebounceId = window.setTimeout(() => {
    buildInputSegments(inputRawText);
    renderInputContent();
    setStatus("Text changed. Press Play to parse again.");
    inputDebounceId = null;
  }, INPUT_DEBOUNCE_MS);
});

wpmSlider.addEventListener("input", updateWpmLabel);

playButton.addEventListener("click", async () => {
  if (isPlaying) {
    return;
  }
  if (tokens.length === 0) {
    const parsed = await parseText();
    if (!parsed) {
      return;
    }
  }
  isPlaying = true;
  inputText.contentEditable = "false";
  startRamp();
  scheduleNext();
});

pauseButton.addEventListener("click", () => {
  if (!isPlaying) {
    return;
  }
  stopPlayback();
  setPlayState("Paused");
  highlightInputWord(currentIndex);
});

resumeButton.addEventListener("click", () => {
  if (isPlaying || tokens.length === 0) {
    return;
  }
  isPlaying = true;
  inputText.contentEditable = "false";
  startRamp();
  scheduleNext();
});

restartButton.addEventListener("click", () => {
  stopPlayback();
  currentIndex = 0;
  showToken(tokens[0]);
  updateMeta();
  highlightInputWord(0);
  setPlayState("Restarted");
});

back10Button.addEventListener("click", () => jumpWords(-10));
forward10Button.addEventListener("click", () => jumpWords(10));

stableButton.addEventListener("click", () => {
  rampEnabled = false;
  stopRamp();
  setStatus("Speed stabilized. Press Play to keep current WPM.");
});

metaToggle.addEventListener("click", () => {
  metaMode = metaMode === "words" ? "percent" : "words";
  updateMeta();
});

document.addEventListener("keydown", (event) => {
  if (shortcutsDialog?.open && event.key === "Escape") {
    closeShortcuts();
    return;
  }
  if (isEditableTarget(event.target)) {
    return;
  }
  if (event.ctrlKey && event.key.toLowerCase() === "k") {
    event.preventDefault();
    rampEnabled = false;
    stopRamp();
    setStatus("Speed stabilized via Ctrl+K.");
    return;
  }
  const key = event.key.toLowerCase();
  if (key === " ") {
    event.preventDefault();
    if (isPlaying) {
      stopPlayback();
      setPlayState("Paused");
      highlightInputWord(currentIndex);
    } else {
      playButton.click();
    }
    return;
  }
  if (key === "r") {
    event.preventDefault();
    restartButton.click();
    return;
  }
  if (key === "j") {
    event.preventDefault();
    back10Button.click();
    return;
  }
  if (key === "l") {
    event.preventDefault();
    forward10Button.click();
    return;
  }
  if (key === "c") {
    event.preventDefault();
    metaToggle.click();
    return;
  }
  if (key === "s") {
    event.preventDefault();
    stableButton.click();
    return;
  }
  if (key === "?") {
    event.preventDefault();
    openShortcuts();
  }
});

updateWpmLabel();
updateMeta();
showToken(null);
inputRawText = inputText.innerText;
buildInputSegments(inputRawText);
renderInputContent();
clearChapters();
