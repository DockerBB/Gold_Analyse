import tkinter as tk
from tkinter import font
import threading
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def fetch_gold_price_from_current_page(driver,self):
    """从已加载的页面中提取黄金价格数据（不刷新页面）"""
    try:
        if not self.wait:
            self.wait = WebDriverWait(self.driver, 5)

        gold_row = self.wait.until(  # 使用已有的wait对象
            EC.presence_of_element_located((By.ID, "XAU"))
        )
        wait = WebDriverWait(driver, 5)
        gold_row = wait.until(
            EC.presence_of_element_located((By.ID, "XAU"))
        )

        if gold_row:
            cells = gold_row.find_elements(By.TAG_NAME, "td")
            data = {
                '名称': cells[0].text,
                '最新价': cells[1].text,
                '涨跌': cells[2].text.strip(),
                '涨跌幅': cells[3].text,
                '最高': cells[4].text,
                '最低': cells[5].text,
                '昨收': cells[6].text,
                '更新时间': cells[7].text
            }
            return data
        else:
            print("未找到ID为'XAU'的表格行。")
            return None

    except Exception as e:
        print(f"从页面提取数据失败: {e}")
        return None


class GoldPriceApp:
    def __init__(self, root):
        self.root = root
        self.last_price = None
        self.previous_price = None
        self.wait = None  # 添加等待对象
        self.update_count = 0
        self.max_updates_before_restart = 100  # 每100次更新重启浏览器
        # 1. 首先初始化Selenium WebDriver
        self.init_selenium_driver()

        # 2. 设置GUI窗口（无边框、透明、置顶）
        self.root.overrideredirect(True)
        self.root.geometry("250x120")
        self.root.resizable(False, False)
        self.root.configure(bg='gray')
        self.root.attributes('-transparentcolor', 'gray')
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)

        # 3. 创建字体
        try:
            self.common_font = font.Font(family="Segoe UI", size=20, weight="bold")
        except:
            try:
                self.common_font = font.Font(family="Microsoft YaHei UI", size=20, weight="bold")
            except:
                self.common_font = font.Font(family="Tahoma", size=25, weight="bold")

        # 4. 创建界面
        self.create_widgets()

        # 关键修复：全局绑定拖动事件（覆盖整个窗口）
        self.bind_global_drag_events()

        self.start_update_thread()
        self.center_window()

    def init_selenium_driver(self):
        """初始化Selenium Chrome WebDriver"""
        try:
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--window-size=1920,1080')

            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(15)
            print("正在初始加载页面（无头模式）...")
            self.driver.get("https://quote.fx678.com/exchange/wgjs")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "XAU"))
            )
            self.wait = WebDriverWait(self.driver, 10)  # 创建一次，重复使用
            print("页面初始加载完成。")
        except Exception as e:
            print(f"初始化WebDriver失败: {e}")
            self.driver = None


    def center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')

    # 关键修复：全局事件绑定
    def bind_global_drag_events(self):
        """全局绑定拖动/刷新/退出事件（确保窗口任意区域响应）"""
        # 使用bind_all绑定到整个应用，避免子组件拦截
        self.root.bind_all('<Button-1>', self.start_drag, add='+')
        self.root.bind_all('<B1-Motion>', self.on_drag, add='+')
        self.root.bind_all('<Button-3>', self.manual_refresh, add='+')
        self.root.bind_all('<Double-Button-1>', self.quit_app, add='+')

    def start_drag(self, event):
        """开始拖动 - 修复坐标计算"""
        # 记录相对于根窗口的坐标（而非子组件）
        self.start_x = event.x_root - self.root.winfo_x()
        self.start_y = event.y_root - self.root.winfo_y()

    def on_drag(self, event):
        """拖动窗口 - 精准计算位置"""
        x = event.x_root - self.start_x
        y = event.y_root - self.start_y
        self.root.geometry(f"+{x}+{y}")

    def manual_refresh(self, event):
        """手动刷新数据"""
        self.status_var.set("手动刷新中...")
        self.update_gold_data()

    def quit_app(self, event):
        """退出程序时关闭WebDriver"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
            print("浏览器驱动已关闭。")
        self.root.quit()

    def create_widgets(self):
        # 主容器
        main_frame = tk.Frame(self.root, bg='gray')
        main_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        content_frame = tk.Frame(main_frame, bg='gray')
        content_frame.pack(expand=True)

        # 价格显示 - 主文本和阴影
        self.price_var = tk.StringVar(value="--.--")
        self.price_shadow_label = tk.Label(
            content_frame,
            textvariable=self.price_var,
            font=self.common_font,
            bg='gray',
            fg='#000000',
        )
        self.price_label = tk.Label(
            content_frame,
            textvariable=self.price_var,
            font=self.common_font,
            bg='gray',
            fg='#E8E8E8',
        )

        # 箭头显示
        self.arrow_var = tk.StringVar(value="→")
        self.arrow_shadow_label = tk.Label(
            content_frame,
            textvariable=self.arrow_var,
            font=self.common_font,
            bg='gray',
            fg='#000000',
        )
        self.arrow_label = tk.Label(
            content_frame,
            textvariable=self.arrow_var,
            font=self.common_font,
            bg='gray',
            fg='#E8E8E8',
        )

        # 涨跌幅显示
        self.change_var = tk.StringVar(value="--.--%")
        self.change_shadow_label = tk.Label(
            content_frame,
            textvariable=self.change_var,
            font=self.common_font,
            bg='gray',
            fg='#000000',
        )
        self.change_label = tk.Label(
            content_frame,
            textvariable=self.change_var,
            font=self.common_font,
            bg='gray',
            fg='#E8E8E8',
        )

        # 使用网格布局
        self.price_shadow_label.grid(row=0, column=0, padx=3, pady=1)
        self.price_label.grid(row=0, column=0, padx=3, pady=0)

        self.arrow_shadow_label.grid(row=0, column=1, padx=3, pady=1)
        self.arrow_label.grid(row=0, column=1, padx=3, pady=0)

        self.change_shadow_label.grid(row=0, column=2, padx=3, pady=1)
        self.change_label.grid(row=0, column=2, padx=3, pady=0)

        # 状态栏
        self.status_var = tk.StringVar(value="正在启动浏览器...")
        self.status_label = tk.Label(
            main_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 15),
            bg='gray',
            fg='#AAAAAA'
        )
        self.status_label.pack(side=tk.BOTTOM, pady=(2, 0))

        content_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def start_update_thread(self):
        """启动数据更新线程"""
        update_thread = threading.Thread(target=self.update_loop, daemon=True)
        update_thread.start()

    def update_loop(self):
        """循环更新数据"""
        time.sleep(2)
        self.update_gold_data()

        while True:
            time.sleep(1)
            self.update_gold_data()

    def update_gold_data(self):
        """获取并更新黄金数据（使用Selenium）"""
        self.update_count += 1
        # 定期重启浏览器释放内存
        if self.update_count >= self.max_updates_before_restart:
            self.restart_browser()
            self.update_count = 0
        if not self.driver:
            self.root.after(0, lambda: self.status_var.set("浏览器驱动未就绪"))
            self.root.after(0, self.update_display, None, 0, 0, "")
            return

        data = fetch_gold_price_from_current_page(self.driver,self)

        if data:
            try:
                current_price = float(data['最新价'].replace(',', ''))
                change_str = data['涨跌'].strip()
                change_percent_str = data['涨跌幅'].replace('%', '')
                yesterday_price = float(data['昨收'].replace(',', ''))

                if change_str.startswith('+'):
                    up_down = 1
                    change_value = float(change_str[1:])
                elif change_str.startswith('-'):
                    up_down = -1
                    change_value = float(change_str[1:])
                else:
                    try:
                        change_value = float(change_str)
                        up_down = 1 if current_price > yesterday_price else (
                            -1 if current_price < yesterday_price else 0)
                    except:
                        up_down = 0
                        change_value = 0

                try:
                    change_percent = float(change_percent_str)
                except:
                    change_percent = 0.0

                self.root.after(0, self.update_display, current_price, up_down, change_percent, data['更新时间'])

            except ValueError as e:
                print(f"数据转换错误: {e}, 原始数据: {data}")
                self.root.after(0, self.update_display, None, 0, 0, "")
            except Exception as e:
                print(f"数据处理错误: {e}")
                self.root.after(0, self.update_display, None, 0, 0, "")
        else:
            self.root.after(0, self.update_display, None, 0, 0, "")
    def restart_browser(self):
        """重启浏览器释放内存"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
            self.init_selenium_driver()

    def update_display(self, price, up_down, change_percent, update_time=""):
        """更新界面显示"""
        if price is None:
            self.price_var.set("--.--")
            self.arrow_var.set("→")
            self.change_var.set("--.--%")
            error_color = '#FFA500'
            error_shadow = '#000000'

            self.price_label.configure(fg=error_color)
            self.price_shadow_label.configure(fg=error_shadow)
            self.arrow_label.configure(fg=error_color)
            self.arrow_shadow_label.configure(fg=error_shadow)
            self.change_label.configure(fg=error_color)
            self.change_shadow_label.configure(fg=error_shadow)

            self.status_var.set("数据获取失败")
            return

        self.price_var.set(f"{price:.2f}")

        if up_down > 0:
            arrow = "↑"
            color = '#FF4444'
        elif up_down < 0:
            arrow = "↓"
            color = '#44FF44'
        else:
            arrow = "→"
            color = '#E8E8E8'

        self.arrow_var.set(arrow)

        if change_percent != 0:
            self.change_var.set(f"{abs(change_percent):.2f}%")
        else:
            self.change_var.set("0.00%")

        self.price_label.configure(fg=color)
        self.price_shadow_label.configure(fg='#000000')
        self.arrow_label.configure(fg=color)
        self.arrow_shadow_label.configure(fg='#000000')
        self.change_label.configure(fg=color)
        self.change_shadow_label.configure(fg='#000000')

        current_time = datetime.now().strftime("%H:%M:%S")
        self.status_var.set(f"更新于 {current_time}")


def main():
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = GoldPriceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()