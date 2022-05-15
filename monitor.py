import requests
import json
import time
import threading
from pathlib import Path
from hashlib import md5
from configparser import ConfigParser

cf = ConfigParser()
config_path = 'config.ini'
config = {
    'monitor': {
        'check_interval': None,
        'request_timeout': None,
    },
    'notify': {
        'push_plus_token_list': None,
        'go_cqhttp_url': None,
        'gocq_access_token': None,
        'qq_group_id': None,
        'notify_goods_time_tuple': None,
        'at_all_when_open': None
    }
}

# 商家类


class Shop:
    config = {}
    res = {}
    firstopen = False

    def __init__(self, config):
        self.config = config
        if self.config['go-cqhttp']:
            start_thread(self.notify_goods)

    def checkShopStatus(self):
        ts = int(time.time())
        temp_token = md5(f'{ts+1}'.encode('utf-8')).hexdigest()
        temp_sign = md5(f'{ts}'.encode('utf-8')).hexdigest()

        url = 'https://merchants-base.anlaiye.com/pub/shop/goodsV2'

        dict_data = {
            'app_version': '8.1.8',
            'data': json.dumps({'shop_id': self.config['shop_id'], 'token': temp_token}),
            'client_type': '2',
            'device_id': '867532784377529',
            'time': str(ts),
            'sign': temp_sign
        }

        headers = {
            'Content-Type': 'application/json',
            'Host': 'merchants-base.anlaiye.com',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'User-Agent': 'okhttp/3.12.1'
        }

        try:
            ret = requests.get(url, params=dict_data, headers=headers, timeout=config['monitor']['request_timeout'],
                               #proxies={"http": "http://127.0.0.1:8888", "https": "http://127.0.0.1:8888"}, verify='./FiddlerRoot.cer'
                               )
            j = json.loads(ret.text)
            if('data' in j and 'shop_detail' in j['data']):
                return j
            else:
                return False
        except Exception as e:
            print(f'获取商家(shop_id = {self.config["shop_id"]})状态出错', e)
            return False

    def notify_goods(self):
        while True:
            time_now = time.strftime("%H:%M", time.localtime())
            for t in self.config['notify_goods_time_tuple']:
                if self.res and time_now == t:
                    qqmsg = f'【{time_now}】当前商品存货信息（售罄的商品已隐藏）\n'
                    for g in self.res['data']['item_list']:
                        if (len(g['goods_list']) > 0):
                            for i in g['goods_list']:
                                if (i['stock'] > 0):
                                    qqmsg += i['goods_name'] + \
                                        ': ' + str(i['stock']) + '\n'
                    qqbot(qqmsg)
                    time.sleep(61)
            time.sleep(1)

    def check(self):
        if not self.config['is_monitored']:
            return
        self.res = self.checkShopStatus()
        if (self.res):
            if (self.res['data']['shop_detail']['is_open'] == '1'):
                if (not self.firstopen):
                    self.firstopen = True
                    # print('OPEN')
                    if self.config['go-cqhttp']:
                        start_thread(
                            qqbot, (f'[CQ:at,qq=all] {self.res["data"]["shop_detail"]["shop_name"]}开门啦！',))
                    if self.config['push_plus']:
                        start_thread(pushplus, (f'{self.res["data"]["shop_detail"]["shop_name"]}开门啦！', json.dumps(
                            self.res['data']['shop_detail']['open_setting'], indent=4)))
            else:
                # print('CLOSE')
                if (self.firstopen):
                    begin_time = self.res['data']['shop_detail']['open_setting'][0]['begin_time']
                    end_time = self.res['data']['shop_detail']['open_setting'][0]['end_time']
                    start_thread(qqbot, (f'{self.res["data"]["shop_detail"]["shop_name"]}已关门\n以下是商家设置的开关门时间：\n开门：' +
                                         begin_time + '\n关门：' + end_time,))
                self.firstopen = False
        else:
            pass
        time.sleep(config['monitor']['check_interval'])

# 加入设置


def load_config():
    if not Path(config_path).exists():
        print("无配置文件，终止运行")
        exit(0)
    global config, cf
    cf.read(config_path, encoding='utf-8')
    for section in cf.sections():
        if section == 'monitor':
            config[section]['check_interval'] = cf.getfloat(
                section, 'check_interval')
            config[section]['request_timeout'] = cf.getfloat(
                section, 'request_timeout')
        elif section == 'notify':
            config[section]['push_plus_token_list'] = cf.get(
                section, 'push_plus_token_list').split(',')
            config[section]['go_cqhttp_url'] = cf.get(section, 'go_cqhttp_url')
            config[section]['gocq_access_token'] = cf.get(
                section, 'gocq_access_token')
            config[section]['qq_group_id'] = cf.getint(section, 'qq_group_id')
            config[section]['at_all_when_open'] = cf.getboolean(
                section, 'at_all_when_open')
        elif section.startswith('shop'):
            config[section] = {}
            config[section]['is_monitored'] = cf.getboolean(
                section, 'is_monitored')
            config[section]['shop_id'] = cf.getint(section, 'shop_id')
            config[section]['push_plus'] = cf.getboolean(section, 'push_plus')
            config[section]['go-cqhttp'] = cf.getboolean(section, 'go-cqhttp')
            config[section]['notify_goods_time_tuple'] = tuple(
                cf.get(section, 'notify_goods_time_tuple').split(','))
        else:
            print(f'未知设置分组：{section}')

# 推送加推送 args = (title,  content)


def pushplus(*args):
    title,  content = args[0], args[1]
    for token in config['notify']['push_plus_token_list']:
        dict_data = {
            'title': title,
            'content': content.replace(' ', '&nbsp;'),
            'token': token
        }
        try:
            ret = requests.post('http://www.pushplus.plus/send',
                                data=dict_data, timeout=config['monitor']['request_timeout'])
            j = json.loads(ret.text)
            print(j)
            if (j['code'] != 200):
                print('推送加推送出错', j['msg'])
        except Exception as e:
            print('推送加推送失败', e)
        finally:
            time.sleep(0.2)
    return

# qq群消息推送 args = (message)


def qqbot(*args):
    message = args[0]
    dict_data = {
        'access_token': config['notify']['gocq_access_token'],
        'group_id': config['notify']['qq_group_id'],
        'message': message,
        'auto_escape': False

    }
    try:
        ret = requests.get(
            config['notify']['go_cqhttp_url'] + '/send_group_msg', params=dict_data, timeout=config['monitor']['request_timeout']
        )
        j = json.loads(ret.text)
        if(j['retcode'] != 0):
            print('qq推送出错', j)
    except Exception as e:
        print('qq推送失败', e)
    return

# 启动一个守护线程


def start_thread(func, arg=()):
    t = threading.Thread(target=func, args=arg)
    t.daemon = True
    t.start()

# 初始化 Shop 列表


def init_shop_list(shop_list):
    for section in cf.sections():
        if section.startswith('shop'):
            if config[section]['is_monitored']:
                shop_list.append(Shop(config[section]))

# 循环检查商家开关门状态


def loop_check_shop_list(shop_list):
    while True:
        for shop in shop_list:
            shop.check()


def main():
    print('开始监控')
    shop_list = []
    load_config()
    init_shop_list(shop_list)
    loop_check_shop_list(shop_list)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('监控已关闭')
