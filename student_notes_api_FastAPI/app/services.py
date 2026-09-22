"""
services.py  -  WHERE THE REAL WORK LIVES
=========================================

LECTURE (slide 12):  "Routes should stay thin. Services should hold the logic."

Nothing in this file knows about URLs, query strings or Swagger.  Every
function takes plain Python values, does the work, and returns plain dicts /
lists.  The ONLY FastAPI import is HTTPException - that is how a service says
"this is a CONTROLLED error, answer 404 / 400" (lecture slide 11).

WHY THE SPLIT MATTERS
  - routes.py can be read in one glance: "which URL calls which function".
  - services can be tested WITHOUT starting a server:
        >>> from app import services
        >>> services.get_note_by_id(1)["title"]
        'FastAPI'
  - On Day 3 the RAG code (retrieval, prompt, LLM call) lands inside
    ask_question() below, and routes.py does not change at all.

THE "DATABASE"
  A plain Python list of dicts.  It lives in memory, so every restart of
  uvicorn (and every file save while --reload is on!) puts the seed notes
  back.  POST /reset does the same on demand.

TWO BUGS FROM THE CLASS VERSION, FIXED HERE
  1. ids were computed as len(notes) + 1.  Create 3 notes, delete note 2,
     create again -> the new note ALSO gets id 3.  Duplicate ids break GET /
     PUT / DELETE by id.  Fix: a counter (_next_id) that only ever goes up.
  2. update_note stored the FUNCTION instead of the dict:
         notes[index] = update_note      # <- the function object!
     It should have been updated_note.  Python happily stores anything in a
     list, so there was no error - just a corrupted note.  A response_model
     on the route would have caught it (422 on the way out); here it is
     simply written right.
"""

import re
from datetime import datetime, timezone

from fastapi import HTTPException

from .config import settings
from .schemas import NoteCreate

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

notes: list[dict] = []
_next_id: int = 1      # the SERVER hands out ids; the client never picks one


def _now() -> datetime:
    """UTC timestamps - one timezone for the whole API, no surprises."""
    return datetime.now(timezone.utc)


def _insert(title: str, content: str) -> dict:
    """Append a note with a fresh id.  Used by the seed AND by create_note."""
    global _next_id
    note = {
        "id": _next_id,
        "title": title,
        "content": content,
        "created_at": _now(),
    }
    notes.append(note)
    _next_id += 1
    return note


def _seed() -> None:
    """Put the store back to a known state (at import time and on POST /reset)."""
    global _next_id
    notes.clear()
    _next_id = 1
    _insert("FastAPI", "FastAPI is a Python framework for building backend APIs.")
    _insert("RAG", "RAG stands for Retrieval Augmented Generation: retrieve the "
                   "relevant text first, then let an LLM answer using it.")
    _insert("Pydantic", "Pydantic models validate request data and document the "
                        "API contract in Swagger.")


def _find_index(note_id: int) -> int | None:
    """Position of the note with this id in the list, or None."""
    for index, note in enumerate(notes):
        if note["id"] == note_id:
            return index
    return None


def _not_found(note_id: int) -> HTTPException:
    """
    The controlled-error recipe (slide 11): say WHAT happened and WHICH id.
    Building it in one place keeps every 404 in the API worded the same way.
    """
    return HTTPException(status_code=404, detail=f"Note {note_id} not found")


def _title_taken(title: str, exclude_id: int | None = None) -> bool:
    """Case-insensitive duplicate check.  exclude_id lets PUT keep its own title."""
    wanted = title.strip().lower()
    return any(
        n["title"].strip().lower() == wanted and n["id"] != exclude_id
        for n in notes
    )


_seed()      # runs once, when the module is first imported by routes.py


# ---------------------------------------------------------------------------
# Notes  -  one function per endpoint in routes.py
# ---------------------------------------------------------------------------

def get_all_notes(limit: int, search: str | None = None) -> list[dict]:
    """
    GET /notes  ->  filter (optional), then cut to `limit`.

    Both arguments arrive as QUERY parameters.  Validation (limit >= 1, etc.)
    already happened in routes.py, so this function trusts its inputs.
    """
    result = notes
    if search:
        needle = search.lower()
        result = [
            n for n in notes
            if needle in n["title"].lower() or needle in n["content"].lower()
        ]
    return result[:limit]


def get_note_by_id(note_id: int) -> dict:
    """GET /notes/{id}  ->  the note, or a controlled 404."""
    index = _find_index(note_id)
    if index is None:
        raise _not_found(note_id)
    return notes[index]


