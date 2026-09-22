"""
schemas.py  -  THE API CONTRACT (what goes in, what comes out)
==============================================================

LECTURE (slide 8):  "Model = agreement between client and API about what data
is allowed."

A Pydantic model does THREE jobs at once:
    1. VALIDATION     - wrong type / missing field  ->  422, handler never runs
    2. DOCUMENTATION  - Swagger UI shows the exact JSON shape and an example
    3. CONSISTENCY    - a response_model filters the output to exactly these
                        keys, so the client always gets the same shape

REQUEST models vs RESPONSE models  (lecture slide 9)
    Professional APIs separate "what the client may SEND" from "what the
    server PROMISES to return".  They are different because:
      - the client never sends an id or a timestamp (the server creates them)
      - the server never echoes back internal fields it does not want to expose
    That is why there is a NoteCreate AND a NoteResponse, not one "Note".

HOW A MODEL BECOMES A REQUEST BODY
    Any handler argument typed as a BaseModel is read from the JSON body:
        def create_note(note: NoteCreate):      # <- Swagger: "Request body"
    Any handler decorated with response_model=X has its output checked and
    trimmed to X:
        @router.get("/notes/{id}", response_model=NoteResponse)

WHERE THE NAMES SHOW UP
    Open http://127.0.0.1:8000/docs and scroll to the bottom: the "Schemas"
    section lists every class in this file.  Expand one - the field types,
    limits and examples you see there come straight from the Field() calls.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ===========================================================================
# NOTES  -  the "items" part of the API
# ===========================================================================

class NoteCreate(BaseModel):
    """
    REQUEST body for   POST /notes   and   PUT /notes/{note_id}.

    Valid body:
        { "title": "Embeddings", "content": "Vectors that capture meaning." }

    Things that make it 422 (try each in Swagger and read the "detail" list):
        { "content": "no title" }              missing key   -> "Field required"
        { "title": "", "content": "x" }        min_length=1  -> "String should have at least 1 character"
        { "title": 123, "content": "x" }       still OK - pydantic coerces 123 -> "123"
        { "title": ["a"], "content": "x" }     not coercible -> "Input should be a valid string"

    Note what is NOT here: no id, no created_at.  The server owns those.
    """
    #        ... = REQUIRED.  Field() adds limits + the example Swagger shows.
    title: str = Field(..., min_length=1, max_length=100, examples=["Embeddings"])
    content: str = Field(..., min_length=1, examples=["Vectors that capture meaning."])


class NoteResponse(BaseModel):
    """
    RESPONSE shape for ONE note.  Every endpoint that returns a note uses it,
    so the JSON always has exactly these four keys in this order.

    Compare with NoteCreate: same title + content, PLUS the two fields only
    the server can produce.  A datetime is serialised to an ISO-8601 string
    automatically ("2026-09-21T10:15:30.123456Z").
    """
    id: int
    title: str
    content: str
    created_at: datetime


class NoteListResponse(BaseModel):
    """
    RESPONSE for   GET /notes.

    Wrapping the list in an object (instead of returning a bare JSON array)
    leaves room to add "total", "page" or "next" later WITHOUT breaking every
    client that already parses the response.
    """
    count: int
    notes: list[NoteResponse]      # a list of the model above - models nest


class DeleteResponse(BaseModel):
    """RESPONSE for   DELETE /notes/{note_id}   - a confirmation, not the note."""
    message: str
    deleted_id: int


# ===========================================================================
# RAG  -  the /ask contract  (lecture slide 13)
# ===========================================================================
# Designed BEFORE any LLM is connected.  Day 3 changes what happens inside
# services.ask_question(); these two models - the contract - stay the same.

class QuestionRequest(BaseModel):
    """
    REQUEST body for   POST /ask.

    Valid body:      { "question": "What is RAG?" }
    422 examples:    { "question": "" }      min_length=3
                     { "q": "What is RAG?" } wrong key name -> "Field required" for question
    """
    question: str = Field(..., min_length=3, max_length=500, examples=["What is RAG?"])


class SourceRef(BaseModel):
    """One source the answer was built from.  Today: a note.  Day 3: a document chunk."""
    note_id: int
    title: str


class AnswerResponse(BaseModel):
    """
    RESPONSE for   POST /ask.

    Slide 13: "The API returns a structured answer, source references, and
    optionally metadata such as confidence or document IDs."  All three are
    here, so the frontend can be built against this shape TODAY even though
    the answer is still produced by keyword matching, not an LLM.
    """
    answer: str
    sources: list[SourceRef]       # which notes the answer came from (may be empty)
    confidence: float              # 0.0 .. 1.0 - a dummy score for now


# ===========================================================================
# META  -  small helpers
# ===========================================================================

class HealthResponse(BaseModel):
    """RESPONSE for   GET /   - proves the server is up and shows where the docs are."""
    status: str
    app: str
    version: str
    docs: str


class MessageResponse(BaseModel):
    """Generic RESPONSE for endpoints that only need to say "done"  (POST /reset)."""
    message: str
