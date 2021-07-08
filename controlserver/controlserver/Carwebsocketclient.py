import datetime
import sys
import threading
import tkinter as tk
from tkinter import *
import time
import os
import socket, time, json
from tkinter import ttk  # 导入ttk模块，因为下拉菜单控件在ttk中
import websocket

AvailableKeys = ["w", "s", "a", "d", "up", "down", "left", "right", "q", "escape"]
msg = """
Move:                   Rotating:
    Increase: w             Clockwise: a
    Decrease: s             Counterclockwise: d

SpeedChange:
    DoubleClick / Arrow keys
Anything else:  stop
QUIT:           esc/q/Ctrl-C
"""
configpath = os.path.join(os.path.expanduser('~/Documents'), "CarController.ini")  # 配置文件
print(configpath)


class StateLabel(Label):
    def __init__(self, master, fg, relief, text=""):
        self.text = StringVar()
        super(StateLabel, self).__init__(master=master, text=text, fg=fg, anchor=NE,
                                         relief=relief, font=('微软雅黑', 12))
        self.fixedtext = Label(self, text="状态:\n    v:\n   Θ:", font=('微软雅黑', 12))
        self.fixedtext.place(x=5, y=0, width=45, height=70)
        self.textlabel = Label(self, textvariable=self.text, anchor=NW, font=('微软雅黑', 12))
        self.textlabel.place(x=50, y=0, width=200, height=70)

    def settext(self, text: str):
        self.text.set(text)

    def setstate(self, connect="未连接", v="--", t="--"):
        statestr = "{: >8}\n{: >8}\n{: >8}".format(connect, v, t)
        self.settext(statestr)


