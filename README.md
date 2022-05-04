# ImComingMonitor

监控俺来也上指定商家的开关门情况和存货信息。

## 功能细节

- 商家开门时通过推送加和 qq 机器人推送通知
- 在指定时间通过 qq 机器人推送商家的存货信息

## 使用方法

1. 安装 Python 环境。
2. 安装并配置一个[go-cqhttp](https://github.com/Mrs4s/go-cqhttp)机器人（可选）。
3. 申请一个[推送加(pushplus)](http://www.pushplus.plus/)token（可选）。
4. Clone 本项目到本地。
5. 安装依赖 `pip install -r requirements.txt`。
6. 打开项目根目录下的`config.example.ini`，根据注释填写设置项，将其重命名为`config.ini`。
7. 运行监控 `python monitor.py`。

## 免责声明

本项目仅用于学习，对于使用者所造成的一切后果，开发者不承担任何责任。
