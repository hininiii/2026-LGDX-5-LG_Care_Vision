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
- Render live `/api/v1/guides/options` guide check:
  - response includes guide option data
  - `tts_provider=google_cloud_tts`
  - `audio_url` string not present
  - `audio_url=null`
- Interpretation: live `/tts/generate` and cached mp3 playback are complete. Guide step automatic `audio_url` pre-generation is wired in code for `/api/v1/ar/plans` and `/api/v1/guides/options`, but not active on Render until `GOOGLE_TTS_PREGENERATE=1` is added.
- Required Render env for automatic guide-step `audio_url` generation:
  - `GOOGLE_TTS_ENABLED=1`
  - `GOOGLE_TTS_PREGENERATE=1`
  - Google service account credential env or file-based credential already configured for live TTS

### 2026-06-19 follow-up after env addition report

- User reported adding `GOOGLE_TTS_PREGENERATE=1` in Render.
- Re-check after the report:
  - `POST /api/v1/tts/generate` -> still works, cached mp3 `GET` -> `200 audio/mpeg`, `29568` bytes
  - `POST /api/v1/ar/plans` -> `tts_provider=google_cloud_tts`, `audio_url=null`, `audio_url_count=0`
  - `GET /api/v1/guides/options?...` -> `google_tts_provider_count=1`, `audio_url_count=0`, `audio_url_null_count=1`
- Re-check again after waiting 60 seconds:
  - `/api/v1/ar/plans` -> `audio_url=null`, `audio_url_count=0`
- Interpretation: the endpoint implementation remains live, but the running Render process still does not expose pre-generation behavior. Most likely the env change has not been saved into the active service deployment or the service has not been redeployed/restarted after adding the variable.

### 2026-06-19 final live verification after Render redeploy

- `/api/v1/ar/plans`
  - `step_count=7`
  - `first_tts_provider=google_cloud_tts`
  - `first_tts_language_code=en-IN`
  - `first_has_audio_url=true`
  - `audio_url_count=7`
  - first audio `GET` -> `200 audio/mpeg`, `23040` bytes
- `/api/v1/guides/options`
  - `manual_guides[0].display_steps[0].tts_provider=google_cloud_tts`
  - `manual_guides[0].display_steps[0].audio_url` present
  - guide option audio `GET` -> `200 audio/mpeg`, `42432` bytes
- Final status: task 7 live behavior is verified. Runtime cache is still temporary by design, so task 8 remains the Supabase Storage persistence migration.

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
- Standard uploads, content type, and upsert behavior: https://supabase.com/docs/guides/storage/uploads/standard-uploads

## Task 8 implementation

### Request / background

- User created the `tts-audio` Supabase Storage file bucket and added Render backend env:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_TTS_BUCKET=tts-audio`
  - `SUPABASE_TTS_STORAGE_ENABLED=1`
- Requirement: move generated Google TTS mp3 files from Render-only runtime cache to persistent Supabase Storage.

### Backend implementation

- Added Supabase Storage feature flag:
  - `SUPABASE_TTS_STORAGE_ENABLED=1`
- Added Storage path policy:
  - `tts/{language_code}/{voice_name}/{cache_key}.mp3`
- Added Storage public URL policy:
  - `https://{project_ref}.supabase.co/storage/v1/object/public/{bucket}/{object_path}`
- Added upload flow:
  - compute deterministic `cache_key`
  - check whether the public Storage object already exists
  - if present, return existing public URL with `storage_provider=supabase_storage`
  - if absent and local runtime cache exists, upload local mp3 bytes to Storage
  - if absent and local runtime cache does not exist, generate Google TTS mp3, write runtime cache, upload bytes to Storage
  - if Supabase lookup/upload fails, fall back to existing Render runtime cache URL
- Extended `/api/v1/tts/generate` response:
  - `storage_provider`
  - `object_path`

### Verification

```powershell
cd backend
python -m pytest tests/test_google_tts_mvp.py -q
```

Result: `8 passed`.

```powershell
cd backend
python -m compileall app
```

Result: compile succeeded.

### Failure / correction notes

- TestClient runs modified the SQLite mock DB file; it was restored and excluded from the commit.
- Supabase service role key was not written to source files or docs.
- The implementation keeps runtime cache fallback so presentation flow still works if Storage lookup/upload fails.

### Remaining live verification

- Completed after Render redeploy.

### 2026-06-19 final live verification after Render deploy

- OpenAPI:
  - `TTSGenerateResponse.storage_provider` present
  - `TTSGenerateResponse.object_path` present
- `POST /api/v1/tts/generate`
  - `storage_provider=supabase_storage`
  - `object_path=tts/en-IN/en-IN-Standard-A/{cache_key}.mp3`
  - `audio_url=https://ozedogtiiwxnqsnvpwby.supabase.co/storage/v1/object/public/tts-audio/...`
  - `GET audio_url` -> `200 audio/mpeg`, `34944` bytes
- `POST /api/v1/ar/plans`
  - `step_count=7`
  - `audio_url_count=7`
  - first step `audio_url` is Supabase Storage public URL
  - first step audio `GET` -> `200 audio/mpeg`, `23040` bytes
- `GET /api/v1/guides/options?...`
  - `manual_guides[0].display_steps[0].audio_url` is Supabase Storage public URL
  - guide option audio `GET` -> `200 audio/mpeg`, `42432` bytes
- Final status: Task 8 Supabase Storage persistence is implemented and live verified.
