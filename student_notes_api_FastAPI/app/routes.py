"""
routes.py  -  THE PUBLIC DOOR OF THE API
========================================

LECTURE (slide 4):  "Router - the public API door. It receives the request and
forwards it to the correct function."

Every handler in this file follows the same 3-step recipe:
    1. declare WHAT comes in   (path parameter / query parameter / request body)
    2. call ONE service function
    3. return its result       (FastAPI turns it into JSON via response_model)
No loops, no if/else business rules - those live in services.py.

THREE ROUTERS, ONE FILE  (lecture slide 6 - APIRouter)
    meta_router    /   /reset   /debug/crash     housekeeping
    notes_router   /notes ...                     the CRUD "items" part
    rag_router     /ask                           the RAG part
  main.py includes all three.  Splitting them costs nothing today, but on
  Day 3 the rag_router can move to its own file (rag_routes.py) without
  touching the notes code.  `prefix` and `tags` are set ONCE on the router
  instead of repeated on every endpoint; `tags` is also what groups the
  endpoints into sections in Swagger UI.

HOW DATA ENTERS A HANDLER  (lecture slide 7)
    PATH  parameter   {note_id} in the decorator   ->  part of the URL      /notes/1
    QUERY parameter   plain argument               ->  after the "?"        /notes?limit=2
    BODY  parameter   argument typed as a model    ->  JSON in the request  {"title": ...}
  Rule of thumb from the slide: the URL identifies or filters; the body
  carries structured data.

THE DRILL
  1. uvicorn app.main:app --reload
  2. open http://127.0.0.1:8000/docs
  3. work through DRILL 1..9 below - each is a comment block sitting right
     above the handler it exercises.  Before every "Execute", PREDICT the
     status code (slide 14), then check the "Server response" panel.
"""

from fastapi import APIRouter, Path, Query

from . import services
from .config import settings
from .schemas import (
    AnswerResponse,
    DeleteResponse,
    HealthResponse,
    MessageResponse,
    NoteCreate,
    NoteListResponse,
    NoteResponse,
    QuestionRequest,
)

meta_router = APIRouter(tags=["meta"])
notes_router = APIRouter(prefix="/notes", tags=["notes"])
rag_router = APIRouter(tags=["rag"])


# ===========================================================================
# DRILL 1  -  GET /   (health check - is the server alive?)
# ===========================================================================
# MAPPING :  GET /
#
#   SWAGGER:  meta -> GET /  -> Try it out -> Execute
#   EXPECT :  200 OK
#             Body -> {"status": "ok", "app": "...", "version": "1.0", "docs": "/docs"}
#
#   NOTICE :  "app" and "version" come from config.py, not from this file.
#             Restart with  $env:APP_NAME = "My Study Notes"  and call it again.

@meta_router.get("/", response_model=HealthResponse)
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


# ===========================================================================
# DRILL 2  -  GET /notes   (the collection  +  QUERY parameters)
# ===========================================================================
# MAPPING :  GET /notes
#
# `limit` and `search` are plain arguments, not in the path and not a model,
# so FastAPI reads them from the query string.  Query() adds validation rules
# and the description Swagger shows next to each field.
#
#   SWAGGER:  notes -> GET /notes -> Try it out -> Execute   (leave fields empty)
#   EXPECT :  200 OK
#             Body -> {"count": 3, "notes": [ {id 1}, {id 2}, {id 3} ]}
#
#   TRY 1  limit = 2               ->  200, count 2, only the first two notes
#   TRY 2  search = rag            ->  200, count 1, only the RAG note (case-insensitive)
#   TRY 3  search = python         ->  200, count 1 - it also searches "content"
#   TRY 4  search = banana         ->  200, count 0, "notes": []  (empty is NOT an error)
#   TRY 5  limit = 0               ->  422, "Input should be greater than or equal to 1"
#   TRY 6  limit = abc             ->  422, "Input should be a valid integer"
#          (5 and 6 never reach services.py - validation happens first)
#
# PATH TRICK:  the router has prefix="/notes", so the path here is "" (empty)
# and the full URL is /notes.  Writing "/" instead would make it /notes/ with
# a trailing slash, and /notes would answer with a 307 redirect.

