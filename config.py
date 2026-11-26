# -*- coding: utf-8 -*-
"""
config.py —— 全局配置
所有「可能想改的数字/地址」都集中在这里
"""

import os
import sys

# Windows 控制台默认 GBK 编码，会导致中文输出乱码；统一改成 UTF-8
# line_buffering=True 让 print 每次换行就立即输出，跑长任务时能实时看到进度。
# 所有脚本都会 import config，所以会自动生效，无需每个脚本重复设置。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

BASE_URL = "https://huggingface.co"

# 数据库文件路径
# 用脚本所在目录的「绝对路径」（而不是相对当前工作目录），
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "hf.db")

# 任务1：每天抓取的 Trending 榜单条数
# 注意：/api/trending 的 limit 上限是 20
TRENDING_LIMIT = 20

# 任务2：具身智能领域大V数量
TOP_INFLUENCERS = 10

# 任务2：每个大V最多抓多少个「粉丝名单」用于画网络图
MAX_FOLLOWERS_PER_USER = 500

# 任务3：最终要输出的热门项目数量
TOP_PROJECTS = 10

# —— 具身智能识别
# 试验版关键词（2026-11-22 实测 HF 官方分类 /api/models-tags-by-type + 100 个 robotics 模型 tags）：
#   pipeline_tag 是官方「任务分类」，与具身智能相关的只有 robotics 和 reinforcement-learning；
#   细分词（VLA/manipulation/humanoid 等）在模型的自由 tags 里。TODO：先跑通，效果不好再增删。

# 任务分类 pipeline_tag：收集候选时用 filter= 逐个拉
EMBODIED_PIPELINE_TAGS = ["robotics", "reinforcement-learning"]

# 自由标签关键词：判断一个模型是否「具身智能」
EMBODIED_TAG_KEYWORDS = [
    "vla", "vision-language-action", "vision-language-action-model",
    "embodied", "embodied-ai", "embodied-navigation",
    "manipulation", "robotic-manipulation", "mobile-manipulation",
    "grasping", "bimanual", "teleoperation",
    "robot-learning", "imitation-learning", "lerobot", "diffusion-policy",
    "humanoid", "locomotion", "legged", "quadruped",
    "motion-generation", "whole-body-control",
    "navigation", "vision-language-navigation",
    "world-model", "world-models", "world-action-model",
    "robot", "robotics",
]


def is_embodied(model):
    """判断一个模型是否属于具身智能领域
    pipeline_tag 含 robot（即 robotics）直接算；否则看 tags 是否命中 EMBODIED_TAG_KEYWORDS
    reinforcement-learning 等通用 RL 模型只有同时带具身 tags 才算"""
    pipeline = (model.get("pipeline_tag") or "").lower()
    tags = " ".join(model.get("tags") or []).lower()
    if "robot" in pipeline:
        return True
    return any(kw in tags for kw in EMBODIED_TAG_KEYWORDS)

# —— 请求频率控制（防止请求过快被官方站限流/封禁）——
REQUEST_DELAY = 1.5   # 最小间隔
MAX_RETRIES = 5       # 单次请求失败后的最大重试次数
TIMEOUT = 20          # 单次请求超时时间
