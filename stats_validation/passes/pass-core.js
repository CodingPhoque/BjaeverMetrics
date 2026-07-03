export const PASS_TEAMS = Object.freeze(["teamA", "teamD"]);
export const DEFAULT_TEAM_A_NAME = "Hold A";
export const DEFAULT_TEAM_D_NAME = "Hold D";
export const DEFAULT_TOLERANCE_SECONDS = 2;

export function isPassTeam(value) {
  return PASS_TEAMS.includes(value);
}

export function roundNumber(value, decimals = 3) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return 0;
  }
  const factor = 10 ** decimals;
  return Math.round(number * factor) / factor;
}

export function normalizeDuration(value) {
  const duration = Number(value);
  if (!Number.isFinite(duration) || duration <= 0) {
    return 0;
  }
  return roundNumber(duration);
}

export function normalizePassEvents(events) {
  if (!Array.isArray(events)) {
    return [];
  }

  return events
    .filter((event) => {
      const timeSeconds = Number(event?.timeSeconds);
      return isPassTeam(event?.team) && Number.isFinite(timeSeconds) && timeSeconds >= 0;
    })
    .map((event) => ({
      ...event,
      id: String(event.id || `pass-${roundNumber(event.timeSeconds)}-${event.team}`),
      timeSeconds: roundNumber(event.timeSeconds),
      team: event.team,
    }))
    .sort((left, right) => left.timeSeconds - right.timeSeconds);
}

export function getTeamLabel(team, teamAName = DEFAULT_TEAM_A_NAME, teamDName = DEFAULT_TEAM_D_NAME) {
  return team === "teamD" ? teamDName || DEFAULT_TEAM_D_NAME : teamAName || DEFAULT_TEAM_A_NAME;
}

export function formatTime(totalSeconds) {
  const seconds = Math.max(0, Number.isFinite(Number(totalSeconds)) ? Number(totalSeconds) : 0);
  const minutes = Math.floor(seconds / 60);
  const rest = seconds - minutes * 60;
  return `${String(minutes).padStart(2, "0")}:${rest.toFixed(1).padStart(4, "0")}`;
}

export function countPassesByTeam(events) {
  const counts = { teamACount: 0, teamDCount: 0, totalCount: 0 };
  for (const event of normalizePassEvents(events)) {
    if (event.team === "teamA") {
      counts.teamACount += 1;
    } else if (event.team === "teamD") {
      counts.teamDCount += 1;
    }
  }
  counts.totalCount = counts.teamACount + counts.teamDCount;
  return counts;
}

export function buildManualExportPayload({
  videoFileName,
  videoDurationSeconds,
  teamAName,
  teamDName,
  annotatedTeam,
  events,
}) {
  const normalizedEvents = normalizePassEvents(events);
  return {
    version: 1,
    type: "manual_pass_annotations",
    videoFileName: String(videoFileName || ""),
    videoDurationSeconds: normalizeDuration(videoDurationSeconds),
    teamAName: String(teamAName || DEFAULT_TEAM_A_NAME),
    teamDName: String(teamDName || DEFAULT_TEAM_D_NAME),
    annotatedTeam: isPassTeam(annotatedTeam) ? annotatedTeam : "",
    events: normalizedEvents,
    statistics: countPassesByTeam(normalizedEvents),
  };
}

export function validateManualPayload(payload) {
  const errors = validateCommonPayload(payload, "manual_pass_annotations");
  if (errors.length > 0) {
    return { ok: false, errors, value: null };
  }

  return {
    ok: true,
    errors: [],
    value: buildManualExportPayload({
      videoFileName: payload.videoFileName,
      videoDurationSeconds: payload.videoDurationSeconds,
      teamAName: payload.teamAName,
      teamDName: payload.teamDName,
      annotatedTeam: payload.annotatedTeam,
      events: payload.events,
    }),
  };
}

