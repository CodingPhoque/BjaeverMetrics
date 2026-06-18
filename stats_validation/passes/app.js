import {
  DEFAULT_TEAM_A_NAME,
  DEFAULT_TEAM_D_NAME,
  DEFAULT_TOLERANCE_SECONDS,
  buildManualExportPayload,
  comparePassEvents,
  countPassesByTeam,
  formatTime,
  getTeamLabel,
  isPassTeam,
  normalizeDuration,
  normalizePassEvents,
  roundNumber,
  validateManualPayload,
  validateSystemPayload,
} from "./pass-core.js";

const STORAGE_KEY = "bjaevermetrics-pass-validation-v1";

const dom = {
  video: document.querySelector("#matchVideo"),
  videoFileInput: document.querySelector("#videoFileInput"),
  videoFileName: document.querySelector("#videoFileName"),
  currentTimeText: document.querySelector("#currentTimeText"),
  durationText: document.querySelector("#durationText"),
  teamANameInput: document.querySelector("#teamANameInput"),
  teamDNameInput: document.querySelector("#teamDNameInput"),
  teamAButton: document.querySelector("#teamAButton"),
  teamDButton: document.querySelector("#teamDButton"),
  teamAButtonText: document.querySelector("#teamAButtonText"),
  teamDButtonText: document.querySelector("#teamDButtonText"),
  activeTeamBadge: document.querySelector("#activeTeamBadge"),
  registerPassButton: document.querySelector("#registerPassButton"),
  registerPassText: document.querySelector("#registerPassText"),
  eventsTableBody: document.querySelector("#eventsTableBody"),
  emptyEventsText: document.querySelector("#emptyEventsText"),
  undoButton: document.querySelector("#undoButton"),
  clearAllButton: document.querySelector("#clearAllButton"),
  manualImportInput: document.querySelector("#manualImportInput"),
  systemImportInput: document.querySelector("#systemImportInput"),
  exportManualButton: document.querySelector("#exportManualButton"),
  statusMessage: document.querySelector("#statusMessage"),
  manualTeamALabel: document.querySelector("#manualTeamALabel"),
  manualTeamDLabel: document.querySelector("#manualTeamDLabel"),
  systemTeamALabel: document.querySelector("#systemTeamALabel"),
  systemTeamDLabel: document.querySelector("#systemTeamDLabel"),
  manualTeamAText: document.querySelector("#manualTeamAText"),
  manualTeamDText: document.querySelector("#manualTeamDText"),
  systemTeamAText: document.querySelector("#systemTeamAText"),
  systemTeamDText: document.querySelector("#systemTeamDText"),
  toleranceInput: document.querySelector("#toleranceInput"),
  matchedText: document.querySelector("#matchedText"),
  manualOnlyText: document.querySelector("#manualOnlyText"),
  systemOnlyText: document.querySelector("#systemOnlyText"),
  totalDiffText: document.querySelector("#totalDiffText"),
};

const state = {
  teamAName: DEFAULT_TEAM_A_NAME,
  teamDName: DEFAULT_TEAM_D_NAME,
  activeTeam: "teamA",
  manualEvents: [],
  systemEvents: [],
  videoFileName: "",
  selectedVideoFileName: "",
  videoDurationSeconds: 0,
  toleranceSeconds: DEFAULT_TOLERANCE_SECONDS,
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
  dom.teamAButton.addEventListener("click", () => setActiveTeam("teamA"));
  dom.teamDButton.addEventListener("click", () => setActiveTeam("teamD"));
  dom.registerPassButton.addEventListener("click", registerManualPass);
  dom.undoButton.addEventListener("click", undoLatestManualPass);
  dom.clearAllButton.addEventListener("click", clearManualPasses);
  dom.exportManualButton.addEventListener("click", exportManualJson);
  dom.manualImportInput.addEventListener("change", importManualJson);
  dom.systemImportInput.addEventListener("change", importSystemJson);
  dom.eventsTableBody.addEventListener("click", handleEventsTableClick);
  dom.toleranceInput.addEventListener("input", updateTolerance);
  document.addEventListener("keydown", handleKeyboard);
}

