# Manuel validering af boldbesiddelse

Dette er et lille statisk MVP-værktøj til manuel annotation af boldbesiddelse i en lokal fodboldvideo.

## Start

Kør fra repoets rod:

```powershell
python -m http.server -d stats_validation/possesion 5501
```

Åbn derefter:

```text
http://127.0.0.1:5501
```

Videofilen bliver kun læst lokalt i browseren og uploades ikke.

## Kontroller

- `Space`: registrer skift til det modsatte hold.
- Venstre pil: hop 5 sekunder tilbage.
- Højre pil: hop 5 sekunder frem.
- `Ctrl+Z` eller `Backspace`: fortryd seneste annotation.

Der er kun to annoterbare tilstande: Hold A og Hold D.

## Tests

```powershell
node --test stats_validation/possesion/possession-core.test.mjs
```

## Filer

- `index.html`: statisk side og markup.
- `styles.css`: layout og visuel styling.
- `app.js`: UI, tastaturgenveje, localStorage, import og eksport.
- `possession-core.js`: datamodel, intervalberegning, statistik og importvalidering.
- `possession-core.test.mjs`: simple tests for intervaller, statistik og importvalidering.
