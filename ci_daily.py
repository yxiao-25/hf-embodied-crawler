# -*- coding: utf-8 -*-
"""
ci_daily.py —— GitHub Actions 每天自动执行的入口

用途：
    在 GitHub Actions（美国服务器，无需翻墙）里每天跑一次：
      1. 抓取当天 HuggingFace Trending 榜单；
      2. 把这一天的数据 upsert 进 docs/data/trending.json（该文件提交在仓库里，是跨天累积的存储）；
      3. 由随后的 workflow 步骤 git commit + push 回仓库，GitHub Pages 自动更新。

    与本地 run_daily.py（写 SQLite）的区别：
      CI 环境没有持久化磁盘，SQLite 每次都会被清空；
      所以这里直接读写 JSON 文件，把「历史天数」都存在 docs/data/trending.json 里（跨天累积）。
"""

import datetime
import json
import os

import config
import crawler_trending

TRENDING_JSON = os.path.join(config.BASE_DIR, "docs", "data", "trending.json")


def main():
    today = datetime.date.today().isoformat()

    print(f"[{today}] 抓取当天 Trending ...")
    rows = crawler_trending.fetch_trending()
    if not rows:
        print("未拿到数据（可能被限流），本次跳过。")
        return
    for r in rows:
        r["crawl_date"] = today

    # 读取已提交的历史数据（里面是之前每天累积的天数）
    payload = {"dates": [], "data": {}}
    if os.path.exists(TRENDING_JSON):
        with open(TRENDING_JSON, encoding="utf-8") as f:
            payload = json.load(f)

    # 覆盖/新增今天这一天的数据（同一天重复跑只会替换，不会累积出重复）
    payload["data"][today] = rows
    payload["dates"] = sorted(payload["data"].keys())

    os.makedirs(os.path.dirname(TRENDING_JSON), exist_ok=True)
    with open(TRENDING_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"已更新 {today}，累计 {len(payload['dates'])} 天：{', '.join(payload['dates'])}")


if __name__ == "__main__":
    main()
