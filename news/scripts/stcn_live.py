from datetime import timedelta, timezone
from playwright.sync_api import sync_playwright
from util.spider_util import SpiderUtil

# 获取当前文件名，用于日志标识
util = SpiderUtil()
filename = "./news/data/stcn_live/list.json"

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

            context = browser.new_context()
            page = context.new_page()
           
            # 使用 expect_response 等待 XHR 响应
            with page.expect_response(
                lambda response: "article/list.html?type=kx" in response.url 
                and response.status == 200
                and "application/json" in response.headers.get("content-type", "")
            ) as response_info:
                # 访问目标网页
                util.info("开始访问网页...")
                page.goto("https://www.stcn.com/article/list.html?type=kx", timeout=10000)
                page.wait_for_load_state("networkidle")

            # 获取响应对象
            response = response_info.value
            json_data = response.json()
            util.info(
                f"成功获取 stcn 内容，共 {len(json_data.get('data', []))} 条"
            )

            # 处理获取到的数据
            articles = json_data.get("data", [])
            if len(articles) == 0:
                util.info("没有获取到数据")
                return
            for article in articles[:10]:  # 只处理前10条
                link = "https://www.stcn.com{}".format(article["url"])
                # 检查链接是否已存在
                if link in _links:
                    util.info(f"链接已存在: {link}")
                    continue

                id = article["id"]
                title = article["title"]
                pub_date = util.convert_utc_to_local(
                    article["show_time"], tz=timezone(timedelta(hours=8))
                )
                description = article["content"]
                if description != "":
                    insert = True
                    _articles.insert(
                        0,
                        {
                            "title": title,
                            "id": id,
                            "description": description,
                            "link": link,
                            "pub_date": pub_date,
                            "source": "stcn",
                            "kind": 2,
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
    util.execute_with_timeout(run)
