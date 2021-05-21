import os
import random
import re
import textwrap
import time
import traceback
from urllib import parse

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup
from pyaes import AESModeOfOperationCBC
from requests import Session as req_Session

base_headers = {
    "Accept":
    "*/*",
    "Accept-Encoding":
    "gzip, deflate, br",
    "Accept-Language":
    "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36 Edg/90.0.818.62"
}

# 代理配置
proxy = '127.0.0.1:10809'
# proxies = {'http': 'http://' + proxy, 'https': 'https://' + proxy} # urllib3(1.25.10) 旧版本写法
# proxies = {'http': proxy, 'https': proxy}  # urllib3(1.26.4) 新版本写法
proxies = {}

# 签到成功后，是否发送信息到TG，如果为True，需要设置两个环境变量TG_CHAT_ID、TG_BOT_TOKEN
send_points_to_tg_flag = True

sched = BlockingScheduler()


# 随机生成用户空间链接
def randomly_gen_uspace_url() -> list:
    url_list = []
    # 访问小黑屋用户空间不会获得积分、生成的随机数可能会重复，这里多生成两个链接用作冗余
    for i in range(15):
        uid = random.randint(10000, 50000)
        url = "https://hostloc.com/space-uid-{}.html".format(str(uid))
        url_list.append(url)
    return url_list


# 使用Python实现防CC验证页面中JS写的的toNumbers函数
def toNumbers(secret: str) -> list:
    text = []
    for value in textwrap.wrap(secret, 2):
        text.append(int(value, 16))
    return text


# 不带Cookies访问论坛首页，检查是否开启了防CC机制，将开启状态、AES计算所需的参数全部放在一个字典中返回
def check_anti_cc() -> dict:
    result_dict = {}
    headers = {
        "user-agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36 Edg/90.0.818.62"
    }
    home_page = "https://hostloc.com/forum.php"
    res = requests.get(home_page, headers=headers)
    aes_keys = re.findall('toNumbers\("(.*?)"\)', res.text)
    cookie_name = re.findall('cookie="(.*?)="', res.text)

    if len(aes_keys) != 0:  # 开启了防CC机制
        print("检测到防 CC 机制开启！")
        if len(aes_keys) != 3 or len(
                cookie_name) != 1:  # 正则表达式匹配到了参数，但是参数个数不对（不正常的情况）
            result_dict["ok"] = 0
        else:  # 匹配正常时将参数存到result_dict中
            result_dict["ok"] = 1
            result_dict["cookie_name"] = cookie_name[0]
            result_dict["a"] = aes_keys[0]
            result_dict["b"] = aes_keys[1]
            result_dict["c"] = aes_keys[2]
    else:
        pass

    return result_dict


# 在开启了防CC机制时使用获取到的数据进行AES解密计算生成一条Cookie（未开启防CC机制时返回空Cookies）
def gen_anti_cc_cookies() -> dict:
    cookies = {}
    anti_cc_status = check_anti_cc()

    if anti_cc_status:  # 不为空，代表开启了防CC机制
        if anti_cc_status["ok"] == 0:
            print("防 CC 验证过程所需参数不符合要求，页面可能存在错误！")
        else:  # 使用获取到的三个值进行AES Cipher-Block Chaining解密计算以生成特定的Cookie值用于通过防CC验证
            print("自动模拟计算尝试通过防 CC 验证")
            a = bytes(toNumbers(anti_cc_status["a"]))
            b = bytes(toNumbers(anti_cc_status["b"]))
            c = bytes(toNumbers(anti_cc_status["c"]))
            cbc_mode = AESModeOfOperationCBC(a, b)
            result = cbc_mode.decrypt(c)

            name = anti_cc_status["cookie_name"]
            cookies[name] = result.hex()
    else:
        pass

    return cookies


# 登录帐户
def login(username: str, password: str) -> req_Session:
    headers = {
        "user-agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36 Edg/90.0.818.62",
        "origin": "https://hostloc.com",
        "referer": "https://hostloc.com/forum.php",
    }
    login_url = "https://hostloc.com/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes&inajax=1"
    login_data = {
        "fastloginfield": "username",
        "username": username,
        "password": password,
        "quickforward": "yes",
        "handlekey": "ls",
    }

    s = req_Session()
    s.headers.update(headers)
    s.cookies.update(gen_anti_cc_cookies())
    res = s.post(url=login_url, data=login_data)
    res.raise_for_status()
    return s


# 通过抓取用户设置页面的标题检查是否登录成功
def check_login_status(s: req_Session, number_c: int) -> bool:
    test_url = "https://hostloc.com/home.php?mod=spacecp"
    res = s.get(test_url)
    res.raise_for_status()
    res.encoding = "utf-8"
    test_title = re.findall("<title>(.*?)<\/title>", res.text)

    if len(test_title) != 0:  # 确保正则匹配到了内容，防止出现数组索引越界的情况
        if test_title[0] != "个人资料 -  全球主机交流论坛 -  Powered by Discuz!":
            print("第", number_c, "个帐户登录失败！")
            return False
        else:
            print("第", number_c, "个帐户登录成功！")
            return True
    else:
        print("无法在用户设置页面找到标题，该页面存在错误或被防 CC 机制拦截！")
        return False


# 抓取并打印输出帐户当前积分
def print_current_points(s: req_Session):
    test_url = "https://hostloc.com/forum.php"
    res = s.get(test_url)
    res.raise_for_status()
    res.encoding = "utf-8"
    points = re.findall("积分: (\d+)", res.text)

    if len(points) != 0:  # 确保正则匹配到了内容，防止出现数组索引越界的情况
        print("帐户当前积分：" + points[0])
    else:
        print("无法获取帐户积分，可能页面存在错误或者未登录！")
    time.sleep(5)


