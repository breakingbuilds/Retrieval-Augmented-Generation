"""
HTTP METHOD DRILL  -  a tiny in-memory Books API for practising verbs in Postman
================================================================================

HOW A "MAPPING" WORKS
---------------------
Every function below is decorated with  @app.<method>("<path>")  - that decorator
IS the mapping (Spring Boot calls the same thing @GetMapping / @PostMapping ...).
When a request arrives FastAPI looks for a route whose METHOD *and* PATH both match:

    @app.get("/books/{book_id}")   <-  GET  /books/1    ok, calls the function
                                   <-  POST /books/1    405 (path matches, method doesn't)
                                   <-  GET  /books      different route (the list one)
                                   <-  GET  /bookz/1    404 (no route matches at all)

Three ways data gets INTO a handler - and where each one lives in Postman:

    PATH  parameter   {book_id} in the decorator    ->  typed straight into the URL
    QUERY parameter   plain function argument       ->  Postman "Params" tab (?key=value)
    BODY  parameter   argument typed as a model     ->  Postman "Body -> raw -> JSON"

POSTMAN SETUP (once)
--------------------
1. Terminal :  uvicorn app.main:app --reload       (serves http://127.0.0.1:8000)
2. Postman  :  New request -> pick METHOD in the dropdown -> type the URL.
               For POST / PUT / PATCH: Body tab -> raw -> choose "JSON" in the little
               dropdown (that also sets the Content-Type header for you).
3. After every Send, look at THREE places in the response pane:
       - the status pill (top-right)   e.g.  201 Created / 204 No Content / 405 ...
       - the Headers tab               e.g.  Location, Allow, X-Book-Title
       - the Body tab                  JSON, or empty for HEAD and 204 responses

THE DRILL
---------
Work through DRILL 1 .. 10 in order - each one is a comment block sitting right
above the handler it exercises.  POST /reset whenever you want the seed data back.
"""

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.models import Book, BookCreate, BookUpdate

