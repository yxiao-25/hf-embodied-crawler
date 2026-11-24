# HuggingFace 具身智能数据爬取与展示

爬取 HuggingFace 的 Trending 榜单、具身智能领域大V 关注网络、最火热的具身智能项目，整理到 SQLite 数据库，并展示成网页。

> **两种使用方式**
> - **云端托管版（推荐，零维护）**：网页部署在 GitHub Pages，每天由 GitHub Actions 自动抓取数据并更新，你电脑开关机、翻不翻墙都不影响。直接打开：`https://<你的用户名>.github.io/<仓库名>/`
> - **本地运行版（学习/调试用）**：Flask + SQLite，跑在自己电脑上，需要开翻墙代理。

## 功能

| # | 功能 | 说明 |
|---|------|------|
| 1 | 一周 Trending 按天展示 | 每日快照 HF 热门模型榜单，按天分组展示（连续 7 天累积满一周） |
| 2 | 具身智能 Top10 大V + 关注网络 | 粉丝数 Top10 的具身智能个人账号，抓取个人账号之间的关注网络，统计入度/出度/总和最高的人 |
| 3 | 最火热的 10 个具身智能项目 | 用官方标签识别，提取 GitHub 链接与 HuggingFace Space |
| 4 | 网页展示 | ECharts，含网络图、柱状图、榜单表格 |

## 云端自动更新是怎么工作的

```
GitHub Actions（美国服务器，免翻墙）
   └─ 每天 09:00（北京时间）定时运行 ci_daily.py
        1. 抓当天 HuggingFace Trending
        2. upsert 进 docs/data/trending.json（跨天累积）
        3. git commit + push 回仓库
              └─ GitHub Pages 自动重新部署网页（任何人随时可打开）
```

- **为什么不用翻墙**：GitHub Actions 的运行环境在美国，直接访问 `huggingface.co` 是通的。
- **为什么数据不会丢**：CI 环境没有持久化磁盘，所以数据以 JSON 文件的形式提交在仓库里，天然持久化、可回溯。
- **任务2/任务3 是快照**：大V、关注网络、热门项目不是每天变的，作为一次性数据导出提交（可随时本地重跑刷新）。

## 技术栈

- **Python 3.13** · 一门语言贯穿全项目
- **requests** · HTTP 请求
- **sqlite3**（内置）· 数据库，单文件零配置
- **Flask** · 本地网页后端
- **ECharts**（本地化）· 图表
- **GitHub Actions + Pages** · 云端定时采集 + 静态网页托管

## 项目结构

```
├── config.py              # 全局配置（官方站地址、关键词、抓取条数、限速）
├── hf_client.py           # HF 请求层（统一地址、限速、重试）
├── db.py                  # SQLite 建表 + 读写
├── crawler_trending.py    # 任务1：每日 Trending 快照（fetch_trending 被两处复用）
├── crawler_influencers.py # 任务2：大V + 关注网络
├── crawler_projects.py    # 任务3：热门具身智能项目
├── analysis.py            # 入度/出度统计
├── app.py                 # Flask 网页后端（本地版）
├── run_daily.py           # 本地每日采集入口（写 SQLite，配合 Windows 计划任务）
├── export_json.py         # 把 SQLite 导出成 docs/data/*.json（供云端网页）
├── ci_daily.py            # GitHub Actions 每日入口（抓 Trending → 更新 JSON）
├── .github/workflows/daily.yml  # 云端定时任务（cron）
├── docs/                  # 云端静态站（GitHub Pages 部署目录）
│   ├── index.html         #   网页（读 data/*.json）
│   ├── echarts.min.js     #   ECharts（本地化）
│   └── data/*.json        #   4 块数据（trending/influencers/network/projects）
├── templates/index.html   # 本地 Flask 版网页（读 /api/*）
├── static/echarts.min.js  # 本地 ECharts
└── data/hf.db             # SQLite 数据库（运行后生成，不入库）
```

## 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 依次运行三个爬虫，抓数据入库（需开全局代理，连官方站 huggingface.co）
python crawler_trending.py       # 任务1
python crawler_influencers.py    # 任务2（较慢，需几分钟）
python crawler_projects.py       # 任务3

# 3. 导出云端版数据（可选，用于更新 docs/data/*.json）
python export_json.py

# 4. 启动本地网页
python app.py
# 浏览器打开 http://127.0.0.1:5000
```

## 数据说明

- **官方站 + 代理**：本地运行数据直接来自 HuggingFace 官方站 `huggingface.co`，需要开全局代理（翻墙）访问；云端 GitHub Actions 无需代理。
- **一周 Trending**：HF 不提供历史按天数据，采用「每日快照」——每天跑一次，连续 7 天累积成一周。
- **粉丝数来源**：`/api/users/{name}` 接口对组织和个人都返回 404，粉丝数改从作者主页 HTML 里内嵌的 `"followerCount"` 字段用正则提取。
- **组织账号限制**：HuggingFace 官方对组织账号的「关注/粉丝列表」接口不开放，因此关注网络只在个人账号之间构建（本项目任务2 只做个人账号）。

## License

MIT
