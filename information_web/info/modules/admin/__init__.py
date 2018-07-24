from flask import Blueprint
from flask import redirect
from flask import request
from flask import session
from flask import url_for

admin_blu = Blueprint("admin",__name__,url_prefix='/admin')

from . import views


@admin_blu.before_request
def before_request():
    # 判断如果不是登录页面的请求
    if request.url.endswith(url_for("admin.admin_index")):
        user_id = session.get("user_id")
        # print(user_id,'lllllll')
        is_admin = session.get("is_admin",False)
        # print(is_admin,'oooooooooooo')

        if not (user_id and is_admin):
            # 判断当前是否有用户登录，或者是否是管理员，如果不是，直接重定向到项目主页
            return redirect('/')