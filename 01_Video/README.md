# 01_Video

Two voiced videos, narrated in the presenter's cloned voice (Chatterbox TTS, local):

| File | Length | What it is |
|---|---|---|
| `project_submission_full.mp4` | about 15:00, 1080p | The full film: Acts I–VII (problem, architecture, ingestion and PII, retrieval, dual gates and cascade, the live in-app demo, measured results). |
| `project_app_demo.mp4` | about 3:09, 1080p | The live dashboard demo alone, with narration aligned to each on-screen scenario and a caption in scenario 6 showing the real PII redaction output. |

Dead air longer than 1.5 s is cut from both (audio and video cut together, so narration stays in sync with the slides).

## How they are built

1. `scripts/generate_voiceover.py` synthesizes each narration segment from `hyperframes_film/DIRECTOR_SCRIPT.md` (needs the Chatterbox environment and a voice sample, which are not in the repo).
2. `scripts/retime_film.py` sets each act's length to its narration and patches `hyperframes_film/index.html`.
3. Render the film: `cd hyperframes_film && npx hyperframes@0.8.222 render -o renders/film_retimed.mp4`.
4. `scripts/assemble_voiceover.py` mixes the audio, adds the PII caption, and calls `scripts/tighten_silence.py` to write the two files above.

The silent source recording is `hyperframes_film/assets/in_app_demo.mp4` (produced by `scripts/record_in_app_demo.js`; scenario timings in `in_app_demo.marks.json`). It was recorded with the first configuration (similarity floor 0.65); the report's current numbers are in Section 7.10.

The narration is synthetic speech of the presenter's own voice, generated from a recorded sample.
