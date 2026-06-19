# 2026-06-18 Google TTS push log

## Request

- Push the Google TTS code changes to the GitHub `taehee` branch.
- Preserve the newly received ARGuide frontend voice UI instead of adding a duplicate simplified button.

## Changes

- Backend
  - Added `POST /api/v1/tts/synthesize`.
  - Added Google Cloud Text-to-Speech MP3 synthesis with local runtime cache.
  - Added `TTSSynthesizeRequest`.
  - Added TTS metadata to AR guide/manual display steps:
    - `tts_enabled`
    - `tts_text`
    - `tts_language_code`
    - `tts_provider`
    - `audio_url`
  - Added `google-cloud-texttospeech` dependency.

- Frontend
  - Synced the newer ARGuide UI that already had voice on/off/replay behavior.
  - Connected ARGuide audio playback to:
    - `audio_url` when present
    - Google TTS endpoint when `tts_provider=google_cloud_tts`
    - browser Web Speech fallback when Google TTS playback fails
  - Propagated backend `display_steps` TTS metadata through Chat and SelfCare AR guide entry points.
  - Added the missing `LG______-1.gif` asset used by the synced frontend.

- Verification / safety
  - Updated ARGuide smoke script to match the newer ARGuide contracts.
  - Ignored backend/frontend runtime log folders.
  - Confirmed no service-account JSON/private key content was committed.

## Verification

Commands run after rebase onto `origin/taehee`:

```powershell
cd backend
python -m pytest tests/test_google_tts_mvp.py -q
```

Result: `3 passed`.

```powershell
cd frontend
npm run build
```

Result: build succeeded. Vite reported only the existing large chunk warning.

```powershell
cd frontend
npm run smoke:ar-guide
```

Result: `ok=true`, `static_contracts=25`, `step_target_contracts=12`.

```powershell
cd backend
# GOOGLE_TTS_ENABLED=1 and GOOGLE_APPLICATION_CREDENTIALS set locally
POST /api/v1/tts/synthesize
```

Result: `200`, `audio/mpeg`, `29568` bytes, MP3 header `fff384`.

## Failure / correction notes

- Initial attempt added a small standalone voice button after inspecting the older GitHub checkout ARGuide file.
- The local project frontend already had a richer voice UI, so the simplified button approach was discarded.
- The frontend was re-synced from the newer local ARGuide implementation and verified with build/smoke.
- The first build failed because `LG______-1.gif` was missing from the GitHub checkout; the asset was added.
- Rebase onto `origin/taehee` produced an ARGuide conflict with the latest helper UI commit; resolved using the newer local ARGuide implementation and re-ran verification.

## Commit

- Branch: `taehee`
- Commit: `e9737af Add Google TTS for AR guide steps`

## Remaining work

- Render must redeploy this pushed commit.
- Render environment variables still need to be configured for live Google TTS:
  - `GOOGLE_TTS_ENABLED=1`
  - `GOOGLE_TTS_VOICE_NAME=en-IN-Standard-A`
  - `GOOGLE_TTS_CREDENTIALS_JSON`
- Supabase Storage mp3 persistence is not implemented yet; current backend uses runtime cache.
