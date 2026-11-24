# -*- coding: utf-8 -*-
"""
run_daily.py —— 每日自动采集入口

用途：
    配合 Windows「任务计划程序」每天定时运行一次，抓取当天的 Trending 榜单。
    连续运行 7 天，就得到「一周 trending、按天展示」的完整数据。

配置 Windows 定时任务的方法（已在本机配好，任务名 HF-Trending-Daily）：
    在任务计划程序里新建任务，触发器设为「每天」，操作设为：
        程序：C:/Users/lx/miniconda3/python.exe
        参数：C:/Users/lx/Desktop/HF爬取与展示方案/run_daily.py

注意：
    - 抓的是官方站 huggingface.co，跑之前必须开着翻墙代理（127.0.0.1:7897）。
    - 本脚本会把 stdout/stderr 重定向到 data/daily_log.txt，方便事后确认是否成功。
"""

import os
import sys
import datetime

import config
import db
import crawler_trending

LOG_PATH = os.path.join(os.path.dirname(config.DB_PATH), "daily_log.txt")


def _setup_log():
    """定时任务运行时通常没有控制台窗口，sys.stdout 可能是空/无输出。
    这里把 stdout/stderr 重定向到日志文件，保证 print 和报错都能留下记录。"""
    try:
        f = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
        sys.stdout = f
        sys.stderr = f
    except Exception:
        pass  # 打不开日志文件就算了，不影响采集本身


if __name__ == "__main__":
    _setup_log()
    print("=" * 60)
    print(f"定时任务启动：{datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    try:
        db.init_db()
        crawler_trending.crawl_trending()
        print("完成：当日 Trending 已入库")
    except Exception as exc:
        print(f"失败：{type(exc).__name__}: {exc}")
