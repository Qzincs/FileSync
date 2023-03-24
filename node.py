import os
import socket
import hashlib
import pickle
from os.path import isfile, isdir
from thread_xmlrpc_server import ThreadXMLRPCServer
from xmlrpc.client import ServerProxy, Binary
from urllib.parse import urlparse


def get_ip_port(url):
    """
    从URL中提取IP和端口
    :param url: 要处理的URL
    :return: URL的IP和端口号
    """
    name = urlparse(url)[1]
    parts = name.split(':')
    return parts[0], int(parts[-1])


class Node:
    """
    共享主机节点类。用于建立共享服务器，连接共享主机，上传下载文件等。
    """

    def __init__(self, data=None, client=None):
        """
        初始化节点
        :param data:存储的节点数据
        :param client: GUI对象
        """
        # 若存储的数据存在，则从中读取共享节点的url和文件夹对象
        if data:
            self.peer_url = data[0]
            self.folder = data[1]
            self.port = data[2]
        # 否则重新初始化
        else:
            self.peer_url = ''
            self.folder = Folder()
            self.port = '6666'
        # 获取本机url，端口号默认为6666
        self.url = 'http://' + socket.gethostbyname(socket.gethostname()) + ':' + self.port
        # 设置GUI对象
        self.client = client
        # 存储节点数据为文件
        self.data = [self.peer_url, self.folder, self.port]
        self.save()

    def set_url(self, port='6666', ip=socket.gethostbyname(socket.gethostname())):
        """
        设置端口号
        :param port:端口号,默认为6666
        :param ip:IP地址，默认自动获取
        """
        self.port = port
        self.url = 'http://' + ip + ':' + port
        self.save()

    def start(self):
        """
        启动XML-RPC服务器
        """
        self.server = ThreadXMLRPCServer(get_ip_port(self.url), allow_none=True)
        self.server.register_instance(self)
        self.server.serve_forever()

    def shutdown(self):
        """
        停止XML-RPC服务器
        """
        self.server.shutdown()

    def save(self):
        """
        保存节点数据到文件中
        """
        with open('data.pk', 'wb') as save:
            # 清空原文件数据
            save.seek(0)
            save.truncate()
            # 存储数据
            self.data = [self.peer_url, self.folder, self.port]
            pickle.dump(self.data, save)

    def connect(self, url):
        """
        尝试与节点进行连接
        :param url:节点的url
        :return: 连接节点的服务器对象。若连接出错，返回None
        """
        try:
            s = ServerProxy(url)
            # 若要连接的主机地址与原来的不同，则重新请求连接
            if self.peer_url != url:
                flag = s.request(self.url)
                # 若对方同意连接
                if flag:
                    # 更新共享主机地址
                    self.peer_url = url
                    self.save()
                    # 弹出提示框
                    self.client.info('成功', '与' + url + '连接成功')
                    self.client.peer_url_label['text'] = self.peer_url
                    return s
                # 若对方拒绝连接，弹出警告提示框
                else:
                    self.client.warning('警告', url + '拒绝连接')
            else:
                return s
        # 捕获异常并提示
        except ConnectionRefusedError:
            self.client.error('错误', '与' + url + '连接失败\n可能的原因：IP地址错误或目标主机不在线')
            return None
        except OSError:
            if self.peer_url == '':
                self.client.error('错误', '尚未进行连接，请先点击”新的连接“与共享主机建立连接')
            else:
                self.client.error('错误', '与' + url + '连接失败\n可能的原因：IP地址错误或目标主机不在线')
            return None

    def request(self, url):
        """
        请求连接许可。服务器远程调用函数。
        :param url: 请求方的url
        :return: 若允许连接，则返回True；否则返回False
        """
        # 弹窗询问是否允许连接
        r = self.client.yesorno('新的连接请求', url + '请求连接，是否允许？')
        # 若允许，更新自己的共享主机地址并返回True；否则返回False
        if r:
            self.peer_url = url
            self.client.peer_url_label['text'] = self.peer_url
            return True
        else:
            return False

    def scan(self):
        """
        扫描自上次同步以来同步文件夹中发生的更改，更新文件列表。若成功，返回True；失败，返回False
        """
        try:
            self.folder.update_file_list()
        except FileNotFoundError:
            if self.folder.path:
                self.client.error('找不到同步文件夹', '同步文件夹可能被重命名、移动或删除。请重新设置同步文件夹！')
            else:
                self.client.error('未设置同步文件夹', '请先设置同步文件夹！')
            return False
        return True

    def sync(self, del_list, change_list):
        """
        同步文件夹。服务器远程调用函数
        :param del_list:共享主机的待删除文件列表
        :param change_list:共享主机的待修改文件列表
        """
        # 若待删除文件列表不为空，则在同步文件夹中删除包含的文件
        if del_list:
            self.folder.del_file(del_list, change_list)
        # 若待修改文件列表不为空，则在同步文件夹中更新包含的文件
        if change_list:
            for file in change_list:
                self.download(file)
        self.folder.add_new_file()

    def sync_now(self):
        """
        与共享主机连接并同步
        """
        # 建立连接
        s = self.connect(self.peer_url)
        if s:
            # 共享主机更改端口号后，进行同步不知什么原因在connect中不会出现异常，所以在此捕获
            try:
                # 进行同步
                s.sync(self.folder.del_list, self.folder.change_list)
                self.client.info('提示', '同步完成')
            except ConnectionRefusedError:
                self.client.error('错误', '同步失败\n可能的原因：共享主机不在线或共享主机更改了程序的端口号')

    def download(self, r_path):
        """
        下载文件。
        :param r_path: 文件的相对路径
        """
        s = self.connect(self.peer_url)
        if s:
            self.folder.write_file(r_path, s.upload(r_path))

    def upload(self, r_path):
        """
        上传文件。远程调用函数。
        :param r_path: 文件的相对路径
        """
        return self.folder.read_file(r_path)


