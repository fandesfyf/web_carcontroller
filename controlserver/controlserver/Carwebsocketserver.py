#!usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2021/7/4 15:38
# @Author  : Fandes
# @FileName: Carwebsocketserver.py
# @Software: PyCharm
import os, sys, time
print(os.getcwd())
os.mkdir("/home/zhihui/AutoRS_v2/"+str(time.time()))
import asyncio
import http.server
import json
import mimetypes
import os
import posixpath
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from socketserver import ThreadingMixIn

import rclpy
import websockets
from geometry_msgs.msg import TwistStamped

Work_Path = os.path.split(sys.argv[0])[0]
print(Work_Path, os.path.split(sys.argv[0])[0])

def get_ips():
    ip_list = []
    if sys.platform == "linux":

        # 使用os.popen()函数执行ifconfig命令，结果为file对象，将其传入cmd_file保存
        cmd_file = os.popen('ifconfig')
        # 使用file对象的read()方法获取cmd_file的内容
        cmd_result = cmd_file.read()
        # 构造用于匹配IP的匹配模式
        pattern = re.compile(r'inet *(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})')
        # 使用re模块的findall函数匹配
        ip_list = re.findall(pattern, cmd_result)
    else:
        addrs = socket.getaddrinfo(socket.gethostname(), None)
        ip_list = [ad[4][0] for ad in addrs if len(ad[4]) == 2]
    return ip_list


print(get_ips(),"端口:10590")


def matchip(host: str):
    requestsip = host.split(":")[0]
    if "." in requestsip:
        return requestsip
    else:
        return "127.0.0.1"
    # try:
    #     requestsiphead = re.findall("(\d{1,3}.\d{1,3}.\d{1,3}).\d{1,3}", requestsip)[0]
    # except:
    #     print(sys.exc_info())
    #     requestsiphead = "127.0.0.1"
    # ips = get_ips()
    # print(requestsiphead, ips)
    # for ip in ips:
    #     if requestsiphead in ip:
    #         print("找到ip", ip)
    #         return ip
    # return "127.0.0.1"


class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        print("do get", self.path, self.headers["Host"])
        f = self.respond_get()
        if f:
            line = f.read(999999)
            try:
                while line:
                    print("doget action")
                    if type(line) is str:
                        self.wfile.write(line.encode("utf-8"))
                    else:
                        # print("2")
                        self.wfile.write(line)

                    line = f.read(999999)
            except WindowsError:
                print(sys.exc_info(), 103)

    def do_HEAD(self):
        print("do head")
        f = self.respond_get()
        if f:
            f.close()

    def do_POST(self):  # 暂时没有用到,懒得删了
        print("do post", self.path)
        # print(self.headers)
        post_data = self.rfile.read(int(self.headers['content-length'])).decode()
        print(post_data)

    # json.dumps()# 将python对象编码成Json字符串
    # json.loads() # 将Json字符串解码成python对象
    # json.dump() # 将python中的对象转化成json储存到文件中
    # json.load()# 将文件中的json的格式转化成python对象提取出来
    def response_post(self, code: int = 200, jsonstr="{}", Content_type="text/plain", ):
        # s = json.dumps(jsonstr)
        self.send_response(code)
        self.send_header("Content-type", Content_type)
        self.send_header("Content-Length", str(len(jsonstr)))
        self.end_headers()
        self.wfile.write(jsonstr.encode())

    def respond_get(self):  # 响应get请求
        path = self.translate_path(self.path)
        print("respond_get path:", self.path, path)
        if path is None: return
        f = None
        ctype = self.guess_type(path)
        try:
            if self.path == "/":
                targetip = matchip(self.headers["Host"])
                with open(path, "r", encoding="utf-8")as tf:
                    ts = tf.read()
                    ts = ts.replace("localhost", targetip)
                    print("replace", targetip)
                    f = BytesIO()
                    f.write(ts.encode("utf-8"))
                    f.seek(0)
            else:
                f = open(path, 'rb')
        except IOError:
            print(sys.exc_info(), path, self.path, "257")
            self.send_error(404, "File not found")
            return None

        self.send_response(200)
        self.send_header("Content-type", ctype)
        l = len(f.read())
        print(l)
        f.seek(0)
        self.send_header("Content-Length", str(l))
        self.send_header("Last-Modified", self.date_time_string(int(50)))
        self.end_headers()
        return f

    def translate_path(self, path):
        path = path.replace("\\", "/")
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        path = posixpath.normpath(urllib.parse.unquote(path))
        words = path.split('/')
        words = [_f for _f in words if _f]
        print(words)
        if self.path == "/":
            return os.path.join(Work_Path, "html/controlpage.html")
        else:
            return os.path.join(Work_Path, path.strip("/"))

    def guess_type(self, path):

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init()  # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
    })


