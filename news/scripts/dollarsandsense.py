from datetime import timedelta, timezone
from playwright.sync_api import sync_playwright
from util.spider_util import SpiderUtil
from bs4 import BeautifulSoup
import re

# 获取当前文件名，用于日志标识
util = SpiderUtil()
filename = "./news/data/dollarsandsense/list.json"
storage_state_path = "./news/auth/dollarsandsense.json"


def get_detail(page):
    # 获取文章详情内容
    try:
        detail_element = page.query_selector("#mvp-content-main")
        print(detail_element)
        if detail_element:
            html_content = detail_element.inner_html()
            # 使用BeautifulSoup处理HTML
            soup = BeautifulSoup(html_content, "html.parser")
            # 移除脚本和样式元素
            for element in soup.select("script, style, iframe, .adsbygoogle"):
                element.decompose()

            # 移除隐藏的段落元素
            for element in soup.find_all("p", style=re.compile(r"display:\s*none")):
                element.decompose()

            # 查找并移除包含 "Read Also" 的段落及其链接
            read_also_elements = soup.find_all("p", string=lambda text: text and "Read Also" in text)
            if not read_also_elements:
                # 查找更复杂的结构，如包含strong、em和a标签的"Read Also"段落
                read_also_elements = soup.find_all("p", 
                    lambda tag: tag.find("strong") and tag.find("em") and 
                                tag.find("a") and "Read Also" in tag.text if hasattr(tag, 'text') else False)
            
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

            # 移除页脚内容
            footer_divs = soup.find_all("div", class_=["posts-nav-link", "mvp-org-wrap"])
            for div in footer_divs:
                util.info(f"移除页脚内容: {div}")
                div.decompose()

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
                headless=util.get_crawler_headless(),
                slow_mo=300,
            )

            # 创建新的浏览器上下文
            try:
                context = browser.new_context(
                    storage_state=util.get_storage_state("dollarsandsense")
                )
            except Exception as e:
                util.error(f"创建浏览器上下文失败: {e}")
                # 创建一个没有存储状态的上下文作为备选
                browser = p.firefox.launch(
                    headless=False,
                    slow_mo=300,
                )
                context = browser.new_context()
                util.info("已创建无状态的浏览器上下文")
            page = context.new_page()

            js = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            page.add_init_script(js)

            # 访问目标网页
            page.goto("https://dollarsandsense.sg/", timeout=10000)
            util.info("开始访问网页...")

            # 检查是否存在 cloudflare 验证
            cloudflare_exists = page.is_visible(
                "text=needs to review the security of your connection before proceeding",
                timeout=3000,
            )
            if cloudflare_exists:
                util.info("检测到需要 cloudflare 验证, 请手动完成验证操作...")
                util.log_action_error("检测到 dollarsandsense 需要 cloudflare 验证")
                # 等待内容出现
                page.wait_for_selector(".mvp-side-tab-story h2 > a", timeout=10000)
                util.info("cloudflare 验证已完成")
                storage = context.storage_state(path=storage_state_path)
            else:
                util.info("已验证状态无须验证")

            # 获取前3个实际加载的新闻项（确保有内容）
            # 等待标签有内容
            page.wait_for_selector(".mvp-side-tab-story h2 > a", timeout=10000)
            util.info("文章链接已加载")

            news_items = page.query_selector_all(".mvp-side-tab-story h2 > a")[:5]

            util.info(f"找到 {len(news_items)} 篇文章")

            # 处理获取到的数据
            for item in news_items[:1]:
                link = item.get_attribute("href").strip()
                if link in ",".join(_links):
                    util.info(f"exists link: {link}")
                    continue

                title = item.inner_text().strip()
                if not title:  # 如果标题为空，跳过这篇文章
                    util.info("跳过空标题文章")
                    continue

                util.info(f"开始访问网页: {link}")
                page.goto(link)

                # 等待文章详情内容加载
                page.wait_for_selector("#mvp-content-main", timeout=10000)
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
                            "source": "dollarsandsense",
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


# 使用 SpiderUtil 的 execute_with_timeout 方法执行 run 函数
# if __name__ == "__main__":
#     util.execute_with_timeout(run, timeout=120)