class Folder:
    """
    同步文件夹类。维护同步文件夹，对文件进行实际的读写操作。
    """

    def __init__(self):
        """
        初始化同步文件夹
        """
        # 同步文件夹路径
        self.path = ''
        # 文件列表(字典)
        self.file_list = {}
        # 待删除文件列表
        self.del_list = []
        # 待修改文件列表
        self.change_list = []
        # 同步时新增或修改文件列表
        self.new_file_list = []

    def add_folder(self, path):
        """
        添加同步文件夹
        :param path: 同步文件夹路径
        """
        # 设置路径
        self.path = path
        # 更新文件列表
        self.file_list = {}
        self.update_file_list()

    def update_file_list(self):
        """
        更新同步文件夹的文件列表
        """
        # 创建文件列表的副本
        old_file_list = self.file_list.copy()
        # 清空文件列表
        self.file_list.clear()
        file_list = self.file_list = {}
        # 遍历同步文件夹内的项目
        for r_path in os.listdir(self.path):
            # 获取此项目的绝对路径
            a_path = self.path + '/' + r_path
            # 子文件夹不进行同步
            if isdir(a_path):
                continue
            else:
                # 计算文件的MD5值并以[文件绝对路径:MD5]的形式存储到文件列表
                with open(a_path, 'rb') as f:
                    md5 = hashlib.md5(f.read()).hexdigest()
                    file_list[a_path] = md5

        # 同步文件夹的文件列表更新完成后，查找自上次同步后发生的修改
        del_list = []
        change_list = []
        # 在旧文件列表中而不在新文件列表内的是待删除的文件，将其添加到待删除文件列表
        for file in old_file_list:
            if file not in file_list:
                r_path = file.replace(self.path + '/', '')
                del_list.append(r_path)
        # 待修改文件包括新的文件，和修改过的文件
        # 在新文件列表中而不在旧文件列表内的是新增的文件
        # MD5值与原来不同的是修改过的文件
        for file in file_list:
            if (file not in old_file_list) or (file_list[file] != old_file_list[file]):
                r_path = file.replace(self.path + '/', '')
                change_list.append(r_path)

        self.del_list = del_list
        self.change_list = change_list

    def add_new_file(self):
        """
        将同步时新增或修改文件添加到文件列表中
        """
        for r_path in self.new_file_list:
            a_path = self.path + '/' + r_path
            with open(a_path, 'rb') as file:
                md5 = hashlib.md5(file.read()).hexdigest()
                self.file_list[a_path] = md5
        self.new_file_list = []

    def read_file(self, r_path):
        """
        读取文件
        :param r_path:文件的相对路径
        :return:返回文件的二进制数据
        """
        # 将相对路径转换为绝对路径
        a_path = self.path + '/' + r_path
        # 读取并返回文件
        return Binary(open(a_path, 'rb').read())

    def write_file(self, r_path, data):
        """
        写入文件
        :param r_path: 文件的相对路径
        :param data: 文件的二进制数据
        """
        self.new_file_list.append(r_path)
        # 将相对路径转换为绝对路径
        a_path = self.path + '/' + r_path
        # 写入文件
        with open(a_path, 'wb') as file:
            file.write(data.data)

    def del_file(self, del_list, change_list):
        """
        删除文件。待修改文件也需要先修改再重新创建。
        :param del_list: 待删除文件列表
        :param change_list: 待修改文件列表
        """
        del_list = del_list + change_list
        for f in del_list:
            a_path = self.path + '/' + f
            if isdir(a_path):
                os.removedirs(a_path)
            elif isfile(a_path):
                os.remove(a_path)
