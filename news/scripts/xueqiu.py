from datetime import timedelta, timezone
from playwright.sync_api import sync_playwright
from util.spider_util import SpiderUtil
from bs4 import BeautifulSoup
import re

# 获取当前文件名，用于日志标识
util = SpiderUtil()
filename = "./news/data/xueqiu/list.json"
storage_state_path = "./news/auth/xueqiu_cookie.json"


def remove_ad_elements(soup, user_id):
    if str(user_id) == "8680038754":
        # 查找包含 "添加⭐️标 不再错过推送" 的元素
        start_b_tags = []
        for b_tag in soup.find_all("b"):
            if "添加⭐️标 不再错过推送" in b_tag.text:
                start_b_tags.append(b_tag)

        # 如果找到了开始标记
        if start_b_tags:
            start_b = start_b_tags[0]
            start_p = start_b.find_parent("p")
            if start_p:
                # 移除这个 <p> 标签之前的所有 <p> 标签
                current = start_p.previous_sibling
                while current:
                    next_element = current.previous_sibling
                    if current.name == "p":
                        current.decompose()
                    current = next_element
                # 移除包含开始标记的 <p> 标签本身
                start_p.decompose()

        # 查找包含 "关注⭐️红与绿⭐️" 的元素
        end_b_tags = []
        for b_tag in soup.find_all("b"):
            if "关注⭐️红与绿⭐️" in b_tag.text:
                end_b_tags.append(b_tag)

        # 如果找到了结束标记
        if end_b_tags:
            end_b = end_b_tags[0]
            end_p = end_b.find_parent("p")
            if end_p:
                # 移除这个 <p> 标签及其之后的所有 <p> 标签
                current = end_p
                while current:
                    next_element = current.next_sibling
                    if current.name == "p":
                        current.decompose()
                    current = next_element


def get_detail(page, user_id):
    # 获取文章详情内容
    try:
        detail_element = page.query_selector(".article__bd__detail")
        if detail_element:
            html_content = detail_element.inner_html()
            # 使用BeautifulSoup处理HTML
            soup = BeautifulSoup(html_content, "html.parser")
            # 移除脚本和样式元素
            for element in soup.select("script, style"):
                element.decompose()

            # 移除隐藏的段落元素
            for element in soup.find_all("p", style=re.compile(r"display:\s*none")):
                element.decompose()

            remove_ad_elements(soup, user_id)
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
                    storage_state=util.get_storage_state("xueqiu_cookie")
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
            page.goto("https://xueqiu.com/", timeout=6000)
            util.info("开始访问网页...")

            # 检查是否存在登录按钮
            login_button_exists = page.is_visible("a:has-text('登录')", timeout=3000)
            if login_button_exists:
                util.info("检测到需要登录, 请手动完成登录操作...")
                util.log_action_error("检测到雪球需要登录")
                # 等待登录按钮消失，表示用户已登录
                page.wait_for_selector(
                    "a:has-text('登录')", state="hidden", timeout=20000
                )
                util.info("登录操作已完成")
                storage = context.storage_state(path=storage_state_path)
                print(storage)
            else:
                util.info("已登录状态，无需重新登录")

            # 点击 class="home-timeline-tabs" 下面的 <a href="" id="" class="active">关注</a>
            # 使用更精确的选择器，避免点击到其他带有"关注"文本的元素
            page.click(".home-timeline-tabs a.active:has-text('关注')")

            # 使用 expect_response 等待 XHR 响应
            with page.expect_response(
                lambda response: "v4/statuses/home_timeline.json" in response.url
                and "sub_type=original" in response.url
                and response.status == 200
            ) as response_info:
                # 点击触发 XHR 请求, 按钮被 modal 挡住
                # 先检查并关闭可能出现的 modal
                if page.is_visible(".modal", timeout=2000):
                    util.info("检测到弹窗，尝试关闭")
                    page.click(".modal .close")
                    page.wait_for_selector(".modal", state="hidden", timeout=5000)

                # 点击"只看原发"按钮
                page.click("a:has-text('只看原发')")

            # 获取响应对象
            response = response_info.value
            json_data = response.json()
            util.info(
                f"成功获取雪球原创内容，共 {len(json_data.get('home_timeline', []))} 条"
            )

            # 处理获取到的数据
            articles = json_data.get("home_timeline", [])
            for article in articles[:10]:  # 只处理前10条
                link = f"https://xueqiu.com{article.get('target', '')}"
                # 检查链接是否已存在
                if link in _links:
                    util.info(f"链接已存在: {link}")
                    continue

                id = article.get("id", "")
                user_id = article.get("user_id", "")
                image = article.get("cover_pic", "")
                type = article.get("type", "")
                title = article.get("title", "")
                created_at = article.get("created_at", "")
                pub_date = util.convert_utc_to_local(
                    created_at / 1000, tz=timezone(timedelta(hours=8))
                )

                util.info(f"开始访问网页: {link}")
                page.goto(link)

                # 等待文章详情内容加载
                author = ""
                page.wait_for_selector(".article__bd__detail", timeout=10000)
                if "user" in article and "screen_name" in article.get("user", {}):
                    author = article.get("user", {}).get("screen_name", "")
                description = get_detail(page, user_id)
                if description != "":
                    # 添加到文章列表
                    insert = True
                    _articles.insert(
                        0,
                        {
                            "id": id,
                            "user_id": user_id,
                            "author": author,
                            "title": title,
                            "type": type,
                            "description": description,
                            "link": link,
                            "pub_date": pub_date,
                            "source": "xueqiu",
                            "image": image,
                            "kind": 1,
                            "language": "zh-CN",
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
if __name__ == "__main__":
    # util.execute_with_timeout(run, timeout=120)
    util.info("stop")
