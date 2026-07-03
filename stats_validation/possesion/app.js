import {
  DEFAULT_TEAM_A_NAME,
  DEFAULT_TEAM_D_NAME,
  buildExportPayload,
  buildIntervals,
  buildStatistics,
  formatTime,
  getNextPossessionState,
  getStateAtTime,
  getStateLabel,
  normalizeDuration,
  normalizeEvents,
  roundSeconds,
  validateExportPayload,
} from "./possession-core.js";

const STORAGE_KEY = "bjaevermetrics-possession-validation-v1";

const dom = {
  video: document.querySelector("#matchVideo"),
  videoFileInput: document.querySelector("#videoFileInput"),
  videoFileName: document.querySelector("#videoFileName"),
  currentTimeText: document.querySelector("#currentTimeText"),
  durationText: document.querySelector("#durationText"),
  teamANameInput: document.querySelector("#teamANameInput"),
  teamDNameInput: document.querySelector("#teamDNameInput"),
  togglePossessionButton: document.querySelector("#togglePossessionButton"),
  togglePossessionText: document.querySelector("#togglePossessionText"),
  teamAButton: document.querySelector("#teamAButton"),
  teamDButton: document.querySelector("#teamDButton"),
  teamAButtonText: document.querySelector("#teamAButtonText"),
  teamDButtonText: document.querySelector("#teamDButtonText"),
  currentPossessionBadge: document.querySelector("#currentPossessionBadge"),
  eventsTableBody: document.querySelector("#eventsTableBody"),
  emptyEventsText: document.querySelector("#emptyEventsText"),
  undoButton: document.querySelector("#undoButton"),
  clearAllButton: document.querySelector("#clearAllButton"),
  jsonImportInput: document.querySelector("#jsonImportInput"),
  exportJsonButton: document.querySelector("#exportJsonButton"),
  statusMessage: document.querySelector("#statusMessage"),
  teamADurationLabel: document.querySelector("#teamADurationLabel"),
  teamDDurationLabel: document.querySelector("#teamDDurationLabel"),
  teamAPercentageLabel: document.querySelector("#teamAPercentageLabel"),
  teamDPercentageLabel: document.querySelector("#teamDPercentageLabel"),
  teamADurationText: document.querySelector("#teamADurationText"),
  teamDDurationText: document.querySelector("#teamDDurationText"),
  teamAPercentageText: document.querySelector("#teamAPercentageText"),
  teamDPercentageText: document.querySelector("#teamDPercentageText"),
};

const state = {
  teamAName: DEFAULT_TEAM_A_NAME,
  teamDName: DEFAULT_TEAM_D_NAME,
  events: [],
  videoFileName: "",
  selectedVideoFileName: "",
  videoDurationSeconds: 0,
  lastCreatedEventId: null,
  videoObjectUrl: "",
};

loadFromStorage();
bindEvents();
loadVideoFromQueryString();
render();

function bindEvents() {
  dom.videoFileInput.addEventListener("change", handleVideoFileChange);
  dom.video.addEventListener("loadedmetadata", handleVideoMetadata);
  dom.video.addEventListener("durationchange", handleVideoMetadata);
  dom.video.addEventListener("timeupdate", renderVideoStatus);
  dom.video.addEventListener("seeked", renderVideoStatus);

  dom.teamANameInput.addEventListener("input", () => updateTeamName("teamA", dom.teamANameInput.value));
  dom.teamDNameInput.addEventListener("input", () => updateTeamName("teamD", dom.teamDNameInput.value));

  dom.togglePossessionButton.addEventListener("click", togglePossessionOwner);

  for (const button of [dom.teamAButton, dom.teamDButton]) {
    button.addEventListener("click", () => registerPossession(button.dataset.state));
  }

  dom.undoButton.addEventListener("click", undoLatestAnnotation);
  dom.clearAllButton.addEventListener("click", clearAllAnnotations);
  dom.exportJsonButton.addEventListener("click", exportJson);
  dom.jsonImportInput.addEventListener("change", importJson);
  dom.eventsTableBody.addEventListener("click", handleEventsTableClick);
  document.addEventListener("keydown", handleKeyboard);
}

