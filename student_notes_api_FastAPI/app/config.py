"""
config.py  -  ONE place for every setting the app needs
=======================================================

LECTURE (slide 5):  "config.py - Central place for settings, keys, and
environment values."

WHY A SEPARATE FILE?
  Today the settings are tiny (an app name, a default page size).  On Day 3
  they grow: an LLM API key, an embedding model name, a chunk size, a vector
  store path...  If those values are sprinkled through routes.py and
  services.py you end up hunting for them.  Keeping them here means:
    - one file to open when something must change
    - secrets come from ENVIRONMENT VARIABLES and are never typed into code
    - every other module just does   from .config import settings

HOW os.getenv WORKS
  os.getenv("NAME", "fallback") returns the environment variable NAME if it is
  set, otherwise the fallback.  Try it - restart the server with a variable set:

      PowerShell :  $env:APP_NAME = "My Study Notes"; uvicorn app.main:app --reload
      bash       :  APP_NAME="My Study Notes" uvicorn app.main:app --reload

  ...and watch the title at the top of http://127.0.0.1:8000/docs change.
  Nothing in the code changed; only the environment did.

WHERE THE .env FILE FITS
  Typing $env:... before every start gets old, and an API key typed into a
  terminal is easy to leak into your shell history.  So the values go in a
  plain text file called .env  (KEY=value, one per line) and load_dotenv()
  copies them INTO the environment when this module is imported:

      .env file  ->  load_dotenv()  ->  environment  ->  os.getenv()

  Two files, on purpose:
      .env.example   committed to git, placeholder values, shows the KEYS
      .env           ignored by git (see .gitignore), your REAL values
  Copy the first to the second and edit it.  If .env does not exist nothing
  breaks: load_dotenv() quietly does nothing and the fallbacks below apply.
  A variable already set in the shell wins over the same key in .env.
"""

import os

from dotenv import load_dotenv

load_dotenv()      # reads .env (if present) BEFORE any os.getenv() below runs


class Settings:
    """
    A plain class is enough for a drill this small.  A production app would
    use `pydantic-settings` (BaseSettings) so these values are validated and
    loaded from .env automatically - same idea, more features.
    """

    # --- identity (shown at the top of Swagger UI) ---------------------------
    app_name: str = os.getenv("APP_NAME", "Student Notes API (homework)")
    app_version: str = os.getenv("APP_VERSION", "1.0")
    app_description: str = (
        "Day 2 drill: a clean FastAPI structure (routes / schemas / services / "
        "config) that is ready to receive a RAG pipeline."
    )

    # --- rules for the ?limit= query parameter on GET /notes -----------------
    # routes.py reads these so the validation rule lives in ONE place.
    default_limit: int = int(os.getenv("DEFAULT_LIMIT", "10"))
    max_limit: int = int(os.getenv("MAX_LIMIT", "100"))

    # --- RAG settings ---------------------------------------------------------
    # max_sources is used today by the dummy /ask.  The other two are unused
    # placeholders: on Day 3 the real retriever + LLM call will read them from
    # here instead of hard-coding them in services.py.
    max_sources: int = int(os.getenv("MAX_SOURCES", "3"))
    llm_api_key: str = os.getenv("LLM_API_KEY", "")            # never commit a real key
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


# One shared instance.  Import THIS, not the class:  from .config import settings
settings = Settings()
