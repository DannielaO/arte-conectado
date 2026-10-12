"""Durable aggregate analytics. Requires DATABASE_URL (PostgreSQL).
Never stores submitted messages, links, IP addresses or user agents.
"""
import os
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
import psycopg

log = logging.getLogger(__name__)
_ready = False

def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    return psycopg.connect(url, connect_timeout=4)

def _init(conn):
    global _ready
    if _ready:
        return
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usage_daily (
                day DATE NOT NULL,
                event TEXT NOT NULL,
                source TEXT NOT NULL,
                decision TEXT NOT NULL,
                count BIGINT NOT NULL DEFAULT 0,
                PRIMARY KEY(day,event,source,decision)
            )
        """)
    conn.commit()
    _ready = True

def record(event, source="direct", decision="none"):
    if not os.getenv("DATABASE_URL"):
        return False
    event = str(event)[:40]
    source = str(source or "direct")[:80]
    decision = str(decision or "none")[:20]
    if event not in {"page_view","clear","analyze_requests","analyze_completed","feedback_yes","feedback_no"}:
        return False
    try:
        with _connect() as conn:
            _init(conn)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usage_daily(day,event,source,decision,count)
                    VALUES (%s,%s,%s,%s,1)
                    ON CONFLICT(day,event,source,decision)
                    DO UPDATE SET count=usage_daily.count+1
                """, (datetime.now(timezone.utc).date(), event, source, decision))
        return True
    except Exception:
        log.exception("Analytics write failed")
        return False

def summary():
    if not os.getenv("DATABASE_URL"):
        return {"configured":False,"note":"DATABASE_URL no configurada"}
    try:
        with _connect() as conn:
            _init(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT day,event,source,decision,count FROM usage_daily ORDER BY day DESC, event, source")
                rows = cur.fetchall()
        daily = {}
        sources = {}
        totals = {}
        for day,event,source,decision,count in rows:
            key = day.isoformat()
            daily.setdefault(key,{})[event] = daily.setdefault(key,{}).get(event,0)+count
            totals[event] = totals.get(event,0)+count
            if event == "page_view":
                sources[source] = sources.get(source,0)+count
        votes = totals.get("feedback_yes",0)+totals.get("feedback_no",0)
        return {"configured":True,"totals":totals,"daily":daily,"sources":sources,
                "helpful_rate":round(100*totals.get("feedback_yes",0)/votes,1) if votes else None,
                "note":"Contadores agregados persistentes en PostgreSQL; no son usuarios únicos."}
    except Exception:
        log.exception("Analytics read failed")
        return {"configured":True,"error":"analytics_unavailable"}