app = FastAPI(
    title="HTTP Method Drill",
    description="Practice GET / POST / PUT / PATCH / DELETE / HEAD / OPTIONS.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# In-memory "database"
# ---------------------------------------------------------------------------
# A plain dict stands in for a real DB so you can focus on the HTTP layer.
# Restarting the server (or POST /reset) puts it back to 3 seed books.

db: dict[int, Book] = {}
_next_id = 1


def _seed() -> None:
    """Reset the store to a known state (startup, tests, and POST /reset)."""
    global _next_id
    db.clear()
    _next_id = 1
    for title, author, year in [
        ("Dune", "Frank Herbert", 1965),          # id 1
        ("Neuromancer", "William Gibson", 1984),  # id 2
        ("Snow Crash", "Neal Stephenson", 1992),  # id 3
    ]:
        _create(BookCreate(title=title, author=author, year=year))


def _create(data: BookCreate) -> Book:
    """Assign the next id and store the book - the server, not the client, picks ids."""
    global _next_id
    book = Book(id=_next_id, **data.model_dump())
    db[book.id] = book
    _next_id += 1
    return book


def _get_or_404(book_id: int) -> Book:
    """Shared lookup: raising HTTPException turns into a JSON {"detail": ...} response."""
    book = db.get(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return book


_seed()


# ---------------------------------------------------------------------------
# Friendlier 405 - tells you which methods the path DOES accept
# ---------------------------------------------------------------------------
# FastAPI already answers 405 when the path matches but the method doesn't.
# This handler just makes the response teach you something: it scans every
# mapping in the app, keeps the ones whose path matches the URL you hit, and
# lists their methods - both in the body and in the standard "Allow" header.
#
#   POSTMAN:  POST  http://127.0.0.1:8000/books/1      (the classic mistake)
#   EXPECT :  405 Method Not Allowed
#             Body    -> "allowed": ["DELETE","GET","HEAD","OPTIONS","PATCH","PUT"]
#             Headers -> Allow: DELETE, GET, HEAD, OPTIONS, PATCH, PUT

@app.exception_handler(405)
async def method_not_allowed(request: Request, exc: StarletteHTTPException):
    path = request.url.path
    allowed = sorted({
        method
        for route in app.routes
        if isinstance(route, APIRoute) and route.path_regex.match(path)
        for method in route.methods
    })
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        headers={"Allow": ", ".join(allowed)},
        content={
            "detail": f"{request.method} is not allowed on {path}",
            "allowed": allowed,
            "hint": "Both the METHOD and the PATH must match a mapping. "
                    "Change the method dropdown, or fix the URL.",
        },
    )


# ---------------------------------------------------------------------------
# Root - a cheat sheet you can GET
# ---------------------------------------------------------------------------
#   POSTMAN:  GET  http://127.0.0.1:8000/
#   EXPECT :  200 OK  and a JSON index of the drills below.

@app.get("/", tags=["meta"])
def root():
    return {
        "message": "HTTP method drill - open app/main.py and follow DRILL 1..10",
        "docs": "/docs",
        "drills": {
            "1": "GET    /books            list (+ ?author= ?year= filters)",
            "2": "GET    /books/{id}       read one, 404 when missing",
            "3": "HEAD   /books/{id}       headers only, no body",
            "4": "POST   /books            create -> 201 + Location header",
            "5": "PUT    /books/{id}       full replace -> 200, or 201 if new",
            "6": "PATCH  /books/{id}       partial update -> 200",
            "7": "DELETE /books/{id}       remove -> 204, again -> 404",
            "8": "OPTIONS /books, /books/{id}   read the Allow header",
            "9": "wrong method on a route  -> 405 with the allowed list",
            "10": "POST  /reset            restore seed data -> 204",
        },
    }


# ===========================================================================
# DRILL 1  -  GET the collection  (+ query parameters)
# ===========================================================================
# MAPPING :  GET /books
#
#   POSTMAN:  Method GET        URL http://127.0.0.1:8000/books        Body: none
#   EXPECT :  200 OK
#             Body -> a JSON ARRAY of 3 books, each with id/title/author/year
#
# QUERY PARAMETERS - the two arguments below are plain (not in the path, not a
# model) so FastAPI reads them from the query string.  In Postman open the
# "Params" tab, add a row, and watch Postman append ?author=... to the URL.
#
#   TRY 1  Params: author = gibson      ->  200, only Neuromancer (case-insensitive)
#   TRY 2  Params: year   = 1992        ->  200, only Snow Crash
#   TRY 3  Params: year   = abc         ->  422 - "year" is typed int, so FastAPI
#                                            validates the query string for you
#   TRY 4  Params: author = nobody      ->  200 with []  (empty list is not an error)
#
# GET is SAFE (changes nothing) and IDEMPOTENT (send it 10x, same result).

@app.get("/books", response_model=list[Book], tags=["books"])
def list_books(author: str | None = None, year: int | None = None):
    books = list(db.values())
    if author:
        books = [b for b in books if author.lower() in b.author.lower()]
    if year is not None:
        books = [b for b in books if b.year == year]
    return books


# ===========================================================================
# DRILL 2  -  GET one item  (path parameter)
# ===========================================================================
# MAPPING :  GET /books/{book_id}
#
# {book_id} in the path becomes the `book_id: int` argument.  FastAPI converts
# and validates it before the function runs.
#
#   POSTMAN:  Method GET        URL http://127.0.0.1:8000/books/1      Body: none
#   EXPECT :  200 OK    Body -> ONE book object (not an array):  {"id": 1, "title": "Dune", ...}
#
#   TRY 1  URL /books/999   ->  404 Not Found, Body {"detail": "Book 999 not found"}
#   TRY 2  URL /books/abc   ->  422 - the path param must be an int; read the
#                               Body: it names the parameter and why it failed
#   TRY 3  URL /books/1/    ->  FastAPI redirects (307) to /books/1 - watch
#                               Postman's console to see the two hops

@app.get("/books/{book_id}", response_model=Book, tags=["books"])
def get_book(book_id: int):
    return _get_or_404(book_id)


# ===========================================================================
# DRILL 3  -  HEAD  (metadata only)
# ===========================================================================
# MAPPING :  HEAD /books/{book_id}
#
# HEAD is "GET without the body".  Clients use it to check that something
# exists, or to read size / caching headers, without downloading the payload.
# Note that FastAPI does NOT add HEAD to a GET route automatically - if this
# handler were missing, HEAD /books/1 would return 405.
#
#   POSTMAN:  Method HEAD       URL http://127.0.0.1:8000/books/1      Body: none
#   EXPECT :  200 OK
#             Body    -> EMPTY (this is the point of HEAD)
#             Headers -> X-Book-Title: Dune    (a custom header we set below)
#                        content-length: 0
#
#   TRY 1  URL /books/999   ->  404 - still no body, only the status tells you
#   TRY 2  Switch method back to GET, same URL -> same headers, now with a body

@app.head("/books/{book_id}", tags=["books"])
def head_book(book_id: int):
    book = _get_or_404(book_id)
    return Response(headers={"X-Book-Title": book.title})


# ===========================================================================
# DRILL 4  -  POST  (create)
# ===========================================================================
# MAPPING :  POST /books          <-- the COLLECTION, no id in the URL!
#
# POST means "add a new item to this collection; server, you pick the id".
# The `data: BookCreate` argument is a Pydantic model, so FastAPI reads it
# from the JSON body and validates every field (see app/models.py).
#
#   POSTMAN:  Method POST       URL http://127.0.0.1:8000/books
#             Body -> raw -> JSON:
#                 {
#                   "title":  "Hyperion",
#                   "author": "Dan Simmons",
#                   "year":   1989
#                 }
#   EXPECT :  201 Created                  (not 200 - "Created" is the correct code)
#             Body    -> the new book WITH its server-assigned "id": 4
#             Headers -> Location: /books/4   (where the new resource lives)
#
#   TRY 1  Press Send AGAIN with the same body  ->  201 again, "id": 5.
#          POST is NOT idempotent: every call creates another row.
#          Confirm with GET /books - you now have 5 books.
#   TRY 2  Body {"title": "", "author": "x", "year": 3000}  ->  422.  Read the
#          Body: "detail" is a list, one entry per failing field, with "loc"
#          telling you where (body -> title) and "msg" telling you why.
#   TRY 3  Body with a Spring-style user {"id": 41, "name": "aa", "email": ...}
#          ->  422 listing title / author / year as "Field required".
#          Extra keys like "id" and "name" are ignored, missing ones are errors.
#   TRY 4  Body tab -> raw -> change the dropdown from JSON to Text, Send
#          ->  422: without Content-Type: application/json FastAPI can't parse it.
#   TRY 5  THE CLASSIC MISTAKE: URL /books/1 with method POST  ->  405.
#          The path /books/1 exists, but no mapping pairs it with POST.
#          Read the "allowed" list in the body, then pick PUT or PATCH (next drills).

@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED, tags=["books"])
def create_book(data: BookCreate, response: Response):
    book = _create(data)
    response.headers["Location"] = f"/books/{book.id}"
    return book


