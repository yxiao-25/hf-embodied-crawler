# -*- coding: utf-8 -*-
"""
analysis.py —— 分析层：给网页提供大V列表和关注网络边。

说明：
    「入度/出度/总和」已按用户要求改成「全平台」口径——即大V的全平台粉丝数（被关注）
    和全平台关注数，不再单独统计「圈内入度/出度」。网页上的三个冠军卡片
    （全平台粉丝最多 / 全平台关注最多 / 粉丝+关注最多）由前端从 top_influencers
    直接算出来，因此这里只负责返回 Top10 大V 和网络边。

只读数据库，不发起网络请求，网页(app.py)会调用这里的函数。
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
