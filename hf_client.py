# -*- coding: utf-8 -*-
"""
hf_client.py —— HuggingFace 请求层
所有爬虫都通过这个类发 HTTP 请求，而不是各自写 requests 调用。
好处：
  1. 统一了站点地址（BASE_URL 只在 config.py 里改一次）
  2. 自动限速（两次请求间隔 >= REQUEST_DELAY，防止被封）
  3. 自动重试（网络抖动时重试 MAX_RETRIES 次，带退避）
"""

import time
import requests

import config


class HFClient:
    """封装对 HuggingFace 的 GET 请求。"""

    def __init__(self):
        self.base_url = config.BASE_URL
        # Session 会复用底层连接，比每次新建连接更快；统一设置 User-Agent 伪装成浏览器
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; HF-Crawler/1.0)"})
        self._last_request_time = 0.0

    def _rate_limit(self):
        """限速：如果距上次请求还没过 REQUEST_DELAY 秒，就睡到够了再走。"""
        elapsed = time.time() - self._last_request_time
        if elapsed < config.REQUEST_DELAY:
            time.sleep(config.REQUEST_DELAY - elapsed)

    def get(self, path, params=None):
        """
        发一个 GET 请求，返回 Response 对象。
        path: 以 / 开头的路径，如 '/api/trending'，会拼到 BASE_URL 后面。
        params: 查询参数 dict，如 {'type': 'model', 'limit': 50}。
        """
        url = self.base_url + path
        for attempt in range(1, config.MAX_RETRIES + 1):
            self._rate_limit()
            try:
                resp = self.session.get(
                    url,
                    params=params,
                    timeout=config.TIMEOUT,
                    allow_redirects=True,  # followers 接口会 302 重定向到正确大小写，必须跟随
                )
                self._last_request_time = time.time()
                if resp.status_code == 200:
                    return resp
                # 503/502 表示服务端过载，多等一会儿再试；其他错误按次数退避
                wait = 10 if resp.status_code in (503, 502) else attempt * 2
                print(f"    [警告] {path} 返回 HTTP {resp.status_code}（第 {attempt}/{config.MAX_RETRIES} 次，等 {wait}s）")
            except requests.RequestException as exc:
                wait = attempt * 2
                print(f"    [警告] {path} 请求异常：{exc}（第 {attempt}/{config.MAX_RETRIES} 次，等 {wait}s）")
            time.sleep(wait)
        raise RuntimeError(f"请求最终失败：{path}")

    def get_json(self, path, params=None):
        """GET 并把结果解析成 JSON（dict 或 list）。"""
        return self.get(path, params=params).json()

    def get_text(self, path):
        """GET 并返回纯文本，用于读模型的 README.md。"""
        return self.get(path).text
