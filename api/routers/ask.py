"""Natural language query endpoint — user question → Claude SQL → DuckDB answer."""
import logging
import os
import re

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_store
from pipeline.store import DelayStore

logger = logging.getLogger(__name__)
router = APIRouter()

# DuckDB delays table schema (for the prompt)
_SCHEMA = """
Table: delays
Columns:
  station_name TEXT       -- e.g. 'Dadar CR', 'Thane', 'Kalyan'
  line         TEXT       -- 'Central', 'Western', or 'Harbour'
  date         DATE       -- observation date
  hour         INTEGER    -- 0-23
  weekday      INTEGER    -- 0=Monday, 6=Sunday
  period       TEXT       -- 'morning_peak', 'evening_peak', 'off_peak'
  avg_delay    REAL       -- average delay in minutes
  ci_lower     REAL       -- 95% CI lower bound
  ci_upper     REAL       -- 95% CI upper bound
"""

_SYSTEM = f"""You are a DuckDB SQL expert for a Mumbai local train delay database.

Schema:
{_SCHEMA}

Rules:
- Return ONLY a valid DuckDB SELECT query, nothing else — no explanation, no markdown fences
- NEVER use DROP, DELETE, INSERT, UPDATE, CREATE, or ALTER
- LIMIT results to 20 rows max unless the user asks for all
- Use friendly column aliases (e.g. AS "Station", AS "Avg Delay (min)")
- Round numeric results to 2 decimal places with ROUND()
"""


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    question: str
    sql: str
    answer: str


def _is_safe_sql(sql: str) -> bool:
    """Reject any non-SELECT statement."""
    normalized = sql.strip().upper()
    if not normalized.startswith("SELECT"):
        return False
    dangerous = re.compile(r"\b(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|TRUNCATE|EXEC|EXECUTE)\b")
    return not dangerous.search(normalized)


def _run_sql(store: DelayStore, sql: str) -> str:
    """Execute SQL on DuckDB, return result as formatted string."""
    try:
        conn = store.conn  # access underlying DuckDB connection
        result = conn.execute(sql).fetchdf()
        if result.empty:
            return "No data found for this query."
        return result.to_string(index=False, max_rows=20)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL execution failed: {e}") from e


@router.post("/ask", response_model=AskResponse)
def ask_question(
    body: AskRequest,
    store: DelayStore = Depends(get_store),
) -> AskResponse:
    """Translate a natural language question to SQL and execute it."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=api_key)

    # Step 1: Generate SQL
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": body.question}],
        )
        sql = message.content[0].text.strip()
    except Exception as e:
        logger.error("Claude API error: %s", e)
        raise HTTPException(status_code=502, detail="Failed to generate SQL") from e

    # Step 2: Safety check
    if not _is_safe_sql(sql):
        raise HTTPException(status_code=400, detail="Generated SQL is not a safe SELECT query")

    # Step 3: Execute
    answer = _run_sql(store, sql)

    return AskResponse(question=body.question, sql=sql, answer=answer)