function loadFromStorage() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    state.teamAName = saved.teamAName || DEFAULT_TEAM_A_NAME;
    state.teamDName = saved.teamDName || DEFAULT_TEAM_D_NAME;
    state.activeTeam = isPassTeam(saved.activeTeam) ? saved.activeTeam : "teamA";
    state.manualEvents = normalizePassEvents(saved.manualEvents);
    state.systemEvents = normalizePassEvents(saved.systemEvents);
    state.videoFileName = saved.videoFileName || "";
    state.videoDurationSeconds = normalizeDuration(saved.videoDurationSeconds);
    state.toleranceSeconds = Number.isFinite(Number(saved.toleranceSeconds))
      ? Math.max(0, Number(saved.toleranceSeconds))
      : DEFAULT_TOLERANCE_SECONDS;
  } catch {
    state.teamAName = DEFAULT_TEAM_A_NAME;
    state.teamDName = DEFAULT_TEAM_D_NAME;
    state.activeTeam = "teamA";
    state.manualEvents = [];
    state.systemEvents = [];
    state.videoFileName = "";
    state.videoDurationSeconds = 0;
    state.toleranceSeconds = DEFAULT_TOLERANCE_SECONDS;
  }
}

function saveToStorage() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      teamAName: state.teamAName,
      teamDName: state.teamDName,
      activeTeam: state.activeTeam,
      manualEvents: normalizePassEvents(state.manualEvents),
      systemEvents: normalizePassEvents(state.systemEvents),
      videoFileName: getExportVideoFileName(),
      videoDurationSeconds: getCalculationDuration(),
      toleranceSeconds: state.toleranceSeconds,
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

function setActiveTeam(team) {
  if (!isPassTeam(team)) {
    return;
  }
  state.activeTeam = team;
  setStatus("");
  saveToStorage();
  render();
}

function registerManualPass() {
  if (!hasVideoLoaded()) {
    setStatus("Vælg en video før du annoterer.", true);
    return;
  }

  const event = {
    id: createEventId(),
    timeSeconds: roundNumber(dom.video.currentTime),
    team: state.activeTeam,
  };

  state.manualEvents = normalizePassEvents([...state.manualEvents, event]);
  state.lastCreatedEventId = event.id;
  setStatus(`Aflevering registreret for ${getTeamLabel(state.activeTeam, state.teamAName, state.teamDName)}.`);
  saveToStorage();
  render();
}

function undoLatestManualPass() {
  if (state.manualEvents.length === 0) {
    setStatus("Der er ingen manuelle afleveringer at fortryde.");
    return;
  }

  const normalized = normalizePassEvents(state.manualEvents);
  const fallbackEvent = normalized[normalized.length - 1];
  const eventId = normalized.some((event) => event.id === state.lastCreatedEventId)
    ? state.lastCreatedEventId
    : fallbackEvent.id;

  state.manualEvents = normalized.filter((event) => event.id !== eventId);
  state.lastCreatedEventId = null;
  setStatus("");
  saveToStorage();
  render();
}

function clearManualPasses() {
  if (state.manualEvents.length === 0) {
    setStatus("Der er ingen manuelle afleveringer at rydde.");
    return;
  }

  if (!window.confirm("Vil du rydde alle manuelle afleveringer?")) {
    return;
  }

  state.manualEvents = [];
  state.lastCreatedEventId = null;
  setStatus("");
  saveToStorage();
  render();
}

function exportManualJson() {
  const payload = buildManualExportPayload({
    videoFileName: getExportVideoFileName(),
    videoDurationSeconds: getCalculationDuration(),
    teamAName: state.teamAName,
    teamDName: state.teamDName,
    annotatedTeam: state.activeTeam,
    events: state.manualEvents,
  });

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = createExportFileName(payload.videoFileName, "manual-passes");
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setStatus("Manuel JSON eksport klar.");
}

async function importManualJson(event) {
  const files = Array.from(event.target.files || []);
  if (files.length === 0) {
    return;
  }

  const importedEvents = [];
  let importedCount = 0;

  for (const file of files) {
    try {
      const text = await file.text();
      const validation = validateManualPayload(JSON.parse(text));
      if (!validation.ok) {
        setStatus(`${file.name}: ${validation.errors.join(" ")}`, true);
        continue;
      }
      const payload = validation.value;
      state.teamAName = payload.teamAName || state.teamAName;
      state.teamDName = payload.teamDName || state.teamDName;
      state.videoFileName = payload.videoFileName || state.videoFileName;
      state.videoDurationSeconds = payload.videoDurationSeconds || state.videoDurationSeconds;
      importedEvents.push(...payload.events);
      importedCount += payload.events.length;
    } catch (error) {
      setStatus(`${file.name}: ${error.message}`, true);
    }
  }

  if (importedEvents.length > 0) {
    state.manualEvents = mergeEvents(state.manualEvents, importedEvents);
    setStatus(`Importerede ${importedCount} manuelle afleveringer.`);
    saveToStorage();
    render();
  }

  event.target.value = "";
}

