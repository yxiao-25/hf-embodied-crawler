# -*- coding: utf-8 -*-
"""
crawler_projects.py —— 任务3：最火热的 10 个具身智能项目 + GitHub/Space 链接

用法：
    python crawler_projects.py

核心逻辑（调用流）：
    1. search_candidates   用关键词搜模型，收集候选去重
    2. is_embodied         用 pipeline_tag / tags 关键词判断是否「具身智能」
    3. 按点赞数(likes)排序，取 Top10
    4. 逐个项目：
       - 取模型详情（tags、标题、spaces）
       - 读 README 提取 GitHub 仓库链接（过滤图片附件）
       - 确定 HF Space 链接（作者本人名下的 Space，或从 README 提取，否则留空）
    5. 存入 projects 表

识别「具身智能」用官方标签（pipeline_tag=robotics 或 tags 里的关键词），
这比 LLM 更权威、稳定，且无需任何 API key。想升级成 LLM 精筛可以后续再加。
"""

import re
import json

import config
import db
from hf_client import HFClient


# 具身智能判断 + 关键词：统一定义在 config.py（config.is_embodied /
# config.EMBODIED_PIPELINE_TAGS / config.EMBODIED_TAG_KEYWORDS），
# 任务2/任务3 共用同一份，这里不再重复定义。


def search_candidates(client):
    """对每个具身智能 pipeline_tag 用 filter 列模型，is_embodied 过滤后去重，返回 list[model]。"""
    models = {}
    for tag in config.EMBODIED_PIPELINE_TAGS:
        try:
            data = client.get_json("/api/models", params={
                "filter": tag,
                "sort": "likes",
                "direction": "-1",
                "limit": 100,
            })
            for m in data:
                if config.is_embodied(m):
                    models[m["id"]] = m
        except Exception as exc:
            print(f"    filter={tag} 收集失败：{exc}")
    return list(models.values())


def extract_github_urls(readme):
    """
    从 README 文本里提取 GitHub 仓库链接。
    会过滤掉 user-attachments 等图片附件，保留源码仓库地址，并去重保序。
    """
    urls = []
    for m in re.finditer(r"https?://(?:www\.)?github\.com/([^/\s\"'<>)\]]+/[^/\s\"'<>)\]]+)", readme):
        url = m.group(0).rstrip(".,;:!?)")
        if "user-attachments" in url or "/assets/" in url:
            continue
        url = re.sub(r"\.git$", "", url).rstrip("/")
        urls.append(url)
    seen, result = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


def _is_meaningless_space(space_id):
    """过滤掉「排行榜/基准/测量」这类非演示 Space。"""
    s = (space_id or "").lower()
    return any(k in s for k in ("leaderboard", "benchmark", "measurement", "evaluat", "metric"))


def find_space_url(detail, author, readme=""):
    """
    确定 HF Space 链接（优先官方演示，其次社区演示）：
    1) 作者本人名下的 Space（最可能是官方 demo）；
    2) README 里 huggingface.co/spaces/... 链接；
    3) 都没有就退回「使用此模型的 Space」里第一个非排行榜类社区演示；
    4) 实在没有才返回 None。
    """
    spaces = []
    for s in (detail.get("spaces") or []):
        sid = s.get("id") if isinstance(s, dict) else str(s)
        if sid:
            spaces.append(sid)

    # 1) 作者本人名下的 Space
    for sid in spaces:
        if sid.split("/")[0] == author:
            return f"https://huggingface.co/spaces/{sid}"
    # 2) README 里的 Space 链接
    links = re.findall(r"https?://[a-zA-Z0-9.-]*huggingface\.co/spaces/([^\s)\"'<>]+)", readme)
    if links:
        return f"https://huggingface.co/spaces/{links[0].rstrip('.,;:!?')}"
    # 3) 社区演示（过滤排行榜/基准类，优先名字含模型「主干名」的）
    short = (detail.get("id") or "").split("/")[-1].lower()
    stem = re.split(r"[-_.]", short)[0]  # 如 alpamayo-r1-10b -> alpamayo，去掉版本/尺寸后缀
    candidates = [s for s in spaces if not _is_meaningless_space(s)]
    for s in candidates:
        if stem and stem in s.lower():
            return f"https://huggingface.co/spaces/{s}"
    if candidates:
        return f"https://huggingface.co/spaces/{candidates[0]}"
    return None


def extract_description(readme, max_len=200):
    """从 README 里取第一段有意义的文字作为项目简介。"""
    lines = []
    for line in readme.splitlines():
        line = line.strip()
        if not line or line.startswith(("---", "#", "<", "![", "```")):
            continue
        line = re.sub(r"[#*>`]", "", line).strip()
        if line:
            lines.append(line)
        if sum(len(x) for x in lines) > max_len:
            break
    return " ".join(lines)[:max_len]


def main():
    db.init_db()
    client = HFClient()

    print("【1/3】搜索候选模型 ...")
    candidates = search_candidates(client)
    print(f"    候选模型 {len(candidates)} 个")

    print("【2/3】筛选具身智能项目 ...")
    embodied = [m for m in candidates if config.is_embodied(m)]
    # 按点赞数排序，最火热的排前面
    embodied.sort(key=lambda m: -(m.get("likes") or 0))
    top = embodied[: config.TOP_PROJECTS]
    print(f"    识别出 {len(embodied)} 个具身智能项目，取 Top{len(top)}")

    print("【3/3】提取 GitHub / Space 链接 ...")
    rows = []
    for i, m in enumerate(top, 1):
        mid = m["id"]
        author = mid.split("/")[0]
        try:
            detail = client.get_json(f"/api/models/{mid}")
        except Exception as exc:
            print(f"    {mid} 详情获取失败：{exc}")
            detail = {}

        github_url = None
        space_url = None
        description = None
        readme = ""
        try:
            readme = client.get_text(f"/{mid}/raw/main/README.md")
            gh_urls = extract_github_urls(readme)
            github_url = gh_urls[0] if gh_urls else None
            description = extract_description(readme)
        except Exception:
            pass
        space_url = find_space_url(detail, author, readme)

        title = (detail.get("cardData") or {}).get("pretty_name") or mid
        keywords_matched = ",".join(
            kw for kw in config.EMBODIED_TAG_KEYWORDS
            if kw in " ".join(m.get("tags") or []).lower() or kw in (m.get("pipeline_tag") or "").lower()
        )

        rows.append({
            "model_id": mid,
            "title": title,
            "description": description,
            "tags": json.dumps(m.get("tags") or [], ensure_ascii=False),
            "downloads": m.get("downloads"),
            "likes": m.get("likes"),
            "github_url": github_url,
            "space_url": space_url,
            "keywords_matched": keywords_matched,
        })
        print(f"    #{i:2d} {mid:<40} 赞={m.get('likes')} GitHub={github_url} Space={space_url}")

    db.insert_many("projects", rows, replace=True)
    print(f"完成：已保存 {len(rows)} 个具身智能项目。")


if __name__ == "__main__":
    main()
