from datetime import timedelta, timezone
from playwright.sync_api import sync_playwright
from util.spider_util import SpiderUtil
from bs4 import BeautifulSoup
import re

# 获取当前文件名，用于日志标识
util = SpiderUtil()
filename = "./news/data/thesmartinvestor/list.json"


def get_detail(page):
    # 获取文章详情内容
    try:
        # 直接获取 HTML 内容而不是先获取元素
        html_content = page.inner_html(".post-content")
        if html_content:
            # 使用BeautifulSoup处理HTML
            soup = BeautifulSoup(html_content, "html.parser")
            # 移除脚本和样式元素
            for element in soup.select("script, style, iframe"):
                element.decompose()

            return str(soup).strip()
        else:
            util.error("未找到文章详情内容")
            return ""
    except Exception as e:
        util.error(f"获取文章详情时出错: {str(e)}")
        return ""


def run():
    data = util.history_posts(filename)
    _articles = data["articles"]
    _links = data["links"]
    insert = False
    with sync_playwright() as p:
        try:
            # 启动浏览器，添加更多安全选项
            browser = p.firefox.launch(headless=util.get_crawler_headless())

            context = browser.new_context()
            page = util.get_page(context)

            # 访问目标网页
            util.info("开始访问网页并等待文章加载...")
            page.goto(
                "https://thesmartinvestor.com.sg/",
                wait_until="domcontentloaded",
                timeout=10000,
            )
            page.wait_for_selector(".loop-list > article", timeout=10000)

            news_items = page.query_selector_all(".loop-list > article")[:2]

            util.info(f"找到 {len(news_items)} 篇文章")

            # 处理获取到的数据
            for item in news_items:
                link = (
                    item.query_selector(".post-title > a").get_attribute("href").strip()
                )
                if link in ",".join(_links):
                    util.info(f"exists link: {link}")
                    continue

                title = item.query_selector(".post-title > a").inner_text().strip()
                if not title:  # 如果标题为空，跳过这篇文章
                    util.info("跳过空标题文章")
                    continue

                image = (
                    item.query_selector(".media > a > img").get_attribute("src").strip()
                )

                detail_page = util.get_page(context)

                util.info(f"开始访问详情: {link}")
                detail_page.goto(link, wait_until="domcontentloaded", timeout=10000)
                description = get_detail(detail_page)
                if description != "":
                    # 添加到文章列表
                    insert = True
                    _articles.insert(
                        0,
                        {
                            "title": title,
                            "description": description,
                            "image": image,
                            "link": link,
                            "pub_date": util.current_time_string(),
                            "source": "thesmartinvestor",
                            "kind": 1,
                            "language": "en",
                        },
                    )
            # 保存数据
            if len(_articles) > 0 and insert:
                if len(_articles) > 20:
                    _articles = _articles[:20]
                util.write_json_to_file(_articles, filename)

            # 完成后关闭浏览器
            page.close()
            context.close()
            browser.close()
        except Exception as e:
            context.close()
            browser.close()
            util.error(f"执行脚本时出错: {str(e)}")


if __name__ == "__main__":
    util.execute_with_timeout(run, timeout=120)
