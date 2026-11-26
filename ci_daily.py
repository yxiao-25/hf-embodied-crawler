# -*- coding: utf-8 -*-
"""
ci_daily.py —— GitHub Actions 每天自动执行的入口

用途：
    在 GitHub Actions里每天跑一次
      1. 把当天 Trending 榜单写进 SQLite 的 trending_daily 表
         （复用 crawler_trending.crawl_trending，含「只留最近 7 天」裁剪）；
      2. 从 SQLite 导出 docs/data/trending.json
      3. 由 workflow 把 data/hf.db + docs/data/trending.json 一起 commit + push
         GitHub Pages 自动更新。


"""

import db
import crawler_trending
import export_json


def main():
    db.init_db()                           # 确保 4 张表存在
    crawler_trending.crawl_trending()      # 抓当天 trending 写 SQLite（追加 + 裁剪到最近 7 天）
    export_json.export_files(["trending"])  # SQLite → docs/data/trending.json


if __name__ == "__main__":
    main()
