from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import redis

db = SQLAlchemy()
migrate = Migrate()
redis_client = None


def init_redis(app):
    global redis_client
    redis_client = redis.from_url(
        app.config['REDIS_URL'],
        decode_responses=True
    )
    return redis_client
