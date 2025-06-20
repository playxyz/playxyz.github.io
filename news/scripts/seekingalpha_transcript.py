from datetime import timedelta, timezone
from playwright.sync_api import sync_playwright
from util.spider_util import SpiderUtil
from bs4 import BeautifulSoup
import re

# 获取当前文件名，用于日志标识
util = SpiderUtil()
filename = "./news/data/seekingalpha/list.json"
storage_state_path = "./news/auth/seekingalpha_cookie.json"

def get_detail(page):
    # 获取文章详情内容
    try:
        detail_element = page.query_selector("div[data-test-id='content-container']")
        if detail_element:
            html_content = detail_element.inner_html()
            # 使用BeautifulSoup处理HTML
            soup = BeautifulSoup(html_content, "html.parser")
            # 移除脚本和样式元素
            for element in soup.select("script, style"):
                element.decompose()

            # 获取清理后的HTML内容
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
                    storage_state=util.get_storage_state("seekingalpha_cookie")
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

            # 访问目标网页
            page.goto("https://seekingalpha.com/", timeout=6000)
            util.info("开始访问网页...")

            page.wait_for_timeout(3000)
            # 检查是否存在人机验证
            if page.is_visible("text=Before we continue...", timeout=3000):
                util.log_action_error("检测到人机验证页面")
                return
            else:
                util.info("无需人机验证")

            # 检查是否存在登录按钮
            login_button_exists = page.is_visible("span.hidden.text-medium-2-r.md\\:flex:has-text('Log in')", timeout=3000)
            if login_button_exists:
                util.log_action_error("检测到 seekingalpha 需要登录")
                # 等待登录按钮消失，表示用户已登录
                page.wait_for_selector(
                    "span.hidden.text-medium-2-r.md\\:flex:has-text('Log in')", state="hidden", timeout=20000
                )
                util.info("登录操作已完成")
                storage = context.storage_state(path=storage_state_path)
                print(storage)
            else:
                util.info("已登录状态，无需重新登录")

            # 使用 expect_response 等待 XHR 响应
            with page.expect_response(
                lambda response: "/api/v3/feed" in response.url
                and "all[]=sa-transcripts" in response.url
                and response.status == 200
            ) as response_info:
                page.goto("https://seekingalpha.com/author/sa-transcripts/analysis", timeout=6000)

            # 获取响应对象
            response = response_info.value
            json_data = response.json()
            util.info(
                f"成功获取seekingalpha原创内容，共 {len(json_data.get('data', []))} 条"
            )

            # 处理获取到的数据
            articles = json_data.get("data", [])
            for article in articles[:5]:  # 只处理前5条
                # 获取文章链接，使用嵌套字典访问方式
                links = article.get('links', {})
                link_path = links.get('self', '')
                link = f"https://seekingalpha.com{link_path}"
                # 检查链接是否已存在
                if link in _links:
                    util.info(f"链接已存在: {link}")
                    continue

                id = article.get("id", "")
                type = article.get("type", "")
                title = article.get("attributes", {}).get("title", "")
                pub_date = util.current_time_string()

                util.info(f"开始访问网页: {link}")
                page.goto(link)

                # 等待文章详情内容加载
                # 等待内容容器加载
                try:
                    page.wait_for_selector("text=View all", timeout=5000)
                except Exception as e:
                    util.info(f"等待'View all'选择器超时: {str(e)}")
                    continue
                # 滚动到页面底部以加载所有内容
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                # 等待一小段时间确保内容加载完成
                page.wait_for_timeout(2000)
                # 检查页面是否包含"Review the latest"文本，如果有则跳过当前文章
                if page.query_selector("text=Review the latest") is not None:
                    # 检测到"Review the latest"文本或"View as PDF"文本，跳过当前文章
                    continue
                    
                description = get_detail(page)
                if description != "":
                    # 添加到文章列表
                    insert = True
                    _articles.insert(
                        0,
                        {
                            "id": id,
                            "title": title,
                            "type": type,
                            "description": description,
                            "link": link,
                            "pub_date": pub_date,
                            "source": "seekingalpha",
                            "kind": 1,
                            "language": "en",
                        },
                    )
            # 保存数据
            if len(_articles) > 0 and insert:
                if len(_articles) > 10:
                    _articles = _articles[:10]
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