function loadFromStorage() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    state.teamAName = saved.teamAName || DEFAULT_TEAM_A_NAME;
    state.teamDName = saved.teamDName || DEFAULT_TEAM_D_NAME;
    state.events = normalizeEvents(saved.events);
    state.videoFileName = saved.videoFileName || "";
    state.videoDurationSeconds = normalizeDuration(saved.videoDurationSeconds);
  } catch {
    state.teamAName = DEFAULT_TEAM_A_NAME;
    state.teamDName = DEFAULT_TEAM_D_NAME;
    state.events = [];
    state.videoFileName = "";
    state.videoDurationSeconds = 0;
  }
}

function saveToStorage() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      teamAName: state.teamAName,
      teamDName: state.teamDName,
      events: normalizeEvents(state.events),
      videoFileName: getExportVideoFileName(),
      videoDurationSeconds: getCalculationDuration(),
    }),
  );
}

function handleVideoFileChange(event) {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }

  if (state.videoObjectUrl) {
    URL.revokeObjectURL(state.videoObjectUrl);
  }

  state.videoObjectUrl = URL.createObjectURL(file);
  state.selectedVideoFileName = file.name;
  state.videoFileName = file.name;
  state.videoDurationSeconds = 0;
  dom.video.src = state.videoObjectUrl;
  dom.video.load();
  setStatus("");
  saveToStorage();
  render();
}

function handleVideoMetadata() {
  state.videoDurationSeconds = normalizeDuration(dom.video.duration);
  saveToStorage();
  render();
}

function loadVideoFromQueryString() {
  const videoPath = new URLSearchParams(window.location.search).get("video");
  if (!videoPath) {
    return;
  }

  const videoUrl = new URL(videoPath, window.location.href);
  if (videoUrl.origin !== window.location.origin) {
    return;
  }

  const fileName = decodeURIComponent(videoUrl.pathname.split("/").pop() || "video");
  state.selectedVideoFileName = fileName;
  state.videoFileName = fileName;
  dom.video.src = videoUrl.href;
  dom.video.load();
}

function updateTeamName(team, value) {
  const cleanValue = value.trim();
  if (team === "teamA") {
    state.teamAName = cleanValue || DEFAULT_TEAM_A_NAME;
  } else {
    state.teamDName = cleanValue || DEFAULT_TEAM_D_NAME;
  }
  saveToStorage();
  render();
}

function registerPossession(nextState) {
  if (!hasVideoLoaded()) {
    setStatus("Vælg en video før du annoterer.", true);
    return;
  }

  const timeSeconds = roundSeconds(dom.video.currentTime);
  const activeState = getStateAtTime(state.events, timeSeconds);

  if (activeState === nextState) {
    setStatus("Tilstanden er allerede aktiv ved dette tidspunkt.");
    return;
  }

  const event = {
    id: createEventId(),
    timeSeconds,
    state: nextState,
  };

  state.events = normalizeEvents([...state.events, event]);
  state.lastCreatedEventId = event.id;
  setStatus("");
  saveToStorage();
  render();
}

function undoLatestAnnotation() {
  if (state.events.length === 0) {
    setStatus("Der er ingen annotationer at fortryde.");
    return;
  }

  const normalized = normalizeEvents(state.events);
  const fallbackEvent = normalized[normalized.length - 1];
  const eventId = normalized.some((event) => event.id === state.lastCreatedEventId)
    ? state.lastCreatedEventId
    : fallbackEvent.id;

  state.events = normalized.filter((event) => event.id !== eventId);
  state.lastCreatedEventId = null;
  setStatus("");
  saveToStorage();
  render();
}

