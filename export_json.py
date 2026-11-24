# -*- coding: utf-8 -*-
"""
export_json.py —— 把 SQLite 数据库导出成静态 JSON 文件（供 GitHub Pages 网页使用）

背景：
    本地 Flask 版网页通过 /api/* 接口实时读 SQLite；
    云端 GitHub Pages 版网页是纯静态的，读不到 SQLite，只能读 JSON 文件。
    所以需要这一步：把数据库里 4 块数据导出成 docs/data/*.json，提交到仓库，
    由 GitHub Pages 直接访问。

    导出结果（与 Flask 各接口返回的 JSON 结构完全一致）：
      docs/data/trending.json     任务1 按天 Trending
      docs/data/influencers.json  任务2 大V + 入度/出度统计
      docs/data/network.json      任务2 关注网络边
      docs/data/projects.json     任务3 热门项目

用法：
    python export_json.py
"""

import json
import os

import config
import db
import analysis


def trending_payload():
    """任务1：与 app.py 的 /api/trending 返回结构一致（dates + data）。"""
    rows = db.query_all("SELECT * FROM trending_daily ORDER BY crawl_date, rank")
    by_date = {}
    for r in rows:
        by_date.setdefault(r["crawl_date"], []).append(r)
    return {"dates": sorted(by_date.keys()), "data": by_date}


def projects_payload():
    """任务3：与 app.py 的 /api/projects 返回结构一致（tags 还原成列表）。"""
    rows = db.query_all("SELECT * FROM projects ORDER BY likes DESC")
    for r in rows:
        try:
            r["tags"] = json.loads(r["tags"]) if r["tags"] else []
        except (TypeError, json.JSONDecodeError):
            r["tags"] = []
    return rows


def export_all():
    out_dir = os.path.join(config.BASE_DIR, "docs", "data")
    os.makedirs(out_dir, exist_ok=True)

    payloads = {
        "trending.json": trending_payload(),
        "influencers.json": analysis.degree_stats(),
        "network.json": analysis.network_edges(),
        "projects.json": projects_payload(),
    }

    for name, data in payloads.items():
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  已导出 {name}")

    print("完成：4 个 JSON 文件已写入 docs/data/")


if __name__ == "__main__":
    db.init_db()
    export_all()
