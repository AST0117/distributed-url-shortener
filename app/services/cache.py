import redis, os

r = redis.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")), decode_responses=True)

CACHE_TTL = 3600  # 1 hour

def get_cached_url(short_code: str):
    return r.get(f"url:{short_code}")

def set_cached_url(short_code: str, long_url: str):
    r.setex(f"url:{short_code}", CACHE_TTL, long_url)

def invalidate_cache(short_code: str):
    r.delete(f"url:{short_code}")