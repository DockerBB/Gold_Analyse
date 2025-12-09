import tkinter as tk
from tkinter import font
import threading
import time
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup


def fetch_gold_price():
    """抓取现货黄金价格"""
    url = "https://quote.fx678.com/exchange/wgjs"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')

        # 找到现货黄金行
        gold_row = soup.find('tr', {'id': 'XAU'})

        if gold_row:
            cells = gold_row.find_all('td')

            data = {
                '名称': cells[0].text.strip(),
                '最新价': cells[1].text.strip(),
                '涨跌': cells[2].find('span').text.strip() if cells[2].find('span') else cells[2].text.strip(),
                '涨跌幅': cells[3].text.strip(),
                '最高': cells[4].text.strip(),
                '最低': cells[5].text.strip(),
                '昨收': cells[6].text.strip(),
                '更新时间': cells[7].text.strip()
            }

            return data
        else:
            return None

    except Exception as e:
        print(f"抓取失败: {e}")
        return None


class GoldPriceApp:
    def __init__(self, root):
        self.root = root
        self.last_price = None
        self.previous_price = None

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

        # 创建界面
        self.create_widgets()

        # 绑定拖动事件
        self.bind_drag_events()

        # 启动数据更新线程
        self.start_update_thread()

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

    def manual_refresh(self, event):
        """手动刷新数据"""
        self.status_var.set("手动刷新中...")
        self.update_gold_data()

    def quit_app(self, event):
        """退出程序"""
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

    def start_update_thread(self):
        """启动数据更新线程"""
        update_thread = threading.Thread(target=self.update_loop, daemon=True)
        update_thread.start()

    def update_loop(self):
        """循环更新数据"""
        # 首次更新
        self.update_gold_data()

        # 然后每秒更新一次
        while True:
            time.sleep(1)
            self.update_gold_data()

    def update_gold_data(self):
        """获取并更新黄金数据"""
        data = fetch_gold_price()

        if data:
            try:
                # 提取价格信息
                current_price = float(data['最新价'].replace(',', ''))
                change_str = data['涨跌']
                change_percent_str = data['涨跌幅'].replace('%', '')

                # 处理涨跌值
                if change_str.startswith('+'):
                    up_down = 1
                    change_value = float(change_str[1:])
                elif change_str.startswith('-'):
                    up_down = -1
                    change_value = float(change_str[1:])
                else:
                    up_down = 0
                    change_value = 0

                # 处理涨跌幅
                try:
                    change_percent = float(change_percent_str)
                except:
                    change_percent = 0


                # 在主线程中更新显示
                self.root.after(0, self.update_display, current_price, up_down, change_percent, data['更新时间'])

            except Exception as e:
                print(f"数据处理错误: {e}")
                self.root.after(0, self.update_display, None, 0, 0, "")
        else:
            self.root.after(0, self.update_display, None, 0, 0, "")

    def update_display(self, price, up_down, change_percent, update_time=""):
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

            # 更新状态
            self.status_var.set("数据获取失败")
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



        self.status_var.set(f"更新于 {update_time or current_time}")


def main():
    root = tk.Tk()
    # 在Windows系统上尝试启用ClearType字体渲染
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = GoldPriceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()