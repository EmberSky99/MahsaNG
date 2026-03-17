#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDP to TCP Port Monitor
监听V2bX进程的UDP端口，并在对应的TCP端口上创建监听
每10分钟检测一次，动态更新监听端口
"""

import subprocess
import socket
import threading
import time
import re
import logging
import gc
from typing import Set, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class UDPTCPMonitor:
    def __init__(self):
        self.tcp_servers = {}  # 存储TCP服务器socket对象
        self.current_ports = set()  # 当前监听的端口
        self.running = True
        self.active_threads = set()  # 跟踪活跃线程
        
    def get_v2bx_udp_ports(self) -> Set[int]:
        """获取V2bX进程监听的UDP端口"""
        try:
            # 执行ss命令获取网络连接信息，使用with语句确保进程正确关闭
            with subprocess.Popen(['ss', '-tulnp'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
                stdout, stderr = proc.communicate(timeout=30)  # 添加超时防止挂起
                
                if proc.returncode != 0:
                    logging.error(f"执行ss命令失败: {stderr}")
                    return set()
            
            ports = set()
            lines = stdout.strip().split('\n')
            
            for line in lines:
                # 查找包含V2bX的UDP连接
                if 'udp' in line and 'V2bX' in line and 'UNCONN' in line:
                    # 使用正则表达式提取端口号
                    # 匹配格式: *:端口号 或 0.0.0.0:端口号
                    match = re.search(r'[*0-9.]+:(\d+)', line)
                    if match:
                        port = int(match.group(1))
                        ports.add(port)
                        logging.info(f"发现V2bX UDP端口: {port}")
            
            return ports
            
        except subprocess.TimeoutExpired:
            logging.error("ss命令执行超时")
            return set()
        except Exception as e:
            logging.error(f"获取UDP端口时出错: {e}")
            return set()
    
    def create_tcp_server(self, port: int) -> socket.socket:
        """在指定端口创建TCP监听服务器"""
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('0.0.0.0', port))
            server_socket.listen(5)
            logging.info(f"TCP服务器已在端口 {port} 上启动")
            return server_socket
        except Exception as e:
            logging.error(f"在端口 {port} 创建TCP服务器失败: {e}")
            return None
    
    def handle_client(self, client_socket: socket.socket, address: tuple, port: int):
        """处理客户端连接"""
        try:
            logging.info(f"端口 {port} 收到来自 {address} 的连接")
            # 设置socket超时，避免长时间阻塞
            client_socket.settimeout(30.0)
            
            # 这里可以添加具体的业务逻辑
            # 目前只是简单地接收数据并关闭连接
            try:
                data = client_socket.recv(1024)
                if data:
                    logging.info(f"端口 {port} 收到数据: {len(data)} 字节")
            except socket.timeout:
                logging.debug(f"端口 {port} 客户端连接超时")
            except Exception as e:
                logging.debug(f"端口 {port} 接收数据时出错: {e}")
                
        except Exception as e:
            logging.error(f"处理客户端连接时出错: {e}")
        finally:
            # 确保socket被正确关闭
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                client_socket.close()
            except:
                pass
    
    def tcp_server_worker(self, port: int):
        """TCP服务器工作线程"""
        server_socket = self.create_tcp_server(port)
        if not server_socket:
            return
        
        self.tcp_servers[port] = server_socket
        
        try:
            while self.running and port in self.tcp_servers:
                try:
                    server_socket.settimeout(1.0)  # 设置超时以便定期检查running状态
                    client_socket, address = server_socket.accept()
                    # 为每个客户端连接创建新线程
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address, port)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    continue
                except OSError as e:
                    # Socket已关闭或其他OS错误
                    if self.running and port in self.tcp_servers:
                        logging.debug(f"端口 {port} TCP服务器OSError: {e}")
                    break
                except Exception as e:
                    if self.running and port in self.tcp_servers:
                        logging.error(f"端口 {port} TCP服务器出错: {e}")
                    break
        finally:
            # 确保socket被正确关闭
            try:
                server_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                server_socket.close()
            except:
                pass
            if port in self.tcp_servers:
                del self.tcp_servers[port]
                logging.info(f"端口 {port} TCP服务器已关闭")    

    def update_tcp_listeners(self):
        """更新TCP监听器"""
        new_ports = self.get_v2bx_udp_ports()
        
        # 停止不再需要的TCP服务器
        ports_to_stop = self.current_ports - new_ports
        for port in ports_to_stop:
            logging.info(f"停止监听端口 {port}")
            if port in self.tcp_servers:
                try:
                    # 先关闭socket再从字典中删除
                    server_socket = self.tcp_servers[port]
                    server_socket.shutdown(socket.SHUT_RDWR)
                    server_socket.close()
                except Exception as e:
                    logging.debug(f"关闭端口 {port} 时出错: {e}")
                finally:
                    # 确保从字典中删除
                    if port in self.tcp_servers:
                        del self.tcp_servers[port]
        
        # 先更新当前端口集合
        self.current_ports = new_ports
        
        # 启动新的TCP服务器
        ports_to_start = new_ports - set(self.tcp_servers.keys())
        for port in ports_to_start:
            logging.info(f"开始监听端口 {port}")
            thread = threading.Thread(target=self.tcp_server_worker, args=(port,))
            thread.daemon = True
            thread.start()
            # 添加小延迟，避免快速创建大量线程
            time.sleep(0.01)
        
        logging.info(f"当前监听的端口: {sorted(self.current_ports)}")
        logging.debug(f"活跃TCP服务器: {sorted(self.tcp_servers.keys())}")
        
        # 检查资源使用情况
        self.check_resource_usage()
    
    def check_resource_usage(self):
        """检查资源使用情况"""
        try:
            # 检查活跃线程数
            active_threads = threading.active_count()
            if active_threads > 50:  # 如果线程数过多，发出警告
                logging.warning(f"活跃线程数较多: {active_threads}")
            
            # 检查TCP服务器数量
            server_count = len(self.tcp_servers)
            if server_count > 20:  # 如果服务器数过多，发出警告
                logging.warning(f"TCP服务器数量较多: {server_count}")
                
            logging.debug(f"资源使用情况 - 线程: {active_threads}, TCP服务器: {server_count}")
            
        except Exception as e:
            logging.debug(f"检查资源使用时出错: {e}")
    
    def run(self):
        """主运行循环"""
        logging.info("UDP to TCP Monitor 启动")
        logging.info("提示: 连续按两次 Ctrl+C 才能停止程序")
        
        interrupt_count = 0
        
        try:
            while self.running:
                try:
                    logging.debug("开始新的监控周期...")
                    self.update_tcp_listeners()
                    
                    # 等待10分钟（600秒）
                    logging.info("等待10分钟后进行下次检查...")
                    for i in range(600):
                        if not self.running:
                            logging.info("检测到停止信号，退出等待循环")
                            break
                        time.sleep(1)
                        
                        # 每分钟进行一次垃圾回收，帮助释放资源
                        if i % 60 == 0 and i > 0:
                            gc.collect()
                            logging.debug(f"已等待 {i//60} 分钟，进行垃圾回收")
                        
                except KeyboardInterrupt:
                    interrupt_count += 1
                    if interrupt_count == 1:
                        logging.warning("收到中断信号，再按一次 Ctrl+C 确认停止...")
                        # 给用户5秒时间决定
                        try:
                            time.sleep(5)
                            interrupt_count = 0  # 重置计数
                            logging.info("继续运行...")
                        except KeyboardInterrupt:
                            logging.info("收到确认停止信号，正在停止...")
                            break
                    else:
                        logging.info("收到确认停止信号，正在停止...")
                        break
                except Exception as e:
                    logging.error(f"运行时出错: {e}")
                    logging.info("10秒后重试...")
                    # 出错时不停止，继续运行
                    time.sleep(10)  # 等待10秒后重试
                    
        except Exception as e:
            logging.error(f"主循环异常退出: {e}")
        finally:
            logging.info("主循环结束，开始清理...")
            self.stop()
    
    def stop(self):
        """停止监控"""
        if not self.running:
            return  # 已经停止了，避免重复执行
            
        logging.info("正在停止所有TCP服务器...")
        self.running = False
        
        # 关闭所有TCP服务器
        for port, server_socket in list(self.tcp_servers.items()):
            try:
                # 先shutdown再close，确保连接正确关闭
                server_socket.shutdown(socket.SHUT_RDWR)
                server_socket.close()
                logging.info(f"已关闭端口 {port} 的TCP服务器")
            except Exception as e:
                logging.debug(f"关闭端口 {port} 服务器时出错: {e}")
        
        self.tcp_servers.clear()
        self.current_ports.clear()
        
        # 给线程一些时间来清理
        time.sleep(1)
        
        # 强制垃圾回收
        gc.collect()
        logging.info("UDP to TCP Monitor 已停止")


def main():
    """主函数"""
    monitor = UDPTCPMonitor()
    
    try:
        monitor.run()
    except Exception as e:
        logging.error(f"程序异常退出: {e}")
        monitor.stop()


if __name__ == "__main__":
    main()