export const POSSESSION_STATES = Object.freeze(["teamA", "teamD"]);

export const DEFAULT_TEAM_A_NAME = "Hold A";
export const DEFAULT_TEAM_D_NAME = "Hold D";

export function isPossessionState(value) {
  return POSSESSION_STATES.includes(value);
}

export function roundSeconds(value, decimals = 3) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return 0;
  }
  const factor = 10 ** decimals;
  return Math.round(number * factor) / factor;
}

export function normalizeDuration(videoDurationSeconds) {
  const duration = Number(videoDurationSeconds);
  if (!Number.isFinite(duration) || duration <= 0) {
    return 0;
  }
  return roundSeconds(duration);
}

export function normalizeEvents(events) {
  if (!Array.isArray(events)) {
    return [];
  }

  return events
    .filter((event) => {
      const timeSeconds = Number(event?.timeSeconds);
      return isPossessionState(event?.state) && Number.isFinite(timeSeconds) && timeSeconds >= 0;
    })
    .map((event) => ({
      id: String(event.id || `event-${roundSeconds(event.timeSeconds)}`),
      timeSeconds: roundSeconds(event.timeSeconds),
      state: event.state,
    }))
    .sort((left, right) => left.timeSeconds - right.timeSeconds);
}

export function getStateLabel(state, teamAName = DEFAULT_TEAM_A_NAME, teamDName = DEFAULT_TEAM_D_NAME) {
  if (state === "teamA") {
    return teamAName || DEFAULT_TEAM_A_NAME;
  }
  if (state === "teamD") {
    return teamDName || DEFAULT_TEAM_D_NAME;
  }
  return teamAName || DEFAULT_TEAM_A_NAME;
}

export function getNextPossessionState(state) {
  return state === "teamA" ? "teamD" : "teamA";
}

export function formatTime(totalSeconds) {
  const seconds = Math.max(0, Number.isFinite(Number(totalSeconds)) ? Number(totalSeconds) : 0);
  const minutes = Math.floor(seconds / 60);
  const rest = seconds - minutes * 60;
  return `${String(minutes).padStart(2, "0")}:${rest.toFixed(1).padStart(4, "0")}`;
}

export function getStateAtTime(events, timeSeconds) {
  const time = Math.max(0, Number.isFinite(Number(timeSeconds)) ? Number(timeSeconds) : 0);
  let state = "teamA";

  for (const event of normalizeEvents(events)) {
    if (event.timeSeconds <= time) {
      state = event.state;
    } else {
      break;
    }
  }

  return state;
}

export function buildIntervals(events, videoDurationSeconds) {
  const duration = normalizeDuration(videoDurationSeconds);
  if (duration === 0) {
    return [];
  }

  const validEvents = normalizeEvents(events).filter((event) => event.timeSeconds <= duration);
  const intervals = [];
  let cursor = 0;
  let currentState = "teamA";

  for (const event of validEvents) {
    const eventTime = Math.max(0, Math.min(duration, event.timeSeconds));
    if (eventTime > cursor) {
      intervals.push(makeInterval(cursor, eventTime, currentState));
    }
    currentState = event.state;
    cursor = eventTime;
  }

  if (cursor < duration) {
    intervals.push(makeInterval(cursor, duration, currentState));
  }

  return intervals;
}

export function buildStatistics(intervals) {
  const totals = {
    teamADurationSeconds: 0,
    teamDDurationSeconds: 0,
    teamAPercentage: 0,
    teamDPercentage: 0,
  };

  for (const interval of Array.isArray(intervals) ? intervals : []) {
    const duration = Number(interval?.durationSeconds);
    if (!Number.isFinite(duration) || duration <= 0) {
      continue;
    }

    if (interval.state === "teamA") {
      totals.teamADurationSeconds += duration;
    } else if (interval.state === "teamD") {
      totals.teamDDurationSeconds += duration;
    }
  }

  totals.teamADurationSeconds = roundSeconds(totals.teamADurationSeconds);
  totals.teamDDurationSeconds = roundSeconds(totals.teamDDurationSeconds);

  const knownDuration = totals.teamADurationSeconds + totals.teamDDurationSeconds;
  if (knownDuration > 0) {
    totals.teamAPercentage = roundSeconds((totals.teamADurationSeconds / knownDuration) * 100, 2);
    totals.teamDPercentage = roundSeconds((totals.teamDDurationSeconds / knownDuration) * 100, 2);
  }

  return totals;
}

export function buildExportPayload({
  videoFileName,
  videoDurationSeconds,
  teamAName,
  teamDName,
  events,
}) {
  const duration = normalizeDuration(videoDurationSeconds);
  const normalizedEvents = normalizeEvents(events);
  const intervals = buildIntervals(normalizedEvents, duration);
  const statistics = buildStatistics(intervals);

  return {
    version: 1,
    videoFileName: String(videoFileName || ""),
    videoDurationSeconds: duration,
    teamAName: String(teamAName || DEFAULT_TEAM_A_NAME),
    teamDName: String(teamDName || DEFAULT_TEAM_D_NAME),
    events: normalizedEvents,
    intervals,
    statistics,
  };
}

export function validateExportPayload(payload) {
  const errors = [];

  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { ok: false, errors: ["JSON-filen skal indeholde et objekt."], value: null };
  }

  if (payload.version !== 1) {
    errors.push("Kun version 1 af annotationsformatet understøttes.");
  }

  if (!Array.isArray(payload.events)) {
    errors.push("Feltet events skal være en liste.");
  }

  const duration = normalizeDuration(payload.videoDurationSeconds);
  const events = [];
  const seenIds = new Set();

  for (const [index, event] of (Array.isArray(payload.events) ? payload.events : []).entries()) {
    const label = `events[${index}]`;
    const timeSeconds = Number(event?.timeSeconds);
    const id = event?.id;

    if (!id || typeof id !== "string") {
      errors.push(`${label}.id skal være en tekst.`);
    }
    if (id && seenIds.has(id)) {
      errors.push(`${label}.id er brugt mere end én gang.`);
    }
    if (id) {
      seenIds.add(id);
    }
    if (!Number.isFinite(timeSeconds) || timeSeconds < 0) {
      errors.push(`${label}.timeSeconds skal være et tal på 0 eller derover.`);
    }
    if (duration > 0 && Number.isFinite(timeSeconds) && timeSeconds > duration) {
      errors.push(`${label}.timeSeconds ligger efter videoens varighed.`);
    }
    if (!isPossessionState(event?.state)) {
      errors.push(`${label}.state skal være teamA eller teamD.`);
    }

    if (
      id &&
      typeof id === "string" &&
      Number.isFinite(timeSeconds) &&
      timeSeconds >= 0 &&
      isPossessionState(event?.state)
    ) {
      events.push({ id, timeSeconds: roundSeconds(timeSeconds), state: event.state });
    }
  }

  if (errors.length > 0) {
    return { ok: false, errors, value: null };
  }

  return {
    ok: true,
    errors: [],
    value: buildExportPayload({
      videoFileName: payload.videoFileName,
      videoDurationSeconds: duration,
      teamAName: payload.teamAName || DEFAULT_TEAM_A_NAME,
      teamDName: payload.teamDName || DEFAULT_TEAM_D_NAME,
      events,
    }),
  };
}

function makeInterval(startSeconds, endSeconds, state) {
  const start = roundSeconds(startSeconds);
  const end = roundSeconds(endSeconds);
  return {
    startSeconds: start,
    endSeconds: end,
    durationSeconds: roundSeconds(end - start),
    state,
  };
}
