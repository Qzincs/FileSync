from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn


class ThreadXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    """
    多线程版本的XML-RPC服务器，可同时处理多个客户端的请求
    """
    pass
