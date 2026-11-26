# -*- coding: utf-8 -*-
"""
ci_weekly.py —— GitHub Actions 每周自动执行的入口

用途：
    每周（周一）在 GitHub Actions里跑一次
      1. 任务2
      2. 任务3
      3. 从 SQLite 导出 influencers.json / network.json / projects.json
      4. 由 workflow 把 data/hf.db + 这三个 JSON 一起 commit + push，GitHub Pages 自动更新。

"""

import db
import crawler_influencers
import crawler_projects
import export_json


def main():
    db.init_db()                                  # 确保 4 张表存在
    crawler_influencers.main()                    # 任务2：写 influencers + follow_edges（清空重写）
    crawler_projects.main()                       # 任务3：写 projects（清空重写）
    export_json.export_files(
        ["influencers", "network", "projects"])   # SQLite → 三个 JSON


if __name__ == "__main__":
    main()
