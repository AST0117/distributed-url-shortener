import pymysql, redis, os
from dotenv import load_dotenv
load_dotenv()

conn = pymysql.connect(host=os.getenv("MYSQL_HOST"), user=os.getenv("MYSQL_USER"),
                        password=os.getenv("MYSQL_PASSWORD"), database=os.getenv("MYSQL_DB"))
print("MySQL connected:", conn.open)

r = redis.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")))
r.set("test", "ok")
print("Redis connected:", r.get("test"))