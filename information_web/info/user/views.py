from flask import current_app
from flask import g,redirect, jsonify
from flask import request
from flask import session


from info import constants
from info import db
from info.models import Category, News
from info.utils.image_storage import storage
from info.utils.response_code import RET

from info.utils.common import user_login_data
from flask import render_template
from . import profile_blu
@profile_blu.route("/info")
@user_login_data
def user_info():

    user = g.user
    if not user:
        return redirect('/')


    data = {
        'user_info': user.to_dict() if user else None
    }

    return render_template('news/user.html',data = data)


@profile_blu.route("/base_info", methods = ["GET","POST"])
@user_login_data
def base_info():
    user = g.user
    if request.method == "GET":
        # print("---------")
        data = {
            'user_info': user.to_dict() if user else None
        }
        return render_template("news/user_base_info.html", data = data)
    nick_name = request.json.get("nick_name")
    # 获取到用户的签名
    signature = request.json.get("signature")
    # 获取到用户的性别
    gender = request.json.get("gender")

    user.nick_name = nick_name
    user.signature = signature
    user.gender = gender

    db.session.commit()

    # 将 session 中保存的数据进行实时更新
    session["nick_name"] = nick_name

    return jsonify(errno = RET.OK, errmsg = "修改成功")


@profile_blu.route("/pic_info",methods = ["GET","POST"])
@user_login_data
def pic_info():
    user = g.user
    if request.method == "GET":
        data = {
            'user_info': user.to_dict() if user else None
        }

        return render_template("news/user_pic_info.html", data = data)
    # 因为下面 storage(avatar) 括号里面的参数要是 二进制的
    # request.files.get("avatar").read() 所以后面要加上  .read()
    avatar = request.files.get("avatar").read()
    #传图片
    key = storage(avatar)
    user.avatar_url = key
    db.session.commit()
    data = {
        "avatar_url": constants.QINIU_DOMIN_PREFIX + key
    }

    return jsonify(errno = RET.OK, errmsg = "上传成功",data = data)



@profile_blu.route("/pass_info",methods = ["GET","POST"])
@user_login_data
def pass_info():
    user = g.user
    if request.method == "GET":
        #  能进入到密码修改说明肯定是登录了
        # data = {
        #     'user_info': user.to_dict() if user else None
        # }
        return render_template("news/user_pass_info.html")
    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")

    if not user.check_password(old_password):
        return jsonify(errno = RET.PWDERR, errmsg = "旧密码错误")

    user.password = new_password
    db.session.commit()
    print("ok")
    return jsonify(errno = RET.OK, errmsg = "密码修改成功")


@profile_blu.route("/collection")
@user_login_data
def user_collection():
    p = request.args.get("p",1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user = g.user
    collections = []
    current_page = 1
    total_page = 1
    try:
        paginate = user.collection_news.paginate(p,2,False)
        # 获取分页数据
        collections = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    # 收藏列表
    collection_dict = []
    for news in collections:
        collection_dict.append(news.to_basic_dict())

    data = {
        "collections":collection_dict,
        "current_page":current_page,
        "total_page":total_page
    }

    return render_template("news/user_collection.html",data = data)


@profile_blu.route("/news_release",methods = ["GET","POST"])
@user_login_data
def news_release():
    user = g.user
    if request.method == 'GET':
        categorys = Category.query.all()
        categories_dicts = []
        for category in categorys:
            categories_dicts.append(category.to_dict())
            # 删除第0个位置的元素（最新）
        categories_dicts.pop(0)
        return render_template('news/user_news_release.html',
                data = {"categories":categories_dicts})


    # 获取要提交的数据
    title = request.form.get("title")
    source = "个人发布"
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image").read()
    category_id = request.form.get("category_id")

    if not all([title,source,digest,content,index_image,category_id]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数有误")


    index_image = storage(index_image)

    news = News()
    news.title = title
    news.source = source
    news.digest = digest
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + index_image
    news.category_id = category_id
    news.user_id = user.id
    news.status = 1
    db.session.add(news)
    db.session.commit()

    return jsonify(errno=RET.OK,errmsg="发布成功，等待审核")


@profile_blu.route('/news_list')
@user_login_data
def user_news_list():
    user = g.user
    page = request.args.get("p",1)
    try:
        page = int(page)
    except Exception as e:
        page = 1

    paginate = News.query.filter(News.user_id == user.id).paginate(page,5,False)

    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    news_list = []
    for news in items:
        news_list.append(news.to_review_dict())

    data = {
        "news_list":news_list,
        "current_page":current_page,
        "total_page":total_page
    }



    return render_template('news/user_news_list.html', data = data)


@profile_blu.route("/user_follow")
@user_login_data
def user_follow():
    p = request.args.get("p",1)

    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user = g.user
    follows = []
    current_page = 1
    total_page = 1
    paginate = user.followed.paginate(p,constants.USER_FOLLOWED_MAX_COUNT,False)
    follows = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    follows_list = []
    for follow in follows:
        follows_list.append(follow.to_dict())

    data = {
        "users":follows_list,
        "current_page":current_page,
        "total_page":total_page
    }
    return render_template('news/user_follow.html', data = data)