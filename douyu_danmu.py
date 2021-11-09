import websocket
import threading
import time
import re

global g_rid, g_thread_main, g_thread_keeplive

class DouYuDanMuData():
    # 将字符串数据按照斗鱼协议封装为字节流
    def dy_encode(self, msg):
        # 头部8字节，尾部1字节，与字符串长度相加即数据长度
        # 为什么不加最开头的那个消息长度所占4字节呢？这得问问斗鱼^^
        data_len = len(msg) + 9
        # 字符串转化为字节流
        msg_byte = msg.encode('utf-8')
        # 将数据长度转化为小端整数字节流
        len_byte = int.to_bytes(data_len, 4, 'little')
        # 前两个字节按照小端顺序拼接为0x02b1，转化为十进制即689（《协议》中规定的客户端发送消息类型）
        # 后两个字节即《协议》中规定的加密字段与保留字段，置0
        send_byte = bytearray([0xb1, 0x02, 0x00, 0x00])
        # 尾部以'\0'结束
        end_byte = bytearray([0x00])
        # 按顺序拼接在一起
        data = len_byte + len_byte + send_byte + msg_byte + end_byte
        return data

    # 发送登录请求消息
    def ws_login_str(self, rid):
        msg = 'type@=loginreq/roomid@={}/'.format(rid)
        msg_bytes = self.dy_encode(msg)
        return msg_bytes

    # 发送入组消息
    def ws_join_group_str(self, rid):
        msg = 'type@=joingroup/rid@={}/gid@=-9999/'.format(rid)
        msg_bytes = self.dy_encode(msg)
        return msg_bytes

    # 保持在线，防止被踢出弹幕服务器
    def ws_keeplive(self, ws):
        while True:
            time.sleep(40)  # 防踢心跳包每40秒执行一次
            msg = 'type@=mrkl/'
            msg_bytes = self.dy_encode(msg)
            ws.send(msg_bytes)

    # 处理message消息数据
    def process_message_data(self, message):
        message = message.split('/') # 分割message字符串为列表list

        cache_list = [] # 重组列表list
        cache_num = 0
        type_order_list = []  # 把type键出现的位置存入list列表中
        for item in message:
            re_res = re.findall('\W(type@=\S+)', item)
            if len(re_res) != 0:
                item = re_res[0]  # 去除冗余不可识别的字符
                type_order_list.append(cache_num)
            if item != '\x00':  # 如果item为空则略过此处
                cache_list.append(item)
            cache_num += 1

        if len(type_order_list) > 1:  # 如果所取出含type的list长度大于1
            for item in range(len(type_order_list)):
                start = type_order_list[item]
                if item != len(type_order_list) - 1:
                    end = type_order_list[item + 1]
                    cache_list_part = cache_list[start:end]  # 根据type_order_list按段分割list
                else:
                    cache_list_part = cache_list[start:]  # 根据type_order_list按段分割list
                self.process_list_data(cache_list_part)
        else:
            self.process_list_data(cache_list)


    # 将所取到的list转化为dict字典，再根据key取出value的值
    def process_list_data(self, cache_list_part):
        cache_dict = {}
        for i in cache_list_part:
            item_list = i.split('@=')
            key = item_list[0]
            if '\x00' in key:
                re_res = re.findall('\W(\w+)', key)
                key = re_res[0]
            value = item_list[1]
            cache_dict[key] = value

        ''' 获取具体数据 开始'''
        # *** chatmsg 弹幕消息***
        typer = cache_dict.get('type')  # 类型
        rid = cache_dict.get('rid')  # 所在直播间id
        uid = cache_dict.get('uid')  # 发送者uid
        nn = cache_dict.get('nn')  # 发送者昵称
        nn = self.str_replace(nn)
        txt = cache_dict.get('txt')  # 弹幕文本内容
        txt = self.str_replace(txt)
        cid = cache_dict.get('cid')  # 弹幕唯一id

        col = cache_dict.get('col')  # 颜色：默认值 0（表示默认颜色弹幕）
        ct = cache_dict.get('ct')  # 客户端类型：默认值 0

        gt = cache_dict.get('gt')  # 礼物头衔:默认值0(表示没有头衔)
        rg = cache_dict.get('rg')  # 房间权限组:默认值1(表示普通权限用户)
        pg = cache_dict.get('pg')  # 平台身份组:默认值1(表示普通权限用户)

        dlv = cache_dict.get('dlv')  # 酬勤等级：默认值 0（表示没有酬勤）
        dc = cache_dict.get('dc')  # 酬勤数量：默认值 0（表示没有酬勤数量）
        bdlv = cache_dict.get('bdlv')  # 最高酬勤等级：默认值 0（表示全站都没有酬勤）

        cmt = cache_dict.get('cmt')  # 弹幕具体类型: 默认值 0（普通弹幕）
        sahf = cache_dict.get('sahf')  # 扩展字段，一般不使用，可忽略

        level = cache_dict.get('level')  # 用户等级
        ic = cache_dict.get('ic')  # 头像
        ic = self.str_replace(ic)
        ic = 'https://apic.douyucdn.cn/upload/{}_middle.jpg'.format(ic)

        nl = cache_dict.get('nl')  # 贵族等级
        nc = cache_dict.get('ic')  # 贵族弹幕标识,0-非贵族弹幕,1-贵族弹幕,默认值 0

        gatin = cache_dict.get('gatin')  # 进入网关服务时间戳
        chtin = cache_dict.get('chtin')  # 进入房间服务时间戳
        repin = cache_dict.get('repin')  # 进入发送服务时间戳

        receive_uid = cache_dict.get('receive_uid')  # 所在直播间主播uid
        receive_nn = cache_dict.get('receive_nn')  # 所在直播间主播昵称
        receive_nn = self.str_replace(receive_nn)

        bnn = cache_dict.get('bnn')  # 徽章昵称（粉丝牌）
        bnn = self.str_replace(bnn)
        bl = cache_dict.get('bl')  # 徽章等级（粉丝等级）
        brid = cache_dict.get('brid')  # 徽章（粉丝牌）所在直播间id
        hc = cache_dict.get('hc')  # 徽章（粉丝牌）信息校验码

        urlev = cache_dict.get('urlev')  # 房间等级
        gid = cache_dict.get('gid')  # 弹幕分组id

        ol = cache_dict.get('ol')  # 主播等级
        rev = cache_dict.get('rev')  # 是否反向弹幕标记: 0-普通弹幕，1-反向弹幕, 默认值 0
        hl = cache_dict.get('hl')  # 是否高亮弹幕标记: 0-普通，1-高亮, 默认值 0
        ifs = cache_dict.get('ifs')  # 是否粉丝弹幕标记: 0-非粉丝弹幕，1-粉丝弹幕, 默认值 0
        p2p = cache_dict.get('p2p')  # 服务功能字段
        el = cache_dict.get('ol')  # 用户获得的连击特效：数组类型，数组包含 eid（特效 id）,etp（特效类型）,sc（特效次数）信息，ef（特效标志）。

        # *** dgb 赠送礼物 ***
        gfid = cache_dict.get('gfid')  # 礼物id，详见函数giftid_get_giftnn()
        gs = cache_dict.get('gs')  # 礼物显示样式
        bg = cache_dict.get('bg')  # 大礼物标识：默认值为 0（表示是小礼物）
        eid = cache_dict.get('eid')  # 礼物关联的特效 id
        dw = cache_dict.get('dw')  # 主播体重
        gfcnt = cache_dict.get('gfcnt')  # 礼物个数:默认值1(表示1个礼物)
        hits = cache_dict.get('hits')  # 礼物连击次数:默认值1(表示1连击)
        bdl = cache_dict.get('bdl')  # 全站最高酬勤等级：默认值 0（表示全站都没有酬勤）

        # *** uenter 用户进入直播间 ***
        strr = cache_dict.get('str')  # 战斗力
        crw = cache_dict.get('crw')  # 用户栏目上周排名
        rpid = cache_dict.get('rpid')  # 红包id:默认值0(表示没有红包)
        slt = cache_dict.get('slt')  # 红包开启剩余时间:默认值0(表示没有红包)
        elt = cache_dict.get('elt')  # 红包销毁剩余时间:默认值0(表示没有红包)

        # *** blab 粉丝等级升级 ***
        lbl = cache_dict.get('lbl')  # 上个徽章等级

        # *** newblackres 禁言操作 ***
        otype = cache_dict.get('otype')  # 操作者类型，0：普通用户，1：房管：，2：主播，3：超管
        if otype == '0':
            otype_status = '[普通用户]'
        elif otype == '1':
            otype_status = '[房管]'
        elif otype == '2':
            otype_status = '[主播]'
        elif otype == '3':
            otype_status = '[超管]'
        else:
            otype_status = ''
        sid = cache_dict.get('sid')  # 操作者 id
        did = cache_dict.get('did')  # 被操作者 id
        snic = cache_dict.get('snic')  # 操作者昵称
        dnic = cache_dict.get('dnic')  # 被禁言用户昵称
        d_time = cache_dict.get('time')  # 禁言的失效时间戳
        ''' 获取具体数据 结束'''

        '''
        type类型：
        loginres 登入房间，chatmsg 弹幕消息，uenter 进入房间，dgb 赠送礼物，upgrade 用户等级提升
        rss 房间开播提醒，al 主播离开提醒，ab 主播回来继续直播提醒
        bc_buy_deserve 赠送酬勤通知，ssd 超级弹幕，spbc 房间内礼物广播，onlinegift 领取在线鱼丸
        ggbb 房间用户抢红包，rankup 房间内top10变化消息，ranklist 广播排行榜消息，mrkl 心跳包
        erquizisn 鱼丸预言，blab 粉丝等级升级，frank 粉丝排行榜消息，srres 用户分享了直播间通知，ranklist 广播排行榜消息
        rtss_complete 星级挑战完成
        fswrank 未知，gbroadcast 未知，rtss_update 未知，ro_date_succ 未知，cthn 未知
        '''

        filter_kw_list = [
            'loginres', 'synexp', 'noble_num_info', 'pingreq', 'qausrespond', 'frank', 'fswrank',
            'ranklist', 'mrkl', 'gbroadcast', 'rtss_update', 'ro_date_succ', 'ro_game_succ', 'configscreen',
            'nlpkseason', 'anbc', 'wirt', 'rtss_complete', 'rankup', 'tsgs', 'tsboxb', 'rquizisn', 'cthn',
            'mfcdopenx', 'lucky_wheel_pool', 'rankl_hend', 'erquizisn'
        ]
        ''' 按type类型处理不同消息 '''
        if typer == 'chatmsg':
            # print(cache_dict)
            info = '[LV{}]{}：{}'.format(level, nn, txt)
            print(info)
        elif typer == 'uenter':
            info = '[LV{}]{}进入直播间'.format(level, nn)
            # print(info)
        elif typer == 'dgb':
            gfid = self.giftid_get_giftnn(gfid)
            info = '[LV{}]{} 送出 {} x {}'.format(level, nn, gfid, gfcnt)
            # print(info)
        elif typer == 'upgrade':
            info = '{} 等级升级到 [LV{}]'.format(nn, level)
            # print(info)
        elif typer == 'blab':
            info = '{} 粉丝等级升级到 [LV{}]，主播更爱你哟'.format(nn, bl)
            # print(info)
        elif typer == 'newblackres':
            time_array = time.localtime(int(d_time))
            d_time = time.strftime('%Y-%m-%d %H:%M:%S', time_array)
            info = '{} 已被 {}{} 禁言，解除时间：{}'.format(dnic, otype_status, snic, d_time)
            # print(info)
        elif typer == 'rank_change':
            rn = cache_dict.get('rn')
            rname = cache_dict.get('rname')  # 排行榜名称，例如 小时榜
            idx = cache_dict.get('idx')  # 排名
            ver = cache_dict.get('ver')
            info = '恭喜本直播间 %s 排名升到第%s名' % (rname, idx)
            # print(info)
        elif typer == 'srres':
            nickname = cache_dict.get('nickname')  # 用户（分享者）昵称
            exp = cache_dict.get('exp')  # 用户获得的经验值
            info = '%s 分享了该直播间' % (nickname)
            # print(info)
        elif typer == 'spbc':  # 房间内礼物广播
            sn = cache_dict.get('sn')  # 赠送者昵称
            dn = cache_dict.get('dn')  # 受赠者昵称
            gn = cache_dict.get('gn')  # 礼物名称
            gc = cache_dict.get('gc')  # 礼物数量
            # info = '%s 赠送 %s %s x %s' % (sn, dn, gn, gc)
            # print(info)
        elif typer not in filter_kw_list:
            # print(cache_dict)
            pass
        else:
            # print(cache_dict)
            pass
        # print(cache_dict)

    # 根据礼物id取出礼物名称
    def giftid_get_giftnn(self, giftid):  # key为giftid，返回的value值为礼物名称
        if giftid == '' or giftid == None:
            return ''
        gift_dict = {
            '20005': '超级火箭', '20760': '风暴超火', '20761': '风暴火箭', '20004': '火箭', '20003': '飞机',
            '20624': '魔法彩蛋', '20002': '办卡', '20010': 'MVP', '20727': '乖乖戴口罩', '20541': '大气',
            '20000': '100鱼丸', '20644': '能量戒指', '20642': '能量电池', '20643': '能量水晶', '20008': '超大丸星',
            '20728': '勤洗手', '20417': '福袋', '20542': '666', '20009': '天秀', '20001': '弱鸡', '20006': '赞',
            '20709': '壁咚', '1859': '小飞碟', '20626': '幸福券', '824': '粉丝荧光棒', '20621': '魔法之翼',
            '20599': '星空飞机', '20615': '花海摩天轮', '20600': '星空火箭', '20614': '踏青卡丁车', '20618': '魔法指环',
            '20616': '春意丘比特', '20613': '永恒钻戒', '20617': '爱的旅行', '520': '稳', '193': '弱鸡', '192': '赞',
            '712': '棒棒哒', '519': '呵呵', '20461': '车队加油卡', '20596': '小星星', '20759': '集结号角', '20597': '星球',
            '20611': '浪漫花束', '713': '辣眼睛', '20620': '魔法皇冠', '20832': '奥利给', '20640': '礼物红包办卡',
            '20523': '礼物红包飞机', '20710': '金鲨鱼', '20842': '时空战机', '20598': '星空卡', '20664': '666',
            '20841': '星际飞车', '1889': '火箭', '20914': '开黑券', '20932': '爆裂飞机', '20931': '战地越野车',
            '20933': '有牌面', '20934': '机械火箭', '20935': '欧皇的祝福', '20936': '一起开黑', '20950': '战斗鸡',
            '20138': '挑战书', '20900': '小厨娘', '20902': '鱼丸粗面', '20906': '满汉全席', '20901': '可乐鸡翅'
        }
        if giftid not in gift_dict:
            return giftid
        giftnn = gift_dict[giftid]
        return giftnn

    # @S替换为'/'，@A替换为'@'
    def str_replace(self, data):
        message = str(data).replace('@S', '/')
        message = message.replace('@A', '@')
        return message