@notes_router.get("", response_model=NoteListResponse)
def list_notes(
    limit: int = Query(
        default=settings.default_limit,
        ge=1,                       # ge = "greater than or equal"
        le=settings.max_limit,      # le = "less than or equal"
        description="Maximum number of notes to return",
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        description="Only notes whose title or content contains this text",
    ),
):
    found = services.get_all_notes(limit=limit, search=search)
    return {"count": len(found), "notes": found}


# ===========================================================================
# DRILL 3  -  GET /notes/{note_id}   (one item  -  PATH parameter)
# ===========================================================================
# MAPPING :  GET /notes/{note_id}
#
# {note_id} in the decorator becomes the `note_id: int` argument.  FastAPI
# converts the text from the URL into an int and validates it BEFORE the
# function body runs.
#
#   SWAGGER:  notes -> GET /notes/{note_id} -> Try it out -> note_id = 1 -> Execute
#   EXPECT :  200 OK
#             Body -> ONE note object (not a list): {"id": 1, "title": "FastAPI", ...}
#
#   TRY 1  note_id = 999   ->  404 Not Found, Body {"detail": "Note 999 not found"}
#                              (a CONTROLLED error raised by services.py - slide 11)
#   TRY 2  note_id = abc   ->  422 - the path parameter must be an int.  Read the
#                              body: "loc": ["path", "note_id"] tells you WHERE.
#   TRY 3  note_id = 0     ->  422 - Path(ge=1) below rejects it before the lookup.
#
#   404 vs 422:  422 = the request is malformed (wrong TYPE).  404 = the request
#   is fine, the thing just does not exist.  Different problems, different codes.

@notes_router.get("/{note_id}", response_model=NoteResponse)
def get_note(note_id: int = Path(ge=1, description="The id of the note")):
    return services.get_note_by_id(note_id)


# ===========================================================================
# DRILL 4  -  POST /notes   (create  -  REQUEST BODY)
# ===========================================================================
# MAPPING :  POST /notes          <-- the COLLECTION, no id in the URL
#
# `note: NoteCreate` is a Pydantic model, so FastAPI reads it from the JSON
# body and validates every field (see schemas.py).  status_code=201 tells
# FastAPI to answer "201 Created" instead of the default 200 (slide 10).
#
#   SWAGGER:  notes -> POST /notes -> Try it out -> Request body:
#                 {
#                   "title": "Embeddings",
#                   "content": "Vectors that capture meaning."
#                 }
#   EXPECT :  201 Created
#             Body -> the note WITH the server-assigned "id": 4 and "created_at"
#
#   TRY 1  Execute AGAIN with the same body   ->  400 Bad Request,
#          "A note titled 'Embeddings' already exists".  Well-formed request,
#          but it makes no logical sense for the API  (400, not 422).
#   TRY 2  Body {"content": "no title here"}  ->  422.  "detail" is a LIST, one
#          entry per failing field: "loc": ["body", "title"], "msg": "Field required".
#   TRY 3  Body {"title": "", "content": "x"}  ->  422, min_length=1 in schemas.py.
#   TRY 4  Body {"id": 99, "title": "Hack", "content": "x"}  ->  201, but the id is
#          NOT 99.  Extra keys are ignored; the server owns the id.
#   TRY 5  GET /notes afterwards            ->  count is now 4 (or 5).

@notes_router.post("", response_model=NoteResponse, status_code=201)
def create_note(note: NoteCreate):
    return services.create_note(note)


# ===========================================================================
# DRILL 5  -  PUT /notes/{note_id}   (full replace  -  PATH + BODY together)
# ===========================================================================
# MAPPING :  PUT /notes/{note_id}          <-- the ITEM, id IS in the URL
#
# Two ways in at once: the PATH says WHICH note, the BODY says the new
# content.  It reuses NoteCreate, so both title and content are required -
# that is what "full replace" means.
#
#   SWAGGER:  notes -> PUT /notes/{note_id} -> Try it out -> note_id = 1, body:
#                 {
#                   "title": "FastAPI (updated)",
#                   "content": "FastAPI builds APIs with automatic docs and validation."
#                 }
#   EXPECT :  200 OK
#             Body -> {"id": 1, "title": "FastAPI (updated)", ...}
#             "id" and "created_at" are UNCHANGED - the server owns them.
#
#   TRY 1  Execute the SAME request again   ->  200, nothing changed.  PUT is
#          idempotent; POST (DRILL 4) is not.
#   TRY 2  Body {"title": "Only a title"}   ->  422 "Field required" for content.
#   TRY 3  note_id = 999 with a full body   ->  404.  This PUT does not create.
#   TRY 4  note_id = 1, title = "RAG"       ->  400, that title belongs to note 2.