async function importSystemJson(event) {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }

  try {
    const text = await file.text();
    const validation = validateSystemPayload(JSON.parse(text));
    if (!validation.ok) {
      setStatus(validation.errors.join(" "), true);
      return;
    }

    const payload = validation.value;
    state.systemEvents = payload.events;
    state.teamAName = payload.teamAName || state.teamAName;
    state.teamDName = payload.teamDName || state.teamDName;
    state.videoFileName = payload.videoFileName || state.videoFileName;
    state.videoDurationSeconds = payload.videoDurationSeconds || state.videoDurationSeconds;
    setStatus(`Importerede ${payload.events.length} system-afleveringer.`);
    saveToStorage();
    render();
  } catch (error) {
    setStatus(`Kunne ikke importere system JSON: ${error.message}`, true);
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
    state.manualEvents = normalizePassEvents(state.manualEvents).filter((item) => item.id !== deleteButton.dataset.deleteEventId);
    state.lastCreatedEventId = null;
    setStatus("");
    saveToStorage();
    render();
  }
}

function updateTolerance() {
  state.toleranceSeconds = Math.max(0, Number(dom.toleranceInput.value) || 0);
  saveToStorage();
  renderComparison();
}

function handleKeyboard(event) {
  if (isTypingTarget(event.target)) {
    return;
  }

  if (event.code === "Space" || event.key === " ") {
    event.preventDefault();
    registerManualPass();
    return;
  }

  const key = event.key.toLowerCase();

  if ((event.ctrlKey && key === "z") || event.key === "Backspace") {
    event.preventDefault();
    undoLatestManualPass();
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
  dom.manualTeamALabel.textContent = `Manuel ${state.teamAName}`;
  dom.manualTeamDLabel.textContent = `Manuel ${state.teamDName}`;
  dom.systemTeamALabel.textContent = `System ${state.teamAName}`;
  dom.systemTeamDLabel.textContent = `System ${state.teamDName}`;
  dom.toleranceInput.value = state.toleranceSeconds;

  renderVideoFileName();
  renderVideoStatus();
  renderEventsTable();
  renderSummary();
  renderComparison();
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
  const label = getTeamLabel(state.activeTeam, state.teamAName, state.teamDName);

  dom.currentTimeText.value = formatTime(currentTime);
  dom.durationText.value = formatTime(duration);
  dom.activeTeamBadge.textContent = label;
  dom.activeTeamBadge.className = `team-badge ${state.activeTeam}`;
  dom.registerPassText.textContent = `Registrer aflevering for ${label}`;

  for (const button of [dom.teamAButton, dom.teamDButton]) {
    button.classList.toggle("active", button.dataset.team === state.activeTeam);
  }
}

function renderEventsTable() {
  const events = normalizePassEvents(state.manualEvents);
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
        <span class="team-pill ${event.team}">
          ${escapeHtml(getTeamLabel(event.team, state.teamAName, state.teamDName))}
        </span>
      </td>
      <td>
        <button type="button" class="delete-button" data-delete-event-id="${escapeHtml(event.id)}">Slet</button>
      </td>
    `;
    dom.eventsTableBody.append(row);
  }
}

function renderSummary() {
  const manualCounts = countPassesByTeam(state.manualEvents);
  const systemCounts = countPassesByTeam(state.systemEvents);
  dom.manualTeamAText.textContent = manualCounts.teamACount;
  dom.manualTeamDText.textContent = manualCounts.teamDCount;
  dom.systemTeamAText.textContent = systemCounts.teamACount;
  dom.systemTeamDText.textContent = systemCounts.teamDCount;
}

function renderComparison() {
  const comparison = comparePassEvents(state.manualEvents, state.systemEvents, state.toleranceSeconds);
  dom.matchedText.textContent = comparison.matches.length;
  dom.manualOnlyText.textContent = comparison.manualOnly.length;
  dom.systemOnlyText.textContent = comparison.systemOnly.length;
  dom.totalDiffText.textContent = signedNumber(comparison.differences.total);
}

function setStatus(message, isError = false) {
  dom.statusMessage.textContent = message;
  dom.statusMessage.classList.toggle("error", isError);
}

function mergeEvents(existingEvents, importedEvents) {
  const byKey = new Map();
  for (const event of normalizePassEvents([...existingEvents, ...importedEvents])) {
    byKey.set(`${event.team}:${event.timeSeconds}:${event.id}`, event);
  }
  return normalizePassEvents([...byKey.values()]);
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

function createExportFileName(videoFileName, suffix) {
  const baseName = (videoFileName || "pass-annotations")
    .replace(/\.[^.]+$/, "")
    .replace(/[^a-z0-9_-]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();
  return `${baseName || "pass-annotations"}-${suffix}.json`;
}

function createEventId() {
  if (crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `pass-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function signedNumber(value) {
  const number = Number(value) || 0;
  return number > 0 ? `+${number}` : String(number);
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
