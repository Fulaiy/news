from flask import current_app
from flask import request, jsonify
from flask import session,g

from info import db
from info.utils.common import user_login_data
from info.models import User, News, Comment, CommentLike
from info.utils.response_code import RET
from . import news_blu
from flask import Flask,render_template

@news_blu.route("/<int:news_id>")
@user_login_data
def news_detail(news_id):
    user = g.user
    # 获取点击排行数据
    # news_list = None
    news_list = News.query.order_by(News.clicks.desc()).limit(10)
    click_news_list = []
    for new in news_list if news_list else []:
        click_news_list.append(new.to_basic_dict())

    news = News.query.get(news_id)
    news.clicks += 1
    db.session.commit()

    comments = []
    comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    # comment_list = []
    # for item in comments:
    #     comment_list.append(item.to_dict())

    # 点赞相关

    comment_likes = []
    comment_like_ids = []
    if user:
        # 查询处理所有的点赞数
        comment_likes = CommentLike.query.filter(CommentLike.user_id == user.id).all()
        comment_like_ids = [comment_like.comment_id for comment_like in comment_likes]

    comment_list = []
    for comment in comments:
        comment_dict = comment.to_dict()
        # 评论默认为未点赞 设为False 如果已经点赞 设置为True
        comment_dict["is_like"] = False
        if comment.id in comment_like_ids:
            comment_dict["is_like"] = True
        comment_list.append(comment_dict)
    # 当前登录用户是否关注当前新闻作者
    is_followed = False
    # 判断用户是否收藏过该新闻
    is_collected = False
    if user:
        if news in user.collection_news:
            is_collected = True
        # 判断当前登录的用户是否关注当前新闻的作者
        if news.user in user.followed:
            is_followed = True

    data = {
        'user_info': user.to_dict() if user else None,
        'click_news_list': click_news_list,
        'news':news.to_dict(),
        'is_collected': is_collected,
        'comments':comment_list,
        "is_followed":is_followed
    }
    return render_template('news/detail.html',data = data)


@news_blu.route("/news_collect",methods = ["POST"])
@user_login_data
def news_collect():
    user = g.user
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    if not news_id:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ("collect", "cancel_collect"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    news = News.query.get(news_id)

    if action == 'collect':
        user.collection_news.append(news)
    else:
        user.collection_news.remove(news)

    db.session.commit()
    return jsonify(errno = RET.OK, errmsg = "收藏成功")



@news_blu.route("/news_comment",methods = ['POST'])
@user_login_data
def news_comment():
    """添加评论"""

    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    news_id = request.json.get('news_id')
    comment_str = request.json.get('comment')
    parent_id = request.json.get('parent_id')

    if not all([news_id, comment_str]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    news = News.query.get(news_id)
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="该新闻不存在")

    # 初始化模型 保存到数据库
    comment = Comment()
    comment.news_id = news_id
    comment.user_id = user.id
    comment.content = comment_str
    if parent_id:
        comment.parent_id = parent_id
    db.session.add(comment)
    db.session.commit()


    return jsonify(errno=RET.OK, errmsg="评论成功", data=comment.to_dict())


@news_blu.route("/comment_like",methods = ["POST"])
@user_login_data
def comment_like():
    user = g.user
    comment_id = request.json.get("comment_id")
    news_id = request.json.get("news_id")
    action = request.json.get("action")
    """
        评论点赞：
        １ 评论点赞都是用户进行点赞，所以首先判断用户是否已经登陆
        ２ 在进行点赞的时候，那么这条评论肯定是需要存在的，所以通过评论id进行查
    询一下，当前这条评论是否存在
        3   判断当前用户的作用，是想进行点赞，还是想进行取消点赞
        4   需要查询当前这条评论，用户是否已经点赞，如果已经点赞，在点击就是取
    消，如果没有点赞，在点击就是进行点赞
        5   如果需要符合点赞的条件，那么必须要知道当前这条点赞的评论是谁进行的点
    赞，页就是查询user_id ,还必须满足当前评论必须存在，所以查询评论的id
    """
    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg = "用户未登录")

    comment = Comment.query.get(comment_id)
    if action == "add":
        comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id,CommentLike.user_id == user.id).first()

        if not comment_like:
            comment_like = CommentLike()
            comment_like.comment_id = comment.id
            comment_like.user_id = user.id

            db.session.add(comment_like)
            # 点赞完成后，点赞的条数必须加1
            comment.like_count += 1
    else:
        # 取消点赞
        comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id,CommentLike.user_id == user.id).first()
        if comment_like:
            db.session.delete(comment_like)
            # 点赞取消后，点赞的条数必须减1
            comment.like_count -= 1

    db.session.commit()

    return jsonify(errno = RET.OK, errmsg = "ok")


@news_blu.route("/followed_user",methods = ["POST"])
@user_login_data
def followed_user():
    # 关注或者取消关注
    if not g.user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    user_id = request.json.get("user_id")  # 被关注的用户id
    action = request.json.get("action")
    if not all([user_id,action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ("follow", "unfollow"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

        # 查询到关注的用户信息
    try:
        target_user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据库失败")

    if not target_user:
        return jsonify(errno=RET.NODATA, errmsg="未查询到用户数据")

    # 根据不同操作做不同逻辑
    if action == "follow":
        if target_user.followers.filter(User.id == g.user.id).count() > 0:
            return jsonify(errno=RET.DATAEXIST, errmsg="当前已关注")
        target_user.followers.append(g.user)
    else:
        if target_user.followers.filter(User.id == g.user.id).count() > 0:
            target_user.followers.remove(g.user)

    # 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据保存错误")

    return jsonify(errno=RET.OK, errmsg="操作成功")