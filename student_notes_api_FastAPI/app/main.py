"""
main.py  -  CREATE THE APP, PLUG IN THE ROUTERS, NOTHING ELSE
=============================================================

LECTURE (slide 5):  "main.py - Creates the FastAPI app and includes routers."

Compare with a single-file API where main.py ALSO holds every endpoint,
every model and every business rule (slide 3).  Here main.py is the table of
contents: you can tell what the app is made of without scrolling.

    Client  ->  FastAPI app  ->  router  ->  schema validation  ->  service  ->  JSON
                 (this file)   (routes.py)     (schemas.py)      (services.py)

RUN IT
    uvicorn app.main:app --reload
            ^^^ ^^^^ ^^^
            |   |    the variable named `app` below
            |   the file  app/main.py  (dots, not slashes)
            the package folder

    --reload restarts the server on every file save.  Remember that the
    in-memory notes are reset each time it restarts.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import settings
from .routes import meta_router, notes_router, rag_router

logger = logging.getLogger("student_notes_api")

# The title / description / version show up at the top of Swagger UI.
# They come from config.py so they can be changed without editing code.
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

# Each include_router() mounts one "route collection" (slide 6).  The order
# here is also the order of the sections in Swagger UI.  Adding a feature on
# Day 3 (an upload router, a documents router) is one more line here.
app.include_router(meta_router)
app.include_router(notes_router)
app.include_router(rag_router)


# ---------------------------------------------------------------------------
# Unexpected errors  ->  a SAFE 500   (lecture slide 11)
# ---------------------------------------------------------------------------
# HTTPException (404 / 400) is a CONTROLLED error: a service raised it on
# purpose and FastAPI already turns it into {"detail": ...}.  This handler is
# for everything else - a bug, a crashed database, a dead LLM API.  Two rules:
#   1. log the full traceback for the DEVELOPER (look at the uvicorn terminal)
#   2. send the CLIENT a short, safe message - never the traceback, never
#      file paths or keys (that would be an information leak)
# DRILL 8 (GET /debug/crash in routes.py) triggers this on purpose.

@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on the server. The error has been logged."},
    )