# 依次访问随机生成的用户空间链接获取积分
def get_points(s: req_Session, number_c: int):
    if check_login_status(s, number_c):
        # print_current_points(s)  # 打印帐户当前积分
        url_list = randomly_gen_uspace_url()
        # 依次访问用户空间链接获取积分，出现错误时不中断程序继续尝试访问下一个链接
        for i in range(len(url_list)):
            url = url_list[i]
            try:
                res = s.get(url)
                res.raise_for_status()
                print("第", i + 1, "个用户空间链接访问成功")
                time.sleep(random.randint(8, 16))  # 每访问一个链接后休眠5秒，以避免触发论坛的防CC机制
            except Exception as e:
                print("链接访问异常：" + str(e))
                traceback.print_exc()
        # print_current_points(s)  # 再次打印帐户当前积分
        time.sleep(5)
        if send_points_to_tg_flag:
            print("发送信息到TG")
            send_points_to_tg(s)
    else:
        print("请检查你的帐户是否正确！")


# 打印输出当前ip地址
def print_my_ip():
    api_url = "https://api.ipify.org/"
    try:
        res = requests.get(url=api_url)
        res.raise_for_status()
        res.encoding = "utf-8"
        print("当前使用 ip 地址：" + res.text)
    except Exception as e:
        print("获取当前 ip 地址失败：" + str(e))
        traceback.print_exc()


def send_points_to_tg(s: req_Session, retry_count: int = 1):
    '''获取积分、威望、金钱数据，并发送到TG'''
    try:
        resp = s.get("https://hostloc.com/forum.php")

        # 昵称
        soup = BeautifulSoup(resp.text, "html.parser")
        nickname = str(soup.find("strong", class_="vwmy").a.string)
        print("昵称：{}".format(nickname))

        # 获取积分
        # >积分: 7318<
        search_obj = re.search(">(积分: \d+)<", resp.text)
        extcredit = "积分: 0"
        if search_obj:
            extcredit = search_obj.group(1)
        print(extcredit)

        time.sleep(5)
        # 获取威望、金钱
        resp = s.get(
            "https://hostloc.com/home.php?mod=spacecp&ac=credit&showcredit=1&inajax=1&ajaxtarget=extcreditmenu_menu"
        )

        # 威望 id="hcredit_1">323<
        search_obj = re.search('id="hcredit_1">(\d+)<', resp.text)
        hcredit_1 = "威望: 0"
        if search_obj:
            hcredit_1 = "威望: {}".format(search_obj.group(1))
        print(hcredit_1)

        # 金钱 id="hcredit_2">7189<
        search_obj = re.search('id="hcredit_2">(\d+)<', resp.text)
        hcredit_2 = "金钱: 0"
        if search_obj:
            hcredit_2 = "金钱: {}".format(search_obj.group(1))
        print(hcredit_2)

        msg = '''*{}*  
*{}*，获取积分成功  
{}，{}，{}'''.format(mark_down("[全球主机交流论坛]"), nickname, extcredit, hcredit_1,
                   hcredit_2)

        send_message_to_tg(msg)
    except:
        print("获取积分、威望、金钱数据发送到TG失败")
        traceback.print_exc()
        time.sleep(5)
        if retry_count > 0:
            send_points_to_tg(s, retry_count - 1)


def mark_down(content: str):
    '''特殊字符前面加上反斜杠进行转义'''
    sign = [
        '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|',
        '{', '}', '.', '!'
    ]
    for k in sign:
        content = content.replace(k, '\\' + k)
    return content


def send_message_to_tg(text: str, retry_count: int = 2):
    '''推送消息到TG'''
    if not text:
        return

    tg_chat_id = os.environ["TG_CHAT_ID"]
    tg_bot_token = os.environ["TG_BOT_TOKEN"]

    try:
        text = parse.quote(text)
        post_url = 'https://api.telegram.org/{}/sendMessage?parse_mode=MarkdownV2&chat_id={}&text={}'.format(
            tg_bot_token, tg_chat_id, text)
        requests.get(post_url, headers=base_headers, proxies=proxies)
    except:
        print("推送失败！")
        traceback.print_exc()
        time.sleep(3)
        if retry_count > 0:
            send_message_to_tg(text, retry_count - 1)


@sched.scheduled_job('cron', hour=20, minute=35)
def main():
    username = os.environ["HOSTLOC_USERNAME"]
    password = os.environ["HOSTLOC_PASSWORD"]

    # 分割用户名和密码为列表
    user_list = username.split(",")
    passwd_list = password.split(",")

    if not username or not password:
        print("未检测到用户名或密码，请检查环境变量是否设置正确！")
    elif len(user_list) != len(passwd_list):
        print("用户名与密码个数不匹配，请检查环境变量设置是否错漏！")
    else:
        print_my_ip()
        print("共检测到", len(user_list), "个帐户，开始获取积分")
        print("*" * 30)

        # 依次登录帐户获取积分，出现错误时不中断程序继续尝试下一个帐户
        for i in range(len(user_list)):
            try:
                s = login(user_list[i], passwd_list[i])
                get_points(s, i + 1)
                print("*" * 30)
                time.sleep(random.randint(15, 20))
            except Exception as e:
                print("程序执行异常：" + str(e))
                print("*" * 30)
                traceback.print_exc()

        print("程序执行完毕，获取积分过程结束")


sched.start()
