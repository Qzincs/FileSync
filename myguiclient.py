import os
import pickle
import re
from os.path import isfile, isdir
from node import Node
from threading import Thread
from tkinter import *
from tkinter.filedialog import *
from tkinter.messagebox import *
from tkinter.ttk import *


class Client:
    """
    图形用户界面类。用户交互的对象。
    """

    def __init__(self):
        self.root = self.root()
        self.node_setup()
        self.create_widgets()

    def root(self):
        """
        初始化窗口
        """
        root = Tk()
        root.title("文件同步程序")
        return root

    def show(self):
        """
        窗口主循环
        """
        self.root.mainloop()

    def node_setup(self):
        """
        初始化节点
        """
        # 尝试从保存数据中读取节点信息，若读取失败则重新创建新的节点
        if isfile('data.pk'):
            with open('data.pk', 'rb') as save:
                try:
                    self.node = Node(pickle.load(save), self)
                    self.flag = True
                except Exception as e:
                    self.node = Node(client=self)
                    self.flag = False
        else:
            self.node = Node(client=self)
            self.flag = True

        # 在新线程中启动节点的服务器
        self.server = Thread(target=self.node.start)
        self.server.daemon = True
        self.server.start()

    def create_widgets(self):
        """
        初始化窗口控件
        """
        # 窗口分栏
        self.bottom = Frame()
        self.bottom.pack(side=BOTTOM)
        self.middle = Frame()
        self.middle.pack(side=BOTTOM)
        self.topleft = Frame()
        self.topleft.pack(side=LEFT)
        self.topright = Frame()
        self.topright.pack(side=RIGHT)
        # 左上角控件设置
        Label(self.topleft, text='本机IP:').grid(column=0, row=0)
        self.url_label = Label(self.topleft, text=self.node.url)
        self.url_label.grid(column=1, row=0)
        Label(self.topleft, text='共享主机IP:').grid(column=0, row=1)
        self.peer_url_label = Label(self.topleft, text=self.node.peer_url)
        self.peer_url_label.grid(column=1, row=1)
        # 右上角控件设置
        Label(self.topright, text='同步文件夹路径:').grid(column=0, row=0)
        self.path_label = Label(self.topright, text=self.node.folder.path)
        self.path_label.grid(column=1, row=0)
        # 中间控件设置
        self.new_connect_button = Button(self.middle, text='新的连接', command=self.connect_window)
        self.new_connect_button.pack(side=LEFT)
        self.set_port_button = Button(self.middle, text='设置端口', command=self.set_port_window)
        self.set_port_button.pack(side=LEFT)
        self.open_folder_button = Button(self.middle, text='打开同步文件夹', command=self.open_folder)
        self.open_folder_button.pack(side=LEFT)
        self.selelct_folder_button = Button(self.middle, text='选择同步文件夹', command=self.select_folder)
        self.selelct_folder_button.pack(side=LEFT)
        self.sync_button = Button(self.middle, text='立即同步', command=self.sync)
        self.sync_button.pack(side=LEFT)
        self.quit_button = Button(self.middle, text='退出', command=self.quit)
        self.quit_button.pack(side=LEFT)
        # 下方控件设置
        Label(self.bottom, text="提示：同步大文件时程序可能进入无响应状态，此时请耐心等待").pack(side=RIGHT)

        if self.flag:
            showinfo('初始化成功', '服务器正在运行。')
        else:
            showerror('初始化失败', '节点数据已损坏，请重新设置节点！')

    def connect_window(self):
        """
        新的连接窗口
        """
        self.top = Toplevel()
        self.top.title("连接到新设备")
        url = StringVar()
        Label(self.top, text='请输入共享节点的IP地址和端口号\n如“127.0.0.1:6666”').pack()
        Entry(self.top, textvariable=url).pack()
        Button(self.top, text='连接', command=lambda: self.connect(url.get())).pack()

    def connect(self, url):
        """
        点击‘连接’按钮的事件。尝试与指定主机连接
        :param url: 要连接的主机的IP地址
        """
        # 用正则表达式判断IP地址是否合法
        pattern = re.compile(
            r'^((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}:([0-9]|[1-9]\d{1,3}|[1-5]\d{4}|6[0-4]\d{3}|65[0-4]\d{2}|655[0-2]\d|6553[0-5])$')
        if pattern.match(url):
            # 尝试连接
            self.node.connect('http://' + url)
            self.top.destroy()
        else:
            showerror('错误：无效的地址', '地址格式不正确，请检查输入！')

    def set_port_window(self):
        """
        设置端口窗口
        """
        self.top = Toplevel()
        self.top.title("设置端口")
        port = StringVar()
        Label(self.top, text='请输入端口号。范围：1024~65535').pack()
        Entry(self.top, textvariable=port).pack()
        Button(self.top, text='确定', command=lambda: self.set_port(port.get())).pack(side=LEFT, padx=5)
        Button(self.top, text='取消', command=self.top.destroy).pack(side=LEFT)

    def set_port(self, port):
        """
        设置端口
        :param port: 端口号
        """
        try:
            # 判断端口合法性
            if 1024 <= int(port) <= 65535:
                # 设置端口
                self.node.set_url(port)
                self.url_label["text"] = self.node.url
                self.top.destroy()
                # 重启服务器
                self.node.shutdown()
                self.server.join()
                self.server = Thread(target=self.node.start)
                self.server.daemon = True
                self.server.start()
            else:
                showerror('错误', '端口无效，请重新输入！')
        except ValueError:
            showerror('错误', '端口无效，请重新输入！')

    def open_folder(self):
        """
        点击‘打开同步文件夹’按钮的事件。在资源管理器中打开同步文件夹
        """
        if self.node.folder.path != '':
            try:
                path = self.node.folder.path
                dir = os.path.dirname(path + "\\")
                os.startfile(dir)
            except FileNotFoundError:
                showerror('找不到同步文件夹', '同步文件夹可能被重命名、移动或删除。请重新设置同步文件夹！')
        else:
            showerror('未设置同步文件夹', '请先设置同步文件夹！')

    def select_folder(self):
        """
        点击‘选择同步文件夹’按钮的事件。在资源管理器中选择同步文件夹
        """
        path = askdirectory() or self.node.folder.path
        self.node.folder.add_folder(path)
        self.node.save()
        self.path_label['text'] = path

    def sync(self):
        """
        点击‘立即同步’按钮的事件。开始同步同步文件夹
        """
        # 扫描自上次同步以来同步文件夹中发生的更改
        if self.node.scan():
            # 同步文件夹
            self.node.sync_now()

    def info(self, title, message):
        """
        弹出信息窗口
        :param title: 窗口标题
        :param message: 提示信息
        """
        showinfo(title, message)

    def warning(self, title, message):
        """
        弹出警告窗口
        :param title: 窗口标题
        :param message: 提示信息
        """
        showwarning(title, message)

    def error(self, title, message):
        """
        弹出错误窗口
        :param title: 窗口标题
        :param message: 提示信息
        """
        showerror(title, message)

    def yesorno(self, title, message):
        """
        弹出选择是或否窗口
        :param title: 窗口标题
        :param message: 提示信息
        :return: 用户的选择：是或否
        """
        return askyesno(title, message)

    def quit(self):
        """
        点击‘退出’按钮的事件。退出程序
        """
        self.node.save()
        self.root.quit()


def main():
    # 启动程序
    client = Client()
    client.show()


if __name__ == '__main__': main()
