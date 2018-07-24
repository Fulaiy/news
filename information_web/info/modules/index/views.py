from flask import current_app, jsonify
from flask import request
from flask import session

from info import constants
from info.models import User, News, Category
from info.utils.response_code import RET
from . import index_blu
from flask import render_template

@index_blu.route('/')
def index():
    user_id = session.get('user_id')
    user = None
    if user_id:
        user = User.query.get(user_id)

    #获取点击排行数据
    # news_list = None
    news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    click_news_list = []
    for news in news_list if news_list else []:
        click_news_list.append(news.to_basic_dict())


    # 获取新闻分类数据
    catagories = Category.query.all()
    categories_list = []
    for category in catagories:
        categories_list.append(category.to_dict())
    # print("--------------")
    # print(categories_list)
    data = {
        'user_info': user.to_dict() if user else None,
        'click_news_list':click_news_list,
        'categories':categories_list
    }

    return render_template('news/index.html',data=data)


@index_blu.route("/newslist")
def get_news_list():
    # 新闻分类的id
    category_id = request.args.get('cid',1)
    # 当前页面表示哪一页的数据
    page = request.args.get('page',1)
    # 每个页面有多少条数据
    per_page = request.args.get('per_page',10)
    # 校验前端传递过来的数据
    try:
        category_id= int(category_id)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        category_id = 1
        page = 1
        per_page = 10

    # 查询数据并分页
    filters = [News.status == 0]
    if category_id != 1:
        filters.append(News.category_id == category_id)

    # paginate: 作用是进行分页
    # 第一个参数：表示当前页面
    # 第二个参数：表示每个页面有多少条数据
    #第三个参数表示没有错误输出
    paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page,per_page,False)
    # items 表示查询出的 当前页的数据
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    news_list = []
    for news in items:
        news_list.append(news.to_dict())


    data = {
        'current_page':current_page,
        "total_page": total_page,
        "news_dict_li":news_list
    }
    return jsonify(errno = RET.OK, errmsg = 'ok', data = data)





@index_blu.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('news/favicon.ico')