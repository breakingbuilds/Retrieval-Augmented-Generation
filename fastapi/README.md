# HTTP Method Drill (FastAPI)

A tiny in-memory Books API whose only purpose is to practice every HTTP verb.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive docs: http://127.0.0.1:8000/docs

## Routes

| Method  | Path            | Purpose                          | Success code | Idempotent |
|---------|-----------------|----------------------------------|--------------|------------|
| GET     | /books          | list (filter: ?author=&year=)    | 200          | yes        |
| GET     | /books/{id}     | read one                         | 200 / 404    | yes        |
| HEAD    | /books/{id}     | headers only, no body            | 200 / 404    | yes        |
| POST    | /books          | create, server assigns id        | 201 + Location | **no**   |
| PUT     | /books/{id}     | full replace (creates if absent) | 200 / 201    | yes        |
| PATCH   | /books/{id}     | partial update                   | 200 / 404    | no*        |
| DELETE  | /books/{id}     | remove                           | 204 / 404    | yes        |
| OPTIONS | /books          | allowed methods (Allow header)   | 200          | yes        |
| OPTIONS | /books/{id}     | allowed methods (Allow header)   | 200          | yes        |
| POST    | /reset          | restore seed data                | 204          | -          |

\* PATCH *can* be idempotent (this one is, since it sets absolute values), but the spec doesn't require it.

## curl drill

```bash
# GET - list, then filter
curl -i http://127.0.0.1:8000/books
curl -i "http://127.0.0.1:8000/books?author=gibson"

# GET one / 404
curl -i http://127.0.0.1:8000/books/1
curl -i http://127.0.0.1:8000/books/999

# HEAD - note: no body, but you still get status + headers
curl -I http://127.0.0.1:8000/books/1

# POST - 201 + Location header; run twice and you get two rows (not idempotent)
curl -i -X POST http://127.0.0.1:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Hyperion","author":"Dan Simmons","year":1989}'

# PUT - full body required; run twice, state is unchanged (idempotent)
curl -i -X PUT http://127.0.0.1:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# PUT with partial body -> 422 (that's what PATCH is for)
curl -i -X PUT http://127.0.0.1:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Only title"}'

# PATCH - only the sent field changes
curl -i -X PATCH http://127.0.0.1:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year":1966}'

# DELETE - 204 first time, 404 second time
curl -i -X DELETE http://127.0.0.1:8000/books/2
curl -i -X DELETE http://127.0.0.1:8000/books/2

# OPTIONS - look at the Allow header
curl -i -X OPTIONS http://127.0.0.1:8000/books
curl -i -X OPTIONS http://127.0.0.1:8000/books/1

# Wrong method on a route -> 405 Method Not Allowed
curl -i -X DELETE http://127.0.0.1:8000/books

# Start over
curl -i -X POST http://127.0.0.1:8000/reset
```

On Windows PowerShell, `curl` is an alias for `Invoke-WebRequest`; use `curl.exe` instead, or `Invoke-RestMethod -Method Patch ...`.

## Postman

| Step | Where in Postman | What to do |
|---|---|---|
| Method | dropdown left of the URL bar | pick GET / POST / PUT / PATCH / DELETE / HEAD / OPTIONS |
| URL | URL bar | `http://127.0.0.1:8000/books` or `/books/1` |
| Query params | **Params** tab | key `author`, value `gibson` -> Postman appends `?author=gibson` |
| JSON body (POST/PUT/PATCH) | **Body** tab -> **raw** -> dropdown **JSON** | paste `{"title":"Hyperion","author":"Dan Simmons","year":1989}` |
| Response status | top-right of response pane | e.g. `201 Created`, `204 No Content`, `405 Method Not Allowed` |
| Response headers | **Headers** tab in the response pane | look for `Location`, `Allow`, `X-Book-Title` |

Selecting **JSON** in the raw body dropdown sets `Content-Type: application/json` for you.
FastAPI rejects a body with the wrong content type as 422.

Things worth noticing while drilling:

- **HEAD** shows headers but the body pane is empty.
- **POST** twice -> two different ids. **PUT** twice -> same state.
- **DELETE** -> `204` with empty body; send again -> `404`.
- **OPTIONS** -> read the `Allow` header, not the body.
- Send **DELETE** to `/books` (no id) -> `405`.
