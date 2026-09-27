# SatQuery AI — PS 26167

Agentic vision-language assistant for remote-sensing imagery. This README
reflects the **actual, verified state** of this scaffold — not aspirational
status. Every checkmark below was run and observed, not assumed.

## 1. What's actually implemented and verified (Phase A)

| Piece | Status | Verified by |
|---|---|---|
| FastAPI backend (`/api/health`, `/api/upload`, `/api/query`) | ✅ Working | 9/9 pytest tests pass + live curl round-trip |
| Real image validation (format, dimensions, band count via Pillow) | ✅ Working | Rejects corrupt bytes, empty files, unsupported formats |
| Rule-based agentic router (query → task classification) | ✅ Working | Routes VQA / captioning / grounding / change / cross-modal correctly in tests |
| Modular tool registry (5 specialist tool slots) | ✅ Working (as honest stubs) | Each tool raises a clear `ModelNotIntegratedError` instead of faking output |
| Execution trace (auditable per-step log) | ✅ Working | Returned in every `/api/query` response |
| React + TypeScript + Tailwind frontend | ✅ Working | `tsc --noEmit` clean, `npm run build` succeeds, dev server serves on :5173 |
| Frontend ↔ backend integration (typed API client) | ✅ Working | Manually verified request/response shapes match |
| Docker / docker-compose config | ⚠️ **Written, NOT tested** | No Docker daemon available in this build environment — see §5 |

## 2. What is intentionally NOT implemented yet

This is the honest, load-bearing part of the README. Per the project's
"never fake success" rule, none of the following are stubbed with fake
output — they fail loudly with `ModelNotIntegratedError` / `status:
"blocked"` in the API response instead:

- **No real specialist models are wired in** (GeoChat, RemoteCLIP, BIT, or
  any VQA/captioning/grounding/change-detection/fusion model). This build
  environment has no GPU and no network access to model hosts like
  `huggingface.co` (only pypi/npm/github package registries are reachable).
  See `backend/app/tools/registry.py` for the exact integration point per
  tool — each `run()` method documents what to implement.
- **No PostgreSQL/PostGIS** — file metadata is in an in-memory dict
  (`app/api/routes.py: _FILES`), which resets on restart. Swap-in point is
  documented in `docker-compose.yml` (commented `db` service) and
  `.env.example` (`DATABASE_URL`).
- **No S3/MinIO object storage** — uploaded files are written to local disk
  (`backend/storage/uploads/`). Swap-in point documented in
  `docker-compose.yml` (commented `minio` service).
- **No real GeoTIFF/CRS metadata parsing** — `has_geo_metadata` detection
  reads raw TIFF tags via Pillow as a best-effort check; real georeferencing
  (CRS, geotransform) needs `rasterio`/GDAL, not installed here to keep this
  scaffold lean. Listed in `requirements.txt` as a documented next step.
- **No true SAR-vs-optical modality detection from pixels.** This cannot be
  done reliably without real sensor metadata or a trained classifier, so the
  system asks the user to state modality in their query rather than
  guessing (see `app/services/router.py: determine_input_configuration`).
- **No pixel-level evidence generation** (bounding boxes, masks, change
  overlays) — this depends on the specialist models above.
- **No LLM-based orchestration** — task classification is a rule-based
  keyword+config classifier (`app/services/router.py: classify_task`),
  documented as the Phase-A stand-in for the LangGraph-based orchestrator
  called for in the target architecture. The function signature is
  designed so an LLM router can replace it without touching the rest of
  the pipeline.
- **No auth, jobs/results/executions persistence endpoints** beyond
  `/api/upload` and `/api/query` — `GET /api/jobs/{id}` etc. from the
  target API surface are not yet built.

## 3. Architecture (as built)

```
Client (React/TS/Tailwind, :5173)
    │  multipart upload / JSON query
    ▼
FastAPI backend (:8000)
    │
    ├─ app/services/validation.py   — real format/dimension checks (Pillow)
    ├─ app/services/router.py       — task classification (rule-based)
    ├─ app/tools/registry.py        — modular specialist-tool adapters (stubs)
    └─ app/api/routes.py            — /health /upload /query, in-memory store
```

