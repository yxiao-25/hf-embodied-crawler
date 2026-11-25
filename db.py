# -*- coding: utf-8 -*-
"""
db.py —— SQLite 数据库层
负责：建表 + 通用的「批量插入 / 查询」函数。
数据库文件存在 data/hf.db，单文件、零配置，符合题目「整理到 sqlite 数据库」的要求。
"""

import os
import sqlite3

import config


def get_conn():
    """建立并返回数据库连接（目录不存在会自动创建）。"""
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row  # 让查询结果既能下标访问，也能按列名访问
    return conn


def init_db():
    """建表（表不存在才创建，重复执行安全）。"""
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        -- 任务1：每日 Trending 快照（每天追加一批，靠 crawl_date 区分是哪天）
        CREATE TABLE IF NOT EXISTS trending_daily (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_date       TEXT,      -- 采集日期，如 2026-11-21
            rank             INTEGER,   -- 当日排名（1 开始）
            model_id         TEXT,      -- 模型ID，如 tencent/Hy-Embodied-0.5-VLA-RoboTwin
            author           TEXT,      -- 作者
            author_followers INTEGER,   -- 作者粉丝数
            downloads        INTEGER,
            likes            INTEGER,
            pipeline_tag     TEXT       -- 模型类型，如 robotics / text-generation
        );

        -- 任务2：具身智能 Top10 大V（个人账号，按 follower_count 排序取）
        CREATE TABLE IF NOT EXISTS influencers (
            username        TEXT PRIMARY KEY,
            fullname        TEXT,
            type            TEXT,       -- 账号类型（'user' 个人 / 'org' 组织）
            follower_count  INTEGER,    -- 全网粉丝总数（从主页 HTML 里取的）
            following_count INTEGER     -- 全网关注总数
        );

        -- 任务2：关注边（有向）：from_user 关注了 to_user
        CREATE TABLE IF NOT EXISTS follow_edges (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user TEXT,
            to_user   TEXT,
            edge_type TEXT               -- 'follower'（谁关注了大V）或 'following'（大V关注了谁）
        );

        -- 任务3：热门具身智能项目
        CREATE TABLE IF NOT EXISTS projects (
            model_id          TEXT PRIMARY KEY,
            title             TEXT,
            description       TEXT,
            tags              TEXT,       -- 模型的 tags，存成 JSON 字符串
            downloads         INTEGER,
            likes             INTEGER,
            github_url        TEXT,       -- 提取到的开源 GitHub 链接
            space_url         TEXT,       -- 关联的 HuggingFace Space 链接
            keywords_matched  TEXT        -- 命中了哪些关键词（逗号分隔）
        );
        """
    )

    # 兼容旧库：早期 influencers 表没有 type 列，这里补上（重复执行安全）
    cols = [r[1] for r in cur.execute("PRAGMA table_info(influencers)")]
    if "type" not in cols:
        cur.execute("ALTER TABLE influencers ADD COLUMN type TEXT")

    conn.commit()
    conn.close()


def insert_many(table, rows, replace=True):
    """
    批量插入 rows（list[dict]）到指定表。
    replace=True 时用 INSERT OR REPLACE（主键冲突则覆盖），
    对 trending_daily 这种「每天都要追加」的表要传 replace=False。
    """
    if not rows:
        return
    conn = get_conn()
    cur = conn.cursor()
    cols = list(rows[0].keys())
    placeholders = ",".join(["?"] * len(cols))
    verb = "INSERT OR REPLACE" if replace else "INSERT"
    sql = f"{verb} INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
    cur.executemany(sql, [tuple(r.get(c) for c in cols) for r in rows])
    conn.commit()
    conn.close()


def query_all(sql, params=()):
    """执行 SELECT，返回 list[dict]。"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
