import tkinter as tk
from tkinter import font
import threading
import time
import json
import websocket
import ssl
from datetime import datetime


class GoldPriceApp:
    def __init__(self, root, open_price=None):
        self.last_bid_price = None
        self.previous_bid_price = None
        self.root = root

        # 设置开盘价，如果没有提供则使用默认值
        self.open_price = open_price

        # 移除窗口标题栏和边框
        self.root.overrideredirect(True)
        self.root.geometry("250x120")  # 稍微增加窗口尺寸以容纳阴影
        self.root.resizable(False, False)

        # 设置透明背景 - 使用灰色作为透明色
        self.root.configure(bg='gray')
        self.root.attributes('-transparentcolor', 'gray')
        self.root.attributes('-topmost', True)  # 保持窗口在最前面
        self.root.attributes('-alpha', 0.95)  # 添加轻微不透明度增强可读性

        # 创建更清晰的字体
        try:
            self.common_font = font.Font(family="Segoe UI", size=20, weight="bold")
        except:
            try:
                self.common_font = font.Font(family="Microsoft YaHei UI", size=20, weight="bold")
            except:
                self.common_font = font.Font(family="Tahoma", size=25, weight="bold")

        # WebSocket相关变量
        self.ws = None
        self.ws_thread = None
        self.is_connected = False
        self.reconnect_interval = 15  # 重连间隔
        self.max_reconnect_attempts = 3  # 最大重连次数
        self.reconnect_attempts = 0  # 当前重连次数
        self.connection_active = False  # 连接活跃状态
        self.should_reconnect = True  # 是否应该重连

        # AllTick API配置
        self.token = "2529a14f7a370b0704cf1008ea8ce271-c-app"  # 请替换为你的实际token
        self.symbol = "XAUUSD"  # 黄金/美元代码
        self.ws_url = f"wss://quote.alltick.co/quote-b-ws-api?token={self.token}"  # 外汇贵金属API地址

        # 创建界面
        self.create_widgets()

        # 绑定拖动事件
        self.bind_drag_events()

        # 启动WebSocket连接
        self.connect_websocket()

        # 初始位置居中
        self.center_window()

    def center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')

    def bind_drag_events(self):
        """绑定拖动事件"""
        # 允许通过点击任何地方拖动窗口
        self.root.bind('<Button-1>', self.start_drag)
        self.root.bind('<B1-Motion>', self.on_drag)

        # 右键点击刷新
        self.root.bind('<Button-3>', self.manual_refresh)

        # 双击退出
        self.root.bind('<Double-Button-1>', self.quit_app)

    def start_drag(self, event):
        """开始拖动"""
        self.x = event.x
        self.y = event.y

    def on_drag(self, event):
        """拖动窗口"""
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def quit_app(self, event):
        """双击退出程序"""
        self.should_reconnect = False  # 停止重连
        if self.ws:
            self.ws.close()
        self.root.quit()

    def create_widgets(self):
        # 主容器 - 使用灰色背景以实现透明效果
        main_frame = tk.Frame(self.root, bg='gray')
        main_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        # 创建一个内容框架，用于更好的视觉层次
        content_frame = tk.Frame(main_frame, bg='gray')
        content_frame.pack(expand=True)

        # 价格显示 - 添加阴影效果
        self.price_var = tk.StringVar(value="--.--")
        self.price_shadow_label = tk.Label(
            content_frame,
            textvariable=self.price_var,
            font=self.common_font,
            bg='gray',
            fg='#000000',  # 阴影颜色 - 黑色
        )
        self.price_label = tk.Label(
            content_frame,
            textvariable=self.price_var,
            font=self.common_font,
            bg='gray',
            fg='#E8E8E8',  # 前景颜色 - 浅灰色
        )

        # 箭头显示 - 添加阴影效果
        self.arrow_var = tk.StringVar(value="→")
        self.arrow_shadow_label = tk.Label(
            content_frame,
            textvariable=self.arrow_var,
            font=self.common_font,
            bg='gray',
            fg='#000000',  # 阴影颜色 - 黑色
        )
        self.arrow_label = tk.Label(
            content_frame,
            textvariable=self.arrow_var,
            font=self.common_font,
            bg='gray',
            fg='#E8E8E8',  # 前景颜色 - 浅灰色
        )

        # 涨跌幅显示 - 添加阴影效果
        self.change_var = tk.StringVar(value="--.--%")
        self.change_shadow_label = tk.Label(
            content_frame,
            textvariable=self.change_var,
            font=self.common_font,
            bg='gray',
            fg='#000000',  # 阴影颜色 - 黑色
        )
        self.change_label = tk.Label(
            content_frame,
            textvariable=self.change_var,
            font=self.common_font,
            bg='gray',
            fg='#E8E8E8',  # 前景颜色 - 浅灰色
        )

        # 使用网格布局精确控制阴影位置
        # 价格标签
        self.price_shadow_label.grid(row=0, column=0, padx=3, pady=1)
        self.price_label.grid(row=0, column=0, padx=3, pady=0)

        # 箭头标签
        self.arrow_shadow_label.grid(row=0, column=1, padx=3, pady=1)
        self.arrow_label.grid(row=0, column=1, padx=3, pady=0)

        # 涨跌幅标签
        self.change_shadow_label.grid(row=0, column=2, padx=3, pady=1)
        self.change_label.grid(row=0, column=2, padx=3, pady=0)

        # 添加状态提示
        self.status_var = tk.StringVar(value="连接中...")
        self.status_label = tk.Label(
            main_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 15),
            bg='gray',
            fg='#AAAAAA'
        )
        self.status_label.pack(side=tk.BOTTOM, pady=(2, 0))

        # 居中显示
        content_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def connect_websocket(self):
        """连接AllTick WebSocket API"""
        # 确保只有一个连接
        if self.ws_thread and self.ws_thread.is_alive():
            print("已有活跃的WebSocket连接，跳过新连接")
            return

        self.ws_thread = threading.Thread(target=self._websocket_thread, daemon=True)
        self.ws_thread.start()

    def _websocket_thread(self):
        """WebSocket线程 - 基于官方示例重构"""

        def on_open(ws):
            """WebSocket连接打开时发送订阅请求"""
            print("WebSocket连接已开启")
            self.root.after(0, lambda: self.status_var.set("已连接"))
            self.is_connected = True
            self.connection_active = True

            # 发送订阅请求 - 使用官方示例格式
            sub_param = {
                "cmd_id": 22002,
                "seq_id": 123,
                "trace": "3baaa938-f92c-4a74-a228-fd49d5e2f8bc-1678419657806",
                "data": {
                    "symbol_list": [
                        {
                            "code": self.symbol,
                            "depth_level": 1,  # 只订阅第一档深度
                        }
                    ]
                }
            }

            sub_str = json.dumps(sub_param)
            ws.send(sub_str)
            print(f"已订阅{self.symbol}深度行情")

            # 启动心跳线程
            threading.Thread(target=self.thread_heartbeat, args=(ws,), daemon=True).start()

        def on_message(ws, message):
            """处理接收到的WebSocket消息"""
            try:
                # 使用json.loads而不是eval，更安全
                data = json.loads(message)
                print(f"收到消息: {data}")  # 调试信息

                # 立即处理数据并更新显示
                self.process_and_update_data(data)

                # 重置重连计数
                self.reconnect_attempts = 0
                # 标记连接为活跃
                self.connection_active = True
            except Exception as e:
                print(f"解析WebSocket数据错误: {e}")
                self.root.after(0, lambda: self.status_var.set(f"数据错误: {str(e)}"))

        def on_error(ws, error):
            """处理WebSocket错误"""
            print(f"WebSocket错误: {error}")
            self.root.after(0, lambda: self.status_var.set(f"连接错误: {str(error)}"))
            self.is_connected = False
            self.connection_active = False

        def on_close(ws, close_status_code, close_msg):
            """处理WebSocket连接关闭"""
            print(f"WebSocket连接关闭: {close_status_code} - {close_msg}")
            self.root.after(0, lambda: self.status_var.set("连接已断开"))
            self.is_connected = False
            self.connection_active = False

            # 只有在应该重连且未达到最大重连次数时才尝试重连
            if self.should_reconnect and self.reconnect_attempts < self.max_reconnect_attempts:
                self.reconnect_attempts += 1
                wait_time = self.reconnect_interval * self.reconnect_attempts  # 递增等待时间
                print(f"尝试重新连接 ({self.reconnect_attempts}/{self.max_reconnect_attempts})，等待 {wait_time} 秒...")
                self.root.after(0, lambda: self.status_var.set(
                    f"重新连接中 ({self.reconnect_attempts}/{self.max_reconnect_attempts})"))
                time.sleep(wait_time)
                self.connect_websocket()
            else:
                print("达到最大重连次数，停止尝试")
                self.root.after(0, lambda: self.status_var.set("连接失败，请检查网络和token"))

        # 创建WebSocket连接 - 使用官方示例方式
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            # 运行WebSocket
            self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        except Exception as e:
            print(f"WebSocket连接异常: {e}")
            self.root.after(0, lambda: self.status_var.set(f"连接异常: {str(e)}"))
            self.connection_active = False

    def thread_heartbeat(self, ws):
        """心跳线程 - 基于官方示例"""
        while self.is_connected and self.should_reconnect:
            time.sleep(10)  # 每10秒发送一次心跳
            if ws.sock and ws.sock.connected:
                heartbeat = {
                    "cmd_id": 22000,
                    "seq_id": 123,
                    "trace": "heartbeat-trace",
                    "data": {}
                }
                try:
                    ws.send(json.dumps(heartbeat))
                    print("已发送心跳")
                except Exception as e:
                    print(f"发送心跳失败: {e}")
                    break

    def process_and_update_data(self, data):
        """处理接收到的数据并立即更新显示"""
        try:
            # 检查是否是深度数据 (cmd_id: 22999)
            if data.get('cmd_id') != 22999:
                return  # 忽略其他类型的数据

            depth_data = data.get('data', {})
            code = depth_data.get('code')

            # 确认是我们订阅的品种
            if code != self.symbol:
                return

            # 获取买盘数据
            bids = depth_data.get('bids', [])

            if not bids:
                print("买盘数据不完整")
                return

            # 获取最优买价
            current_price = float(bids[0].get('price', 0))

            # 保存当前价格到历史记录
            self.previous_bid_price = self.last_bid_price
            self.last_bid_price = current_price

            # 计算涨跌额和涨跌幅（相对于开盘价）
            up_down = 0
            change_percent = 0

            # 如果有开盘价，则与开盘价比较
            if self.open_price is not None and self.open_price != 0:
                up_down = current_price - self.open_price
                change_percent = (up_down / self.open_price) * 100
            # 如果没有开盘价，则与前一个价格比较
            elif self.previous_bid_price is not None and self.previous_bid_price != 0:
                up_down = current_price - self.previous_bid_price
                change_percent = (up_down / self.previous_bid_price) * 100

            # 更新显示
            self.root.after(0, lambda: self.update_display(current_price, up_down, change_percent))

        except Exception as e:
            print(f"处理买盘数据时出错: {e}")
            self.root.after(0, lambda: self.status_var.set(f"处理错误: {str(e)}"))

    def update_display(self, price, up_down, change_percent):
        """更新界面显示"""
        if price is None:
            # 显示错误状态
            self.price_var.set("--.--")
            self.arrow_var.set("→")
            self.change_var.set("--.--%")
            error_color = '#FFA500'  # 橙色表示错误
            error_shadow = '#000000'  # 阴影保持黑色

            # 更新前景和阴影颜色
            self.price_label.configure(fg=error_color)
            self.price_shadow_label.configure(fg=error_shadow)
            self.arrow_label.configure(fg=error_color)
            self.arrow_shadow_label.configure(fg=error_shadow)
            self.change_label.configure(fg=error_color)
            self.change_shadow_label.configure(fg=error_shadow)
            return

        # 更新价格
        self.price_var.set(f"{price:.2f}")

        # 确定箭头和颜色
        if up_down > 0:
            arrow = "↑"
            color = '#FF4444'  # 亮红色表示上涨
        elif up_down < 0:
            arrow = "↓"
            color = '#44FF44'  # 亮绿色表示下跌
        else:
            arrow = "→"
            color = '#E8E8E8'  # 浅灰色表示平盘

        # 更新箭头和涨跌幅显示
        self.arrow_var.set(arrow)

        if change_percent != 0:
            self.change_var.set(f"{abs(change_percent):.2f}%")
        else:
            self.change_var.set("0.00%")

        # 设置颜色 - 前景使用指定颜色，阴影保持黑色
        self.price_label.configure(fg=color)
        self.price_shadow_label.configure(fg='#000000')
        self.arrow_label.configure(fg=color)
        self.arrow_shadow_label.configure(fg='#000000')
        self.change_label.configure(fg=color)
        self.change_shadow_label.configure(fg='#000000')

        # 更新状态为最新时间
        current_time = datetime.now().strftime("%H:%M:%S")
        # 如果有开盘价，在状态栏显示开盘价
        if self.open_price is not None:
            self.status_var.set(f"开盘价: {self.open_price:.2f} | 更新于 {current_time}")
        else:
            self.status_var.set(f"更新于 {current_time}")

    def manual_refresh(self, event=None):
        """手动刷新价格 - 重新连接WebSocket"""
        self.root.after(0, lambda: self.status_var.set("重新连接中..."))
        if self.ws:
            self.ws.close()
        self.connect_websocket()


def main():
    root = tk.Tk()

    # 设置开盘价 - 这里可以修改为您需要的开盘价
    # 例如：假设开盘价是 2350.00
    open_price = 4227.00

    # 将开盘价传递给应用
    app = GoldPriceApp(root, open_price=open_price)

    # 在Windows系统上尝试启用ClearType字体渲染
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    root.mainloop()


if __name__ == "__main__":
    main()