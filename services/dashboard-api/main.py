import os
import psycopg2
import redis
import json
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import time

# --- Environment Configuration ---
POSTGRES_URL = os.environ.get('POSTGRES_URL', 'postgresql://pulseuser:pulsepassword@postgres:5432/pulsedb')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379')
CACHE_TTL_SECONDS = int(os.environ.get('CACHE_TTL_SECONDS', 10))

# --- Global Connections (init as None) ---
pg_conn = None
redis_conn = None

# --- Connection Functions ---
def connect_postgres():
    """Connects to PostgreSQL database with retry logic."""
    while True:
        try:
            conn = psycopg2.connect(POSTGRES_URL)
            print("[PG] Connected to PostgreSQL successfully.")
            return conn
        except psycopg2.OperationalError as e:
            print(f" [!] PostgreSQL connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def connect_redis():
    """Connects to Redis with retry logic."""
    while True:
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True)
            r.ping()
            print("[Redis] Connected to Redis successfully.")
            return r
        except redis.exceptions.ConnectionError as e:
            print(f" [!] Redis connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

# --- FastAPI App ---
app = FastAPI()

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins (for development)
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods
    allow_headers=["*"], # Allow all headers
)

@app.on_event("startup")
def startup_event():
    """On app startup, connect to databases."""
    global pg_conn, redis_conn
    pg_conn = connect_postgres()
    redis_conn = connect_redis()

@app.get("/health")
def health_check():
    return {"status": "ok", "postgres_ready": not pg_conn.closed, "redis_ready": redis_conn.ping()}

@app.get("/api/metrics/summary")
def get_metrics_summary(request: Request):
    global pg_conn
    cursor = None
    cache_key = "metrics:summary:v2" # Updated cache key
    metrics = [] # Ensure metrics is initialized

    try:
        # 1. Check Redis Cache
        cached_data = redis_conn.get(cache_key)
        
        if cached_data:
            print("[Cache] HIT")
            return Response(
                content=cached_data,
                media_type="application/json",
                headers={"X-Cache-Status": "HIT"}
            )
        
        # 2. If Cache MISS, query database
        print("[Cache] MISS")
        
        if not pg_conn or pg_conn.closed:
            print("[PG] Reconnecting to PostgreSQL...")
            pg_conn = connect_postgres()
        
        cursor = pg_conn.cursor(cursor_factory=RealDictCursor)
        
        # --- NEW AGGREGATING QUERY ---
        # This query now sums all metrics PER USER, 
        # giving us a clean summary.
        cursor.execute("""
            SELECT 
                user_id, 
                SUM(event_count) AS total_events,
                SUM(tasks_created) AS total_tasks_created,
                SUM(tasks_completed) AS total_tasks_completed
            FROM daily_user_metrics
            GROUP BY user_id
            ORDER BY total_events DESC
        """)
        metrics = cursor.fetchall()
        
        json_metrics = json.dumps(metrics, default=str)

        # 3. Store in Redis Cache
        redis_conn.setex(cache_key, CACHE_TTL_SECONDS, json_metrics)
        
        return Response(
            content=json_metrics,
            media_type="application/json",
            headers={"X-Cache-Status": "MISS"}
        )

    except psycopg2.Error as e:
        print(f" [!] Database query error: {e}")
        return Response(content=json.dumps({"error": "Database error"}), status_code=500, media_type="application/json")
    except redis.exceptions.RedisError as e:
        print(f" [!] Redis error: {e}")
        # If Redis fails, just return DB data without caching
        return Response(content=json.dumps(metrics), media_type="application/json", headers={"X-Cache-Status": "ERROR"})
    except Exception as e:
        print(f" [!] An unexpected error occurred: {e}")
        return Response(content=json.dumps({"error": str(e)}), status_code=500, media_type="application/json")
    finally:
        if cursor:
            cursor.close()

