import random
import re

from datetime import datetime
from flask import make_response, jsonify
from flask import request
from flask import session

from info import constants, db
from info import redis_store
from info.lib.yuntongxun.sms import CCP
from info.models import User
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET

from . import passport_blu

@passport_blu.route("/image_code")
def get_image_code():
    # 获取当前的图片编号id
    code_id = request.args.get("code_id")
    print("前段生成的UUID：",code_id)
    #获取图片验证码
    # name:表示图片验证码的名字
    # text：表示图片验证码里面的内容
    # image：这个是验证码的图片
    name,text,image = captcha.generate_captcha()
    print("验证码：",text)
    # 保存当前生成的图片验证码内容
    redis_store.set("imagecode_"+code_id,text,constants.IMAGE_CODE_REDIS_EXPIRES)

    #返回响应体内容
    resp = make_response(image)
    #设置内容类型
    resp.headers['Content-Type'] = 'image/jpg'

    return resp


@passport_blu.route("/sms_code",methods = ["POST"])
def send_msg():
    """
    1. 接收参数并判断是否有值
    2. 校验手机号是正确
    3. 通过传入的图片编码去redis中查询真实的图片验证码内容
    4. 进行验证码内容的比对
    5. 生成发送短信的内容并发送短信
    6. redis中保存短信验证码内容
    7. 返回发送成功的响应
    :return:
    """
    # 1. 接收参数并判断是否有值
    mobile = request.json.get("mobile")
    image_code = request.json.get("image_code")
    image_code_id = request.json.get("image_code_id")
    if not all([mobile,image_code,image_code_id]):
        return jsonify(errno = RET.PARAMERR, errmsg = "参数不全")

    # 2 校验手机号是正确
    if not re.match(r"1[35789]\d{9}",mobile):
        return jsonify(errno=RET.DATAERR, errmsg="手机号错误")

    # 3. 通过传入的图片编码去redis中查询真实的图片验证码内容

    real_image_code = redis_store.get("imagecode_"+image_code_id).decode()
    if not real_image_code:
        return jsonify(errno=RET.NODATA, errmsg="验证码已过期")

    # 4. 进行验证码内容的比对
    # lower()  提升用户体验 不区分大小写
    if image_code.lower() != real_image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg="验证码输入错误01")
    # 4.1 校验该手机是否已经注册
    user = User.query.filter(User.mobile==mobile).first()
    if user:
        return jsonify(errno = RET.DATAERR, errmsg = "手机号已经被注册")

    # 5. 生成发送短信的内容并发送短信
    num = random.randint(0,999999)
    sms_code = "%06d"%num
    print("短信验证码为：",sms_code)
    # 使用第三方软件发送短信验证码
    # 第一个参数是 要发送给的号码
    # 第二个参数是验证码 和 验证码有效的时长 分钟
    # 第三个参数 表示模板id 固定写法是1
    # result = CCP().send_template_sms(mobile, [sms_code, 5], 1)
    # if result != 0:
    #     return jsonify(errno = RET.THIRDERR, errmsg = "短信发送失败")

    # 6 redis中保存短信验证码内容
    redis_store.set("sms_"+mobile,sms_code,constants.SMS_CODE_REDIS_EXPIRES)
    # redis_store.setex("sms_"+mobile,constants.SMS_CODE_REDIS_EXPIRES,sms_code)

    # 7.返回发送成功的响应
    return jsonify(errno = RET.OK, errmsg = "发送成功")


@passport_blu.route("/register",methods = ["POST"])
def register():
    """
        1. 获取参数和判断是否有值
        2. 从redis中获取指定手机号对应的短信验证码的
        3. 校验验证码
        4. 初始化 user 模型，并设置数据并添加到数据库
        5. 保存当前用户的状态
        6. 返回注册的结果
        :return:
        """
    #  1. 获取参数和判断是否有值
    mobile = request.json.get("mobile")
    sms_code = request.json.get("smscode")
    password = request.json.get("password")
    print('-----',mobile,sms_code,password)
    if not all([mobile,sms_code,password]):
        return jsonify(errno = RET.PARAMERR,errmsg = "参数不全")
    # 2. 从redis中获取指定手机号对应的短信验证码的
    print(mobile,sms_code,password)
    real_sms_code = redis_store.get("sms_"+mobile)
    if not real_sms_code:
        return jsonify(errno = RET.NODATA, errmsg = "验证码已经过期")
    # 3. 校验验证码
    # 需要解码
    if real_sms_code.decode() != sms_code:
        return jsonify(errno = RET.PARAMERR, errmsg = "验证码输入错误02")
    # 4. 初始化 user 模型，并设置数据并添加到数据库
    user = User()
    user.nick_name = mobile
    user.mobile = mobile
    user.password = password
    user.last_login = datetime.now()
    db.session.add(user)
    db.session.commit()

    # 5. 保存当前用户的状态
    session['user_id'] = user.id
    session['user_nick_name'] = user.nick_name
    session['user_mobile'] = user.mobile

    # 6. 返回注册结果
    print('-----')
    return jsonify(errno=RET.OK, errmsg="OK")


@passport_blu.route("/login",methods = ['POST'])
def login():
    """
        1. 获取参数和判断是否有值
        2. 从数据库查询出指定的用户
        3. 校验密码
        4. 保存用户登录状态
        5. 返回结果
        :return:
        """
    # 1. 获取参数和判断是否有值
    mobile = request.json.get('mobile')
    password = request.json.get('password')
    if not all([mobile,password]):
        return jsonify(errno = RET.PARAMERR,errmsg = "参数不全03")
    # 2. 从数据库查询出指定的用户
    user = User.query.filter(User.mobile == mobile).first()
    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户不存在")
    # 3. 校验密码
    if not user.check_password(password):
        return jsonify(errno=RET.PWDERR, errmsg="密码错误")

    # 4. 保存用户登录状态
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile
    session['is_admin'] = user.is_admin
    user.last_login = datetime.now()
    db.session.commit()

    # 5. 登录成功
    return jsonify(errno=RET.OK, errmsg="OK")



@passport_blu.route("/logout")
def logout():
    session.pop("user_id",None)
    session.pop("nick_name", None)
    session.pop("mobile", None)
    session.pop("is_admin", None)

    return jsonify(errno = RET.OK, errmsg = "OK")
