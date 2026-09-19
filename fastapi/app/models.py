"""
Request / response models  -  what you paste into Postman's Body tab.

A Pydantic model used as a handler argument tells FastAPI two things:
  1. read this from the JSON request body (Postman: Body -> raw -> JSON)
  2. validate every field; on failure answer 422 and never run the handler

There are three models because the three verbs have different rules about
what the client must send:

    POST  /books        BookCreate   all fields REQUIRED, no id (server picks it)
    PUT   /books/{id}   BookCreate   all fields REQUIRED  ("full replacement")
    PATCH /books/{id}   BookUpdate   all fields OPTIONAL  ("send only what changes")
    every response      Book         BookCreate + the id

Extra keys in the body (e.g. "id" or "name") are silently ignored by default.
Missing required keys, wrong types, or values outside the Field() limits -> 422.
"""

from pydantic import BaseModel, Field


class BookCreate(BaseModel):
    """
    Body for POST /books and PUT /books/{id}.

    Valid Postman body:
        {
          "title":  "Hyperion",
          "author": "Dan Simmons",
          "year":   1989
        }

    Things that make it 422 (try each one and read the "detail" list):
        {"title": "", ...}            min_length=1 fails      -> "String should have at least 1 character"
        {"year": 3000, ...}           le=2100 fails           -> "Input should be less than or equal to 2100"
        {"year": "1989", ...}         still ok! pydantic coerces "1989" -> 1989
        {"year": "next year", ...}    not coercible           -> "Input should be a valid integer"
        {"title": "x", "author": "y"} missing key             -> "Field required" for year
    """
    title: str = Field(..., min_length=1, examples=["Dune"])      # ... means REQUIRED
    author: str = Field(..., min_length=1, examples=["Frank Herbert"])
    year: int = Field(..., ge=0, le=2100, examples=[1965])


class BookUpdate(BaseModel):
    """
    Body for PATCH /books/{id}  -  every field optional, send only what changes.

    Valid Postman bodies:
        { "year": 1966 }
        { "title": "Dune (40th anniversary)", "year": 2005 }

    The handler calls .model_dump(exclude_unset=True), which returns ONLY the
    keys that were present in the JSON.  That is how "I didn't send title"
    stays different from "I sent title: null".

    Constraints still apply to whatever you DO send:
        { "title": "" }     -> 422 (min_length=1)
        { "year": "soon" }  -> 422 (not an int)
        { }                 -> passes validation, but the handler answers 400
    """
    title: str | None = Field(None, min_length=1)    # None default means OPTIONAL
    author: str | None = Field(None, min_length=1)
    year: int | None = Field(None, ge=0, le=2100)


class Book(BookCreate):
    """
    What every successful response contains: the stored record plus its id.

    Inherits title/author/year from BookCreate and adds id.  Used as
    response_model=Book on the handlers, so FastAPI also filters the output
    to exactly these four keys and documents them in /docs.
    """
    id: int