# ===========================================================================
# DRILL 5  -  PUT  (full replace)
# ===========================================================================
# MAPPING :  PUT /books/{book_id}          <-- the ITEM, id IS in the URL
#
# PUT means "here is the COMPLETE new version of the resource at this URL".
# Because the client names the URL, PUT may also CREATE if nothing is there yet.
# It reuses BookCreate, so every field is required - that is what "full" means.
#
#   POSTMAN:  Method PUT        URL http://127.0.0.1:8000/books/1
#             Body -> raw -> JSON:
#                 {
#                   "title":  "Dune Messiah",
#                   "author": "Frank Herbert",
#                   "year":   1969
#                 }
#   EXPECT :  200 OK     Body -> {"id": 1, "title": "Dune Messiah", ...}
#             (GET /books/1 afterwards shows the replaced record)
#
#   TRY 1  Send the SAME request again  ->  200, nothing changed, still 3 rows.
#          PUT IS idempotent - compare with POST in DRILL 4.
#   TRY 2  Body {"title": "Only title"}  ->  422 "Field required" for author, year.
#          PUT wants the whole object.  Partial updates are PATCH's job (DRILL 6).
#   TRY 3  URL /books/42 (does not exist) with a full body  ->  201 Created
#          + Location: /books/42.  The client chose the id, the server honoured it.
#          GET /books now lists 4 books.
#   TRY 4  Body {"id": 99, "title": "x", "author": "y", "year": 2000} on /books/1
#          ->  200 and the id is STILL 1: the URL wins, "id" in the body is ignored.

@app.put("/books/{book_id}", response_model=Book, tags=["books"])
def replace_book(book_id: int, data: BookCreate, response: Response):
    created = book_id not in db
    book = Book(id=book_id, **data.model_dump())
    db[book_id] = book
    if created:
        response.status_code = status.HTTP_201_CREATED
        response.headers["Location"] = f"/books/{book_id}"
    return book


# ===========================================================================
# DRILL 6  -  PATCH  (partial update)
# ===========================================================================
# MAPPING :  PATCH /books/{book_id}
#
# PATCH means "change ONLY these fields, leave the rest alone".  It uses
# BookUpdate, where every field is Optional.  `exclude_unset=True` is the key
# trick: it gives us only the keys the client actually sent, so a field you
# omit is untouched (not reset to null).
#
#   POSTMAN:  Method PATCH      URL http://127.0.0.1:8000/books/1
#             Body -> raw -> JSON:      { "year": 1966 }
#   EXPECT :  200 OK
#             Body -> year is 1966, title and author are UNCHANGED
#
#   TRY 1  Body {"title": "Only title"}  ->  200.  Same body that PUT rejected
#          in DRILL 5 TRY 2 - that is the whole PUT-vs-PATCH difference.
#   TRY 2  Body {}                       ->  400 "must contain at least one field"
#          (our own rule - an empty PATCH is almost always a client bug)
#   TRY 3  Body {"year": "soon"}         ->  422, types are still validated
#   TRY 4  URL /books/999                ->  404, PATCH never creates
#   TRY 5  Body {"publisher": "Ace"}     ->  400.  Unknown keys are silently
#          dropped by the model, so after exclude_unset nothing is left.

