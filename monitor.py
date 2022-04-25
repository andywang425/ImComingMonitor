import requests
import json
import time
import threading
import os
from hashlib import md5
from configparser import ConfigParser

config_path = 'config.ini'

res = None

config = {
    'check_interval': None,
    'push_plus_token_list': None,
    'go_cqhttp_url': None,
    'gocq_access_token': None,
    'shop_id': None,
    'qq_group_id': None,
    'notify_goods_time_tuple': None
}


def load_config():
    if not os.path.exists(config_path):
        print("无配置文件，终止运行")
        exit(0)
    global config
    cf = ConfigParser()  # 实例化
    cf.read(config_path, encoding='utf-8')
    config['check_interval'] = cf.getint("monitor", "check_interval")
    config['push_plus_token_list'] = cf.get(
        "monitor", "push_plus_token_list").split(',')
    config['go_cqhttp_url'] = cf.get("monitor", "go_cqhttp_url")
    config['gocq_access_token'] = cf.get("monitor", "gocq_access_token")
    config['shop_id'] = cf.getint("monitor", "shop_id")
    config['qq_group_id'] = cf.getint("monitor", "qq_group_id")
    config['notify_goods_time_tuple'] = tuple(
        cf.get("monitor", "notify_goods_time_tuple").split(','))


def checkShopStatus():
    ts = int(time.time())

    url = 'https://merchants-base.anlaiye.com/pub/shop/goodsV2'

    dict_data = {
        'app_version': '8.1.8',
        'data': json.dumps({'shop_id': config['shop_id'], 'token':  md5(f'{ts+1}'.encode('utf-8')).hexdigest()}),
        'client_type': '2',
        'device_id': '867532784377529',
        'time': str(ts),
        'sign': md5(f'{ts}'.encode('utf-8')).hexdigest()
    }

    headers = {
        'Content-Type': 'application/json',
        'Host': 'merchants-base.anlaiye.com',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip',
        'User-Agent': 'okhttp/3.12.1'
    }

    proxies = {
        "http": "http://127.0.0.1:8888",
        "https": "http://127.0.0.1:8888"
    }

    try:
        ret = requests.get(url, params=dict_data, headers=headers, timeout=10,
                           #proxies=proxies, verify='./FiddlerRoot.cer'
                           )
        j = json.loads(ret.text)
        if('data' in j and 'shop_detail' in j['data']):
            return j
        else:
            return False
    except Exception as e:
        print(e)
        return False


def pushplus(*args):
    if config['push_plus_token_list'] == ['']:
        return
    title,  content = args[0], args[1]
    for token in config['push_plus_token_list']:
        dict_data = {
            'title': title,
            'content': content,
            'token': token
        }
        try:
            ret = requests.post('http://www.pushplus.plus/send',
                                data=dict_data, timeout=10)
            j = json.loads(ret.text)
            print(j)
        except Exception as e:
            print('推送加推送失败')
            return False
        time.sleep(0.2)
    return


def qqbot(*args):
    message, group_id = args[0], args[1]
    dict_data = {
        'access_token': config['gocq_access_token'],
        'group_id': group_id,
        'message': message,
        'auto_escape': False

    }
    ret = requests.get(
        config['go_cqhttp_url'] + '/send_group_msg', params=dict_data, timeout=10
    )
    try:
        j = json.loads(ret.text)
        print(j)
    except Exception as e:
        print('qq推送失败')
        return False
    return


def print_good(*timelist):
    while True:
        time_now = time.strftime("%H:%M", time.localtime())
        for t in timelist:
            if time_now == t and res:  # !=
                qqmsg = f'【{t}】当前商品存货信息（售罄的商品已隐藏）\n'
                for g in res['data']['item_list']:
                    if (len(g['goods_list']) > 0):
                        for i in g['goods_list']:
                            if (i['stock'] > 0):
                                qqmsg += i['goods_name'] + \
                                    ': ' + str(i['stock']) + '\n'
                qqbot(qqmsg, config['qq_group_id'])
                time.sleep(61)
        time.sleep(1)


def start_thread(func, arg):
    t = threading.Thread(target=func, args=arg)
    t.daemon = True
    t.start()


if __name__ == "__main__":
    print('开始监控')
    load_config()
    firstopen = False
    if config['gocq_access_token'] != ['']:
        start_thread(print_good, config['notify_goods_time_tuple'])
    while(True):
        res = checkShopStatus()
        if (res):
            if (res['data']['shop_detail']['is_open'] == '1'):
                if (not firstopen):
                    firstopen = True
                    # print('OPEN')
                    if config['gocq_access_token'] != ['']:
                        start_thread(
                            qqbot, (f'[CQ:at,qq=all] {res["data"]["shop_detail"]["shop_name"]}开门啦！', config['qq_group_id']))
                    if config['push_plus_token_list'] != ['']:
                        start_thread(pushplus, (f'{res["data"]["shop_detail"]["shop_name"]}开门啦！', json.dumps(
                            res['data']['shop_detail']['open_setting'], indent=4)))
            else:
                # print('CLOSE')
                if (firstopen):
                    begin_time = res['data']['shop_detail']['open_setting'][0]['begin_time']
                    end_time = res['data']['shop_detail']['open_setting'][0]['end_time']
                    start_thread(qqbot, (f'{res["data"]["shop_detail"]["shop_name"]}已关门\n以下是商家设置的开关门时间：\n开门：' +
                                         begin_time + '\n关门：' + end_time + '\n当前检测间隔：' + str(config['check_interval']) + '秒', config['qq_group_id']))
                firstopen = False
        else:
            pass
        time.sleep(config['check_interval'])
