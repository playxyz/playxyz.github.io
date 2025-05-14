from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import threading
import time
import traceback
from contextlib import contextmanager
import random
from typing import Dict, Optional
import random
import time


class SpiderUtil:
    def __init__(self, notify=True):
        # 打印调用栈信息
        stack = traceback.extract_stack()
        # 获取倒数第二个调用（即调用 SpiderUtil() 的地方）
        filename = os.path.basename(stack[-2].filename)
        # 获取文件名，不要后缀
        self.current_file = filename.split(".")[0]
        self.path = "./news/scripts/util/urls.json"
        # 添加 notify 属性
        self.notify = notify

    # 打印日志
    def info(self, message):
        print(f"[\033[32m{self.current_file}\033[0m] {message}")

    def error(self, message):
        print(f"[\033[31m{self.current_file}\033[0m] {message}")

    def get_storage_state(self, name):
        """
        获取指定名称的浏览器上下文

        参数:
        name (str): 浏览器上下文的名称
        """
        from_env = os.getenv("from_env")
        if from_env and (name == "xueqiu_cookie" or name == "seekingalpha_cookie"):
            self.info("使用环境变量中的 cookie")
            return json.loads(os.getenv(name))
        else:
            self.info("使用默认的 cookie 文件")
            storage_state_path = f"./news/auth/{name}.json"
            # 检查 storage_state_path 是否存在，不存在则创建空的 cookie 文件
            if not os.path.exists(storage_state_path):
                self.info(
                    f"Cookie 文件不存在，创建新的 cookie 文件: {storage_state_path}"
                )
                # 确保目录存在
                os.makedirs(os.path.dirname(storage_state_path), exist_ok=True)
                # 创建空的 cookie 文件
                with open(storage_state_path, "w") as f:
                    f.write('{"cookies": [], "origins": []}')
            return storage_state_path

    def history_posts(self, filepath):
        """
        从指定文件中读取历史文章数据，并返回文章列表和链接列表。

        参数:
        filepath (str): 包含历史文章数据的文件路径。

        返回:
        dict: 包含文章列表和链接列表的字典。
        """
        try:
            with open(filepath) as user_file:
                articles = json.load(user_file)["data"]
                links = []
                for article in articles:
                    links.append(article["link"])
                return {"articles": articles, "links": links}
        except:
            return {"articles": [], "links": []}

    def parse_time(self, time_str, format):
        """
        将给定的时间字符串解析为本地时间，并返回格式化后的时间字符串。

        参数:
        time_str (str): 要解析的时间字符串。
        format (str): 时间字符串的格式。

        返回:
        str: 格式化后的本地时间字符串。
        """
        timeObj = datetime.strptime(time_str, format)
        local_time = timeObj + timedelta(hours=8)
        return local_time.strftime("%Y-%m-%d %H:%M:%S")

    def has_chinese(self, string):
        """
        检查字符串中是否包含中文字符。

        参数:
        string (str): 要检查的字符串。

        返回:
        bool: 如果字符串中包含中文字符，返回True；否则返回False。
        """
        for ch in string:
            if "\u4e00" <= ch <= "\u9fff":
                return True
        return False

    def current_time(self):
        """
        获取当前的本地时间，时区为UTC+8。

        返回:
        datetime: 当前的本地时间。
        """
        return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))

    def md5(self, string):
        """
        计算给定字符串的MD5哈希值。

        参数:
        string (str): 要计算哈希值的字符串。

        返回:
        str: 字符串的MD5哈希值。
        """
        return hashlib.md5(string.encode()).hexdigest()

    def current_time_string(self):
        """
        获取当前的本地时间字符串，格式为"YYYY-MM-DD HH:MM:SS"。

        返回:
        str: 当前的本地时间字符串。
        """
        return self.current_time().strftime("%Y-%m-%d %H:%M:%S")

    def convert_utc_to_local(self, timestamp, tz=timezone.utc):
        """
        将传入的时间戳转换为本地时间（UTC+8），并返回格式化后的时间字符串。

        参数:
        timestamp (int/str): 要转换的时间戳，可以是整数或字符串。

        返回:
        str: 格式化后的本地时间字符串，格式为"YYYY-MM-DD HH:MM:SS"。
        """
        if isinstance(timestamp, str):
            timestamp = float(timestamp)
        utc_time = datetime.fromtimestamp(timestamp, tz)
        local_time = utc_time.astimezone(timezone(timedelta(hours=8)))
        return local_time.strftime("%Y-%m-%d %H:%M:%S")

    def append_to_temp_file(self, file_path, data):
        try:
            # 检查文件是否存在，如果不存在则创建一个空文件
            if not os.path.exists(file_path):
                with open(file_path, "w") as file:
                    pass
            # 以追加模式打开文件并写入数据
            with open(file_path, "a") as file:
                file.write(data)
        except Exception as e:
            # 捕获异常并打印错误信息
            print(f"写入临时文件过程中发生错误: {str(e)}")

    def log_action_error(self, error_message, notify=None):
        # 打印错误信息
        print(error_message)
        # 将错误信息追加到临时文件中
        # 如果传入了 notify 参数，使用传入的值，否则使用类的 notify 属性
        should_notify = self.notify if notify is None else notify
        if should_notify:
            # 定义临时文件路径
            temp_file_path = "./tmp/action_errors.log"
            # 如果错误信息长度超过100，截取前100个字符并换行
            if len(error_message) > 100:
                error_message = error_message[:100] + "\n"
            self.append_to_temp_file(temp_file_path, error_message + "\n")
        return

    def get_crawler_headless(self):
        """
        获取 crawler_headless 环境变量的值，如果未设置则返回 False

        返回:
        bool: crawler_headless 环境变量的值
        """
        return not self.get_env_variable("CRAWLER_HEADLESS", False)

    def get_env_variable(self, key, fallback):
        """
        获取环境变量的值，如果不存在则返回默认值

        参数:
        key (str): 环境变量的键
        fallback (str): 如果环境变量不存在时返回的默认值

        返回:
        str: 环境变量的值或默认值
        """
        return os.getenv(key, fallback)

    def execute_with_timeout(self, func, *args, timeout=50, notify=None, **kwargs):
        """
        接受一个函数，执行这个函数并设置超时时间，同时统计函数的执行时间

        参数:
        func (callable): 要执行的函数
        *args: 传递给函数的位置参数
        timeout (int): 超时时间，单位为秒
        notify (bool): 是否发送通知，默认使用类的 notify 属性
        **kwargs: 传递给函数的关键字参数

        返回:
        tuple: (执行结果, 执行时间) 如果在超时时间内完成
        None: 如果函数执行超时
        """

        # 打印调用栈信息
        stack = traceback.extract_stack()
        # 获取倒数第二个调用（即调用execute_with_timeout的地方）
        filename = os.path.basename(stack[-2].filename)
        lineno = stack[-2].lineno

        class FuncThread(threading.Thread):
            def __init__(self, func, *args, **kwargs):
                threading.Thread.__init__(self)
                self.func = func
                self.args = args
                self.kwargs = kwargs
                self.result = None
                self.execution_time = None

            def run(self):
                start_time = time.time()
                try:
                    self.func(*self.args, **self.kwargs)
                except Exception as e:
                    traceback.print_exc()
                    # 使用外部的log_action_error方法，传递 notify 参数
                    should_notify = self._outer.notify if notify is None else notify
                    self._log_action_error(
                        f"{filename}#{lineno} error: {repr(e)}\n", should_notify
                    )
                finally:
                    end_time = time.time()
                    self.execution_time = end_time - start_time

            def _log_action_error(self, error_message, notify=True):
                # 调用外部类的log_action_error方法
                self._outer.log_action_error(error_message, notify)

        # 将外部类的实例传递给线程类
        thread = FuncThread(func, *args, **kwargs)
        thread._outer = self
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            return None
        if thread.execution_time > 2:
            print(
                f"Function #{filename}#{lineno} executed in {thread.execution_time:.3f} seconds."
            )
        return None

    def write_json_to_file(self, data, filename):
        """
        将 JSON 数据以格式化的形式写入传入的文件，并同时写入 SQLite 数据库

        参数:
        data (dict): 要写入文件的 JSON 数据
        filename (str): 文件名

        返回:
        None
        """
        try:
            # 确保目标文件夹存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            # 写入 JSON 文件
            with open(filename, "w", encoding="utf-8") as f:
                json.dump({"data": data}, f, ensure_ascii=False, indent=4)
                print(f"JSON data has been written to {filename} successfully.")

            # # 写入数据库
            # with self._get_db_connection() as conn:
            #     cursor = conn.cursor()
            #     self._insert_articles(cursor, data)
            #     conn.commit()
            #     print(f"{filename} inserted to db successfully.")

        except Exception as e:
            print(f"Error writing data: {e}")
            # 记录详细错误日志，使用类的 notify 属性
            self.log_action_error(f"Error in write_json_to_file: {str(e)}", self.notify)

    def click_human_verification(self, page, max_wait_time=15000):
        """
        检查页面是否存在"确认您是真人"的复选框，如果存在则点击它

        参数:
        page (Page): Playwright Page 实例
        max_wait_time (int): 最大等待时间（毫秒），默认为10000毫秒

        返回:
        bool: 如果找到并点击了复选框返回True，否则返回False
        """
        try:
            # 使用XPath查找包含特定文本的标签
            xpath = "//span[contains(@class, 'cb-lb-t') and (contains(text(), '确认您是真人') or contains(text(), 'Verify you are human'))]"
            
            # 等待元素出现
            label_element = page.wait_for_selector(xpath, timeout=max_wait_time)
            
            if label_element:
                # 找到了验证复选框，等待随机时间（1秒内）
                random_wait = random.uniform(0.3, 1.0)
                time.sleep(random_wait)
                
                # 找到复选框并点击
                checkbox = label_element.query_selector(".cb-lb-t input")
                if checkbox:
                    checkbox.click()
                else:
                    # 如果找不到复选框，尝试点击标签元素
                    label_element.click()
                
                # 点击后等待1秒
                time.sleep(1)
                
                print("已点击'确认您是真人'复选框")
                return True
                
        except Exception as e:
            # 没有找到验证复选框或发生其他错误
            print(f"没有找到人机验证复选框或点击失败: {str(e)}")
            return False
            
        return False

    def get_page(self, context):
        """
        从浏览器上下文创建新页面并进行基本配置

        参数:
        context (BrowserContext): Playwright 浏览器上下文
        url (str): 可选，如果提供则导航到该URL
        js_disable_webdriver (bool): 是否禁用 webdriver 检测，默认为 True
        timeout (int): 导航超时时间（毫秒），默认为 10000

        返回:
        Page: 配置好的 Playwright Page 实例
        """
        try:
            # 创建一个新的页面（相当于浏览器中的一个新标签页）
            # 在Playwright中，context代表一个浏览器会话，而page代表会话中的一个标签页
            # 每次调用new_page()都会在同一个浏览器会话中创建一个新的标签页
            page = context.new_page()
            
            # 禁用 webdriver 检测
            js = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            page.add_init_script(js)
            
            return page
        except Exception as e:
            self.error(f"创建页面时出错: {str(e)}")
            raise

    def contains_language(self, text, languages=None):
        """
        判断文本是否包含指定的语言字符。

        参数:
        text (str): 要检查的文本
        languages (list): 要检查的语言列表，支持以下值：
            'japanese' - 日语
            'korean' - 韩语
            'french' - 法语
            'spanish' - 西班牙语
            默认为 ['japanese']

        返回:
        bool: 如果文本包含指定语言的字符，返回True；否则返回False
        """
        if not text:
            return False

        # 默认检查中文和英文
        if languages is None:
            languages = ["japanese"]

        for ch in text:
            # 检查日语
            if "japanese" in languages and (
                "\u3040" <= ch <= "\u309f"  # 平假名
                or "\u30a0" <= ch <= "\u30ff"  # 片假名
                or "\u4e00" <= ch <= "\u9fff"  # 汉字
            ):
                return True
            # 检查韩语
            if "korean" in languages and "\uac00" <= ch <= "\ud7a3":
                return True
            # 检查法语/西班牙语（主要检查特殊字符）
            if (
                "french" in languages or "spanish" in languages
            ) and ch in "éèêëàâäôöûüçñ":
                return True

        return False