class MainWindow(tk.Frame):
    def __init__(self, master: tk.Tk = None, ):
        super().__init__(master)
        self.master = master
        self.master.title("KeyboardConrollerClient")
        self.master.geometry("618x400")
        self.pack()
        self.readconfig()
        self.create_widgets()
        self.host, self.port = list(self.hostdict.keys())[0], self.hostdict[list(self.hostdict.keys())[0]]
        self.reset_count = 25  # 重置速度时延时的计数,主循环中周期为0.005,则延时0.005*reset_counts
        self.last_click = ["0", 0]  # 记录上一次按键释放的时间和键
        self.cur_v = 0  # 当前速度
        self.cur_theta = 0  # 当前角速度
        self.p_v = 0  # 此前发送的速度
        self.p_t = 0  # ..
        self.controlling = False  # 控制主线程的变量
        self.reset_v_count = -1  # 按键释放时重置速度计数器
        self.reset_t_count = -1  # 重置角速度
        self.client = ControllerClient(self, self.host, self.port)
        self.key_config()
        # print(msg)

    def readconfig(self):
        try:
            with open(configpath, "r+", encoding="utf-8")as configfile:
                self.configjs = json.loads(configfile.read())
                self.reloadconfig()
        except:
            print(sys.exc_info(), 68)
            self.hostdict = {"127.0.0.1": 8787}
            self.max_v = 2.5  # 最大速度
            self.max_theta = 2  # 最大角速度
            self.init_v = 0.15
            self.init_t = 0.2
            self.inc_v = 0.2  # 速度增量
            self.inc_t = 0.15  # 角速度..
            self.doubleclick_delay = 0.2  # 判定双击的时间间隔
            self.configjs = {"hostdict": self.hostdict, "max_v": self.max_v, "max_theta": self.max_theta,
                             "init_v": self.init_v, "inc_v": self.inc_v, "inc_t": self.inc_t, "init_t": self.init_t,
                             "doubleclick_delay": self.doubleclick_delay, "topmost": 1}
            with open(configpath, "w", encoding="utf-8")as configfile:
                configfile.write(json.dumps(self.configjs))

    def reloadconfig(self):
        if '127.0.0.1' in self.configjs["hostdict"].keys():
            self.configjs["hostdict"].pop("127.0.0.1")
            self.configjs["hostdict"]["127.0.0.1"] = 8787
        self.hostdict = self.configjs["hostdict"]
        # self.heartbeat = self.configjs["heartbeat"]  # 心跳计数,3次心跳连接无反应则断开
        self.max_v = self.configjs["max_v"]  # 最大速度
        self.max_theta = self.configjs["max_theta"]  # 最大角速度
        self.init_v = self.configjs["init_v"]
        self.init_t = self.configjs["init_t"]
        self.inc_v = self.configjs["inc_v"]  # 速度增量
        self.inc_t = self.configjs["inc_t"]  # 角速度..
        a = self.configjs["topmost"]
        self.doubleclick_delay = self.configjs["doubleclick_delay"]  # 判定双击的时间间隔

    def save_config(self):
        with open(configpath, "w", encoding="utf-8")as configfile:
            configfile.write(json.dumps(self.configjs))

    def connnect(self):
        self.state.setstate("正在连接..")
        self.connectbtn.configure(state="disable")
        self.host, self.port = self.host_textedit.get(), int(self.port_textedit.get())
        self.client = ControllerClient(self, self.host, self.port)
        self.client.connect_to(self.host, self.port)

    def connect_successfully(self):
        self.host_textedit.configure(state='disable')
        self.port_textedit.configure(state="disable")
        self.connectbtn.configure(state="disable")
        self.speedup.configure(state="normal")
        self.speeddown.configure(state="normal")
        self.thetaleft.configure(state="normal")
        self.thetaright.configure(state="normal")
        self.state.setstate("连接成功", "0.0", "0.0")
        if self.host not in self.configjs["hostdict"].keys():
            self.configjs["hostdict"][self.host] = self.port
            self.save_config()
        self.doubleclickThread = threading.Thread(target=self.delay_stop)
        self.doubleclickThread.start()
        self.check_heartbeatThread = threading.Thread(target=self.check_heartbeat)
        self.check_heartbeatThread.start()

    def disconnect(self):
        if self.controlling:
            try:
                self.stop()
                self.client.join(5)
                self.client.disconnect()
                # self.doubleclickThread.join()
            except:
                print(sys.exc_info(), 84)

    def getconfig(self, configname, value):
        try:
            self.configjs[configname] = value
            self.reloadconfig()
            self.save_config()
        except:
            print(sys.exc_info(), 128)

    def key_config(self):
        self.master.bind("<KeyRelease>", self.on_release)
        self.master.bind("<KeyPress>", self.on_press)

    def create_widgets(self):
        def checkport(text: str, s):
            print(text)
            if (text.replace(".", "").isdigit() or s == "." or text == "") and len(text) <= 15:
                return True
            else:
                return False

        entry_validate = self.master.register(checkport)
        self.connectiongroup = tk.LabelFrame(self.master, text="Connection", width=400, height=55)
        self.connectiongroup.place(x=5, y=0)
        self.connectiongroup.update()
        self.settinggroup = tk.LabelFrame(self.master, text="Settings", width=200,
                                          height=self.master.winfo_height() - 5)
        self.settinggroup.place(x=self.connectiongroup.winfo_x() + self.connectiongroup.winfo_width() + 8, y=0)
        self.settinggroup.update()
        tips = StringVar()
        tipslabel = Label(self.master, fg="MidnightBlue", textvariable=tips,
                          wraplength=110, font=('微软雅黑', 10), justify='left')
        tipslabel.place(x=260, y=140, width=120, height=200)
        tips.set("WS键改变前进后退速度,AD键改变转弯速度;双击WSAD键可在对应方向加速,箭头键连续加速;ESC/q键断开,其他键急停,运动时按反向键急停;")

        self.state = StateLabel(self.master, fg='black', relief=SUNKEN)
        self.state.place(x=self.connectiongroup.winfo_x(),
                         y=self.connectiongroup.winfo_y() + self.connectiongroup.winfo_height() + 5,
                         width=self.connectiongroup.winfo_width(), height=75)
        self.state.setstate()
        self.host_textedit = ttk.Combobox(self.connectiongroup,
                                          values=[str(k) for k in self.configjs["hostdict"].keys()],
                                          width=14, validate='key',
                                          )
        self.host_textedit.configure(validatecommand=(entry_validate, '%P', '%S'))
        self.host_textedit.current(0)
        self.host_textedit.place(x=30, y=0)
        self.master.update()
        iptext = tk.Label(self.connectiongroup, text="IP")
        iptext.place(x=12, width=12, y=0)

        self.port_textedit = tk.Entry(self.connectiongroup, width=7, justify=CENTER, validate='key',
                                      vcmd=(entry_validate, '%P', '%S'))
        self.port_textedit.insert(0, 8787)
        self.port_textedit.place(x=self.host_textedit.winfo_x() + self.host_textedit.winfo_width() + 35, y=0,
                                 height=self.host_textedit.winfo_height())
        self.master.update()

        porttext = tk.Label(self.connectiongroup, text="端口")
        porttext.place(x=self.port_textedit.winfo_x() - 28, width=24, y=0)
        self.connectbtn = tk.Button(self.connectiongroup, text="连接", fg="black", width=7,
                                    command=self.connnect)
        self.connectbtn.place(x=self.port_textedit.winfo_x() + self.port_textedit.winfo_width() + 10, y=0,
                              height=self.port_textedit.winfo_height())
        self.master.update()
        self.disconnectbtn = tk.Button(self.connectiongroup, text="断开", fg="red", width=7,
                                       command=self.disconnect)
        self.disconnectbtn.place(x=self.connectbtn.winfo_x() + self.connectbtn.winfo_width() + 5, y=0,
                                 height=self.port_textedit.winfo_height(), )

        def changeontop():
            self.master.wm_attributes('-topmost', CheckVar.get())
            self.configjs["topmost"] = CheckVar.get()
            self.save_config()

        CheckVar = IntVar()
        self.ontop = ttk.Checkbutton(self.settinggroup, text="窗口置顶", variable=CheckVar, onvalue=1, offvalue=0,
                                     command=changeontop)
        self.ontop.place(x=10, y=-2)
        self.master.wm_attributes('-topmost', self.configjs["topmost"])
        CheckVar.set(self.configjs["topmost"])

        settingslabel = ["默认v", "默认Θ", "最大v", "最大Θ", "v增量", "Θ增量", "双击判定"]
        for i, tl in enumerate(settingslabel):
            text = tk.Label(self.settinggroup, text=tl, width=8, justify=RIGHT)
            text.place(x=0, y=25 + i * 30)

        def settingcallback(add, P: str, name: str):
            name = name.split(".")[-1]
            areadict = {"max_v": [1, 5], "max_theta": [1, 5],
                        "init_v": [0.01, 2],
                        "inc_v": [0.01, 2], "inc_t": [0.1, 2], "init_t": [0.01, 2],
                        "doubleclick_delay": [0.2, 1]}
            if P == "":
                return 1
            if (not P[-1].isdigit()) or (P[-1] == "." and "." in P[:-1]) or len(P) > 5 or P[0] == ".":
                return 0
            if float(P) == 0:
                return 1
            if areadict[name][0] <= float(P) <= areadict[name][1]:
                self.getconfig(name, float(P))
                print("change config", name, P)
                return 1
            else:
                return 0

        CMD = self.master.register(settingcallback)
        self.init_v_sinbox = Spinbox(self.settinggroup, name="init_v", from_=0.1, validate="key",
                                     to=2, format='%0.2f', increment=0.1, width=8)
        self.init_v_sinbox.delete(0, "end")
        self.init_v_sinbox.insert(0, self.configjs["init_v"])
        self.init_v_sinbox.place(x=80, y=25)
        self.init_t_sinbox = Spinbox(self.settinggroup, name="init_t", format='%0.2f', from_=0.1, validate="key",
                                     to=2, increment=0.1, width=8)
        self.init_t_sinbox.delete(0, "end")
        self.init_t_sinbox.insert(0, self.configjs["init_t"])
        self.init_t_sinbox.place(x=80, y=55)

        self.max_v_sinbox = Spinbox(self.settinggroup, name="max_v", format='%0.2f', from_=0.1, validate="key",
                                    to=5, increment=0.1, width=8)
        self.max_v_sinbox.delete(0, "end")
        self.max_v_sinbox.insert(0, self.configjs["max_v"])
        self.max_v_sinbox.place(x=80, y=85)
        self.max_theta_sinbox = Spinbox(self.settinggroup, name="max_theta", format='%0.2f', from_=0.1, validate="key",
                                        to=5, increment=0.1, width=8)
        self.max_theta_sinbox.delete(0, "end")
        self.max_theta_sinbox.insert(0, self.configjs["max_theta"])
        self.max_theta_sinbox.place(x=80, y=115)

        self.inc_v_sinbox = Spinbox(self.settinggroup, format='%0.2f', name="inc_v", from_=0.1, validate="key",
                                    to=2, increment=0.1, width=8)
        self.inc_v_sinbox.delete(0, "end")
        self.inc_v_sinbox.insert(0, self.configjs["inc_v"])
        self.inc_v_sinbox.place(x=80, y=145)
        self.inc_t_sinbox = Spinbox(self.settinggroup, name="inc_t", format='%0.2f', from_=0.1, validate="key",
                                    to=2, increment=0.1, width=8)
        self.inc_t_sinbox.delete(0, "end")
        self.inc_t_sinbox.insert(0, self.configjs["inc_t"])
        self.inc_t_sinbox.place(x=80, y=175)

        self.doubleclick_delay_sinbox = Spinbox(self.settinggroup, format='%0.2f', name="doubleclick_delay", from_=0.1,
                                                validate="key",
                                                to=1, increment=0.1, width=8)
        self.doubleclick_delay_sinbox.delete(0, "end")
        self.doubleclick_delay_sinbox.insert(0, self.configjs["doubleclick_delay"])
        self.doubleclick_delay_sinbox.place(x=80, y=205)

        self.init_v_sinbox.configure(validatecommand=(CMD, '%d', '%P', '%W'))
        self.init_t_sinbox.configure(validatecommand=(CMD, '%d', '%P', '%W'))
        self.inc_v_sinbox.configure(validatecommand=(CMD, '%d', '%P', '%W'))
        self.inc_t_sinbox.configure(validatecommand=(CMD, '%d', '%P', '%W'))
        self.max_v_sinbox.configure(validatecommand=(CMD, '%d', '%P', '%W'))
        self.max_theta_sinbox.configure(validatecommand=(CMD, '%d', '%P', '%W'))
        self.doubleclick_delay_sinbox.configure(validatecommand=(CMD, '%d', '%P', '%W'))
        self.master.update()

        self.speedup = Button(self.master, text='∧\nW', bd=2, relief='groove')
        self.speedup.place(x=70, y=270, height=40, width=28)
        self.speedup.update()
        self.speeddown = Button(self.master, text='S\n∨', bd=2, relief='groove')
        self.speeddown.place(x=self.speedup.winfo_x(),
                             y=self.speedup.winfo_y() + self.speedup.winfo_height() + self.speedup.winfo_width() + 2
                             , height=self.speedup.winfo_height(), width=self.speedup.winfo_width())
        self.thetaleft = Button(self.master, text='＜A', bd=2, relief='groove')
        self.thetaleft.place(x=self.speedup.winfo_x() - self.speedup.winfo_height() - 1,
                             y=self.speedup.winfo_y() + self.speedup.winfo_height() + 1
                             , height=self.speedup.winfo_width(), width=self.speedup.winfo_height())
        self.master.update()
        self.thetaright = Button(self.master, text='D＞', bd=2, relief='groove')
        self.thetaright.place(
            x=self.thetaleft.winfo_x() + self.thetaleft.winfo_width() + self.speedup.winfo_width() + 2,
            y=self.thetaleft.winfo_y()
            , height=self.speedup.winfo_width(), width=self.speedup.winfo_height())
        self.speedup.configure(state="disable")
        self.speeddown.configure(state="disable")
        self.thetaleft.configure(state="disable")
        self.thetaright.configure(state="disable")
        # self.master.resizable(0,0)
        self.master.protocol('WM_DELETE_WINDOW', self.close)
        self.event_bind()

    def event_bind(self):
        self.host_textedit.bind("<Return>", lambda x: self.port_textedit.focus_set())
        self.port_textedit.bind("<Return>", lambda x: self.connnect())
        self.speedup.bind("<ButtonRelease-1>", lambda x: self.sendbuttonReleaseevent("w"))
        self.speedup.bind("<ButtonPress-1>", lambda x: self.sendbuttonpressevent("w"))
        self.speeddown.bind("<ButtonRelease-1>", lambda x: self.sendbuttonReleaseevent("s"))
        self.speeddown.bind("<ButtonPress-1>", lambda x: self.sendbuttonpressevent("s"))
        self.thetaleft.bind("<ButtonRelease-1>", lambda x: self.sendbuttonReleaseevent("a"))
        self.thetaleft.bind("<ButtonPress-1>", lambda x: self.sendbuttonpressevent("a"))
        self.thetaright.bind("<ButtonRelease-1>", lambda x: self.sendbuttonReleaseevent("d"))
        self.thetaright.bind("<ButtonPress-1>", lambda x: self.sendbuttonpressevent("d"))

    def sendbuttonpressevent(self, target):
        ev = tk.Event()
        ev.keysym = target
        self.on_press(ev)

    def sendbuttonReleaseevent(self, target):
        ev = tk.Event()
        ev.keysym = target
        self.on_release(ev)

    def check_heartbeat(self):
        try:
            while self.controlling:
                if not self.client.heartbeat():
                    print("heartbreak")
                    self.stop()
                    break
                time.sleep(0.3)
        except:
            print(sys.exc_info(), 124)
            self.stop()

    def delay_stop(self):
        try:
            while self.controlling:
                if self.reset_v_count >= 0:  # 检查是否释放了ws
                    self.reset_v_count -= 1
                    if self.reset_v_count == 0:
                        self.cur_v = 0
                        # print("释放ws")
                        self.send_speed()
                if self.reset_t_count >= 0:
                    self.reset_t_count -= 1
                    if self.reset_t_count == 0:
                        # print("释放ad")
                        self.cur_theta = 0
                        self.send_speed()

                time.sleep(0.005)
        except KeyboardInterrupt:
            print("KeyboardInterrupt!")
            self.stop()
        except Exception:
            print(sys.exc_info())
            self.stop()
        finally:
            print("stop control")


    def on_press(self, ke):
        if not self.controlling:
            return
        # print(ke, time.time())
        kn = ke.keysym.lower()
        if kn not in AvailableKeys:
            self.cur_v = self.cur_theta = 0  # 急停
        elif kn in ["q", "escape"]:  # 退出
            self.controlling = False
        elif kn == self.last_click[0] and time.time() - self.last_click[1] < self.doubleclick_delay:  # 判断是否是双击
            self.doubleclick(kn)
        else:  # 剩下的只有wsad和箭头键
            if kn == "w":
                if self.cur_v == 0:
                    self.cur_v = self.init_v
                else:
                    self.cur_v = 0 if self.cur_v < 0 else self.cur_v
            elif kn == "s":
                if self.cur_v == 0:
                    self.cur_v = -self.init_v
                else:
                    self.cur_v = 0 if self.cur_v > 0 else self.cur_v
            elif kn == "d":
                if self.cur_theta == 0:
                    self.cur_theta = -self.init_t
                else:
                    self.cur_theta = 0 if self.cur_theta > 0 else self.cur_theta
            elif kn == "a":
                if self.cur_theta == 0:
                    self.cur_theta = self.init_t
                else:
                    self.cur_theta = 0 if self.cur_theta < 0 else self.cur_theta
            else:
                if kn in "updown" and self.cur_v != 0:  # 箭头上下调速度
                    self.cur_v += self.inc_v if kn == "up" else -self.inc_v
                elif kn in "leftright" and self.cur_theta != 0:  # 箭头左右调角速度
                    self.cur_theta += -self.inc_t if kn == "right" else self.inc_t
        self.send_speed()

    def doubleclick(self, kn):
        print("doubleclick")
        if kn in "ws":
            self.reset_v_count = -1  # 检查到双击时重置计数器
            self.cur_v += self.inc_v if kn == "w" else -self.inc_v
        else:  # 双击ad键
            self.reset_t_count = -1  # 同上
            self.cur_theta += self.inc_t if kn == "a" else -self.inc_t
        self.send_speed()

    def on_release(self, ke):
        if not self.controlling:
            return
        kn = ke.keysym.lower()
        if kn not in AvailableKeys:
            return
        if len(kn) == 1:
            cv = self.cur_v
            ct = self.cur_theta
            self.last_click = [ke.keysym.lower(), time.time()]
            if kn in "ws":
                self.reset_v_count = self.reset_count
                if kn == "w" and self.cur_v > 2 * self.inc_v:
                    self.cur_v -= 0.1
                elif kn == "s" and self.cur_v < -2 * self.inc_v:
                    self.cur_v += 0.1
            elif kn in "ad":
                self.reset_t_count = self.reset_count
            else:
                self.cur_v = self.cur_theta = 0
            self.send_speed()
            self.cur_v = cv
            self.cur_theta = ct

    def publish_speed(self):
        self.client.send({"v": self.cur_v, "t": self.cur_theta})

    def send_speed(self):  # 发送速度
        if abs(self.cur_v) > self.max_v:  # 最大速度判定
            print("最大速度!{}".format(self.max_v))

            self.cur_v = self.cur_v / abs(self.cur_v) * self.max_v
        if abs(self.cur_theta) > self.max_theta:
            self.cur_theta = self.cur_theta / abs(self.cur_theta) * self.max_theta
        print("speed:{: <8}    theta:{: <8}".format(self.cur_v, self.cur_theta))
        if self.cur_v != self.p_v or self.cur_theta != self.p_t:
            self.publish_speed()
            self.state.setstate("控制中..." if self.cur_v != self.max_v else "最大速度!", format(self.cur_v, "2.2f"),
                                format(self.cur_theta, "2.2f"))
        self.p_v, self.p_t = self.cur_v, self.cur_theta

    def stop(self):
        print("exit")
        self.stopping = True
        if self.cur_v or self.cur_theta:
            self.cur_v = self.cur_theta = 0
            self.send_speed()
        self.controlling = False
        self.state.setstate("已断开", "--", "--")
        self.host_textedit.configure(state='normal')
        self.port_textedit.configure(state="normal")
        self.connectbtn.configure(state="normal")
        self.speedup.configure(state="disable")
        self.speeddown.configure(state="disable")
        self.thetaleft.configure(state="disable")
        self.thetaright.configure(state="disable")

    def close(self):
        try:
            self.stop()
            self.doubleclickThread.join(2)
            self.check_heartbeatThread.join(2)
        except:
            print(sys.exc_info(), 487)
        self.master.destroy()
        print("destroy")


