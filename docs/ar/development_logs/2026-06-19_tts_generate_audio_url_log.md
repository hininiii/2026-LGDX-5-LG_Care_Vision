# 2026-06-19 TTS generate/audio_url log

## Request

- Implement task 7:
  - Add `/tts/generate`.
  - Add cached mp3 serving URL.
  - Add `audio_url` to guide step responses when pre-generation is enabled.
- Explain how task 8 should store generated mp3 files in Supabase Storage.

## Implemented task 7

### Backend endpoints

- `POST /api/v1/tts/generate`
  - Input: same request body as `/api/v1/tts/synthesize`.
  - Output:
    - `audio_url`
    - `cache_key`
    - `provider`
    - `cached`
    - `content_type`

- `GET /api/v1/tts/audio/{cache_key}.mp3`
  - Serves a previously generated runtime-cache mp3 file as `audio/mpeg`.
  - Rejects invalid cache keys.
  - Returns `404` if the cache file does not exist.

### Backend service logic

- Added cache-key helpers in `backend/app/tts_service.py`.
- The cache key is based on:
  - language code
  - selected voice
  - speaking rate
  - normalized TTS text
- Existing `/tts/synthesize` remains available for direct mp3 byte responses.
- New `/tts/generate` returns a reusable runtime URL:

```json
{
  "audio_url": "/api/v1/tts/audio/{cache_key}.mp3",
  "cache_key": "{cache_key}",
  "provider": "google_cloud_tts",
  "cached": true,
  "content_type": "audio/mpeg"
}
```

### Guide step `audio_url`

- Added `GOOGLE_TTS_PREGENERATE`.
- If `GOOGLE_TTS_ENABLED=1` and `GOOGLE_TTS_PREGENERATE=1`, guide step generation tries to pre-generate mp3 and attach:
  - `audio_url`
  - `tts_cache_key`
- If pre-generation is disabled, `audio_url` remains `null`.
- If pre-generation fails, guide generation does not fail; it falls back to `audio_url=null`.

### Frontend compatibility

- ARGuide already plays `audio_url` first, then falls back to `/tts/synthesize`, then Web Speech.
- Added relative URL resolution so `/api/v1/tts/audio/...mp3` uses the backend API origin in Vite/local deployments.

## Verification

```powershell
cd backend
python -m pytest tests/test_google_tts_mvp.py -q
```

Result: `6 passed`.

```powershell
cd frontend
npm run build
```

Result: build succeeded. Vite reported only the existing large chunk warning.

```powershell
cd frontend
npm run smoke:ar-guide
```

Result: `ok=true`.

Manual local TestClient check with real Google credentials:

- `POST /api/v1/tts/generate` -> `200`
- returned `audio_url=/api/v1/tts/audio/de6cdd2dea7d36377e16891b479947a81e6cb2cc3a7eac1187194a4e5a53923a.mp3`
- `GET` returned `200`, `audio/mpeg`, `29568` bytes, MP3 header `fff384`.
- 2026-06-19 re-run:
  - `python -m pytest tests/test_google_tts_mvp.py -q` -> `6 passed`
  - `npm run smoke:ar-guide` -> `ok=true`, `static_contracts=27`, `step_target_contracts=12`
  - `npm run build` -> success, with existing Vite large chunk warning
  - Real Google credential local TestClient smoke -> `POST /api/v1/tts/generate` `200`, cached mp3 `GET` `200 audio/mpeg`, `29568` bytes

## Failure / correction notes

- The SQLite mock DB file changed during TestClient runs; it was excluded from the commit.
- No Google service-account JSON or private key content was committed.
- Runtime cache is not persistent across Render restarts/redeploys; this is acceptable for task 7 MVP, but task 8 should move mp3 files to Supabase Storage.

## Live Render status

- GitHub branch: `taehee`
- Implemented commits:
  - `1368bf2 Add TTS audio URL generation`
  - `4f7e60b Document TTS generate deploy status`
- Render live health check: `GET /api/v1/health` -> `200`
- Render live OpenAPI re-check:
  - `/api/v1/tts/synthesize` -> present
  - `/api/v1/tts/generate` -> present
  - `/api/v1/tts/audio/{cache_key}.mp3` -> present
- Render live `/tts/generate` smoke:
  - `POST /api/v1/tts/generate` -> provider `google_cloud_tts`, `cache_key` length `64`, `audio_url` prefix `/api/v1/tts/audio/`
  - `GET {audio_url}` -> `200`, `audio/mpeg`, `29568` bytes
- Render live `/api/v1/ar/plans` guide step check:
  - `tts_provider=google_cloud_tts`
  - `tts_language_code=en-IN`
  - `audio_url=null`
- Interpretation: live `/tts/generate` and cached mp3 playback are complete. Guide step automatic `audio_url` pre-generation is wired in code, but not active on Render until `GOOGLE_TTS_PREGENERATE=1` is added.
- Required Render env for automatic guide-step `audio_url` generation:
  - `GOOGLE_TTS_ENABLED=1`
  - `GOOGLE_TTS_PREGENERATE=1`
  - Google service account credential env or file-based credential already configured for live TTS

## Task 8 Supabase Storage direction

Task 8 should replace Render runtime cache URLs with persistent Supabase Storage URLs.

Recommended MVP path:

1. Create a Supabase Storage bucket, for example `tts-audio`.
2. Keep generated mp3 object names deterministic:

```text
tts/{language_code}/{voice_name}/{cache_key}.mp3
```

3. Backend generates Google TTS mp3 once.
4. Backend uploads the bytes to Supabase Storage with:
   - `content-type: audio/mpeg`
   - long cache control, for example `cacheControl=31536000`
   - `upsert=false` for immutable hash-keyed objects
5. Backend stores or returns the Storage URL as `audio_url`.
6. If the object already exists, skip Google TTS and return the existing URL.

Storage access choice:

- Public bucket:
  - easiest for demo and static mp3 playback
  - frontend can directly play public URL
  - suitable because generated guide audio is not personally sensitive

- Private bucket + signed URL:
  - better if guide audio may contain user-specific text
  - backend creates time-limited signed URL
  - frontend plays signed URL

Official Supabase docs checked:

- Storage overview: https://supabase.com/docs/guides/storage
- Public/private bucket serving: https://supabase.com/docs/guides/storage/serving/downloads
- Upload API: https://supabase.com/docs/reference/javascript/storage-from-upload
