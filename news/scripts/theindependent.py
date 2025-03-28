from datetime import timedelta, timezone
from playwright.sync_api import sync_playwright
from util.spider_util import SpiderUtil
from bs4 import BeautifulSoup
import re

# 获取当前文件名，用于日志标识
util = SpiderUtil()
filename = "./news/data/theindependent/list.json"

def get_detail(page):
    # 获取文章详情内容
    try:
        detail_element = page.query_selector("article")
        print(detail_element)
        if detail_element:
            html_content = detail_element.inner_html()
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
            browser = p.firefox.launch(
                headless=util.get_crawler_headless()
            )

            context = browser.new_context()
            page = context.new_page()

            js = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            page.add_init_script(js)

            # 访问目标网页
            util.info("开始访问网页...")
            page.goto("https://theindependent.sg/", timeout=12000)
            
            # 等待标签有内容
            util.info("等待文章加载")
            page.wait_for_selector(".type-post", timeout=12000)

            news_items = page.query_selector_all(".type-post")[:5]

            util.info(f"找到 {len(news_items)} 篇文章")

            # 处理获取到的数据
            for item in news_items[:5]:
                link_element = item.query_selector(".entry-title > a")
                if not link_element:
                    util.info("未找到链接元素")
                    continue
                    
                link = link_element.get_attribute("href").strip()
                if link in ",".join(_links):
                    util.info(f"exists link: {link}")
                    continue

                title = link_element.inner_text().strip()
                if not title:  # 如果标题为空，跳过这篇文章
                    util.info("跳过空标题文章")
                    continue

                util.info(f"开始访问详情: {link}")
                page.goto(link, timeout=12000)

                # 等待文章详情内容加载
                page.wait_for_selector("article", timeout=10000)
                description = get_detail(page)
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
                            "source": "theindependent",
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


# if __name__ == "__main__":
#     util.execute_with_timeout(run, timeout=120)
