# Student Notes API - Day 2 drill (clean FastAPI project structure)

A small in-memory Notes API whose purpose is to practise the **project structure**
taught in *Day 2 - Clean FastAPI Project Structure for RAG APIs*: routes, schemas,
services and config in separate files, three ways data enters an API, request vs
response models, meaningful status codes, and a RAG-ready `/ask` endpoint that
is designed before any LLM is connected.

Every file is commented so it can be read top to bottom like a tutorial.
Start with `app/main.py`, then `routes.py`, `schemas.py`, `services.py`, `config.py`.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env         # optional: local settings (cp on macOS/Linux)
uvicorn app.main:app --reload
```

Interactive docs: http://127.0.0.1:8000/docs

## Folder structure (lecture slide 5)

```
student_notes_api_homework/
├── app/
│   ├── main.py        creates the FastAPI app, includes the routers, safe 500 handler
│   ├── routes.py      the endpoints - thin functions that call services (DRILL 1..9)
│   ├── schemas.py     Pydantic request / response models = the API contract
│   ├── services.py    business logic, the in-memory store, the dummy RAG
│   └── config.py      settings read from environment variables (via .env)
├── .env.example       every setting key with a placeholder value - committed
├── .env               your real values - git-ignored, optional
├── Student_Notes_API_Day2.pptx   presentation of this project
├── requirements.txt
└── README.md
```

## Settings and the `.env` file

`config.py` reads every setting with `os.getenv("KEY", fallback)`. `load_dotenv()` at the
top of that file copies `.env` into the environment first, so the chain is:

```
.env file  ->  load_dotenv()  ->  environment  ->  os.getenv()  ->  settings.<name>
```

- No `.env`? Nothing breaks - every key has a fallback.
- A variable set in the shell (`$env:APP_NAME = "..."`) wins over the same key in `.env`.
- `.env.example` is committed and lists the keys; `.env` is git-ignored and holds real values.
  On Day 3 the LLM API key goes in `.env` only - never in code, never in `.env.example`.

## How a request flows (lecture slide 4)

```
Client ──► main.py ──► routes.py ──► schemas.py ──► services.py ──► JSON response
            (app)     (which URL?)   (valid data?)   (do the work)   (response_model)
```

## Routes

Three `APIRouter`s (lecture slide 6): `meta`, `notes`, `rag`. Swagger groups them the same way.

| Method | Path                | Data enters via          | Success | Errors     | Service function          |
|--------|---------------------|--------------------------|---------|------------|---------------------------|
| GET    | `/`                 | -                        | 200     | -          | (reads `config.settings`) |
| GET    | `/notes`            | query `?limit=&search=`  | 200     | 422        | `get_all_notes`           |
| GET    | `/notes/{note_id}`  | path                     | 200     | 404, 422   | `get_note_by_id`          |
| POST   | `/notes`            | body `NoteCreate`        | **201** | 400, 422   | `create_note`             |
| PUT    | `/notes/{note_id}`  | path **+** body          | 200     | 400, 404, 422 | `update_note`          |
| DELETE | `/notes/{note_id}`  | path                     | 200     | 404, 422   | `delete_note`             |
| POST   | `/ask`              | body `QuestionRequest`   | 200     | 422        | `ask_question`            |
| GET    | `/debug/crash`      | -                        | -       | **500**    | (deliberate bug)          |
| POST   | `/reset`            | -                        | 200     | -          | `reset_notes`             |

## Status codes you will see (lecture slide 10)

| Code | Meaning          | Where it comes from in this project                                  |
|------|------------------|----------------------------------------------------------------------|
| 200  | OK               | default for a handler that returns normally                          |
| 201  | Created          | `status_code=201` on `POST /notes`                                   |
| 400  | Bad request      | `HTTPException(400)` in services - duplicate title (well-formed, illogical) |
| 404  | Not found        | `HTTPException(404)` in services - unknown `note_id`                 |
| 422  | Validation error | raised by FastAPI **before** the handler runs - wrong type / missing field |
| 500  | Server error     | the `@app.exception_handler(Exception)` in main.py - safe message, full traceback in the terminal |

## The drill

Open `app/routes.py` and work through **DRILL 1 .. 9** in Swagger. Each drill is a
comment block above its handler with the exact input, the expected status code, and
a few `TRY` variations. Predict the code before pressing Execute.

| Drill | Endpoint                  | What it practises                                   |
|-------|---------------------------|-----------------------------------------------------|
| 1     | `GET /`                   | health check; values come from `config.py`          |
| 2     | `GET /notes`              | **query parameters** + `Query()` validation (422)   |
| 3     | `GET /notes/{note_id}`    | **path parameter**; 404 vs 422                      |
| 4     | `POST /notes`             | **request body**; 201; 400 vs 422                   |
| 5     | `PUT /notes/{note_id}`    | path + body together; full replace; idempotent      |
| 6     | `DELETE /notes/{note_id}` | 404 on second delete; ids are never reused          |
| 7     | `POST /ask`               | the RAG contract: answer + sources + confidence     |
| 8     | `GET /debug/crash`        | unexpected error -> safe 500 (slide 11)             |
| 9     | `POST /reset`             | restore the seed notes                              |

## curl drill

```bash
# DRILL 1 - health
curl -i http://127.0.0.1:8000/