function clearAllAnnotations() {
  if (state.events.length === 0) {
    setStatus("Der er ingen annotationer at rydde.");
    return;
  }

  if (!window.confirm("Vil du rydde alle annotationer?")) {
    return;
  }

  state.events = [];
  state.lastCreatedEventId = null;
  setStatus("");
  saveToStorage();
  render();
}

function exportJson() {
  const payload = buildExportPayload({
    videoFileName: getExportVideoFileName(),
    videoDurationSeconds: getCalculationDuration(),
    teamAName: state.teamAName,
    teamDName: state.teamDName,
    events: state.events,
  });

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = createExportFileName(payload.videoFileName);
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setStatus("JSON eksport klar.");
}

async function importJson(event) {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }

  try {
    const text = await file.text();
    const parsed = JSON.parse(text);
    const validation = validateExportPayload(parsed);

    if (!validation.ok) {
      setStatus(validation.errors.join(" "), true);
      return;
    }

    const imported = validation.value;
    state.teamAName = imported.teamAName || DEFAULT_TEAM_A_NAME;
    state.teamDName = imported.teamDName || DEFAULT_TEAM_D_NAME;
    state.events = imported.events;
    state.videoFileName = imported.videoFileName || "";
    state.videoDurationSeconds = imported.videoDurationSeconds;
    state.lastCreatedEventId = null;
    setStatus("JSON importeret. Vælg videofilen manuelt igen.");
    saveToStorage();
    render();
  } catch (error) {
    setStatus(`Kunne ikke importere JSON: ${error.message}`, true);
  } finally {
    event.target.value = "";
  }
}

function handleEventsTableClick(event) {
  const seekButton = event.target.closest("[data-seek-seconds]");
  const deleteButton = event.target.closest("[data-delete-event-id]");

  if (seekButton) {
    if (!hasVideoLoaded()) {
      setStatus("Vælg en video før du hopper til tidspunktet.", true);
      return;
    }
    const time = Number(seekButton.dataset.seekSeconds);
    dom.video.currentTime = Math.max(0, Math.min(getCalculationDuration(), time));
    dom.video.focus();
    renderVideoStatus();
  }

  if (deleteButton) {
    state.events = normalizeEvents(state.events).filter((item) => item.id !== deleteButton.dataset.deleteEventId);
    state.lastCreatedEventId = null;
    setStatus("");
    saveToStorage();
    render();
  }
}

function handleKeyboard(event) {
  if (isTypingTarget(event.target)) {
    return;
  }

  if (event.code === "Space" || event.key === " ") {
    event.preventDefault();
    togglePossessionOwner();
    return;
  }

  const key = event.key.toLowerCase();

  if ((event.ctrlKey && key === "z") || event.key === "Backspace") {
    event.preventDefault();
    undoLatestAnnotation();
    return;
  }

  if (event.code === "ArrowLeft" || event.key === "ArrowLeft" || event.key === "Left") {
    event.preventDefault();
    seekRelative(-5);
    return;
  }

  if (event.code === "ArrowRight" || event.key === "ArrowRight" || event.key === "Right") {
    event.preventDefault();
    seekRelative(5);
  }
}

function togglePossessionOwner() {
  if (!hasVideoLoaded()) {
    setStatus("Vælg en video før du annoterer.", true);
    return;
  }

  const activeState = getStateAtTime(state.events, dom.video.currentTime);
  registerPossession(getNextPossessionState(activeState));
}

function seekRelative(deltaSeconds) {
  if (!hasVideoLoaded()) {
    return;
  }

  const duration = getCalculationDuration();
  dom.video.currentTime = Math.max(0, Math.min(duration, dom.video.currentTime + deltaSeconds));
  renderVideoStatus();
}