class ControllerClient(threading.Thread):
    def __init__(self, parent=None, host="127.0.0.1", port=8787):
        super(ControllerClient, self).__init__()
        self.parent = parent
        self.host = host
        self.port = port
        self.reconnecttime = 3  # 三次重连机会
        self.datelist = []
        print('ready')

    def run(self) -> None:
        self.reconnect()
        if self.parent.controlling:
            self.parent.connect_successfully()
        else:
            print("连接失败")
            self.parent.state.setstate("连接失败")
            return
        while self.parent.controlling:
            if len(self.datelist):
                self._send_data()
            time.sleep(0.01)
        self._send_data(reset=True)

    def connect_to(self, host: str, port: int):
        self.host = host
        self.port = port
        self.start()

    def reconnect(self):
        while self.reconnecttime:
            try:
                print("connecting to", self.host, self.port)
                self.websocket = websocket.create_connection("ws://{}:{}/control".format(self.host, self.port),
                                                             timeout=3, ping_timeout=3)
            except:
                print("连接主机失败", sys.exc_info())
                self.parent.state.setstate("连接失败{}/3".format(self.reconnecttime - 1))
                self.parent.controlling = False
                if self.reconnecttime == 1:
                    self.parent.connectbtn.configure(state="normal")
            else:
                print("连接{}:{}成功".format(self.host, self.port))
                self.parent.controlling = True
                break
            self.reconnecttime -= 1
        self.reconnecttime = 3

    def send(self, data: dict):
        self.datelist.append(data)

    def _send_data(self, reset=False):
        if reset:
            data = {"v": 0, "t": 0}
            self.websocket.send(json.dumps(data))
        else:
            data = self.datelist.pop(0)
            if not self.parent.controlling:
                print("尝试重新连接主机")
                self.reconnect()  # 重连
            if self.parent.controlling:  # 重连后再判断连上了再发送
                # print("send", data)
                try:
                    self.websocket.send(json.dumps(data))
                except ConnectionResetError and ConnectionAbortedError:
                    print(sys.exc_info(), 42)
                    self.websocket.close()
                    self.parent.controlling = False

    def disconnect(self):
        self.parent.controlling = False
        self.websocket.close()

    def heartbeat(self):
        try:
            a = self.websocket.recv()
            # print("beat", a)
            if len(a) == 0:
                return False
            else:
                return True
        except:
            print(sys.exc_info(), 290)
            return False


root = tk.Tk()
app = MainWindow(master=root)
app.mainloop()
