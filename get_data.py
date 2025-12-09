import requests
from bs4 import BeautifulSoup
import time


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


# 示例：每秒抓取一次
if __name__ == "__main__":
    print("开始抓取现货黄金数据...")

    try:
        while True:
            data = fetch_gold_price()
            if data:
                print(f"\n[{time.strftime('%H:%M:%S')}] 现货黄金:")
                print(f"最新价: {data['最新价']}")
                print(f"涨跌: {data['涨跌']} ({data['涨跌幅']})")
                print(f"最高: {data['最高']} | 最低: {data['最低']}")
                print(f"更新时间: {data['更新时间']}")
            else:
                print("数据抓取失败")

            time.sleep(1)  # 每秒一次

    except KeyboardInterrupt:
        print("\n程序已停止")