def create_note(data: NoteCreate) -> dict:
    """
    POST /notes  ->  the stored note (now WITH id and created_at).

    `data` is the validated NoteCreate model.  By the time we get here Pydantic
    has guaranteed that title and content exist and are non-empty strings.

    400 vs 422 (slide 10):
      A duplicate title is a perfectly well-formed request that makes no
      logical sense for this API  ->  400 Bad Request, raised by US.
      A missing title is a malformed request                ->  422, raised by
      FastAPI before this function is ever called.
      (Some APIs answer 409 Conflict for duplicates; both are defensible.)
    """
    if _title_taken(data.title):
        raise HTTPException(
            status_code=400,
            detail=f"A note titled '{data.title}' already exists",
        )
    return _insert(data.title, data.content)


def update_note(note_id: int, data: NoteCreate) -> dict:
    """
    PUT /notes/{id}  ->  the replaced note.

    PUT = "here is the COMPLETE new version".  title AND content are required
    (same NoteCreate model as POST), but id and created_at are preserved from
    the stored note - the client cannot change what the server owns.
    """
    index = _find_index(note_id)
    if index is None:
        raise _not_found(note_id)
    if _title_taken(data.title, exclude_id=note_id):
        raise HTTPException(
            status_code=400,
            detail=f"A note titled '{data.title}' already exists",
        )
    # {**old, "title": ..., "content": ...} copies the old dict and overrides two keys
    updated_note = {**notes[index], "title": data.title, "content": data.content}
    notes[index] = updated_note          # <- the dict, not the function (bug #2)
    return updated_note


def delete_note(note_id: int) -> dict:
    """DELETE /notes/{id}  ->  a confirmation dict (routes.py wraps it in DeleteResponse)."""
    index = _find_index(note_id)
    if index is None:
        raise _not_found(note_id)
    notes.pop(index)
    return {"message": "Note deleted successfully", "deleted_id": note_id}


def reset_notes() -> dict:
    """POST /reset  ->  seed data is back, ids start from 1 again."""
    _seed()
    return {"message": f"Store reset - {len(notes)} seed notes restored"}


# ---------------------------------------------------------------------------
# RAG  -  a dummy /ask that already has the RIGHT SHAPE  (slide 13)
# ---------------------------------------------------------------------------
# A real RAG answer is built in three steps:
#     1. RETRIEVE  - find the pieces of text most relevant to the question
#     2. GENERATE  - give those pieces + the question to an LLM
#     3. RESPOND   - return the answer together with its sources
# Below, step 1 is a toy keyword match over the notes and step 2 is faked by
# quoting the best note.  Step 3 is REAL: the dict returned here already
# matches AnswerResponse, so on Day 3 only the inside of this function changes.

# Words that carry no meaning for matching ("what is the ...").
_STOPWORDS = {
    "a", "an", "and", "are", "about", "can", "do", "does", "explain", "for",
    "how", "i", "in", "is", "it", "me", "of", "on", "or", "please", "tell",
    "the", "to", "what", "which", "why", "you",
}


def _keywords(text: str) -> set[str]:
    """'What is RAG?' -> {'rag'}   (lower-case, punctuation gone, stopwords gone)."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def ask_question(question: str) -> dict:
    """
    POST /ask  ->  {"answer": ..., "sources": [...], "confidence": ...}

    `question` is already validated (min 3 chars) by QuestionRequest.
    """
    # ---- 1. RETRIEVE ------------------------------------------------------
    # Score every note by how many question keywords appear in it.
    # Day 3 replaces this loop with embeddings + cosine similarity, which
    # also finds notes that use DIFFERENT words for the same idea.
    question_words = _keywords(question)
    scored: list[tuple[int, dict]] = []
    for note in notes:
        note_words = _keywords(note["title"] + " " + note["content"])
        hits = len(question_words & note_words)      # & = set intersection
        if hits:
            scored.append((hits, note))
    scored.sort(key=lambda pair: pair[0], reverse=True)   # best match first
    top_notes = [note for _, note in scored[: settings.max_sources]]

    # ---- 2. GENERATE (dummy) ----------------------------------------------
    # No LLM yet: quote the best note.  Day 3 builds a prompt from top_notes
    # and calls the model configured in config.py instead.
    if not top_notes:
        return {
            "answer": "I could not find anything about that in your notes yet.",
            "sources": [],
            "confidence": 0.0,
        }
    best = top_notes[0]
    answer = f"From your note '{best['title']}': {best['content']}"
    # share of the question's keywords found in the best note, 0.0 .. 1.0
    confidence = round(scored[0][0] / max(1, len(question_words)), 2)

    # ---- 3. RESPOND -------------------------------------------------------
    # This shape is the contract (schemas.AnswerResponse).  It does not change
    # when the dummy parts above are replaced.
    return {
        "answer": answer,
        "sources": [{"note_id": n["id"], "title": n["title"]} for n in top_notes],
        "confidence": min(confidence, 1.0),
    }
