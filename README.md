# AI Video Studio — Backend (Idea 2: Motion Comic)

Django + DRF backend for the character/scene/voice database and episode
pipeline. This scaffold is fully working end-to-end **except the actual
paid generation calls**, which are left as clearly marked stubs — see
"What's left to wire up" below. Everything up to that point costs
nothing and needs no GPU: it's just database and API logic, and it's
already tested.

## What's here

- **`voices`** — preset voice records (narrator + per-character), backed
  by whichever TTS provider you plug in later.
- **`characters`** — character definitions, each with a set of
  `CharacterReferenceImage`s that anchor visual consistency across panels.
- **`scenes`** — recurring locations, same reference-image pattern as
  characters.
- **`episodes`** — the core: `Episode` → `Panel`s (one per story beat) →
  `DialogueLine`s, plus `GenerationJob` records that track every unit of
  billable work (one per panel image, one per narration/dialogue audio
  line) so a long generation run can be resumed instead of restarted.

## Running it locally

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # optional, for /admin/
python manage.py runserver
```

Uses SQLite by default — zero setup. Swap to PostgreSQL later by
uncommenting the `DATABASES` block in `videostudio/settings.py` (see the
comment there).

Visit `/admin/` for a quick way to create voices/characters/scenes by
hand while testing, or use the API directly.

## The pipeline, as implemented

1. `POST /api/characters/` — create a character (name, description, voice)
2. `POST /api/characters/{id}/reference-images/` — upload reference images
3. `POST /api/scenes/` — same pattern for locations
4. `POST /api/voices/` — register narrator/character voice presets
5. `POST /api/episodes/` — create an episode (title + storyline)
6. `POST /api/episodes/{id}/submit-script/` — submit the structured script:
   a list of panels, each with a scene, characters, `action_description`
   (narration text), and `dialogue_lines` (character + text)
7. `POST /api/episodes/{id}/generate/` — queues one `GenerationJob` per
   panel image and per narration/dialogue audio line
8. `GET /api/episodes/{id}/status/` — job counts by status
9. `GET /api/episodes/{id}/jobs/` — the full job list

This whole flow is tested and confirmed working (see the smoke test run
during scaffolding) with **zero GPU cost** — it's pure Django/DRF logic.

## What's left to wire up (this is where cost enters)

Two functions remain in `episodes/services.py`, clearly marked `NotImplementedError`:

- **`run_image_job(job)`** — call the image provider (FLUX.2 recommended)
  using `job.panel.scene.reference_images` and each character's
  `reference_images` as identity anchors. Save the result to
  `job.panel.generated_image`.
- **`run_voice_job(job)`** — call the TTS provider (Chatterbox
  recommended) with the narrator voice for panel narration, or the
  character's assigned voice for a dialogue line. Save to
  `narration_audio` / `DialogueLine.audio`.

**`assemble_episode(episode)` is already implemented and tested** —
see `episodes/ffmpeg_utils.py`. It takes whatever ends up in
`generated_image` / `narration_audio` / `DialogueLine.audio` (real
provider output or otherwise), applies a pan/zoom to each panel, burns
in `"Character: line"` captions on dialogue segments, muxes in audio,
and concatenates everything into `episode.final_video`. This was
verified end-to-end using placeholder images/audio standing in for real
generation output - zero GPU/API cost to build and confirm it works.

Recommended order (matches the earlier build plan): get one image
generation working standalone first, then one voice generation
standalone, then wire both into `run_image_job`/`run_voice_job` - once
real assets land in those model fields, assembly already works with no
further changes needed.

## Note on scale

Before generating anything at real volume, remember the pilot-first
approach: run one short scene through the full pipeline first (few
panels, few lines) to confirm quality and cost before queuing a full
episode. See the project notes on why 15-minute episodes need per-panel
generation, not per-second, to stay cheap.