@app.patch("/books/{book_id}", response_model=Book, tags=["books"])
def update_book(book_id: int, data: BookUpdate):
    book = _get_or_404(book_id)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="PATCH body must contain at least one field")
    updated = book.model_copy(update=changes)
    db[book_id] = updated
    return updated


# ===========================================================================
# DRILL 7  -  DELETE
# ===========================================================================
# MAPPING :  DELETE /books/{book_id}
#
#   POSTMAN:  Method DELETE     URL http://127.0.0.1:8000/books/2      Body: none
#   EXPECT :  204 No Content
#             Body -> EMPTY.  204 promises "no body", so Postman shows nothing.
#
#   TRY 1  Send AGAIN            ->  404.  The first call removed it.
#          (DELETE is still considered idempotent: the END STATE - "book 2 is
#          gone" - is the same either way, even though the status code differs.)
#   TRY 2  GET /books            ->  200 and only 2 books remain
#   TRY 3  URL /books (no id), method DELETE  ->  405: you cannot delete the
#          whole collection here.  Check the "allowed" list: GET, OPTIONS, POST.

@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["books"])
def delete_book(book_id: int):
    _get_or_404(book_id)
    del db[book_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# DRILL 8  -  OPTIONS  (discover what a URL supports)
# ===========================================================================
# MAPPING :  OPTIONS /books   and   OPTIONS /books/{book_id}
#
# OPTIONS asks "what can I do at this URL?".  The answer lives in the "Allow"
# RESPONSE HEADER - the body is just a convenience copy.  Browsers also send
# OPTIONS automatically for CORS pre-flight checks; that is the same verb.
#
#   POSTMAN:  Method OPTIONS    URL http://127.0.0.1:8000/books        Body: none
#   EXPECT :  200 OK
#             Headers -> Allow: GET, POST, OPTIONS        <-- look here
#             Body    -> {"allow": ["GET", "POST", "OPTIONS"]}
#
#   TRY 1  URL /books/1   ->  Allow: GET, HEAD, PUT, PATCH, DELETE, OPTIONS
#          Notice POST is missing - that is DRILL 4 TRY 5 explained.
#   TRY 2  Compare the two Allow lists with the 405 bodies you got earlier.

@app.options("/books", tags=["books"])
def options_books():
    allowed = "GET, POST, OPTIONS"
    return JSONResponse(content={"allow": allowed.split(", ")}, headers={"Allow": allowed})


@app.options("/books/{book_id}", tags=["books"])
def options_book(book_id: int):
    allowed = "GET, HEAD, PUT, PATCH, DELETE, OPTIONS"
    return JSONResponse(content={"allow": allowed.split(", ")}, headers={"Allow": allowed})


# ===========================================================================
# DRILL 9  -  405 Method Not Allowed  (no handler needed - it is automatic)
# ===========================================================================
# There is no mapping to write for this one.  Any time the PATH matches some
# route but the METHOD does not, FastAPI answers 405 and our handler at the top
# of the file fills in the "allowed" list.
#
#   POSTMAN:  Method POST    URL /books/1     ->  405   (item route, no POST)
#             Method DELETE  URL /books       ->  405   (collection, no DELETE)
#             Method PUT     URL /books       ->  405   (collection, no PUT)
#             Method PATCH   URL /reset       ->  405   (/reset only has POST)
#   EXPECT :  Headers -> Allow: ...     Body -> "allowed": [...]
#
#   Compare with:  GET /nope   ->  404.  No route has that path at all, so it is
#   "not found", not "wrong method".  404 = wrong PATH, 405 = wrong METHOD.


# ===========================================================================
# DRILL 10  -  reset  (helper, not a REST verb lesson)
# ===========================================================================
# MAPPING :  POST /reset
#
# A side-effect with no resource to return, so POST + 204 is a reasonable fit.
#
#   POSTMAN:  Method POST       URL http://127.0.0.1:8000/reset       Body: none
#   EXPECT :  204 No Content, then GET /books shows the original 3 books again.

@app.post("/reset", status_code=status.HTTP_204_NO_CONTENT, tags=["meta"])
def reset():
    _seed()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