@notes_router.put("/{note_id}", response_model=NoteResponse)
def update_note(note: NoteCreate, note_id: int = Path(ge=1)):
    return services.update_note(note_id, note)


# ===========================================================================
# DRILL 6  -  DELETE /notes/{note_id}
# ===========================================================================
# MAPPING :  DELETE /notes/{note_id}
#
#   SWAGGER:  notes -> DELETE /notes/{note_id} -> Try it out -> note_id = 1 -> Execute
#   EXPECT :  200 OK
#             Body -> {"message": "Note deleted successfully", "deleted_id": 1}
#
#   TRY 1  Execute AGAIN            ->  404.  The first call removed it.
#   TRY 2  GET /notes               ->  count went down by one; id 1 is gone
#   TRY 3  POST /notes a new note   ->  its id is one higher than the LAST note
#          ever created, not "number of notes + 1".  The class version used
#          len(notes)+1, which after a delete hands out an id that already
#          exists - see the "bugs fixed" note at the top of services.py.
#
#   DESIGN NOTE:  many APIs answer 204 No Content (empty body) for a delete.
#   Returning 200 + a small confirmation, like the class version, is also
#   fine - what matters is that the shape is declared (DeleteResponse) and
#   therefore documented and consistent.

@notes_router.delete("/{note_id}", response_model=DeleteResponse)
def delete_note(note_id: int = Path(ge=1)):
    return services.delete_note(note_id)


# ===========================================================================
# DRILL 7  -  POST /ask   (the RAG-ready contract  -  slide 13)
# ===========================================================================
# MAPPING :  POST /ask
#
# Question in, answer + sources + confidence out.  The route is 2 lines and
# will STAY 2 lines when the real retriever and LLM are plugged in on Day 3 -
# everything happens in services.ask_question().
#
#   SWAGGER:  rag -> POST /ask -> Try it out -> body: {"question": "What is RAG?"}
#   EXPECT :  200 OK
#             Body -> {
#                       "answer": "From your note 'RAG': RAG stands for ...",
#                       "sources": [{"note_id": 2, "title": "RAG"}],
#                       "confidence": 1.0
#                     }
#
#   TRY 1  "Tell me about Pydantic models"  ->  the Pydantic note, confidence 1.0
#   TRY 2  "How do I bake bread?"           ->  200 (!), answer "I could not find
#          anything...", sources [], confidence 0.0.  Not finding an answer is a
#          normal outcome, not an error - so it is NOT a 404.
#   TRY 3  Body {"question": ""}            ->  422, min_length=3.
#   TRY 4  Body {"q": "What is RAG?"}       ->  422, "question" is required.
#   TRY 5  POST a new note first, then ask about it  ->  it shows up as a source.
#          That is retrieval: the answer changes because the DATA changed.

@rag_router.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    return services.ask_question(request.question)


# ===========================================================================
# DRILL 8  -  GET /debug/crash   (an UNEXPECTED error  -  slide 11)
# ===========================================================================
# MAPPING :  GET /debug/crash
#
# Everything so far raised HTTPException on purpose (controlled).  This
# handler has a real bug in it - division by zero - to show what happens
# when code simply crashes.  The handler in main.py catches it.
#
#   SWAGGER:  meta -> GET /debug/crash -> Execute
#   EXPECT :  500 Internal Server Error
#             Body -> {"detail": "Something went wrong on the server. The error has been logged."}
#             Terminal (uvicorn) -> the FULL traceback with the file and line.
#
#   NOTICE :  the client gets a short safe sentence; the developer gets the
#             details.  Never send tracebacks, paths or keys to the client.
#   (Only for the drill - a real API would not ship this endpoint.)

@meta_router.get("/debug/crash")
def crash():
    return 1 / 0


# ===========================================================================
# DRILL 9  -  POST /reset   (start over)
# ===========================================================================
# MAPPING :  POST /reset
#
#   SWAGGER:  meta -> POST /reset -> Execute
#   EXPECT :  200 OK, Body -> {"message": "Store reset - 3 seed notes restored"}
#             GET /notes now shows the original 3 notes with ids 1, 2, 3.

@meta_router.post("/reset", response_model=MessageResponse)
def reset():
    return services.reset_notes()
