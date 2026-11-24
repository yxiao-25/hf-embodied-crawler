# -*- coding: utf-8 -*-
"""
analysis.py —— 分析层：计算题目要求的「入度最多 / 出度最多 / 入度+出度最多」。

概念解释（这里的度数是在「具身智能作者关注网络」上算的，不是全网粉丝数）：
    - 入度(in-degree)   = 圈内有多少个作者关注了你（follow_edges 里 to_user 出现的次数）
    - 出度(out-degree)  = 你关注了多少个圈内作者（from_user 出现的次数）
    - 入度+出度         = 两者之和，衡量在圈内的连接程度

只读数据库，不发起网络请求，网页(app.py)会调用这里的函数。
"""

from collections import defaultdict

import config
import db


def degree_stats():
    """
    返回：
    {
        "top_influencers":  [...],   # Top10 大V（按全网粉丝数 follower_count 降序）
        "in_degree_top":    [...],   # 圈内入度最多
        "out_degree_top":   [...],   # 圈内出度最多
        "total_degree_top": [...],   # 圈内入度+出度最多
    }
    每个元素含 username/fullname/type/follower_count/in_degree/out_degree/total_degree。
    """
    influencers = db.query_all("SELECT * FROM influencers ORDER BY follower_count DESC")
    meta = {r["username"]: r for r in influencers}

    edges = db.query_all("SELECT from_user, to_user FROM follow_edges")
    in_deg = defaultdict(int)
    out_deg = defaultdict(int)
    for e in edges:
        out_deg[e["from_user"]] += 1
        in_deg[e["to_user"]] += 1

    # 节点 = 边里出现的人 ∪ 所有候选作者（保证粉丝多但没人关注的账号也能上榜）
    nodes = set(in_deg) | set(out_deg) | set(meta)
    rows = []
    for n in nodes:
        m = meta.get(n, {})
        rows.append({
            "username": n,
            "fullname": m.get("fullname"),
            "type": m.get("type"),
            "follower_count": m.get("follower_count"),
            "in_degree": in_deg[n],
            "out_degree": out_deg[n],
            "total_degree": in_deg[n] + out_deg[n],
        })

    return {
        "top_influencers": influencers[: config.TOP_INFLUENCERS],
        "in_degree_top": sorted(rows, key=lambda x: -x["in_degree"])[:10],
        "out_degree_top": sorted(rows, key=lambda x: -x["out_degree"])[:10],
        "total_degree_top": sorted(rows, key=lambda x: -x["total_degree"])[:10],
    }


def network_edges():
    """返回所有关注边（供网页画网络图），list[{from_user, to_user, edge_type}]。"""
    return db.query_all("SELECT from_user, to_user, edge_type FROM follow_edges")
