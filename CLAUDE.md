# 个人主页项目 — CLAUDE.md

## 项目简介

基于 **FastAPI + Jinja2 + SQLite** 的个人主页网站，包含：
- **日记系统** — Markdown 格式日记的 CRUD、分页、标签、点赞
- **测验系统** — 选择题测验、自动配图（Unsplash / Pexels 双数据源）
- **留言板** — 访客留言、置顶、分页（管理端可删除/置顶）
- **作品集** — 项目作品展示、分类筛选、外链
- **站点设置** — 站点标题、作者信息等动态配置

所有管理路由（`/manage/*`）仅限本地访问（127.0.0.1）。

### 功能模块详解

#### 留言板
- **访客端**（`/messages`）：浏览留言列表、发表新留言
- **管理端**（`/manage/messages`）：删除留言、切换置顶状态
- 数据模型：`Message(id, nickname, content, is_pinned, created_at)`
- 留言列表按时间倒序排列，置顶留言始终在前
- 所有留言无需登录即可提交，需 CSRF 保护
- 管理端分页，每页 20 条

#### 作品集
- **公开端**（`/projects`）：浏览作品列表、按分类筛选
- **管理端**（`/manage/projects`）：作品 CRUD
- 数据模型：`Project(id, title, description, category, tags, demo_url, source_url, image_url, order, is_published, created_at, updated_at)`
- 分类为预定义枚举：`web`、`tool`、`design`、`ai`、`other`
- 公开端按 `order` 升序排列，只显示 `is_published=True` 的作品
- 支持分类筛选（前端 JS 交互，通过 URL 参数 `?category=web` 共享状态）

---

## 技术栈

| 层面 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 模板引擎 | Jinja2（服务端渲染） |
| ORM | SQLAlchemy 2.0 |
| 数据库 | SQLite |
| 前端 | 原生 HTML/CSS/JS（CSS 变量设计系统） |
| 字体 | `Playfair Display`（英文标题）+ `Noto Sans SC`（正文）|
| 图片 API | Unsplash（默认）+ Pexels（备选，质量更高） |
| HTTP | httpx（异步） |
| 运行 | uvicorn |

---

## 项目结构

```
个人主页/
├── app/
│   ├── main.py              # FastAPI 应用工厂
│   ├── config.py             # 配置（.env → 环境变量）
│   ├── database.py           # SQLAlchemy 引擎 & 会话
│   ├── models/               # SQLAlchemy 数据模型
│   │   ├── diary.py
│   │   ├── quiz.py
│   │   ├── message.py        # 留言模型
│   │   ├── project.py        # 作品集模型
│   │   └── setting.py
│   ├── routes/               # 路由处理器
│   │   ├── pages.py          # 首页、关于、404
│   │   ├── diaries.py        # 日记系统
│   │   ├── quiz.py           # 测验系统（含图片管理端点）
│   │   ├── messages.py       # 留言板路由
│   │   ├── projects.py       # 作品集路由
│   │   └── settings.py       # 站点设置
│   ├── services/             # 业务逻辑层
│   │   ├── diary_service.py
│   │   ├── quiz_service.py
│   │   ├── message_service.py    # 留言业务逻辑
│   │   ├── project_service.py    # 作品集业务逻辑
│   │   ├── unsplash_service.py   # Unsplash 图片搜索
│   │   └── pexels_service.py     # Pexels 图片搜索
│   ├── templates/            # Jinja2 模板
│   │   ├── base.html
│   │   ├── home.html
│   │   ├── about.html
│   │   ├── 404.html
│   │   ├── diaries/
│   │   ├── quiz/
│   │   ├── messages/         # 留言板模板
│   │   └── projects/         # 作品集模板
│   ├── static/
│   │   ├── css/              # CSS 设计系统
│   │   └── js/               # 前端 JS
│   └── utils/                # 工具函数
├── data/
│   └── homepage.db           # SQLite 数据库
├── .env                      # API Keys 等环境变量
├── requirements.txt          # Python 依赖
├── run.py                    # 启动入口
├── ui-prototype.html         # 日式美学 UI 原型（设计参考）
├── design-inspiration.html   # 设计灵感库
└── CLAUDE.md                 # 本文件
```

---

## 多 Agent 并行工作模式

