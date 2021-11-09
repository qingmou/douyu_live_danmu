# -*- coding:utf-8 -*-
# 本代码基于python3.7
import requests
import re
import execjs
import time
from urllib import parse
import os
import hashlib
import pyperclip
import inspect
import ctypes
import douyu_danmu
from configparser import ConfigParser


''' ------ douyu video start ------ '''
# roomid 直播间id，不一定是真实id，例如：https://m.douyu.com/88888，真实id并非88888

def get_douyu_vurl(roomid):
    dy_did = '3179e930f45e2d6e6cba653200071501'  # cookies中的dy_did
    now_time = int(time.time())
    try:
        source = requests.request("GET", "https://m.douyu.com/" + roomid)
        source = source.text
    except Exception as e:
        print(e)
        return

    # get real rid
    try:
        rid_res = re.search(r'rid":(\d{1,10}),"vipId', source)
        rid = rid_res.group(1)
    except Exception as e:
        print('直播间号错误')
        return
    else:
        print('直播间id：' + rid)

    global g_thread_main, g_thread_keeplive

    ''' get_js start '''
    try:
        result = re.search(r'(function ub98484234.*)\s(var.*)', source).group()
        # print(result)
        func_ub9 = re.sub(r'eval.*;}', 'strc;}', result)  # re.sub 正则表达式替换，参数1表达式 参数2被替换的字符串 参数3被搜寻的字符串
        js = execjs.compile(func_ub9)
        res = js.call('ub98484234')
    except Exception as e:
        print(e)
        return

    try:
        v = re.search(r'"v.*?=\s*(\d+)', res).group(1)
        rb = crypto_md5(rid + dy_did + str(now_time) + v)
        func_sign = re.sub(r'return rt;}\);?', 'return rt;}', res)
        func_sign = func_sign.replace('(function (', 'function sign(')
        func_sign = func_sign.replace('CryptoJS.MD5(cb).toString()', '"' + rb + '"')
        js = execjs.compile(func_sign)
        # print(func_sign)
    except Exception as e:
        print(e)
        return

    try:
        params = js.call('sign', rid, dy_did, now_time)
        params += '&ver=219032101&rid=' + rid + '&rate=1'
        params = dict(parse.parse_qsl(params))
        # print(params)
    except Exception as e:
        print(e)
        return

    try:
        s = requests.Session()
        res = s.post("https://m.douyu.com/api/room/ratestream", params)
        res = res.text
        # print(res)
    except Exception as e:
        print(e)
        return

    try:
        key = re.search(r'dyliveflv1[A-Za-z]?/([A-Za-z0-9]+)', res).group(1)
        live_vurl = 'http://tx2play1.douyucdn.cn/live/' + key + '.xs'

        if os.path.dirname(__file__) == '':
            ffplay_path = 'ffplay.exe'
        else:
            ffplay_path = os.path.dirname(__file__) + r'\ffplay.exe'

        if os.path.exists(ffplay_path):
            nick_title = get_zhubo_info(source)
            hide_log = '-loglevel quiet -stats'
            # x = '-x 1920'
            # y = '-y 1080'
            x = ' '
            y = ' '
            nick_title_info = '-window_title "正在观看直播间：{}{}"'.format(rid, nick_title)
            print('直播流地址：{}'.format(live_vurl))
            print('正在观看直播间：{}{}'.format(rid, nick_title))
            save_roominfo_to_file('roominfo.ini', rid, nick_title[3:])
            ''' ------ douyu danmu start ------ '''
            # 启动弹幕主线程
            douyu_danmu.start_danmu_thread(rid)
            ''' ------ douyu danmu end ------ '''

            # 使用ffplay，需要自行下载放到项目根目录
            os.system('{} {} {} {} {} "{}"'.format(ffplay_path, nick_title_info, x, y, hide_log, live_vurl))  # 使用ffplay播放视频

            # 自定义播放器
            # os.system(r'D:\E\项目\播放器\CoolPlayer.exe "{}"'.format(live_vurl))

        else:
            pyperclip.copy(live_vurl)
            print('执行程序所在文件夹找不到ffplay.exe，直播流地址已复制到剪贴板：' + live_vurl)
    except Exception as e:
        print('主播未开播或其他错误')
        return


    ''' get_js end '''


def crypto_md5(data):
    return hashlib.md5(data.encode('utf-8')).hexdigest()


def get_zhubo_info(source):
    try:
        result = re.findall(r'"nickname":"(.*?)"', source)
        nick = result[0]
        result = re.findall(r'"roomName":"(.*?)"', source)
        title = result[0]
        return ' | 主播：{} | 标题：{}'.format(nick, title)
    except Exception as e:
        print(e)
        return ''


''' ------ douyu video end ------ '''

'''
*** stop thread 结束线程 ***
'''
def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")
def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)


''' 
*** 保存浏览过的直播间信息 ***
*** filename 保存的文件全路径
*** option 配置项名称
*** value 配置项的值
'''
def save_roominfo_to_file(filename, option, value):
    conf = ConfigParser()
    if os.path.exists(filename):
        conf.read(filename, encoding='utf-8')  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    else:
        conf.add_section('RoomInfo')
        fp = open(filename, 'w', encoding='utf-8')
        fp.write('[RoomInfo]')
    conf.set('RoomInfo', option, value)
    # 保存csv
    with open(filename, 'w', encoding='utf-8') as f:
        conf.write(f)


if __name__ == '__main__':
    os.system('color f0')
    while True:
        roomid = input('请输入斗鱼直播间号：')

        if 'douyu.com/' in roomid:
            _roomid = re.search(r'douyu.com/(\d+)', roomid).group(1)

        else:
            _roomid = roomid.strip()

        if _roomid == '':
            continue

        get_douyu_vurl(_roomid)

        try:
            stop_thread(douyu_danmu.g_thread_main)
            stop_thread(douyu_danmu.g_thread_keeplive)
        except Exception as e:
            pass
