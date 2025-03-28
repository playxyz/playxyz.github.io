from playwright.sync_api import sync_playwright
from util.spider_util import SpiderUtil
import requests
from bs4 import BeautifulSoup
import os

# 获取当前文件名，用于日志标识
util = SpiderUtil()
filename = "./news/data/ainvest/list.json"

# 添加请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "upgrade-insecure-requests": "1",
}


def get_detail(link):
    util.info(f"link: {link}")
    try:
        response = requests.get(link, headers=headers)
        if response.status_code == 200:
            lxml = BeautifulSoup(response.text, "lxml")
            soup = lxml.select_one(".news-content")

            ad_elements = soup.select("script,style,visualization")
            # 移除这些元素
            for element in ad_elements:
                element.decompose()

            return str(soup).strip()
        else:
            util.error(f"request: {link} error: {response.status_code}")
            return ""
    except Exception as e:
        util.error(f"Error fetching {link}: {str(e)}")
        return ""


def run():
    data = util.history_posts(filename)
    _articles = data["articles"]
    _links = data["links"]
    insert = False
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.firefox.launch(
            headless=util.get_crawler_headless(),
            slow_mo=300,
        )
        context = browser.new_context()
        page = util.get_page(context)
        # 访问目标网页
        page.goto(
            "https://www.ainvest.com/news/articles/",
            wait_until="domcontentloaded",
            timeout=10000,
        )
        util.info("开始访问网页...")

        # 等待第一个带有实际内容的文章标题出现
        page.wait_for_selector("#news-articles h3:not(:empty)", timeout=10000)
        util.info("文章内容已加载")

        # 获取前3个实际加载的新闻项（确保有内容）
        news_items = page.query_selector_all("#news-articles .grid a")[:5]
        util.info(f"找到 {len(news_items)} 篇文章")

        results = []
        for idx, item in enumerate(news_items, 1):
            # 添加调试信息
            util.info(f"\n正在处理第 {idx} 篇文章")
            util.info("HTML 结构：")
            util.info(item.evaluate("el => el.outerHTML"))

            try:
                # 等待每个文章的具体元素
                title = item.query_selector("h3").inner_text().strip()
                if not title:  # 如果标题为空，跳过这篇文章
                    util.info("跳过空标题文章")
                    continue

                link = "https://www.ainvest.com{}".format(
                    item.get_attribute("href").strip()
                )
                if link in ",".join(_links):
                    util.info(f"exists link: {link}")
                    continue
                image = ""
                description = get_detail(link)
                if description != "":
                    insert = True
                    _articles.insert(
                        0,
                        {
                            "title": title,
                            "description": description,
                            "link": link,
                            "pub_date": util.current_time_string(),
                            "source": "ainvest",
                            "image": image,
                            "kind": 1,
                            "language": "en",
                        },
                    )
            except Exception as e:
                util.error(f"处理文章时出错: {e}")
                continue

        if len(_articles) > 0 and insert:
            if len(_articles) > 20:
                _articles = _articles[:20]
            util.write_json_to_file(_articles, filename)
        browser.close()
        return results


if __name__ == "__main__":
    util.execute_with_timeout(run)
