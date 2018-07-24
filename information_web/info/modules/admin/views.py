from datetime import datetime, timedelta
import time
from flask import current_app, jsonify
from flask import g
from flask import redirect
from flask import request
from flask import session
from flask import url_for

from info import constants
from info import db
from info.utils.common import user_login_data
from info.models import User, News, Category
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import admin_blu
from flask import render_template

@admin_blu.route('/index')
@user_login_data
def admin_index():
    user = g.user
    data = {
        'user_info': user.to_dict()
    }
    return render_template('admin/index.html',data = data)

@admin_blu.route("/login",methods = ["GET","POST"])
def admin_login():
    if request.method == "GET":
        # 去session 中取指定的值
        user_id = session.get("user_id",None)
        is_admin = session.get("is_admin",None)
        if user_id and is_admin:
            return redirect(url_for("admin.admin_index"))
        return render_template('admin/login.html')

    # 取到登录的参数
    username = request.form.get("username")
    password = request.form.get("password")
    if not all([username, password]):
        return render_template('admin/login.html',errmsg= "参数不全")
    try:
        user = User.query.filter(User.mobile == username).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template('admin/login.html', errmsg="数据查询失败")

    if not user:
        return render_template('admin/login.html', errmsg="用户不存在")

    if not user.check_password(password):
        return render_template('admin/login.html', errmsg="密码错误")

    if not user.is_admin:
        return render_template('admin/login.html', errmsg="用户权限错误")

    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    session["is_admin"] = True

    return redirect(url_for('admin.admin_index'))


@admin_blu.route("/user_count")
def user_count():
    # 当前的总人数
    total_count = 0
    # 每月新增人数
    mon_count = 0
    # 每天新增人数
    day_count = 0
    # 管理员是公司员工，不算是用户，所以需要去掉
    total_count = User.query.filter(User.is_admin == False).count()
    # 获取到本地时间(本月)
    t = time.localtime()
    # 2018-07-01
    mon_time = "%d-%02d-01"%(t.tm_year,t.tm_mon)
    # 2018-07-01 0点0分0秒
    mon_time_begin = datetime.strptime(mon_time,"%Y-%m-%d")
    print(mon_time,"-----",mon_time_begin)

    mon_count = User.query.filter(User.is_admin == False,
                    User.create_time > mon_time_begin).count()

    # 获取到本地时间(当天)
    t = time.localtime()
    # 2018-07-12
    day_time = "%d-%02d-%02d" % (t.tm_year, t.tm_mon,t.tm_mday)
    # 2018-07-12 0点0分0秒
    day_time_begin = datetime.strptime(day_time, "%Y-%m-%d")

    # 查询今天的新增用户
    day_count = User.query.filter(User.is_admin == False,
                        User.create_time > day_time_begin).count()

    # 计算今天的开始时间 2018年7月12号0点0分0秒
    t = time.localtime()
    # 2018-07-12
    today_bigin = "%d-%02d-%02d" % (t.tm_year, t.tm_mon, t.tm_mday)
    # 2018-07-12 0点0分0秒
    today_begin_date = datetime.strptime(today_bigin, "%Y-%m-%d")

    # 人数， 时间
    active_count = []
    active_time = []
    for i in range(0,31):
        # 今天开始时间
        begin_date = today_begin_date - timedelta(days=i)
        # 今天结束时间
        end_date = today_begin_date - timedelta(days=(i-1))

        count = User.query.filter(User.is_admin == False,
                    User.create_time > begin_date,User.create_time < end_date).count()

        active_count.append(count)
        active_time.append(begin_date.strftime("%Y-%m-%d"))


    data = {
        "total_count":total_count,
        "mon_count":mon_count,
        "day_count": day_count,
        "active_count":active_count,
        "active_date":active_time
    }

    return render_template('admin/user_count.html',data = data)



@admin_blu.route("/user_list")
def user_list():
    """获取用户列表"""

    # 获取参数
    page = request.args.get("p",1)
    try:
        page = int(page)
    except Exception as e:
        page = 1

    users = []
    current_page = 1
    total_page = 1

    paginate = User.query.filter(User.is_admin == False).order_by(User.last_login.desc()).paginate(page,10,False)
    users = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    users_list = []
    for user in users:
        users_list.append(user.to_admin_dict())

    data = {
        "total_page":total_page,
        "current_page":current_page,
        "users":users_list
    }

    return render_template('admin/user_list.html',data = data)


@admin_blu.route("/logout")
def admin_logout():
    session.pop("user_id", None)
    session.pop("nick_name", None)
    session.pop("mobile", None)
    session.pop("is_admin", None)

    return redirect('/')


