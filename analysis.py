# -*- coding: utf-8 -*-
"""
analysis.py —— 分析层：给网页提供大V列表和关注网络边。

说明：
    这里只负责返回 Top10 大V 和网络边。

只读数据库，不发起网络请求，export_json.py 会调用这里的函数。
"""

import config
import db


def influencer_stats():
    """
    返回 Top10 大V（含全平台粉丝数/关注数），供网页表格 + 冠军卡片使用。
    结构：{"top_influencers": [{username, fullname, type, follower_count, following_count}, ...]}
    按全平台粉丝数 follower_count 降序。
    """
    influencers = db.query_all("SELECT * FROM influencers ORDER BY follower_count DESC")
    return {"top_influencers": influencers[: config.TOP_INFLUENCERS]}


def network_edges():
    """返回所有关注边（供网页画网络图），list[{from_user, to_user, edge_type}]。"""
    return db.query_all("SELECT from_user, to_user, edge_type FROM follow_edges")
