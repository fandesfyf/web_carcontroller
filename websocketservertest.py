#!usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2021/7/4 15:38
# @Author  : Fandes
# @FileName: Carwebsocketserver.py
# @Software: PyCharm
import asyncio
import datetime
import json
import os
import sys
import time

import websockets
import threading
from httpserver import httpserver as Httpserver

class CarWebSocketserver():
    def __init__(self, host="", port=8787):
        super(CarWebSocketserver, self).__init__()
        self.host, self.port = host, port
        self.websockets_server = websockets.serve(self.requestcallback, self.host, self.port,ping_timeout=1,timeout=1,ping_interval=1)

    async def requestcallback(self, websocket, path):
        print("request path:", path)
        if path == "/control":
            print("控制速度")
            try:
                task = asyncio.get_event_loop().create_task(self.speedcontrol(websocket))
                task2 = asyncio.get_event_loop().create_task(self.heartbeat(websocket))
                await task
                await task2
            except:
                print(sys.exc_info(), 31)

        else:
            print("未知请求")
            await websocket.send("unknown request")
        print("end")

    def run(self):
        asyncio.get_event_loop().run_until_complete(self.websockets_server)

    # def sendmessage(self,message):
    #     self.websockets_server.

    # 接收客户端消息并处理，这里只是简单把客户端发来的返回回去
    async def speedcontrol(self, websocket:websockets.server.WebSocketServerProtocol):#websockets.server.WebSocketServerProtocol
        while True:
            recv_text =await websocket.recv()
            print("rec:", recv_text)

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
    sys.stdout=Logger(os.path.join(os.path.expanduser("~"),"test.log"))
    main()