class Httpserver(threading.Thread):
    def __init__(self):
        super(Httpserver, self).__init__()
        self.http_handler = SimpleHTTPRequestHandler
        self.threadingServer = ThreadingServer(("", 10590), self.http_handler)

    def run(self):
        self.threadingServer.serve_forever()


class ThreadingServer(ThreadingMixIn, http.server.HTTPServer):
    pass



class CarWebSocketserver():
    def __init__(self, host="", port=8787):
        super(CarWebSocketserver, self).__init__()
        self.host, self.port = host, port
        self.websockets_server = websockets.serve(self.requestcallback, self.host, self.port, ping_timeout=0.5,
                                                  timeout=0.5, ping_interval=0.5)
        self.on_running = True
        rclpy.init()
        self.node = rclpy.create_node('nw_chassis_control_node')
        self.pub = self.node.create_publisher(TwistStamped, 'twist_auto', 1)

    def publish(self, speed, steer):
        twist_temp = TwistStamped()
        twist_temp.twist.linear.x = float(speed)
        # base_line = 0.41
        # w = speed * math.tan(math.pi * steer/180.0) / base_line
        w = steer
        twist_temp.twist.angular.z = w
        self.pub.publish(twist_temp)
        print("publish:v={: <8} t={: <8} at {}".format(speed, steer,
                                                       time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))

    async def requestcallback(self, websocket, path):  # websockets.legacy.server.WebSocketServerProtocol
        print("request path:", path, websocket.remote_address)
        if path == "/control":
            print("控制速度")
            try:
                task = asyncio.get_event_loop().create_task(self.speedcontrol(websocket))
                task2 = asyncio.get_event_loop().create_task(self.heartbeat(websocket))
                await task
                await task2
            except:
                print(sys.exc_info(), 31)
                return

        else:
            print("未知请求")
            await websocket.send("unknown request")
        print("end")

    def run(self):
        asyncio.get_event_loop().run_until_complete(self.websockets_server)

    # def sendmessage(self,message):
    #     self.websockets_server.

    # 接收客户端消息并处理，这里只是简单把客户端发来的返回回去
    async def speedcontrol(self, websocket):
        while True:

            recv_text = await websocket.recv()
            print("recspeed:", recv_text)
            try:
                d = json.loads(recv_text)
                if "v" in d.keys():
                    self.publish(float(d["v"]), float(d["t"]))
            except:
                self.publish(0., 0.)
                print(sys.exc_info(), 79)

    async def heartbeat(self, websocket):
        while True:
            # print("heartbeat")
            await websocket.send("0")
            await asyncio.sleep(0.5)


class Logger(threading.Thread):
    def __init__(self, log_path="jamtools.log"):
        super(Logger, self).__init__()
        # sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        self.terminal = sys.stdout
        self.log_path = log_path
        self.logtime = time.time() - 2
        self.loglist = []
        self.start()

    def run(self) -> None:
        if os.path.exists(self.log_path):
            ls = os.path.getsize(self.log_path)
            print("日志文件大小为:", ls, " 保存于:", self.log_path)
            if ls > 2485760:
                print("日志文件过大")
                with open(self.log_path, "r+", encoding="utf-8")as f:
                    f.seek(ls - 1885760)
                    log = "已截断日志" + time.strftime("%Y-%m-%d %H:%M:%S:\n", time.localtime(time.time())) + f.read()
                    f.seek(0)
                    f.truncate()
                    f.write(log)
                print("新日志大小", os.path.getsize(self.log_path))
        self.log = open(self.log_path, "a", encoding='utf8')
        self.log.write("\n\nOPEN@" + time.strftime("%Y-%m-%d %H:%M:%S:\n", time.localtime(time.time())))
        try:
            while True:
                if len(self.loglist):
                    self.process(self.loglist.pop(0))
                else:
                    time.sleep(0.05)
        except:
            print(sys.exc_info(), "log47")

    def write(self, message):
        self.loglist.append(message)

    def process(self, message):
        self.terminal.write(message)
        now = time.time()
        timestr = ""
        if now - self.logtime > 1:
            timestr = "\n@" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())) + "-" * 40 + "\n"

        log = timestr + message
        self.log.write(log)
        if now - self.logtime > 1:
            self.logtime = now
            self.log.flush()
        self.terminal.flush()

    def flush(self):
        pass


def main():
    wsserver = CarWebSocketserver()
    wsserver.run()
    print("websocket server started!")
    httpserver = Httpserver()
    httpserver.start()
    print("http server started!")
    print("ready")
    asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    sys.stdout = Logger()
    main()