# DRILL 2 - query parameters
curl -i "http://127.0.0.1:8000/notes"
curl -i "http://127.0.0.1:8000/notes?limit=2"
curl -i "http://127.0.0.1:8000/notes?search=rag"
curl -i "http://127.0.0.1:8000/notes?limit=0"          # 422

# DRILL 3 - path parameter
curl -i http://127.0.0.1:8000/notes/1
curl -i http://127.0.0.1:8000/notes/999               # 404
curl -i http://127.0.0.1:8000/notes/abc               # 422

# DRILL 4 - request body -> 201; run it twice -> 400 (duplicate title)
curl -i -X POST http://127.0.0.1:8000/notes \
  -H "Content-Type: application/json" \
  -d '{"title":"Embeddings","content":"Vectors that capture meaning."}'

# DRILL 5 - path + body
curl -i -X PUT http://127.0.0.1:8000/notes/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"FastAPI (updated)","content":"FastAPI builds APIs with automatic docs."}'

# DRILL 6 - delete once (200), again (404)
curl -i -X DELETE http://127.0.0.1:8000/notes/1
curl -i -X DELETE http://127.0.0.1:8000/notes/1

# DRILL 7 - the RAG contract
curl -i -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is RAG?"}'
curl -i -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"How do I bake bread?"}'             # 200, empty sources

# DRILL 8 - safe 500
curl -i http://127.0.0.1:8000/debug/crash

# DRILL 9 - start over
curl -i -X POST http://127.0.0.1:8000/reset
```

On Windows PowerShell, `curl` is an alias for `Invoke-WebRequest`; use `curl.exe` instead.

## What `/ask` returns today, and what changes on Day 3

```json
{
  "answer": "From your note 'RAG': RAG stands for Retrieval Augmented Generation: ...",
  "sources": [{ "note_id": 2, "title": "RAG" }],
  "confidence": 1.0
}
```

`services.ask_question()` is written as the three RAG steps - **retrieve**, **generate**,
**respond**. Today step 1 is a keyword match over the notes and step 2 quotes the best
note. On Day 3 step 1 becomes embeddings + similarity search and step 2 becomes a prompt
+ LLM call. The route (`routes.py`) and the contract (`schemas.AnswerResponse`) stay
exactly as they are.

## Differences from the class version

- `config.py` added (the lecture's recommended structure has it; the class demo did not),
  with `.env` support through `python-dotenv`.
- Three routers instead of one, so Swagger groups `meta` / `notes` / `rag`.
- Every endpoint has a `response_model`; `GET /notes` returns `{count, notes}` instead of a bare list.
- `created_at` on notes shows that the response model carries fields the client never sends.
- Query / path validation with `Query(ge=1, le=...)` and `Path(ge=1)`.
- `/ask` returns `sources` and `confidence` (slide 13), and actually searches the notes.
- Two bugs fixed: ids were `len(notes) + 1` (reused after a delete), and `update_note`
  stored the function object instead of the updated dict. See the top of `services.py`.

## Slides

`Student_Notes_API_Day2.pptx` presents the project (12 slides, speaker notes included).
