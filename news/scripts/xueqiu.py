from datetime import timedelta, timezone
from playwright.sync_api import sync_playwright
from util.spider_util import SpiderUtil

# 获取当前文件名，用于日志标识
util = SpiderUtil()
filename = "./news/data/xueqiu/list.json"

def run():
    data = util.history_posts(filename)
    _articles = data["articles"]
    _links = data["links"]
    insert = False
    with sync_playwright() as p:
        try:
            # 启动浏览器，添加更多安全选项
            browser = p.firefox.launch(
                headless=False,
                slow_mo=1000,
            )

            # 创建新的浏览器上下文
            context = browser.new_context(storage_state=util.get_storage_state("xueqiu_cookie"))
            page = context.new_page()

            # 访问目标网页
            page.goto("https://xueqiu.com/", timeout=60000)
            util.info("开始访问网页...")

            # 检查是否存在登录按钮
            login_button_exists = page.is_visible("a:has-text('登录')", timeout=3000)
            if login_button_exists:
                util.info("检测到需要登录")
                # 等待用户手动完成登录操作
                util.info("请手动完成登录操作...")
                # 等待登录按钮消失，表示用户已登录
                page.wait_for_selector("a:has-text('登录')", state="hidden", timeout=20000)
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
                lambda response: "v4/statuses/home_timeline.json" in response.url and 
                                "sub_type=original" in response.url and 
                                response.status == 200
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
            util.info(f"成功获取雪球原创内容，共 {len(json_data.get('home_timeline', []))} 条")
            
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
                pub_date = util.convert_utc_to_local(created_at/1000, tz=timezone(timedelta(hours=8)))
                
                util.info(f"开始访问网页: {link}")
                page.goto(link)

                # 等待文章详情内容加载
                page.wait_for_selector(".article__bd__detail", timeout=10000)
                
                # 获取文章详情内容
                try:
                    detail_element = page.query_selector(".article__bd__detail")
                    if detail_element:
                        # 移除不需要的元素，如脚本、样式等
                        # 移除 <p style="display: none;">...</p>
                        page.evaluate("""() => {
                            // 移除脚本和样式元素
                            const adElements = document.querySelectorAll('.article__bd__detail script, .article__bd__detail style');
                            for (const element of adElements) {
                                element.remove();
                            }
                            
                            // 移除隐藏的段落元素 <p style="display: none;">
                            const hiddenParagraphs = document.querySelectorAll('.article__bd__detail p[style*="display: none"]');
                            for (const element of hiddenParagraphs) {
                                element.remove();
                            }
                        }""")
                        
                        # 获取清理后的HTML内容
                        description = detail_element.inner_html().strip()
                    else:
                        util.error("未找到文章详情内容")
                        description = ""
                except Exception as e:
                    util.error(f"获取文章详情时出错: {str(e)}")
                    description = ""

                if description != "":
                    # 添加到文章列表
                    insert = True
                    _articles.insert(
                        0,
                        {
                            "id": id,
                            "user_id": user_id,
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
            util.error(f"执行脚本时出错: {str(e)}")
            
# 使用 SpiderUtil 的 execute_with_timeout 方法执行 run 函数
util.execute_with_timeout(run, timeout=120)