@admin_blu.route("/news_review")
def news_review():
    """
        新闻审核:
        1 这个里面查询的是所有作者发布的新闻,在查询的时候,既然是审核页面,
          那么肯定都是没有通过审核,或者审核中的页面,那么就需要把news.status !=0过滤
        2 新闻审核页面也需要进行分页
        3 通过新闻的标题进行搜索News.title.是否包含当前新闻的关键字,所有的新闻
        :return:
        """
    page = request.args.get("p",1)
    keywords = request.args.get("keywords")
    # print(keywords)
    try:
        page = int(page)
    except Exception as e:
        page = 1
    filter = [News.status != 0]
    # 小编通过关键字进行搜索的时候,不可能每次都会搜索关键字,
    # 所以,需要判断是否有关键字,有关键字才搜索,没有就不需要添加到数据库查询
    if keywords:
        filter.append(News.title.contains(keywords))

    paginate = News.query.filter(*filter).order_by(News.create_time.desc()).paginate(page,10,False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    news_list = []
    for item in items:
        news_list.append(item.to_review_dict())

    data = {
        "news_list":news_list,
        "current_page":current_page,
        "total_page":total_page
    }

    return render_template("admin/news_review.html", data = data)


@admin_blu.route("/news_review_detail", methods = ["GET","POST"])
def news_review_detail():
    if request.method == "GET":
        news_id = request.args.get("news_id")
        news = News.query.get(news_id)
        data = {
            "news":news.to_dict()
        }
        return render_template('admin/news_review_detail.html', data = data)

    # action 表示审核的动作，要么通过accept，要么拒绝reject
    action = request.json.get("action")
    # print(action)
    news_id = request.json.get("news_id")
    # print(news_id)
    # 暂时不需要拿这个参数，因为只有当真正拒绝的时候，才需要给原因
    # reason = request.json.get("reason")
    news = News.query.get(news_id)
    if action == "accept":
        news.status = 0
    else:
        reason = request.json.get("reason")
        if not reason:
            return jsonify(errno = RET.PARAMERR, errmsg = "没写不通过原因")
        news.status = -1
        news.reason = reason

    db.session.commit()
    return jsonify(errno=RET.OK,errmsg="ok")


@admin_blu.route("/news_edit")
def news_edit():
    page = request.args.get("p",1)
    try:
        page = int(page)
    except Exception as e:
        page = 1

    paginate = News.query.order_by(News.create_time.desc()).paginate(page,10,False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    news_list = []
    for item in items:
        news_list.append(item.to_review_dict())

    data = {
        "current_page":current_page,
        "total_page":total_page,
        "news_list":news_list
    }
    return render_template("admin/news_edit.html",data = data)


@admin_blu.route("/news_edit_detail",methods=["GET", "POST"])
def news_edit_detail():
    # 编辑新闻详情
    if request.method == "GET":
        news_id = request.args.get("news_id")
        if not news_id:
            return render_template('admin/news_edit_detail.html', data={"errmsg": "未查询到此新闻"})
        news = News.query.get(news_id)
        if not news:
            return render_template('admin/news_edit_detail.html', data={"errmsg": "未查询到此新闻"})
        # 查询分类的数据
        categories = Category.query.all()
        categories_list = []
        for category in categories:
            c_dict = category.to_dict()
            c_dict["is_selected"] = False
            if category.id == news.category_id:
                c_dict["is_selected"] = True
            categories_list.append(c_dict)
        # 删除“最新”分类
        categories_list.pop(0)
        data = {
            "news":news.to_dict(),
            "categories":categories_list
        }
        return render_template('admin/news_edit_detail.html',data = data)

    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image").read()
    category_id = request.form.get("category_id")

    if not all([title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")
    news = News.query.get(news_id)
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")

    key = storage(index_image)
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.title = title
    news.digest = digest
    news.content = content
    news.category_id = category_id

    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="编辑成功")



@admin_blu.route("/news_type")
def news_type():
    categories = Category.query.all()
    categories_list = []
    for category in categories:
        categories_list.append(category.to_dict())
    categories_list.pop(0)
    data = {
        "categories":categories_list
    }
    return render_template("admin/news_type.html",data = data)



@admin_blu.route("/add_category",methods = ["POST"])
def add_category():
    """增加和修改分类"""

    # id 表示分类id
    id = request.json.get("id")
    name = request.json.get("name")

    if id:
        # 如果有id说明，小编想修改分类的名字
        category = Category.query.get(id)
        category.name = name
        db.session.commit()
    else:
        category = Category()
        category.name = name
        db.session.add(category)
        db.session.commit()

    return jsonify(errno = RET.OK, errmsg = "ok")


@admin_blu.route("/del_category",methods = ["POST"])
def del_category():
    """删除分类"""

    # id 表示分类id
    id = request.json.get("id")
    category = Category.query.get(id)
    db.session.delete(category)
    db.session.commit()

    return jsonify(errno = RET.OK, errmsg = "ok")