本项目采用**多 Agent 并行协作**的开发模式，以最大化效率、缩短项目周期。

### 并行工作原则

1. **任务分解** — 每个大功能拆解为可独立并行执行的子任务
2. **并行启动** — 使用 Task 工具同时启动多个 Agent，各司其职
3. **依赖管理** — 无依赖关系的任务完全并行；有依赖的在上下游衔接点同步
4. **独立工作区** — 每个 Agent 在独立上下文中工作，互不阻塞

### 典型并行 Agent 配置

```
功能开发流程（并行）：
┌─────────────────────────────────────────────────────┐
│  Agent 1: 项目经理        ← 整体架构、技术选型、任务分解  │
│  Agent 2: 后端开发        ← 路由、服务、模型层实现       │
│  Agent 3: 前端开发        ← 模板、CSS、JS 交互          │
│  Agent 4: 图片采集        ← 根据提示词从公共 API 抓取    │
│  Agent 5: 测试            ← 单元测试、集成测试           │
└─────────────────────────────────────────────────────┘
```

---

## Agent 角色定义

### 1. 项目经理（Orchestrator）

**职责**：+ 整体架构规划、任务分解、进度协调

**工作方式**：
- 使用 `planner` 子 Agent 制定详细实施计划
- 使用 `architect` 子 Agent 做架构决策
- 将大功能拆解为独立子任务，分配给并行 Agent
- 在关键节点进行质量审查（`code-reviewer`、`security-reviewer`）
- 控制项目节奏，避免过度设计

**交付物**：
- 技术方案文档
- 任务分解清单
- 接口约定文档
- 代码审查报告

### 2. 图片审美专家（Image Curator）

**职责**：从 Unsplash/Pexels 等公共图片 API 抓取高质量、符合页面布局的图片

**工作方式**：
- 理解页面 UI 布局和视觉风格，据此构造搜索关键词
- 使用**高质量美学关键词**指导 Agent 搜索：
  - 构图类：`minimal composition`、`negative space`、`rule of thirds`、`leading lines`
  - 光影类：`soft natural light`、`golden hour`、`dramatic lighting`、`diffuse light`
  - 色调类：`warm tone palette`、`pastel color scheme`、`monochrome`、`vibrant colors`
  - 质感类：`high resolution`、`sharp focus`、`fine art photography`、`editorial style`
  - 情绪类：`serene atmosphere`、`cozy mood`、`energetic vibe`、`melancholic tone`
- 候选图片的筛选标准：
  - 与页面布局匹配（横图用于横幅/标题区，竖图用于卡片/头像区）
  - 有足够的"留白"区域（便于叠加文字）
  - 色调与站点设计系统（CSS 变量）协调
  - 避免过于杂乱或主体不明确的图片
- 当前项目使用双数据源：**Pexels 优先**（质量更高）、Unsplash 降级

**图片尺寸规范**：
| 用途 | 尺寸参数 | 说明 |
|------|---------|------|
| 题目配图 | `w=1080&h=480` | 横图，适合横幅布局 |
| 选项配图 | `w=400&h=225` | 16:9 小卡片图 |
| 首页背景 | `w=1920&h=1080` | 全屏背景 |
| 缩略图 | `w=200&h=120` | 列表预览 |

**搜索策略**：中文关键词 → 翻译映射表 → 追加美学修饰词 → 多轮降级搜索

### 3. 后端开发（Backend Developer）

**职责**：实现路由（`routes/`）、服务层（`services/`）、数据模型（`models/`）

**技术约束**：
- FastAPI + SQLAlchemy + Jinja2（服务端渲染，无前端框架）
- 所有 `/manage/*` 路由必须使用 `require_local` 保护
- 表单使用 double-submit cookie 模式的 CSRF 保护
- 使用 `httpx.AsyncClient` 进行异步 HTTP 请求
- 函数必须包含类型注解

### 4. 前端开发（Frontend Developer）

**职责**：Jinja2 模板、CSS 设计系统、JS 交互

