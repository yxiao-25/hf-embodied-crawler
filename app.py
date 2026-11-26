# -*- coding: utf-8 -*-
"""
app.py —— Flask 网页后端

用法：
    python app.py
    然后浏览器打开 http://127.0.0.1:5000

职责：
    1. 提供首页 /（渲染 templates/index.html）
    2. 提供几个 JSON 数据接口，前端(index.html)用 fetch 拉取后交给 ECharts 渲染：
       - /api/trending      任务1：按天分组的 Trending 榜单
       - /api/influencers   任务2：Top10 大V（全平台粉丝/关注数）
       - /api/network       任务2：关注网络边
       - /api/projects      任务3：热门具身智能项目
"""

import json

from flask import Flask, render_template, jsonify

import config
import db
import analysis

app = Flask(__name__)


@app.route("/")
def index():
    """首页：渲染模板。"""
    return render_template("index.html")


@app.route("/api/trending")
def api_trending():
    """任务1：返回按日期分组的 Trending 数据。"""
    rows = db.query_all("SELECT * FROM trending_daily ORDER BY crawl_date, rank")
    by_date = {}
    for r in rows:
        by_date.setdefault(r["crawl_date"], []).append(r)
    return jsonify({"dates": sorted(by_date.keys()), "data": by_date})


@app.route("/api/influencers")
def api_influencers():
    """任务2：返回 Top10 大V（含全平台粉丝数/关注数）。"""
    return jsonify(analysis.influencer_stats())


@app.route("/api/network")
def api_network():
    """任务2：返回关注网络边（画网络图用）。"""
    return jsonify(analysis.network_edges())


@app.route("/api/projects")
def api_projects():
    """任务3：返回热门具身智能项目，tags 从 JSON 字符串还原成列表。"""
    rows = db.query_all("SELECT * FROM projects ORDER BY likes DESC")
    for r in rows:
        try:
            r["tags"] = json.loads(r["tags"]) if r["tags"] else []
        except (TypeError, json.JSONDecodeError):
            r["tags"] = []
    return jsonify(rows)


if __name__ == "__main__":
    db.init_db()                      # 启动前确保表存在
    app.run(host="127.0.0.1", port=5000, debug=False)