Every `/api/query` call returns a full `execution_trace` array — this is
what makes the agentic workflow visible/auditable, per the UI demo
requirement in the target spec.

## 4. Folder structure

```
satquery-ai/
├── backend/
│   ├── app/
│   │   ├── api/routes.py
│   │   ├── models/schemas.py
│   │   ├── services/{validation,router}.py
│   │   ├── tools/registry.py
│   │   └── main.py
│   ├── tests/test_api.py
│   ├── storage/uploads/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/client.ts
│   │   ├── components/{UploadArea,ExecutionTrace}.tsx
│   │   └── App.tsx
│   ├── Dockerfile
│   ├── nginx.conf
│   └── .env.example
├── docker-compose.yml
└── README.md   ← you are here
```

## 5. Running it locally (verified commands)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
export PYTHONPATH=.
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs for interactive API docs
```

**Backend tests** (9 passing):
```bash
cd backend
export PYTHONPATH=.
pytest tests/ -v
```

**Frontend:**
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
# → http://localhost:5173
```

**Frontend production build:**
```bash
cd frontend
npm run build   # verified: succeeds, outputs dist/
```

**Docker** — ⚠️ config is written but **could not be tested** in this
build environment (no Docker daemon available here). Before you trust it:
```bash
docker compose up --build
# then verify:
curl http://localhost:8000/api/health
open http://localhost:5173
```
If this fails, the most likely issues are: nginx.conf path assumptions, or
the frontend build-arg `VITE_API_URL` needing to be `http://backend:8000/api`
instead of `localhost` when frontend and backend are both in containers
talking to each other (as opposed to the browser talking to the backend
directly, which is what the current default assumes — this is a genuine
design decision you should confirm: **do you want the browser to call the
backend directly, or should nginx proxy `/api` to the backend container?**
The current config uses the direct-call approach, which is simpler but
requires the backend port to be exposed to wherever the browser runs.)

## 6. Environment constraints encountered (documented per project rule 31)

These are real blockers hit during this build, not assumptions:

1. **No GPU** in this build environment → no specialist model can actually
   run here. All five tools are honest stubs.
2. **No network access to `huggingface.co`** (or general internet) from
   this sandbox — only pypi.org, npm, and github package registries are
   reachable. Model checkpoints must be downloaded in an environment with
   that access, or with the checkpoint files supplied directly.
3. **No Docker daemon** in this build environment — `docker-compose.yml`
   and both Dockerfiles are written to the target spec but unverified.
4. **This sandbox does not persist background processes across separate
   tool invocations** — servers were started and tested within single
   command blocks. This has no bearing on a real dev machine or CI, but is
   why you won't see a "still running" server if you check back later in
   this conversation; re-run the commands above.

## 7. Recommended next steps

1. **Confirm target compute for model integration** — you'll need a
   GPU-enabled environment (local or cloud) with access to model hosts to
   wire in GeoChat/RemoteCLIP/BIT per `backend/app/tools/registry.py`.
2. **Move this into Claude Code** (or another persistent dev environment)
   for the actual model-integration and Docker-verification work — this
   chat's sandbox resets between sessions and has no GPU, so it's suited to
   scaffolding and logic (what's been done here) but not to the
   model-integration and deployment-verification phases (§17–23 of the
   original spec).
3. Decide the frontend↔backend networking model for Docker (see §5 above)
   before treating `docker-compose up` as verified.
4. Add `rasterio` + system GDAL for real GeoTIFF metadata once you're in an
   environment where `apt-get install gdal-bin libgdal-dev` is available.

## 8. Known limitations (summary)

No real AI inference yet; no persistence beyond process memory/local disk;
no auth; Docker unverified; SAR/optical modality is user-declared, not
detected. All of the above are the honest current boundary of this
scaffold, not omissions from documentation.
