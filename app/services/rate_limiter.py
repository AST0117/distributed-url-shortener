import redis, os, time

r = redis.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")), decode_responses=True)

BUCKET_CAPACITY = 10      # max tokens
REFILL_RATE = 1           # tokens added per second

def is_allowed(client_id: str) -> bool:
    key = f"ratelimit:{client_id}"
    now = time.time()

    bucket = r.hgetall(key)
    if not bucket:
        tokens = BUCKET_CAPACITY - 1
        r.hset(key, mapping={"tokens": tokens, "last_refill": now})
        r.expire(key, 60)
        return True

    tokens = float(bucket["tokens"])
    last_refill = float(bucket["last_refill"])

    elapsed = now - last_refill
    refill = elapsed * REFILL_RATE
    tokens = min(BUCKET_CAPACITY, tokens + refill)

    if tokens < 1:
        r.hset(key, mapping={"tokens": tokens, "last_refill": now})
        r.expire(key, 60)
        return False

    tokens -= 1
    r.hset(key, mapping={"tokens": tokens, "last_refill": now})
    r.expire(key, 60)
    return True