export function validateSystemPayload(payload) {
  const errors = validateCommonPayload(payload, "system_pass_events");
  if (errors.length > 0) {
    return { ok: false, errors, value: null };
  }

  const events = normalizePassEvents(payload.events).map((event) => ({
    id: event.id,
    timeSeconds: event.timeSeconds,
    team: event.team,
    frame: Number.isFinite(Number(event.frame)) ? Number(event.frame) : null,
    systemTeam: event.systemTeam || "",
    fromTrackId: Number.isFinite(Number(event.fromTrackId)) ? Number(event.fromTrackId) : null,
    toTrackId: Number.isFinite(Number(event.toTrackId)) ? Number(event.toTrackId) : null,
    gapFrames: Number.isFinite(Number(event.gapFrames)) ? Number(event.gapFrames) : null,
    segmentName: event.segmentName || null,
  }));

  return {
    ok: true,
    errors: [],
    value: {
      version: 1,
      type: "system_pass_events",
      videoFileName: String(payload.videoFileName || ""),
      videoDurationSeconds: normalizeDuration(payload.videoDurationSeconds),
      videoId: String(payload.videoId || ""),
      teamAName: String(payload.teamAName || DEFAULT_TEAM_A_NAME),
      teamDName: String(payload.teamDName || DEFAULT_TEAM_D_NAME),
      events,
      statistics: countPassesByTeam(events),
      generatedFrom: payload.generatedFrom || {},
      parameters: payload.parameters || {},
    },
  };
}

export function comparePassEvents(manualEvents, systemEvents, toleranceSeconds = DEFAULT_TOLERANCE_SECONDS) {
  const tolerance = Math.max(0, Number(toleranceSeconds) || 0);
  const manual = normalizePassEvents(manualEvents);
  const system = normalizePassEvents(systemEvents);
  const usedSystemIds = new Set();
  const matches = [];
  const manualOnly = [];

  for (const manualEvent of manual) {
    const candidates = system
      .filter((systemEvent) => {
        return (
          systemEvent.team === manualEvent.team &&
          !usedSystemIds.has(systemEvent.id) &&
          Math.abs(systemEvent.timeSeconds - manualEvent.timeSeconds) <= tolerance
        );
      })
      .sort((left, right) => {
        return (
          Math.abs(left.timeSeconds - manualEvent.timeSeconds) -
          Math.abs(right.timeSeconds - manualEvent.timeSeconds)
        );
      });

    const match = candidates[0];
    if (!match) {
      manualOnly.push(manualEvent);
      continue;
    }

    usedSystemIds.add(match.id);
    matches.push({
      manualEvent,
      systemEvent: match,
      deltaSeconds: roundNumber(match.timeSeconds - manualEvent.timeSeconds),
    });
  }

  const systemOnly = system.filter((event) => !usedSystemIds.has(event.id));
  const manualCounts = countPassesByTeam(manual);
  const systemCounts = countPassesByTeam(system);
  const matchCounts = countPassesByTeam(matches.map((match) => match.manualEvent));
  const manualOnlyCounts = countPassesByTeam(manualOnly);
  const systemOnlyCounts = countPassesByTeam(systemOnly);

  return {
    toleranceSeconds: tolerance,
    manualCounts,
    systemCounts,
    differences: {
      teamA: systemCounts.teamACount - manualCounts.teamACount,
      teamD: systemCounts.teamDCount - manualCounts.teamDCount,
      total: systemCounts.totalCount - manualCounts.totalCount,
    },
    matches,
    manualOnly,
    systemOnly,
    matchCounts,
    manualOnlyCounts,
    systemOnlyCounts,
  };
}

function validateCommonPayload(payload, expectedType) {
  const errors = [];
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return ["JSON-filen skal indeholde et objekt."];
  }
  if (payload.version !== 1) {
    errors.push("Kun version 1 understøttes.");
  }
  if (payload.type !== expectedType) {
    errors.push(`Filen skal have type ${expectedType}.`);
  }
  if (!Array.isArray(payload.events)) {
    errors.push("Feltet events skal være en liste.");
  }

  for (const [index, event] of (Array.isArray(payload.events) ? payload.events : []).entries()) {
    const label = `events[${index}]`;
    const timeSeconds = Number(event?.timeSeconds);
    if (!event?.id || typeof event.id !== "string") {
      errors.push(`${label}.id skal være tekst.`);
    }
    if (!Number.isFinite(timeSeconds) || timeSeconds < 0) {
      errors.push(`${label}.timeSeconds skal være et tal på 0 eller derover.`);
    }
    if (!isPassTeam(event?.team)) {
      errors.push(`${label}.team skal være teamA eller teamD.`);
    }
  }

  return errors;
}