**设计约束**：
- **日式美学（Wabi-Sabi）** 风格 — 详情参考 `ui-prototype.html`
- 配色：`#faf6f0` 和纸米白底 / `#c9a96e` 金色点缀 / `#8b7355` 鼠尾草褐
- 字体：`Playfair Display`（英文标题、斜体标签）+ `Noto Sans SC`（正文）
- 圆角克制（`3-8px`），细边框（`1px solid`），大量留白
- Hero 区域：左侧文字 + 右侧照片轮播
- Bento Grid 3 列布局（首页）
- 响应式设计（768px / 480px 断点）
- Scroll Reveal 滚动渐入动效
- 导航栏顺序：首页 / 日记 / 作品集 / 留言板 / 测验 / 关于（管理链接：日记管理 / 测验管理 / 作品管理 / 留言管理 / 设置，仅本地显示）

### 5. 质量保证（QA / Tester）

**职责**：编写 pytest 测试、确保 80%+ 覆盖率

**测试类型**：
- 单元测试（服务层、工具函数）
- 集成测试（路由端点、数据库操作）
- 所有状态转换必须测试：loading → success、loading → error、retry

---

## 关键接口约定

### API 响应格式
```python
{"success": bool, "data": Any | None, "error": str | None}
```

### 图片服务接口
```python
# 输入：中文/英文文本
# 输出：ImageCandidate(url, thumb_url, raw_url, author, likes)
async def fetch_image_candidates(query: str, count: int = 8) -> list[ImageCandidate]
async def fetch_option_candidates(options: list[str], count: int = 8) -> list[list[ImageCandidate]]
```

### 留言板接口

| 路由 | 方法 | 说明 |
|------|------|------|
| `/messages` | GET | 公开留言列表（分页，置顶在前） |
| `/messages` | POST | 提交新留言 (`nickname`, `content`, `csrftoken`) |
| `/manage/messages/{id}/delete` | POST | 删除留言（本地+CSRF） |
| `/manage/messages/{id}/toggle-pin` | POST | 切换置顶（本地+CSRF） |

```python
# 数据模型
class Message(Base):
    __tablename__ = "messages"
    id: int           # PK, auto
    nickname: str     # max 50
    content: str      # max 2000
    is_pinned: bool   # default False
    created_at: datetime  # default now
```

### 作品集接口

| 路由 | 方法 | 说明 |
|------|------|------|
| `/projects` | GET | 公开作品列表 (`?category=web`) |
| `/manage/projects` | GET | 管理端作品列表 |
| `/manage/projects/create` | POST | 创建作品 |
| `/manage/projects/{id}/edit` | POST | 编辑作品 |
| `/manage/projects/{id}/delete` | POST | 删除作品 |
| `/manage/projects/{id}/toggle-publish` | POST | 切换发布状态 |

```python
# 数据模型
class Project(Base):
    __tablename__ = "projects"
    id: int           # PK, auto
    title: str
    description: str
    category: str     # web | tool | design | ai | other
    tags: str         # 逗号分隔
    demo_url: str | None
    source_url: str | None
    image_url: str | None
    order: int        # default 0, 排序用
    is_published: bool  # default False
    created_at: datetime
    updated_at: datetime
```

### 首页上下文数据
```python
# home.html 模板接收的数据
{
    "site_author": str,           # 作者名（可从站点设置覆盖）
    "photo_url": str | "",        # 头像/照片 URL
    "about_me": str | "",         # 简短介绍
    "latest_diaries": list,       # 最新 3 篇公开日记
    "diary_count": int,           # 日记总数
    "quiz_count": int,            # 已发布题目数
    "quiz_best": int | None,      # 历史最高分
    "project_count": int,         # 已发布作品数
    "active_page": "home",
}
```

---

## 开发命令

```bash
# 启动开发服务器
python run.py
# 或：DEBUG=true python run.py （热重载模式）

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest -v --cov=app tests/
```

---

## 安全检查清单

- [ ] 无硬编码密钥（API Key 仅存放在 `.env` 中）
- [ ] CSRF 保护应用于所有管理表单
- [ ] 管理路由限制为本地访问
- [ ] Markdown 渲染转义 HTML
- [ ] 用户输入在存储前验证
- [ ] 错误日志不泄露敏感信息
- [ ] 图片 URL 格式验证

---

## 个性化配置

在 `app/config.py` 中修改：
```python
SITE_TITLE = "我的个人主页"
SITE_AUTHOR = "你的名字"
SITE_DESCRIPTION = "欢迎来到我的个人空间"
```
