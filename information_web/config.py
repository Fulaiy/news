
import redis
import logging


class Config(object):
    # DEBUG = True

    SQLALCHEMY_DATABASE_URI = 'mysql://root:mysql@127.0.0.1:3306/information_web'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = '6379'

    SECRET_KEY = 'kjhadhfalhfkahdfiahuwieuilaakl'
    # flask_session 的配置信息
    SESSION_TYPE = 'redis'
    SESSION_USE_SIGNER = True
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST,port=REDIS_PORT)
    PERMANENT_SESSION_LIFETIME = 86400


class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = logging.DEBUG


class ProductionConfig(Config):
    LOG_LEVEL = logging.ERROR



config = {
    'development':DevelopmentConfig,
    'production':ProductionConfig
}