''' /// douyu websocket start /// '''
def on_error(ws, error):
    # print('连接出错：', error)
    pass
def on_close(ws):
    print('连接已关闭')
def on_open(ws):
    print('弹幕服务器连接成功')
    # 发送登录消息
    ws.send(DouYuDanMuData().ws_login_str(g_rid))
    # 登录后发送入组消息
    ws.send(DouYuDanMuData().ws_join_group_str(g_rid))
    # 启动keeplive心跳包线程
    global g_thread_keeplive
    g_thread_keeplive = threading.Thread(target=DouYuDanMuData().ws_keeplive, args=(ws,))
    g_thread_keeplive.start()

def on_message(ws, message):
    # 将字节流转化为字符串，忽略无法解码的错误（即斗鱼协议中的头部尾部）
    DouYuDanMuData().process_message_data(message.decode(encoding='utf-8', errors='ignore'))
# 主线程
def douyu_websocket():
    ws = websocket.WebSocketApp(
        'wss://danmuproxy.douyu.com:8502/',  # 端口范围 8501~8506
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    ws.run_forever()
''' /// douyu websocket end /// '''

def start_danmu_thread(rid):
    global g_rid, g_thread_main
    g_rid = rid
    g_thread_main = threading.Thread(target=douyu_websocket)
    g_thread_main.start()


if __name__ == '__main__':
    start_danmu_thread('99999')
