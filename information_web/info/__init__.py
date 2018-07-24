
import redis
from flask import Flask,render_template
import logging
from logging.handlers import RotatingFileHandler

from flask import g

from flask_sqlalchemy import SQLAlchemy
from config import Config,config
from flask_wtf.csrf import CSRFProtect,generate_csrf
from flask_session import Session


db = SQLAlchemy()
redis_store = None


def create_app(config_name):

    setup_log(config_name)
    app = Flask(__name__)

    app.config.from_object(config[config_name])
    db.init_app(app)
    global redis_store
    redis_store = redis.StrictRedis(host=Config.REDIS_HOST,port=Config.REDIS_PORT)
    CSRFProtect(app)
    @app.after_request
    def after_request(response):
        csrf_token = generate_csrf()
        response.set_cookie("csrf_token",csrf_token)
        print(g.csrf_token)
        return response
    Session(app)
    from info.modules.index import index_blu
    app.register_blueprint(index_blu)
    from info.modules.passport import passport_blu
    app.register_blueprint(passport_blu)
    from info.modules.news import news_blu
    app.register_blueprint(news_blu)
    from info.user import profile_blu
    app.register_blueprint(profile_blu)
    from info.modules.admin import admin_blu
    app.register_blueprint(admin_blu)
    # 添加自定义过滤器
    from info.utils.common import filer_index_class
    #第一个参数为自定义的函数  第二个参数为 过滤器的名称
    app.add_template_filter(filer_index_class,"indexClass")
    from info.utils.common import user_login_data
    @app.errorhandler(404)
    @user_login_data
    # 注意 因为上面写了404 所以下面函数里面也要传一个参数
    def page_not_found(_):
        user = g.user
        data = {
            "user_info":user.to_dict() if user else  None
        }
        return render_template('news/404.html',data = data)

    return app


def setup_log(config_name):
    """配置日志"""

    # 设置日志的记录等级
    logging.basicConfig(level=config[config_name].LOG_LEVEL)  # 调试debug级
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)