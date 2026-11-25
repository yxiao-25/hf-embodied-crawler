# -*- coding: utf-8 -*-
"""
crawler_trending.py —— 任务1：抓取「当日」Trending 榜单并存库

用法：
    python crawler_trending.py

原理：
    HuggingFace 不提供「历史按天」的 Trending 数据，只返回当前榜单。
    所以采用「每日快照」：每天运行一次，把当天的榜单存进 trending_daily 表（用 crawl_date 区分）。
    连续运行 7 天，就自然得到「一周 trending、按天展示」的完整数据。

调用流：
    main -> db.init_db() 建表 -> crawl_trending() -> HFClient().get_json('/api/trending')
         -> 解析 recentlyTrending -> 拼成 rows -> db.insert_many() 存库
"""

import datetime

import config
import db
from hf_client import HFClient


def fetch_trending():
    """抓取当天 Trending 榜单，返回 list[dict]（不含 crawl_date，由调用方补充）。
    供本文件的 crawl_trending（写 SQLite）调用；crawl_trending 再被 run_daily.py 和 ci_daily.py 复用。"""
    client = HFClient()

    print(f"正在抓取 Trending（limit={config.TRENDING_LIMIT}）...")
    # type=model 表示只看模型；limit 控制条数
    data = client.get_json("/api/trending", params={"type": "model", "limit": config.TRENDING_LIMIT})

    # 接口返回结构：{'recentlyTrending': [{'repoType':..., 'repoData': {...}}, ...]}
    items = data.get("recentlyTrending", [])
    rows = []
    for rank, item in enumerate(items, start=1):
        repo = item.get("repoData", {})
        author_data = repo.get("authorData") or {}  # 作者信息里带 followerCount
        rows.append({
            "rank": rank,
            "model_id": repo.get("id"),
            "author": repo.get("author"),
            "author_followers": author_data.get("followerCount"),
            "downloads": repo.get("downloads"),
            "likes": repo.get("likes"),
            "pipeline_tag": repo.get("pipeline_tag"),
        })
    return rows


def crawl_trending():
    rows = fetch_trending()
    if not rows:
        print("未拿到数据，请检查网络或接口返回。")
        return

    today = datetime.date.today().isoformat()  # 形如 '2026-11-21'
    for r in rows:
        r["crawl_date"] = today

    # 同一天重复运行：先删掉今天的旧数据，保证每天只保留一份最新快照
    conn = db.get_conn()
    conn.execute("DELETE FROM trending_daily WHERE crawl_date = ?", (today,))
    conn.commit()
    conn.close()

    # replace=False 表示「追加」而不是覆盖（每天的数据靠 crawl_date 区分）
    db.insert_many("trending_daily", rows, replace=False)

    # 题目只要「一周」：只保留最近 7 个不同日期的快照，更早的删掉
    prune_to_recent_days(7)

    print(f"完成：已保存 {len(rows)} 条当日 Trending 数据（日期 {today}）。")


def prune_to_recent_days(n=7):
    """只保留 trending_daily 里最近 n 个不同日期的快照，更早的删掉。"""
    conn = db.get_conn()
    keep = [r[0] for r in conn.execute(
        "SELECT DISTINCT crawl_date FROM trending_daily ORDER BY crawl_date DESC LIMIT ?", (n,))]
    if keep:
        placeholders = ",".join("?" * len(keep))
        conn.execute(
            f"DELETE FROM trending_daily WHERE crawl_date NOT IN ({placeholders})", keep)
        conn.commit()
    conn.close()


if __name__ == "__main__":
    db.init_db()      # 先确保 4 张表都存在
    crawl_trending()
