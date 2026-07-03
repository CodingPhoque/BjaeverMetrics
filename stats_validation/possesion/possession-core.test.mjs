import assert from "node:assert/strict";
import test from "node:test";

import {
  buildExportPayload,
  buildIntervals,
  buildStatistics,
  getNextPossessionState,
  getStateAtTime,
  normalizeEvents,
  validateExportPayload,
} from "./possession-core.js";

test("buildIntervals starts with teamA before the first annotation", () => {
  const intervals = buildIntervals(
    [
      { id: "d", timeSeconds: 10, state: "teamD" },
      { id: "a", timeSeconds: 25, state: "teamA" },
    ],
    50,
  );

  assert.deepEqual(intervals, [
    { startSeconds: 0, endSeconds: 10, durationSeconds: 10, state: "teamA" },
    { startSeconds: 10, endSeconds: 25, durationSeconds: 15, state: "teamD" },
    { startSeconds: 25, endSeconds: 50, durationSeconds: 25, state: "teamA" },
  ]);
});

test("buildIntervals sorts events by time before calculating intervals", () => {
  const intervals = buildIntervals(
    [
      { id: "late", timeSeconds: 20, state: "teamD" },
      { id: "early", timeSeconds: 5, state: "teamA" },
    ],
    30,
  );

  assert.deepEqual(intervals, [
    { startSeconds: 0, endSeconds: 5, durationSeconds: 5, state: "teamA" },
    { startSeconds: 5, endSeconds: 20, durationSeconds: 15, state: "teamA" },
    { startSeconds: 20, endSeconds: 30, durationSeconds: 10, state: "teamD" },
  ]);
});

test("empty events make the full video teamA", () => {
  assert.deepEqual(buildIntervals([], 12), [
    { startSeconds: 0, endSeconds: 12, durationSeconds: 12, state: "teamA" },
  ]);
});

test("buildStatistics calculates team percentages from team durations", () => {
  const statistics = buildStatistics([
    { startSeconds: 0, endSeconds: 15, durationSeconds: 15, state: "teamA" },
    { startSeconds: 15, endSeconds: 20, durationSeconds: 5, state: "teamD" },
  ]);

  assert.equal(statistics.teamADurationSeconds, 15);
  assert.equal(statistics.teamDDurationSeconds, 5);
  assert.equal(statistics.teamAPercentage, 75);
  assert.equal(statistics.teamDPercentage, 25);
});

test("buildStatistics avoids division by zero", () => {
  const statistics = buildStatistics([]);

  assert.equal(statistics.teamAPercentage, 0);
  assert.equal(statistics.teamDPercentage, 0);
});

test("getStateAtTime returns teamA before the first event and active state later", () => {
  const events = [
    { id: "d", timeSeconds: 4, state: "teamD" },
    { id: "a", timeSeconds: 9, state: "teamA" },
  ];

  assert.equal(getStateAtTime(events, 2), "teamA");
  assert.equal(getStateAtTime(events, 4), "teamD");
  assert.equal(getStateAtTime(events, 12), "teamA");
});

test("getNextPossessionState toggles between the two teams", () => {
  assert.equal(getNextPossessionState("teamA"), "teamD");
  assert.equal(getNextPossessionState("teamD"), "teamA");
});

test("normalizeEvents drops legacy unknown events", () => {
  assert.deepEqual(
    normalizeEvents([
      { id: "a", timeSeconds: 1, state: "teamA" },
      { id: "x", timeSeconds: 2, state: "unknown" },
    ]),
    [{ id: "a", timeSeconds: 1, state: "teamA" }],
  );
});

test("export payload contains recalculated intervals and statistics", () => {
  const payload = buildExportPayload({
    videoFileName: "kamp.mp4",
    videoDurationSeconds: 20,
    teamAName: "Bjaever",
    teamDName: "Gaester",
    events: [{ id: "d", timeSeconds: 5, state: "teamD" }],
  });

  assert.equal(payload.version, 1);
  assert.equal(payload.videoFileName, "kamp.mp4");
  assert.deepEqual(payload.intervals, [
    { startSeconds: 0, endSeconds: 5, durationSeconds: 5, state: "teamA" },
    { startSeconds: 5, endSeconds: 20, durationSeconds: 15, state: "teamD" },
  ]);
  assert.equal(payload.statistics.teamDPercentage, 75);
});

test("validateExportPayload reports invalid states clearly", () => {
  const validation = validateExportPayload({
    version: 1,
    videoDurationSeconds: 10,
    teamAName: "A",
    teamDName: "D",
    events: [{ id: "bad", timeSeconds: 5, state: "unknown" }],
  });

  assert.equal(validation.ok, false);
  assert.match(validation.errors.join(" "), /teamA eller teamD/);
});
