# 个人主页项目 — CLAUDE.md

## 项目简介

基于 **FastAPI + Jinja2 + SQLite** 的个人主页网站，采用日式侘寂（Wabi-Sabi）美学设计。

### 功能模块

| 模块 | 描述 | 状态 |
|------|------|------|
| **日记系统** | Markdown 格式日记的 CRUD、分页、标签、点赞 | ✅ 完成 |
| **测验系统** | 选择题测验（答题/管理/结果回顾），自动配图 | ✅ 完成（UI 已重设计）|
| **留言板** | 访客留言、置顶、分页、管理端删除/置顶 | ✅ 完成 |
| **作品集** | 项目展示、分类筛选、外链 | ✅ 基础完成 |
| **站点设置** | 作者信息、联系方式、头像等动态配置 | ✅ 完成（含联系字段）|

所有管理路由（`/manage/*`）仅限本地访问（127.0.0.1），CSRF 双提交 Cookie 保护。

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
│   ├── database.py           # SQLAlchemy 引擎 & 会话（含初始种子数据）
│   ├── models/               # SQLAlchemy 数据模型
│   │   ├── diary.py
│   │   ├── quiz.py
│   │   ├── message.py        # 留言模型
│   │   ├── project.py        # 作品集模型
│   │   └── setting.py        # SiteSetting(key, value) 键值对存储
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
│   │   ├── message_service.py
│   │   ├── project_service.py
│   │   ├── unsplash_service.py   # Unsplash 图片搜索
│   │   └── pexels_service.py     # Pexels 图片搜索
│   ├── templates/            # Jinja2 模板
│   │   ├── base.html
│   │   ├── home.html
│   │   ├── about.html
│   │   ├── 404.html
│   │   ├── diaries/
│   │   ├── quiz/             # play.html / manage.html / results.html
│   │   ├── messages/         # list.html / manage.html
│   │   ├── projects/         # list.html / manage.html / edit.html
│   │   └── manage/
│   │       └── settings.html # 站点设置页面
│   ├── static/
│   │   ├── css/
│   │   │   ├── variables.css     # 设计 Token（颜色、间距、字体）
│   │   │   ├── base.css          # 重置、布局、导航、页脚
│   │   │   ├── components.css    # 组件样式（按钮、卡片、表单等）
│   │   │   └── pages.css         # 页面专属样式（日记、测验、作品等）
│   │   └── js/
│   │       ├── main.js           # 全局 JS（导航、滚动渐入等）
│   │       └── quiz.js           # 测验答题交互（单页应用式）
│   └── utils/
│       ├── csrf.py               # CSRF 双提交 Cookie 保护
│       ├── locals.py             # require_local 本地访问限制
│       └── markdown.py           # Markdown 渲染（含语法高亮）
├── data/
│   └── homepage.db           # SQLite 数据库
├── .env                      # API Keys 等环境变量（不提交）
├── .gitignore                # 排除 .env / data/ / venv/ / .claude/ 等
├── requirements.txt          # Python 依赖
├── run.py                    # 启动入口
├── ui-prototype.html         # 日式美学 UI 原型（设计参考）
├── design-inspiration.html   # 设计灵感库
└── CLAUDE.md                 # 本文件
```

---

## CSS 设计系统

4 层文件级联，按 `variables.css` → `base.css` → `components.css` → `pages.css` 顺序加载。

### 设计 Token（variables.css）

| Token | 值 | 说明 |
|-------|-----|------|
| `--bg` | `#faf6f0` | 和纸米白背景 |
| `--accent` | `#c9a96e` | 金色点缀 |
| `--accent-hover` | `#b8944a` | 金色悬停 |
| `--accent-subtle` | `rgba(201,169,110,0.12)` | 金色半透明 |
| `--accent-subtler` | `rgba(201,169,110,0.06)` | 金色极淡 |
| `--sage` | `#8b7355` | 鼠尾草褐 |
| `--text` | `#2d2d2d` | 主文字色 |
| `--text-secondary` | `#6b6b6b` | 次要文字 |
| `--text-muted` | `#a09888` | 弱化文字 |
| `--card` | `#ffffff` | 卡片背景 |
| `--border` | `#e0d8cc` | 边框 |
| `--border-light` | `#ece6dc` | 浅边框 |
| `--radius-sm` | `3px` | 小圆角 |
| `--radius-md` | `8px` | 中圆角 |
| `--font-serif` | `Playfair Display` | 英文衬线 |
| `--font-sans` | `Noto Sans SC` | 中文无衬线 |

---

## 功能模块详解

### 留言板

