# -*- coding: utf-8 -*-
"""
crawler_influencers.py —— 任务2 具身智能领域 Top10 大V + 关注网络



核心逻辑（调用流）：
    1. collect_candidates  对每个具身智能 pipeline_tag 用 filter 列模型 is_embodied 过滤噪音，
       收集「作者」去重
    2. fetch_user_meta     访问每个作者主页 HTML 提取 fullname / 粉丝数 / 账号类型
    3. 只保留个人账号，按粉丝数排序 → Top10 大V
    4. 关注网络：对这 10 人分别抓 following+ followers 构成人脉网，
       全部边存进 follow_edges（from_user → to_user 表示「from 关注了 to」）
    5. Top10 大V存进 influencers 表，关注边存进 follow_edges 表

关键点（HuggingFace 官方站，实测）：
    - 粉丝总数：/api/users/{name} 接口 404，但主页 HTML 里内嵌 "followerCount":数字，
      用正则从 HTML 提取。
    - 关注列表：个人账号 /api/users/{name}/following 和 /followers 两个接口，
    - 具身智能关键词统一定义在 config.py（config.EMBODIED_PIPELINE_TAGS /
      config.EMBODIED_TAG_KEYWORDS / config.is_embodied）任务2/任务3 共用。
"""

import re
import html as htmlmod

import config
import db
from hf_client import HFClient


def collect_candidates(client):
    """
    收集候选作者，返回 {用户名: set(该作者的 pipeline_tag)}。
    对 config.EMBODIED_PIPELINE_TAGS 里的每个 pipeline_tag 用 filter 列出模型，
    再用 config.is_embodied 过滤掉非具身智能的噪音（主要是 reinforcement-learning 里的通用 RL）。
    """
    authors = {}
    for tag in config.EMBODIED_PIPELINE_TAGS:
        try:
            data = client.get_json("/api/models", params={
                "filter": tag,
                "sort": "likes",
                "direction": "-1",
                "limit": 100,
            })
        except Exception as exc:
            print(f"    filter={tag} 拉取失败：{exc}")
            continue
        kept = 0
        for m in data:
            if not config.is_embodied(m):
                continue
            kept += 1
            author = m["id"].split("/")[0]
            authors.setdefault(author, set()).add(m.get("pipeline_tag") or "")
        print(f"    filter={tag}: 返回 {len(data)} 个模型，具身 {kept} 个")
    return authors


def fetch_user_meta(client, username):
    """
    访问用户主页 HTML，提取 fullname / 粉丝数 / 账号类型。
    返回 dict：{username, fullname, follower_count, type}。
    """
    raw = client.get_text("/" + username)

    # fullname：从 <title>用户名 (Fullname)</title> 里取括号内的部分
    fullname = None
    title = re.search(r"<title>([^<]+)</title>", raw)
    if title:
        m = re.search(r"\(([^)]+)\)", title.group(1))
        fullname = m.group(1).strip() if m else None

    # 粉丝数：内嵌 JSON 里是 &quot;followerCount&quot;:数字，先还原 HTML 实体再匹配
    unescaped = htmlmod.unescape(raw)
    fc = re.search(r'"followerCount":(\d+)', unescaped)
    follower_count = int(fc.group(1)) if fc else 0

    # 关注数（全平台）：主页里 numFollowingUsers + numFollowingOrgs 分别是「关注的人 + 关注的组织」
    fu = re.search(r'"numFollowingUsers":(\d+)', unescaped)
    fo = re.search(r'"numFollowingOrgs":(\d+)', unescaped)
    following_count = (int(fu.group(1)) if fu else 0) + (int(fo.group(1)) if fo else 0)

    # 账号类型：主页里出现 /organizations/<username> 链接的是组织账号（据此排除，只保留个人）
    is_org = f"/organizations/{username}" in raw

    return {
        "username": username,
        "fullname": fullname,
        "follower_count": follower_count,
        "following_count": following_count,
        "type": "org" if is_org else "user",
    }


