import redis, json, os

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_db   = int(os.getenv("REDIS_DB", 0))

r = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)

# 工具函数 -------------------------------------------------
def get(key):
    val = r.get(key)
    return json.loads(val) if val else None

def set(key, value, ex=3600):
    r.set(key, json.dumps(value, ensure_ascii=False), ex=ex)

def delete(key):
    r.delete(key)