- **访客端**（`/messages`）：浏览留言列表、发表新留言
- **管理端**（`/manage/messages`）：删除留言、切换置顶状态
- 数据模型：`Message(id, nickname, content, is_pinned, created_at)`
- 留言列表按时间倒序，置顶留言始终在前
- 无需登录即可提交，需 CSRF 保护
- 管理端分页，每页 20 条

### 作品集

- **公开端**（`/projects`）：浏览作品列表、按分类筛选
- **管理端**（`/manage/projects`）：作品 CRUD（AJAX 编辑、发布切换）
- 数据模型：`Project(id, title, description, category, tags, demo_url, source_url, image_url, order, is_published, created_at, updated_at)`
- 公开端按 `order` 升序排列，只显示 `is_published=True`
- 分类筛选通过 URL 参数 `?category=` 共享状态

> **⚠️ 已知问题**：作品分类目前硬编码在 `routes/projects.py`（`CATEGORIES = ["web", "tool", "design", "ai", "other"]`），前端显示名称和图标也硬编码在模板中。计划使用 `SiteSetting` 存储可编辑的分类配置（JSON 格式），在站点设置页面增加分类管理界面。

### 测验系统

- **答题端**（`/quiz`）：由 `quiz.js` 动态渲染，分欢迎 → 答题 → 回顾 → 结果四阶段
- **管理端**（`/manage/quiz`）：题目的增删改、批量配图
- 数据模型：`QuizQuestion(id, question, option_a/b/c/d, correct_index, explanation, image_url, option_images)`
- 答题时 JS 只收到不含 `correct_index` 的 JSON（防止泄露答案）
- 管理端表格二维码配图：🟢 有图 / 🔴 无图，支持按有无图片筛选
- 自动配图：基于题目和选项文本搜索 Unsplash/Pexels（Pexels 优先）
- 结果页展示得分、正确率、每题解析及正误标记

### 站点设置

- **路由**：`/manage/settings`
- 使用 `SiteSetting(key, value)` 键值对存储，当前支持：
  - `site_author` — 站点作者名
  - `photo_url` — 头像 URL
  - `about_me` — 关于我
  - `contact_email` — 联系邮箱
  - `contact_github` — GitHub 用户名
- 数据库初始化时自动写入默认种子值

---

## 已完成的重构/优化

1. **测验管理页面 UI 重设计** — 移除 743 行内联样式，改用 `.qm-*` CSS 类体系
2. **测验答题页面 UI 重设计** — 补充 `quiz.js` JS 渲染阶段的完整 CSS（~380 行），修复 CSS 变量名兼容性
3. **废弃样式清理** — 移除 `components.css` 中约 150 行废弃的 `.q-*` 样式
4. **设置页增加联系字段** — 新增 `contact_email`、`contact_github` 字段
5. **Git 初始化** — 首次提交包含 56 个源文件

---

## 待办事项

1. **作品分类可编辑化** — 用 `SiteSetting` 存储分类 JSON（key/name/icon），替换硬编码
2. **新增首页统计卡片** — 日记数、作品数、测验最高分在 Bento Grid 中的动态展示
3. **响应式优化** — 小屏设备上的 Bento Grid、照片轮播、表格等组件的适配审查

---

## 开发命令

```bash
# 启动开发服务器
python run.py
# 热重载模式：
DEBUG=true python run.py

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest -v --cov=app tests/
```

---

## 安全检查清单

- [x] 无硬编码密钥（API Key 仅存放在 `.env` 中）
- [x] CSRF 保护应用于所有管理表单
- [x] 管理路由限制为本地访问（`require_local`）
- [x] Markdown 渲染转义 HTML
- [x] 用户输入在存储前验证
- [x] 错误日志不泄露敏感信息
- [x] 图片 URL 格式验证

---

## 项目约束

- 所有 `/manage/*` 路由必须使用 `require_local` 保护
- 表单使用 double-submit cookie 模式的 CSRF 保护
- 函数必须包含类型注解
- 前端为服务端渲染 + 原生 JS，无前端框架依赖
- `nul` 文件（Windows 保留设备名）无法删除，已在 `.gitignore` 中排除
- `venv/` 和 `.claude/` 目录不提交到 git

---

## Agent 协作模式

本项目采用多 Agent 并行协作的开发模式。典型任务分解：

```
功能开发流程（并行）：
┌──────────────────────────────────────────────────────┐
│  Agent 1: 项目经理     ← 整体架构、技术选型、任务分解   │
│  Agent 2: 后端开发     ← 路由、服务、模型层实现         │
│  Agent 3: 前端开发     ← 模板、CSS、JS 交互            │
│  Agent 4: 图片采集     ← 根据提示词从公共 API 抓取      │
│  Agent 5: 测试         ← 单元测试、集成测试             │
└──────────────────────────────────────────────────────┘
```
