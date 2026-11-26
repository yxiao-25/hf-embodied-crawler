# -*- coding: utf-8 -*-
"""
export_json.py —— 把 SQLite 数据库导出成静态 JSON 文件（供 GitHub Pages 网页使用）

背景：
    云端 GitHub Pages 版网页是纯静态的，读不到 SQLite，只能读 JSON 文件。
    所以需要这一步：把数据库里 4 块数据导出成 docs/data/*.json，提交到仓库，
    由 GitHub Pages 直接访问。

    导出结果：
      docs/data/trending.json     任务1 按天 Trending
      docs/data/influencers.json  任务2 Top10 大V（全平台粉丝/关注数）
      docs/data/network.json      任务2 关注网络边
      docs/data/projects.json     任务3 热门项目

用法：
    python export_json.py                       # 导出全部 4 个
    export_json.export_files(["trending"])      # 只导出指定几个（云端每日/每周分别用）
"""

import json
import os

import config
import db
import analysis


def trending_payload():
    """任务1：按天分组的 Trending（dates + data）。"""
    rows = db.query_all("SELECT * FROM trending_daily ORDER BY crawl_date, rank")
    by_date = {}
    for r in rows:
        by_date.setdefault(r["crawl_date"], []).append(r)
    return {"dates": sorted(by_date.keys()), "data": by_date}


def projects_payload():
    """任务3：热门项目（tags 还原成列表）。"""
    rows = db.query_all("SELECT * FROM projects ORDER BY likes DESC")
    for r in rows:
        try:
            r["tags"] = json.loads(r["tags"]) if r["tags"] else []
        except (TypeError, json.JSONDecodeError):
            r["tags"] = []
    return rows


# 文件名 → 生成数据的函数（惰性调用：只算真正要导出的那几个）
PAYLOADS = {
    "trending": ("trending.json", trending_payload),
    "influencers": ("influencers.json", analysis.influencer_stats),
    "network": ("network.json", analysis.network_edges),
    "projects": ("projects.json", projects_payload),
}


def export_files(names):
    """导出指定 JSON 文件。names 是 ['trending','influencers','network','projects'] 的子集。"""
    out_dir = os.path.join(config.BASE_DIR, "docs", "data")
    os.makedirs(out_dir, exist_ok=True)
    for name in names:
        fname, fn = PAYLOADS[name]
        path = os.path.join(out_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fn(), f, ensure_ascii=False, indent=2)
        print(f"  已导出 {fname}")


def export_all():
    """导出全部 4 个 JSON（手动一次性导出用）。"""
    export_files(list(PAYLOADS.keys()))
    print("完成：4 个 JSON 文件已写入 docs/data/")


if __name__ == "__main__":
    db.init_db()
    export_all()
