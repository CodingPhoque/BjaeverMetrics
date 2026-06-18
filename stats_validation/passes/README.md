# Manuel validering af afleveringer

Statisk browserværktøj til manuel annotation af afleveringer og sammenligning med systemets pass-events.

## Start UI

Kør fra repoets rod:

```powershell
python -m http.server -d stats_validation/passes 5501
```

Åbn derefter:

```text
http://127.0.0.1:5501
```

Hvis possession-værktøjet allerede kører på `5501`, skal den server stoppes først.

## Manuel annotation

- Vælg aktivt hold.
- Kør videoen igennem én gang for det ene hold.
- `Space` registrerer en aflevering for det aktive hold.
- Venstre/højre pil hopper 5 sekunder.
- Eksporter manuel JSON.
- Gentag for det andet hold og importer begge manuelle JSON-filer i UI’et for merge.

## System pass-events

Udtræk systemets individuelle pass-events fra artifacts:

```powershell
python stats_validation/passes/extract_pass_events.py `
  --io data/interim/kamp_io.json `
  --tracking data/interim/kamp_tracking.json `
  --team-assignment data/interim/kamp_team_assignment.json `
  --output stats_validation/passes/kamp_system_passes.json
```

Scriptet bruger samme kriterier som `count_passes()`:

- samme hold før/efter
- forskellig `track_id`
- kontrollerede possession-intervaller
- gap under `max_pass_gap_seconds`

Pass-tidspunktet er sat til tidspunktet hvor modtageren får registreret kontrol.

## Tests

```powershell
node --test stats_validation/passes/pass-core.test.mjs
python -m py_compile stats_validation/passes/extract_pass_events.py
```