def fetch_user_list(client, username, kind, max_items=500):
    """
    抓某人的 following 或 followers 列表，返回 list[username]。
    kind: 'following' 或 'followers'（只对个人账号有效）。
    HF 这两个接口一次只返回一页、不带分页游标，所以这里只发一次请求；
    max_items 只作为结果条数上限（防御性截断）。
    """
    try:
        resp = client.get(f"/api/users/{username}/{kind}", params={"limit": 100})
    except RuntimeError:
        return []  # 拿不到就返回空列表
    return [item["user"] for item in resp.json()][:max_items]


def main():
    db.init_db()
    client = HFClient()

    # —— 第 1 步：收集候选作者 ——
    print("【1/4】搜索具身智能模型，收集候选作者 ...")
    candidates = collect_candidates(client)
    print(f"    共找到 {len(candidates)} 个候选作者")

    # —— 第 2 步：抓粉丝数等元数据（每个候选访问一次主页 HTML）——
    print("【2/4】逐个抓取粉丝数...")
    metas = []
    total = len(candidates)
    for i, name in enumerate(candidates, 1):
        try:
            metas.append(fetch_user_meta(client, name))
        except Exception as exc:
            print(f"    {name} 抓取失败：{exc}")
            metas.append({"username": name, "fullname": None, "follower_count": 0, "type": "user"})
        if i % 10 == 0:
            print(f"    进度 {i}/{total} ...")

    # 排除组织账号，按粉丝数取 Top10 大V（只保留个人）
    individuals = [m for m in metas if m["type"] == "user"]
    individuals.sort(key=lambda x: -x["follower_count"])
    top10 = individuals[: config.TOP_INFLUENCERS]

    print("【3/4】Top10 大V：")
    for i, m in enumerate(top10, 1):
        print(f"    #{i:2d} {m['username']:<28} 粉丝={m['follower_count']}  ({m['fullname']})")

    # —— 第 4 步：抓关注网络（对这 10 人的 following + followers 构成人脉网）——
    print(f"【4/4】抓取关注网络（{len(top10)} 个个人大V的 following + followers）...")
    edge_rows = []
    seen_edges = set()
    for m in top10:
        name = m["username"]
        # 出度：他们关注了谁
        try:
            following = fetch_user_list(client, name, "following", max_items=config.MAX_FOLLOWERS_PER_USER)
        except Exception as exc:
            following = []
            print(f"    {name} 关注列表抓取失败：{exc}")
        for f in following:
            key = (name, f)
            if key not in seen_edges:
                seen_edges.add(key)
                edge_rows.append({"from_user": name, "to_user": f, "edge_type": "following"})
        # 入度：谁关注了他们（上限 MAX_FOLLOWERS_PER_USER）
        try:
            followers = fetch_user_list(client, name, "followers", max_items=config.MAX_FOLLOWERS_PER_USER)
        except Exception as exc:
            followers = []
            print(f"    {name} 粉丝列表抓取失败：{exc}")
        for f in followers:
            key = (f, name)
            if key not in seen_edges:
                seen_edges.add(key)
                edge_rows.append({"from_user": f, "to_user": name, "edge_type": "follower"})
        print(f"    {name}: 关注 {len(following)} 人 / 被 {len(followers)} 人关注")

    # 存库（重复运行先清空这两张表，避免累积脏数据）
    conn = db.get_conn()
    conn.execute("DELETE FROM influencers")
    conn.execute("DELETE FROM follow_edges")
    conn.commit()
    conn.close()

    influencer_rows = [
        {
            "username": m["username"],
            "fullname": m["fullname"],
            "type": m["type"],
            "follower_count": m["follower_count"],
            "following_count": m.get("following_count"),
        }
        for m in top10
    ]
    db.insert_many("influencers", influencer_rows, replace=True)
    db.insert_many("follow_edges", edge_rows, replace=False)
    print(f"完成：已保存 {len(influencer_rows)} 个大V、{len(edge_rows)} 条关注边。")


if __name__ == "__main__":
    main()