function render() {
  dom.teamANameInput.value = state.teamAName;
  dom.teamDNameInput.value = state.teamDName;
  dom.teamAButtonText.textContent = state.teamAName;
  dom.teamDButtonText.textContent = state.teamDName;
  dom.teamADurationLabel.textContent = state.teamAName;
  dom.teamDDurationLabel.textContent = state.teamDName;
  dom.teamAPercentageLabel.textContent = `${state.teamAName} %`;
  dom.teamDPercentageLabel.textContent = `${state.teamDName} %`;

  renderVideoFileName();
  renderVideoStatus();
  renderEventsTable();
  renderStatistics();
}

function renderVideoFileName() {
  if (state.selectedVideoFileName) {
    dom.videoFileName.textContent = state.selectedVideoFileName;
  } else if (state.videoFileName) {
    dom.videoFileName.textContent = `${state.videoFileName} (vælg fil igen)`;
  } else {
    dom.videoFileName.textContent = "Ingen video valgt";
  }
}

function renderVideoStatus() {
  const currentTime = hasVideoLoaded() ? dom.video.currentTime : 0;
  const duration = getCalculationDuration();
  const activeState = getStateAtTime(state.events, currentTime);
  const nextState = getNextPossessionState(activeState);

  dom.currentTimeText.value = formatTime(currentTime);
  dom.durationText.value = formatTime(duration);
  dom.currentPossessionBadge.textContent = getStateLabel(activeState, state.teamAName, state.teamDName);
  dom.currentPossessionBadge.className = `possession-badge ${activeState}`;
  dom.togglePossessionText.textContent = `Skift til ${getStateLabel(nextState, state.teamAName, state.teamDName)}`;

  for (const button of [dom.teamAButton, dom.teamDButton]) {
    button.classList.toggle("active", button.dataset.state === activeState);
  }
}

function renderEventsTable() {
  const events = normalizeEvents(state.events);
  dom.emptyEventsText.hidden = events.length > 0;
  dom.eventsTableBody.innerHTML = "";

  for (const event of events) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>
        <button type="button" class="time-button" data-seek-seconds="${event.timeSeconds}">
          ${formatTime(event.timeSeconds)}
        </button>
      </td>
      <td>
        <span class="state-pill ${event.state}">
          ${escapeHtml(getStateLabel(event.state, state.teamAName, state.teamDName))}
        </span>
      </td>
      <td>
        <button type="button" class="delete-button" data-delete-event-id="${escapeHtml(event.id)}">Slet</button>
      </td>
    `;
    dom.eventsTableBody.append(row);
  }
}

function renderStatistics() {
  const intervals = buildIntervals(state.events, getCalculationDuration());
  const statistics = buildStatistics(intervals);

  dom.teamADurationText.textContent = formatDuration(statistics.teamADurationSeconds);
  dom.teamDDurationText.textContent = formatDuration(statistics.teamDDurationSeconds);
  dom.teamAPercentageText.textContent = `${statistics.teamAPercentage.toFixed(1)}%`;
  dom.teamDPercentageText.textContent = `${statistics.teamDPercentage.toFixed(1)}%`;
}

function setStatus(message, isError = false) {
  dom.statusMessage.textContent = message;
  dom.statusMessage.classList.toggle("error", isError);
}

function hasVideoLoaded() {
  return Boolean(dom.video.currentSrc) && getCalculationDuration() > 0;
}

function getCalculationDuration() {
  return normalizeDuration(dom.video.duration) || normalizeDuration(state.videoDurationSeconds);
}

function getExportVideoFileName() {
  return state.selectedVideoFileName || state.videoFileName || "";
}

function createExportFileName(videoFileName) {
  const baseName = (videoFileName || "possession-annotations")
    .replace(/\.[^.]+$/, "")
    .replace(/[^a-z0-9_-]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();

  return `${baseName || "possession-annotations"}-possession.json`;
}

function createEventId() {
  if (crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `event-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function formatDuration(seconds) {
  return `${roundSeconds(seconds, 1).toFixed(1)} s`;
}

function isTypingTarget(target) {
  const tagName = target?.tagName?.toLowerCase();
  return tagName === "input" || tagName === "textarea" || target?.isContentEditable;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
