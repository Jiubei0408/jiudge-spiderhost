import redis

from app.config.secure import REDIS_PASSWORD, REDIS_HOST, REDIS_PORT

queue = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)
