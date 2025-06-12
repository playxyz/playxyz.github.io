from datetime import timedelta, timezone
from playwright.sync_api import sync_playwright
from util.spider_util import SpiderUtil
from bs4 import BeautifulSoup
import re

# 获取当前文件名，用于日志标识
util = SpiderUtil()
filename = "./news/data/theedgemalaysia/list.json"


def get_detail(page):
    # 获取文章详情内容
    try:
        # 直接获取 HTML 内容而不是先获取元素
        html_content = page.inner_html("body")
        if html_content:
            # 使用BeautifulSoup处理HTML
            soup = BeautifulSoup(html_content, "html.parser")
            # 选取新闻内容主体
            soup = soup.select_one("div[class*=news-detail_newsTextDataWrap]")
            # 移除脚本和样式元素
            for element in soup.select(
                "script, style, iframe, .sharethis-inline-share-buttons,.insert_ads,[class*=tisg-],.post-share,.instagram-media,.navigation"
            ):
                element.decompose()

            # 查找并移除包含 "Read Also" 的段落及其链接
            read_also_elements = soup.find_all(
                "p", string=lambda text: text and "Read also" in text
            )
            if not read_also_elements:
                # 查找更复杂的结构，如包含strong、em和a标签的"Read Also"段落
                read_also_elements = soup.find_all(
                    "p",
                    lambda tag: (
                        tag.find("strong")
                        and tag.find("em")
                        and tag.find("a")
                        and "Read also" in tag.text
                        if hasattr(tag, "text")
                        else False
                    ),
                )

            for read_also_p in read_also_elements:
                util.info(f"移除 Read Also 段落: {read_also_p.get_text()[:30]}...")
                # 移除该段落
                read_also_p.decompose()

                # 移除该段落后面的所有内容
                next_element = read_also_p.next_sibling
                while next_element:
                    next_sibling = next_element.next_sibling
                    next_element.decompose()
                    next_element = next_sibling

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
                "https://theedgemalaysia.com/categories/corporate",
                wait_until="domcontentloaded",
                timeout=10000,
            )

            # 等待页面加载并查找所有包含 "/node/" 的链接
            page.wait_for_selector("a[href^='/node/']", timeout=10000)
            util.info("页面已加载，开始查找文章链接...")

            # 查找所有 href 是 "/node/" + 数字 的 a 标签
            news_items = page.query_selector_all("a[href^='/node/']")

            if len(news_items) > 0:
                util.info(f"找到 {len(news_items)} 篇文章")
                news_items = news_items[:2]
            else:
                util.info("未找到文章链接")
                return

            # 处理获取到的数据
            for item in news_items:
                link = (
                    "https://theedgemalaysia.com" + item.get_attribute("href").strip()
                )
                if link in ",".join(_links):
                    util.info(f"exists link: {link}")
                    continue

                title = item.query_selector(".row > .col-12 > span").inner_text().strip()
                if not title:
                    util.info("跳过空标题文章")
                    continue

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
                            "link": link,
                            "pub_date": util.current_time_string(),
                            "source": "theedgemalaysia",
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
            context.close()
            browser.close()
        except Exception as e:
            context.close()
            browser.close()
            util.error(f"执行脚本时出错: {str(e)}")


if __name__ == "__main__":
    util.execute_with_timeout(run, timeout=120)
