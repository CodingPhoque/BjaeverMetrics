import assert from "node:assert/strict";
import test from "node:test";

import {
  buildManualExportPayload,
  comparePassEvents,
  countPassesByTeam,
  normalizePassEvents,
  validateManualPayload,
  validateSystemPayload,
} from "./pass-core.js";

test("normalizePassEvents keeps valid team events sorted by time", () => {
  assert.deepEqual(
    normalizePassEvents([
      { id: "d", timeSeconds: 10, team: "teamD" },
      { id: "bad", timeSeconds: 11, team: "unknown" },
      { id: "a", timeSeconds: 4, team: "teamA" },
    ]),
    [
      { id: "a", timeSeconds: 4, team: "teamA" },
      { id: "d", timeSeconds: 10, team: "teamD" },
    ],
  );
});

test("countPassesByTeam counts each team and total", () => {
  assert.deepEqual(
    countPassesByTeam([
      { id: "a1", timeSeconds: 1, team: "teamA" },
      { id: "a2", timeSeconds: 2, team: "teamA" },
      { id: "d1", timeSeconds: 3, team: "teamD" },
    ]),
    { teamACount: 2, teamDCount: 1, totalCount: 3 },
  );
});

test("manual export stores annotated team and statistics", () => {
  const payload = buildManualExportPayload({
    videoFileName: "kamp.mp4",
    videoDurationSeconds: 90,
    teamAName: "A",
    teamDName: "D",
    annotatedTeam: "teamA",
    events: [{ id: "a1", timeSeconds: 1, team: "teamA" }],
  });

  assert.equal(payload.type, "manual_pass_annotations");
  assert.equal(payload.annotatedTeam, "teamA");
  assert.deepEqual(payload.statistics, { teamACount: 1, teamDCount: 0, totalCount: 1 });
});

test("comparePassEvents matches nearest system event by team within tolerance", () => {
  const comparison = comparePassEvents(
    [
      { id: "m1", timeSeconds: 10, team: "teamA" },
      { id: "m2", timeSeconds: 20, team: "teamD" },
      { id: "m3", timeSeconds: 30, team: "teamA" },
    ],
    [
      { id: "s1", timeSeconds: 10.8, team: "teamA" },
      { id: "s2", timeSeconds: 19, team: "teamD" },
      { id: "s3", timeSeconds: 50, team: "teamA" },
    ],
    2,
  );

  assert.equal(comparison.matches.length, 2);
  assert.equal(comparison.manualOnly.length, 1);
  assert.equal(comparison.systemOnly.length, 1);
  assert.equal(comparison.differences.total, 0);
  assert.deepEqual(comparison.matchCounts, {
    teamACount: 1,
    teamDCount: 1,
    totalCount: 2,
  });
  assert.deepEqual(comparison.manualOnlyCounts, {
    teamACount: 1,
    teamDCount: 0,
    totalCount: 1,
  });
  assert.deepEqual(comparison.systemOnlyCounts, {
    teamACount: 1,
    teamDCount: 0,
    totalCount: 1,
  });
  assert.deepEqual(comparison.differences, {
    teamA: 0,
    teamD: 0,
    total: 0,
  });
});

test("manual payload validation rejects wrong type", () => {
  const validation = validateManualPayload({ version: 1, type: "system_pass_events", events: [] });
  assert.equal(validation.ok, false);
});

test("system payload validation accepts event details", () => {
  const validation = validateSystemPayload({
    version: 1,
    type: "system_pass_events",
    events: [
      {
        id: "sys-1",
        timeSeconds: 12,
        team: "teamA",
        frame: 360,
        systemTeam: "home",
        fromTrackId: 7,
        toTrackId: 12,
        gapFrames: 0,
        segmentName: "first_half",
      },
    ],
  });

  assert.equal(validation.ok, true);
  assert.equal(validation.value.events[0].frame, 360);
});
