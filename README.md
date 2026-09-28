# 🌸 萌语博客 · MoeBlog（ACGBlog）

> 一个粉紫蓝萌系的二次元个人博客 / 轻内容社区。
> **Django 5.2 · DRF · MySQL 8 · Celery / Redis · WhiteNoise · Live2D · PWA**

柔和圆润、清新通透，自带看板娘、樱花花瓣、明暗双主题与一堆体验彩蛋；
内置完整的 **投稿 → 审核 → 发布 → 软删除 → 回收站** 运营闭环，
以及一个 **全局永久强制** 的访问日志中间件（三层降级投递，保证日志不丢且不阻塞请求）。

> 本 README 已按「最新重构」重写：
> - 原单文件 `blog/models.py`（约 2000 行）拆为 **`blog/models/` 包（15 文件 / 51 模型）**；
> - blog 根散落的业务服务归入 **`blog/services/`**、纯工具归入 **`blog/utils/`**；
> - 各文件设置常量统一收拢到 **`DjangoBlog/settings.py`**（带来源与含义注释）；
> - 新增三段式权限装饰器 `staff_required_moe`，修复非员工访问看板无提示的问题。

---

## 目录

1. [项目定位与设计语言](#1-项目定位与设计语言)
2. [功能总览](#2-功能总览)
3. [技术栈与系统架构](#3-技术栈与系统架构)
4. [目录结构](#4-目录结构)
5. [数据模型（models 包 · 51 个模型）](#5-数据模型models-包--51-个模型)
6. [核心实现细节](#6-核心实现细节)
7. [路由与 API 一览](#7-路由与-api-一览)
8. [环境要求与部署](#8-环境要求与部署)
9. [运维手册（Celery / Redis / 兜底队列）](#9-运维手册celery--redis--兜底队列)
10. [测试与验收](#10-测试与验收)
11. [扩展开发指南](#11-扩展开发指南)
12. [安全约定](#12-安全约定)
13. [工单变更历史](#13-工单变更历史)
14. [常见问题 FAQ](#14-常见问题-faq)

---

## 1. 项目定位与设计语言

**定位**：二次元轻量萌系个人博客 / 内容社区，单 Django app（`blog`）承载全部业务。

| 维度 | 约定 |
| --- | --- |
| 主色 | 粉 `#ff8fb1`、紫 `#a06cd5`、蓝 `#6ea8fe`，点缀樱花粉 |
| 形态 | 大圆角（卡片约 18px、胶囊 999px）、柔和投影、半透明玻璃拟态 |
| 质感 | 清新通透、留白充足、渐变克制 |
| 文案 | 全站中文 + 语气词「喵~」；集中在后端文案注册表（见 [6.4](#64-文案系统site_messages)） |
| 动效 | 樱花飘落、入场淡入、卡片悬浮、按钮回弹、看板娘互动 |
| 主题 | 明 / 暗双主题，一键切换并持久化（前端 `data-theme`） |
| 响应式 | 移动 / 平板 / 桌面自适应，覆盖 360–1920 常见视口 |
| 无障碍 | 跳过导航链接、`aria-*` 语义、`:focus-visible` 焦点环、`prefers-reduced-motion` 降动效 |

设计令牌（Design Token）统一用 CSS 自定义属性维护，明暗主题分别在 `:root` 与
`:root[data-theme="dark"]` 下定义；全站组件只引用变量、不写死颜色。

### 1.1 三类用户角色

| 角色 | 典型能力 |
| --- | --- |
| 游客（未登录） | 浏览、搜索、查看评论；访问看板等权限路由被引导登录 |
| 文章作者（普通注册用户） | 发布 / 编辑自己的文章、评论、申请置顶 / 精华、收藏、关注 |
| 管理员（`is_staff` / 超级用户） | 看板、站点设置、文案总表、审核队列、分类创建、审批推广申请 |

---

## 2. 功能总览

### 内容与阅读
- 文章 / 笔记 / 独立页面三种类型；草稿 / 待审 / 已发布状态。
- 文章列表（最新 / 热门）、置顶 / 精华 / 热门徽章、NEW / HOT 角标。
- 详情：目录 TOC（可拖动 / 导出 Markdown）、阅读进度、字数与预计时长、上一 / 下一篇。
- 专注阅读、阅读设置（字号 / 行距 / 配色）、TTS、阅读进度记忆。
- 导出：全文复制、Markdown、PDF、打印；分享卡片 + 二维码 + 短链。
- 封面智能布局（封面 → 正文首图 → 无图文字填充）。
- 分类、标签（标签云可拖动 + 索引 + 排行榜）、系列（连载 + 序号）、归档。
- 文章访问密码（哈希存储）、文章评分（1~5 星）。
- **定时发布**：预约未来时间，Celery beat 或 Web 兜底扫描自动流转上线。

### 互动社区
- 多级评论（楼中楼）、评论点赞 / 表情回应、图片评论、折叠、举报。
- 评论可在设定时限内撤回（软删除）。
- 文章点赞 / 踩、收藏（收藏夹分组）、关注（用户 / 分类 / 标签）、黑名单与静音。
- @提及、回复通知、站内通知中心、评论摘要邮件（Celery 异步）。
- 徽章 / 成就（个人中心可视化面板：已获得置顶、未获得折叠可展开、含获取方式与进度）。
- 积分体系、用户主页、个性签名、用户笔记、阅读历史、登录历史、API Key。

### 运营与治理
- **投稿审核闭环**：待审 → 通过 / 驳回（驳回退回草稿并通知作者）。
- **推广申请（置顶 / 精华 / 热门）**：作者发起 → 管理员审批 →
  审批结论与「系统执行状态」分离记录（名额满时明确显示「未执行·已达上限」）。
- **软删除 + 回收站**：文章 / 评论删除先进回收站，可恢复或彻底删除。
- **审核日志 `ModerationLog`**：提交 / 通过 / 驳回 / 软删 / 恢复 / 彻底删除全程留痕。
- 运营看板：实时统计、访问趋势、热门文章 Top、分类分布、待办计数。
- **站点设置（`SiteInfo` 单例）**：站名 / Logo / 副标题 / SEO / 页脚在线编辑。
- 一键刷新静态压缩与缓存（管理命令 + 看板按钮 + API）。
- **访问日志中间件**（全局永久强制模块）：异步优先 → Redis 兜底队列 → 极端同步。

### 前端体验
- Live2D 看板娘：多模型 / 服装、对话气泡、工具栏、猜拳小游戏；
  支持 `?waifu=off` 关闭，并尊重「减少动态效果」偏好。
- 樱花花瓣、粒子背景、Konami 彩蛋、404「接樱花」小游戏。
- 全站统一 `moeToast` 轻提示与 `moeConfirm` 确认弹窗（**零原生 alert / confirm**）。
- PWA：manifest、Service Worker、可安装、可离线。
- 静态资源自动压缩（CSS/JS minify）、构建号破缓存、`.gz` 预压缩（WhiteNoise 直发）。
- 按钮交互骨架（hover 上浮 + 渐变描边 / active 下沉缩放 / 选中渐变白字 /
  禁用降饱和 / 键盘焦点环 / 触屏与降动效适配）。

---

## 3. 技术栈与系统架构

### 3.1 技术选型

| 层 | 技术 | 版本 | 说明 |
| --- | --- | --- | --- |
| Web 框架 | Django | 5.2.17 | 单 app（`blog`）承载全部业务 |
| API | djangorestframework | 3.15.2 | 通知 / 评论 / 点赞 / 分类等 JSON API |
| 数据库 | mysqlclient + MySQL 8 | 2.2.7 | 默认库 `acgblog`，字符集 `utf8mb4`，建议严格模式 |
| 异步任务 | Celery + Redis | 5.3.1 / 5.2.1 | broker `redis://127.0.0.1:6379/0` |
| 缓存 | Django LocMemCache | 内置 | 默认 300s；**进程内**，多进程部署需换 Redis 缓存后端 |
| 静态托管 | WhiteNoise | 6.12.0 | 生产压缩（Manifest）+ 长期缓存 |
| 图片处理 | Pillow | 10.3.0 | 封面 / 头像裁剪 / 校验 |
| HTML 净化 | bleach | 6.4.0 | 富文本与评论白名单清洗（配合 `utils/html_safety.py`） |
| 搜索 / 导出 | pypinyin / html2text / qrcode / xhtml2pdf | — | 拼音搜索、MD / PDF 导出、二维码 |
| 富文本 | CKEditor 4（本地静态 `static/ckeditor`） | — | 无需 pip 安装 |
| 看板娘 | Live2D（本地静态 `static/assets/live2d`） | — | 第三方运行时 |

### 3.2 请求链路与分层

```
┌──────────────────────────────────────────────────────────────────────┐
│                        浏览器 Chrome / Edge / 移动端                  │
│  base.html · 明暗主题 · Live2D · 樱花 · PWA(SW) · window.SITE_MSG    │
└───────────────▲────────────────────────────────┬─────────────────────┘
                │ HTML / JSON                    │ /static /media
┌───────────────┴────────────────────────────────▼─────────────────────┐
│                          Django 5.2 (WSGI)                            │
│  中间件链（自上而下请求、自下而上响应）：                              │
│    Security → WhiteNoise → AccessLog★ → Session → Common →            │
│    CsrfView → Authentication → Message → XFrameOptions →              │
│    OnlineStatus → SiteInfo → SiteMessages → MascotToggle →            │
│    CuteErrorPages★（★ = 本项目自研）                                   │
│                                                                       │
│  URL Router（页面路由 + /api/ 路由）                                  │
│        │                                                              │
│        ▼                                                              │
│  Views（blog/views/ 包：15 个功能子模块 + DRF 类视图）              │
│        │                                                              │
│        ├──► Templates（40+ 模板 + MSG 文案命名空间）                  │
│        ├──► Services（blog/services：访问日志 / 定时发布 / 文案）     │
│        └──► Utils（blog/utils：权限装饰器 / HTML 安全 / 缓存键）      │
└───────┬──────────────────────┬───────────────────────┬───────────────┘
        ▼                      ▼                       ▼
   MySQL 8 (51 模型)      LocMem Cache           Static / Media 磁盘
        ▲                  （分片 TTL）                  ▲
        │                                                 │
┌───────┴──────────────────────┐              WhiteNoise（生产托管 + .gz）
│ Celery Worker / Beat（可选）  │  Broker: Redis 6379/0
│  访问日志入库 / 定时投稿流转 / │  Result: Redis 6379/0
│  日志清理 / 邮件摘要 / 兜底补齐 │
└──────────────────────────────┘
```

### 3.3 分层约定

| 层 | 职责 | 位置 |
| --- | --- | --- |
| 中间件 | 横切关注点：日志采集、站点信息、文案注入、看板娘开关、错误页 | `blog/middleware/*.py`（一个中间件一个文件） |
| 上下文处理器 | 向所有模板注入公共数据（导航 / 侧栏 / 统计 / 文案 / 构建号） | `blog/context_processors.py` |
| 服务层 | 可复用业务逻辑，供视图与任务共用 | `blog/services/*.py` |
| 工具层 | 与业务无关的纯工具（装饰器、安全、缓存键、告警过滤） | `blog/utils/*.py` |
| 视图 | 页面渲染与 API 响应 | `blog/views/`（按功能拆 15 子模块，`__init__` 再导出） |
| 模型 | 数据结构与 ORM | `blog/models/`（15 文件包，`__init__` 统一导出） |
| 异步任务 | 不阻塞请求的副作用 | `blog/tasks.py` |
| 信号 | 模型状态变化的副作用（缓存失效 / 计数 / 徽章 / 通知 / 审核） | `blog/signals.py` |

---

## 4. 目录结构

```
ACGBlog/
├── manage.py                          # Django 入口
├── requirements.txt                   # 精确锁定的依赖
├── README.md                          # 本文档
├── DjangoBlog/                        # 项目配置包
│   ├── settings.py                    # 全局设置 + 重构收拢的功能开关/运行参数（带来源注释）
│   ├── urls.py                        # 根路由（挂载 blog.urls）
│   ├── celery.py                      # Celery 应用
│   └── wsgi.py / asgi.py
├── blog/                              # 唯一业务应用
│   ├── models/                        # ★ 模型包（原单文件 models.py 拆为 15 文件）
│   │   ├── __init__.py                #   统一导出全部模型 + __all__（外部 from blog.models import X）
│   │   ├── user.py  catalog.py  series.py
│   │   ├── article.py  comment.py  interaction.py
│   │   ├── logs.py  notification.py  badge.py
│   │   ├── site.py  moderation.py  messages.py
│   │   ├── social.py  system.py
│   ├── views/                         # ★ 视图包（按功能拆 15 子模块，__init__ 再导出）
│   │   ├── common.py articles.py comments.py auth.py users.py
│   │   ├── series.py catalog.py search.py interactions.py
│   │   ├── api.py console.py moderation.py
│   │   ├── features.py seo.py errors.py
│   ├── middleware/                    # ★ 中间件包（一个中间件一个文件）
│   │   ├── access_log.py              #   ★ 访问日志（全局永久强制，三层降级）
│   │   ├── site_messages.py site_info.py mascot.py
│   │   ├── cute_error_pages.py online_status.py
│   │   ├── slow_query.py              #   慢 SQL 日志 filter
│   │   └── __init__.py
│   ├── services/                      # ★ 业务服务层
│   │   ├── access_log_service.py      #   访问日志三级降级投递
│   │   ├── scheduled_publishing.py    #   定时文章处理（process / maybe_sweep）
│   │   ├── site_messages.py           #   文案大字典 MESSAGES + msg()
│   │   └── __init__.py
│   ├── utils/                         # ★ 纯工具层
│   │   ├── decorators.py              #   staff_required_moe 三段式权限装饰器
│   │   ├── html_safety.py             #   HTML/CSS 安全净化
│   │   ├── cache_keys.py              #   缓存键口径
│   │   ├── deprecation_filters.py     #   弃用/版本告警过滤
│   │   └── __init__.py
│   ├── urls.py                        # 应用路由（页面 + /api/）
│   ├── serializers.py                 # DRF 序列化器
│   ├── context_processors.py          # 导航 / 侧栏 / 统计 / 文案 / 构建号
│   ├── live2d.py                      # 看板娘 API（/api/live2d/）
│   ├── tasks.py                       # Celery 任务
│   ├── signals.py                     # 模型信号（审核 / 状态流转）
│   ├── admin.py                       # 自定义后台
│   ├── apps.py  tests.py
│   ├── cache_version.txt              # 缓存版本号
│   ├── management/commands/           # 管理命令（见 9.1）
│   ├── templatetags/                  # blog_extras / search_extras
│   └── migrations/                    # 迁移（自动生成，不手改）
├── templates/                         # 模板
│   ├── base.html                      # 全站骨架（导航 / 弹窗 / 文案包 / SW）
│   ├── 400.html 403.html 404.html 500.html   # 萌系错误页（自包含）
│   ├── _article_card.html _comment_item.html _badge_panel.html
│   ├── _auth_bg.html _hot_list.html _pagination.html _seo_meta.html
│   └── （index/detail/edit/categories/tags/archive/series_*/login/register/
│         user_profile/console/moderation/site_settings/status/
│         notifications/favorites/my_*/api_docs 等页面）
├── static/
│   ├── sw.js                          # Service Worker（PWA）
│   ├── manifest.json
│   ├── ckeditor/                      # 第三方编辑器（本地，不要求注释）
│   └── assets/
│       ├── css/                       # 34 个源样式（产物 .min.css + .gz）
│       ├── js/                        # 53 个源脚本（产物 .min.js + .gz）
│       ├── icons/ images/ img/        # 图标与占位插图
│       └── live2d/                    # 第三方看板娘运行时
├── staticfiles/                       # collectstatic 产物（生产）
├── media/                             # 用户上传（avatars / covers / uploads）
└── docs/                              # 全部文档、临时工具、备份与验收产物
    ├── refactor_tools/                # 重构工具（注释审计 / 三类注释增强器）
    ├── refactor_backup/               # 重构前权威备份（models.py.bak 等）
    ├── ui_screenshots/                # 浏览器实测截图集（chrome / edge）
    └── （历史工单 bugfix_* 目录）
```

> 临时 / 备份文件统一放 `docs/` 下子目录，禁止随意放置。

---

## 5. 数据模型（models 包 · 51 个模型）

`blog/models/__init__.py` **统一导出全部模型与 `__all__`**，外部一律
`from blog.models import Article`，调用方无需感知拆分。跨文件外键用字符串
（`'User'` / `'Article'`），表名、字段、choices 保持不变，**不产生新迁移**。

自定义用户模型：`AUTH_USER_MODEL = 'blog.User'`。

| 文件 | 模型 |
| --- | --- |
| `user.py` | `User` |
| `catalog.py` | `Category`、`Tag` |
| `series.py` | `Series` |
| `article.py` | `ArticleQuerySet`、`Article`、`ArticleHistory`、`ArticleShare`、`ScheduledPost`、`ShortLink` |
| `comment.py` | `Comment`、`CommentReaction`、`CommentReport` |
| `interaction.py` | `FavoriteFolder`、`Favorite`、`Rating`、`ArticleBookmark`、`ReadingList`、`UserNote` |
| `logs.py` | `AccessLog`、`EditLog`、`LoginHistory` |
| `notification.py` | `Notification` |
| `badge.py` | `Badge`、`UserBadge`、`UserPoint`、`PointLog`、`UserAchievement` |
| `site.py` | `SiteInfo`、`SiteNotice`、`FriendlyLink` |
| `moderation.py` | `ModerationLog`、`ModerationSettings`、`PromotionRequest` |
| `messages.py` | `SiteMessage`、`SiteMessageRetired` |
| `social.py` | `UserFollow`、`UserProfile`、`UserActivity`、`UserBlock`、`UserMute`、`CategoryFollow`、`TagFollow`、`ContentReport` |
| `system.py` | `UserAPIKey`、`Webhook`、`UserDevice`、`ThemePreset`、`SearchHistory`、`ExportJob`、`UserWidget` |

### 5.1 关键模型约定

- **Article**（表 `blog_article`）：手动摘要字段是 **`excerpt_field`**（`excerpt` 是 `@property`）；
  含 `title / content / kind`(article/note/page) ` / status`(draft/pending/published) ` /
  published_at / is_pinned / is_featured / is_hot / views / likes / dislikes /
  comment_count / cover_image / password / series + series_order / is_deleted + deleted_at / rating_avg`。
- **Comment**（表 `blog_comment`）：`parent_comment`（`related_name='replies'`）、
  `is_approved / is_deleted + deleted_at / reported / likes / image / floor / is_folded`。
- **AccessLog**（表 `blog_access_log`）：IP 字段是 **`ip_address`**（`GenericIPAddressField`）；
  含 `username / session_key / path / full_url / method / status_code / duration_ms /
  referer / user_agent / browser / os / view_func / created_at`；
  索引 `created_at / ip_address / path`。
- **PromotionRequest**（表 `blog_promotion_request`）：`kind`(pin/feature/hot)、
  `status`(pending/approved/rejected)、`execution_status`(not_run/success/skipped/failed)、
  `execution_note / executed_at / handled_by / handled_at`。
- **ModerationSettings**（单例 pk=1）：`.load()`；`require_article_review /
  require_comment_review / comment_recall_minutes / max_pinned`；读取走缓存。
- **SiteInfo**（单例）：站名 / Logo emoji / 副标题 / SEO 描述与关键词 / 页脚 / ICP。

> 核对任何字段，以代码与 `docs/refactor_backup/models.py.bak` 为权威。

---

## 6. 核心实现细节

### 6.1 访问日志中间件（全局永久强制模块）★

> **不可删除、不可破坏。** 实现：
> `blog/middleware/access_log.py`（采集）、
> `blog/services/access_log_service.py`（投递通道 + 熔断）、
> `blog/tasks.py::save_access_log`（worker 落库）、
> `blog/management/commands/accesslog_queue.py`（兜底队列运维）。

**三层降级投递策略**

```
请求 → process_response 采集元信息（IP / 用户 / 路径 / 状态 / 耗时 / UA / 来源）
   │
   ├─ 层1 正常：save_access_log.delay(payload) ──► Redis broker ──► Celery worker ──► MySQL
   │        请求线程只做一次入队，**零数据库写入**；worker 未启动时任务安全滞留队列
   │
   ├─ 层2 Broker 故障（delay() 抛错）：RPUSH acgblog:access_log:fallback
   │        仍不写库；Broker 恢复后批量消费：
   │          python manage.py accesslog_queue --drain
   │        （Celery beat 周期自动跑 flush_access_log_queue 兜底补齐）
   │
   └─ 层3 极端降级（Redis 也写不进去）：同步 AccessLog.objects.create()
            仅此一层允许同步入库并打 ERROR，保证日志一条不丢
```

**性能 / 调参（在 settings.py，注释注明用途）**

| 参数 | 默认 | 作用 |
| --- | --- | --- |
| `ACCESS_LOG_ENABLED` | `1` | 总开关（强制模块，仅极端压测临时关闭） |
| `ACCESS_LOG_REDIS_TIMEOUT` | 0.35s | 单次 Redis 操作 socket 超时 |
| `ACCESS_LOG_REDIS_COOLDOWN` | 20.0s | Redis 失败后的熔断窗口（避免每请求白等超时） |
| `ACCESS_LOG_BROKER_COOLDOWN` | 15.0s | Broker 熔断窗口：投递失败后直接走兜底队列 |
| `ACCESS_LOG_FALLBACK_KEY` | `acgblog:access_log:fallback` | 兜底队列键名 |
| `ACCESS_LOG_FALLBACK_MAX_LEN` | 20000 | 队列长度上限（`LTRIM` 保留最新） |
| `ACCESS_LOG_FALLBACK_REDIS_URL` | 同 broker | 兜底队列专用地址，建议独立实例 / db |
| `ACCESS_LOG_DRAIN_BATCH` | 500 | 批量消费单批条数 |
| `CELERY_TASK_PUBLISH_RETRY` | `False` | 发布任务不重试，快速失败交给兜底队列 |
| `CELERY_BROKER_TRANSPORT_OPTIONS` | 0.4s | broker 连接 / 读写超时 |

> 设计目标：broker 宕机并熔断后，单请求耗时保持毫秒级，且故障期间数据库零写入。

`_is_asset()` 直接剔除 `/static/`、`/media/`、`favicon`、`robots.txt`，避免污染 PV/UV；
IP 合法性校验在 worker 与兜底消费两侧都做。

### 6.2 内容审核与 Django 信号

- 文章发布 / 编辑、评论新增**不可破坏信号**（内容审核、文章状态流转），也不能干扰访问日志采集。
- 写操作走 `save()/create()`，由信号决定是否进入待审、如何流转；勿绕过信号直接改状态。
- 缓存失效、计数重算、徽章 / 通知触发也统一在 `blog/signals.py`。

### 6.3 定时发布状态机

```
作者填写未来发布时间 → 保存为 draft（published_at = 预约时间）
        │  Celery beat 每分钟 check_scheduled_articles
        │  或  请求侧兜底扫描 maybe_sweep_due_articles()（缓存锁 + 最小间隔）
        ├─ 关闭「普通作者新文章需审核」→ published（直接发布）
        └─ 开启审核              → pending（待审核 + 写 ModerationLog）
                   │ 管理员通过
                   └─ published（published_at 对齐实际通过时刻）

可见性：作者 / 管理员可预览定时内容并显示状态条；
       其他登录用户 / 游客对未到点、草稿、待审核一律 404。
```

- 流转逻辑在 `blog/services/scheduled_publishing.py::process_due_articles()`，任务与兜底共用；
- 逐条 `save()` 而非 bulk `update()`，保证 `post_save` 信号（缓存失效 / 搜索 / 徽章）照常触发；
- 即使未启动 Celery beat，到点文章也会被请求侧扫描器在间隔内流转；
- 间隔与每轮上限：`SCHEDULED_SWEEP_INTERVAL` / `SCHEDULED_MAX_PER_ROUND`（settings）。

### 6.4 文案系统 `site_messages`

- 代码默认大字典 `MESSAGES`（位于 `blog/services/site_messages.py`），键名 `<域>.<语义>`。
- 取值函数 `msg(key, *args, **kwargs)` 优先级：**数据库覆盖 > 代码默认**；
  缺键返回 `⟪key⟫` 并 warning（**绝不因文案缺失导致 500**）；占位符用 `str.format`。
- 数据库覆盖整表缓存（key `v1:site_messages:overrides`，TTL 300s），
  靠 `MAX(updated_at)` 时间戳（节流 `SITE_MSG_DB_POLL_SECONDS=1.0`）实现 LocMemCache 跨进程失效。

| 层 | 用法 |
| --- | --- |
| 视图 | `msg('auth.login_failed')`、`msg('promo.limit_warn', 5, 5)`、`request.msg(...)` |
| 模板 | `{{ MSG.err.404_heading }}`、`{{ MSG.btn.back_home }}` |
| 前端 | `window.moeMsg('network_error')`、`window.SITE_MSG.network_error` |

- 文案总表页 `/console/site-messages/` 可搜索、按域分组、编辑保存。

### 6.5 权限反馈装饰器 `staff_required_moe` ★

Django 自带 `staff_member_required(login_url='/login/')` 底层 `user_passes_test` 对
「已登录但非员工」也重定向登录页，登录页又把已登录者弹回首页，导致作者点看板
莫名回首页、无提示。`blog/utils/decorators.py` 的 `staff_required_moe` 三段式：

1. 已登录 + active + is_staff → 放行；
2. 未登录 → `redirect_to_login` 跳 `/login/`，带安全 `next`；
3. 已登录非员工 → `raise PermissionDenied`，渲染萌系 `403.html`。

> 看板 / 站点设置 / 文案总表等员工页统一使用该装饰器。

### 6.6 推广申请：审批结论与系统执行分离

| 审批 `status` | 系统执行 `execution_status` | 展示 / 通知 |
| --- | --- | --- |
| 通过 | `success` | ✅ 通过 + ✅ 已执行 |
| 通过（名额满 / 未落地） | `skipped` | ✅ 通过 + ⏸ 未执行·已达上限 |
| 通过（写库异常） | `failed` | ✅ 通过 + ⚠️ 执行失败 |
| 驳回 | `not_run` | 🚫 已驳回 + ⏳ 未执行 |

- 详情页申请按钮三态：`applied`（已置顶，禁用）/ `pending`（审核中，禁用）/ `open`（可申请）。

### 6.7 缓存与失效

- 缓存键集中在 `blog/utils/cache_keys.py`，统一带版本前缀（`v{ver}:...`），bump 即全局失效；
- 详情页片段缓存（article / comment_tree / related / prevnext / 404 墓碑防穿透）；
  **只缓存「所有用户可见且一致」的数据**，登录态相关的点赞 / 收藏 / 可编辑按钮实时判定；
- 失效由信号统一驱动：`Article` / `Comment` 的 save / delete 收敛到 `invalidate_article(pk)`；
- 分级 TTL：短 60 / 中 300 / 长 3600。

### 6.8 内容安全

- 富文本入库前 `sanitize_html()`（bleach 白名单）；评论 `sanitize_comment()` 仅保留行内标签；
- `blog/utils/html_safety.py` 提供共享 CSS 净化（白名单）；
- 模板统一 `|escape` / `escapejs`；JSON-LD 转义 `<` `>`；
- 头像上传用 Pillow 校验真实图片 + 扩展名白名单 + 大小上限（2MB）。

### 6.9 前端主题与按钮交互

- `theme.js` + `base.html` 首帧内联脚本：`<html data-theme="dark">` 防闪烁；
  用户未手动选择时跟随系统 `prefers-color-scheme`。
- 按钮交互骨架：hover 上浮 + 渐变描边 + 柔和投影；active 下沉 + `scale(.98)`；
  选中渐变实心白字 + 内发光；禁用降饱和 + `not-allowed`；`:focus-visible` 焦点环；
  `prefers-reduced-motion` 取消位移；`@media (hover:none)` 触屏用 `:active` 替代 hover。
- 看板娘：`?waifu=off` 或 cookie `waifu_pref` 关闭，初始化脚本判定为 off 时不创建容器、不请求模型。

> ⚠️ **CSS 变量「静默失效」防护**：`background:var(--x)` 在 `--x` 未定义时整条声明静默失效，
> 可能产出「白底白字」不可用界面。故所有颜色 / 圆角 / 阴影 / 渐变令牌集中在 `base.css :root`
> （暗色在 `[data-theme="dark"]`），新增或改样式后用审计脚本核对未定义 / 跨作用域令牌。

---

## 7. 路由与 API 一览

### 7.1 前台页面（节选）

| 路径 | 说明 |
| --- | --- |
| `/` | 首页（?sort=hot 热门 / 默认最新） |
| `/register/` `/login/` `/logout/` | 注册 / 登录 / 登出 |
| `/new/` `/edit/<pk>/` `/my-articles/` | 发文 / 编辑 / 我的文章 |
| 文章详情（`detail.html`） | 含 TOC、评论、推广按钮 |
| `/series/` `/series/new/` `/series/<pk>/` | 系列列表 / 创建 / 详情 |
| `/categories/` `/category/<pk>/` | 分类总览 / 分类文章 |
| `/tags/` `/search/` `/archive/` | 标签 / 搜索 / 归档 |
| `/notifications/` `/favorites/` | 通知 / 收藏 |
| `/random/` `/status/` | 随机文章 / 状态页 |
| `/console/` | 看板（仅员工；非员工 403，游客登录） |
| `/console/site-settings/` `/console/site-messages/` `/console/moderation/` | 站点设置 / 文案总表 / 审核队列 |

### 7.2 API（节选）

| 路径 | 方法 / 权限 |
| --- | --- |
| `/api/categories/` | GET 公开；POST 需 staff（否则 403） |
| `/api/categories/<pk>/` | GET / PUT / DELETE（写需 staff） |
| `/api/articles/` `/api/comments/` | 文章 / 评论相关 |
| `/api/site-messages/` | 文案包 |
| `/api/refresh-assets/` | 资源刷新（需权限） |
| `/api/live2d/...` | 看板娘：models / get / switch / game |
| `/api/notifications/` | 通知列表 / 已读 |

### 7.3 约定

| 项 | 约定 |
| --- | --- |
| 前缀 | `/api/`（后续可加 `/api/v2/`） |
| 认证 | Session（浏览器）+ Basic（调试 / 客户端） |
| 权限 | 默认 `IsAuthenticatedOrReadOnly`，写操作按视图显式校验 |
| 分页 | `PageNumberPagination`，`PAGE_SIZE=10` |
| 错误信封 | `{'ok':False,'code':…,'message':…}`（错误页中间件统一生成） |

> 完整路由清单可用 `python manage.py routes_audit --list` 打印。

---

## 8. 环境要求与部署

### 8.1 环境要求

| 项 | 要求 |
| --- | --- |
| Python | 3.10+（本机解释器 `D:\Python\python.exe`） |
| MySQL | 8.x，字符集 `utf8mb4`，建议严格模式（默认库 `acgblog`） |
| Redis | 6/7（Celery broker、访问日志异步 / 兜底；未启动时中间件自动降级不丢日志） |
| 浏览器 | Chrome / Edge（含移动端） |

### 8.2 本地开发（Windows / 本机）

```powershell
# 1) 安装依赖
D:\Python\python.exe -m pip install -r requirements.txt

# 2) 建库
mysql -u root -p -e "CREATE DATABASE acgblog CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 3) 迁移 + 压缩静态 + 超级用户
D:\Python\python.exe manage.py migrate
D:\Python\python.exe manage.py refresh_assets
D:\Python\python.exe manage.py createsuperuser

# 4) 启动（多终端）
redis-server
D:\Python\python.exe manage.py runserver 127.0.0.1:8765
D:\Python\python.exe -m celery -A DjangoBlog worker --pool=solo -l info
D:\Python\python.exe -m celery -A DjangoBlog beat -l info   # 可选
```

本机 runserver（独立进程、不自动重载，改代码后需手动重启）：

```powershell
Start-Process -FilePath 'D:\Python\python.exe' `
  -ArgumentList 'manage.py','runserver','127.0.0.1:8765','--noreload' `
  -WorkingDirectory 'E:\Az_Code_E\ACGBlog' -WindowStyle Hidden
```

### 8.3 环境变量清单

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | 内置开发值 | **生产必须覆盖**为强随机串 |
| `DJANGO_DEBUG` | `1` | 生产置 `0` |
| `DJANGO_ENV` | development | 环境标识 |
| `DJANGO_MYSQL_*` | 见 settings | database / user / password / host / port |
| `CELERY_BROKER_URL` | redis://127.0.0.1:6379/0 | Celery broker |
| `CELERY_RESULT_BACKEND` | 同上 | 任务结果后端 |
| `ACCESS_LOG_FALLBACK_REDIS_URL` | 同 broker | 兜底队列专用 Redis，建议隔离 |
| `ACCESS_LOG_ENABLED` | `1` | 访问日志总开关（不建议关） |

### 8.4 生产部署

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py refresh_assets
```

**Gunicorn + Nginx 示例**

```bash
gunicorn DjangoBlog.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 60
celery -A DjangoBlog worker -l info
celery -A DjangoBlog beat -l info
```

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    client_max_body_size 25m;

    location /static/ { alias /srv/acgblog/staticfiles/; expires 30d; add_header Cache-Control "public, immutable"; }
    location /media/  { alias /srv/acgblog/media/; expires 7d; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # 访问日志取真实 IP
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

生产检查清单：`DEBUG=0` · 强随机 `SECRET_KEY` · `ALLOWED_HOSTS` 收紧 · TLS + 安全响应头 ·
MySQL 与 `media/` 备份 · Redis 持久化 · Celery worker / beat 常驻 · 兜底队列 Redis 隔离。

---

## 9. 运维手册（Celery / Redis / 兜底队列）

### 9.1 管理命令

| 命令 | 作用 |
| --- | --- |
| `refresh_assets` | 重压缩 CSS/JS、生成 `.gz`、写构建号、清缓存。`--only a,b` 只压指定；`--collect` 同时 collectstatic；`--token-only` 只更新版本号 |
| `accesslog_queue` | **访问日志兜底队列运维**：无参数=查看积压；`--drain` 批量入库；`--dry-run` 只统计；`--reset-circuit` 清熔断；`--purge --yes` 清空（危险） |
| `routes_audit` | 路由 / 视图审计：`--list` 全列；`--dead` 零引用死代码；`--stub` 占位视图；`--json` 导出 |
| `messages_audit` | 文案收敛审计：规模统计、未收编硬编码中文 |
| `security_test` | 安全自检（约 40~51 项）；`--category xss/sql/auth/accesslog` 分类 |
| `diag` | 综合诊断：配置 / 依赖 / 权限 / DB / 缓存 / Celery / 静态 / 慢查询 / N+1 等 |
| `data_maintain` | 数据维护：重建计数、清理临时数据、一致性修复 |
| `cache_bump` | 缓存版本号 bump（详情片段整体失效） |
| `seed_demo_stats` | 演示访问日志回填 |

### 9.2 Redis 与 Celery 启停

```powershell
# 启动顺序：Redis → MySQL → Web → Worker → Beat
redis-server
D:\Python\python.exe manage.py runserver 127.0.0.1:8765
D:\Python\python.exe -m celery -A DjangoBlog worker --pool=solo -l info   # Windows 必须 solo
D:\Python\python.exe -m celery -A DjangoBlog beat -l info

# 验证 worker
D:\Python\python.exe -m celery -A DjangoBlog inspect ping
# 停止：Ctrl+C 或结束对应进程
```

**Beat 定时任务（`settings.CELERY_BEAT_SCHEDULE`）**

| 任务 | 频率 | 作用 |
| --- | --- | --- |
| `check_scheduled_articles` | 每分钟 | 定时投稿到点流转 |
| `flush_access_log_queue` | 周期 | 兜底队列批量补齐 |
| `flush_buffered_views` | 每 5 分钟 | 阅读量缓冲落库 |
| `send_comment_digest` | 每 15 分钟 | 评论通知摘要邮件 |
| `clean_old_logs` | 每天 03:00 | 清理过期访问日志 |

### 9.3 访问日志降级演练（建议每季度）

```powershell
# 1) 制造 broker 故障（停 Redis 或改错 broker），观察熔断日志
# 2) 查看兜底队列积压
python manage.py accesslog_queue
# 3) 恢复 broker 后批量补录（beat 在线也会自动补齐）
python manage.py accesslog_queue --drain
# 4) 清残留熔断
python manage.py accesslog_queue --reset-circuit
# 队列长度（应为 0）
redis-cli LLEN acgblog:access_log:fallback
```

判定：①请求耗时毫秒级；②故障期 DB 零写入（层 2）；③恢复后日志 100% 入库。

### 9.4 日常巡检

| 频率 | 项目 |
| --- | --- |
| 每日 | 看板待办计数、访问趋势连续性；`accesslog_queue` 积压应为 0；日志中有无层 3 ERROR |
| 每周 | `check`、`diag --all`、`routes_audit`、`messages_audit`、`security_test` |
| 每月 | 磁盘 / `media` 体积、慢查询、Redis 内存、静态体积 |
| 发布前 | `check` + `security_test` + `refresh_assets` + 浏览器验收 |

### 9.5 备份与恢复

```powershell
mysqldump --single-transaction --default-character-set=utf8mb4 acgblog > blog_YYYYMMDD.sql
# media 备份：robocopy ... /MIR
# 恢复：建库 → 导入 SQL → 回灌 media → migrate → refresh_assets
```

### 9.6 故障排查速查

| 现象 | 排查方向 |
| --- | --- |
| 页面 500 | 终端 traceback / runserver 日志；`manage.py check`；`diag --db` |
| 访问日志缺失 | 兜底队列积压；worker 是否在线（`inspect ping`）；有无层 3 告警 |
| 首页数据不更新 | LocMemCache 进程内，多进程各自持有；`cache_bump` 或换 Redis 缓存 |
| 定时文章没发布 | beat 是否运行；`process_due_articles()` 手动验证；`published_at` |
| 静态资源没更新 | 是否 `refresh_assets`；浏览器硬刷新（构建号） |
| 改文案不生效 | 文案在 `services/site_messages.py`，重启 Web（模块常量） |
| requests 版本告警 | `diag --deps`；requirements 锁定 + deprecation_filters |

---

## 10. 测试与验收

### 10.1 硬性指标（每次交付全绿）

| 项目 | 命令 | 期望 |
| --- | --- | --- |
| 系统检查 | `python manage.py check` | 0 错误 0 警告 |
| 依赖告警 | `diag --deps` | 无 RequestsDependencyWarning |
| 安全测试 | `security_test` | 全部通过（含访问日志模块） |
| 路由 / 文案审计 | `routes_audit` / `messages_audit` | 0 占位 / 核心文案 100% 收编 |
| 访问日志 | `accesslog_queue` | 积压 0；三层降级演练通过 |
| 浏览器矩阵 | 见 10.2 | 多视口 × 亮暗，问题 0 |

### 10.2 浏览器 UI 视觉验收

- **三类用户：管理员 / 文章作者 / 游客**。
- 流程：注册、异常注册、登录、异常登录、发布文章、定时发布、创建系列、创建分类、
  系列中新增文章、分类中新增文章、多级评论、申请置顶 / 精华；访问异常路由与权限路由
  （看板）核对返回；同时观察看板计数、后台请求、访问日志是否完整记录 **用户、时间、路由**。
- 交互态：所有按钮 hover / 点击 / 选中；字体与背景符合二次元萌系。
- 矩阵：Chrome + Edge；桌面 + 移动；亮 / 暗双主题；视口 360/390/414/768/1024/1440/1920。
- 截图集：`docs/ui_screenshots/`（chrome / edge）。

> 规则：每修复单个问题即做一次 UI 验收；全部完成再做一次全量回归，防止后续改动破坏前面。

### 10.3 访问日志降级专项

- 正常：Worker 异步消费，队列归零、字段完整；
- Broker 故障：日志进兜底队列不丢，恢复后 `--drain` 入库；
- Redis 不可用：才同步入库。

---

## 11. 扩展开发指南

- **新增模型 / 字段**：在 `blog/models/` 对应领域文件添加（或新建文件并在 `__init__.py` 导出）；
  跨文件外键用字符串；`makemigrations` → `migrate`；在 `admin.py` 注册。
  纯新增向后兼容；改动既有字段 / 表关系前先评审影响面。
- **新增视图 / 路由**：在 `blog/views/` 对应文件实现（页面 render / 接口 DRF），
  `blog/urls.py` 注册并命名；员工页用 `staff_required_moe`；模板 `extends 'base.html'`，
  选中态用 `aria-current="page"`。
- **新增中间件**：`blog/middleware/` 新建独立文件，`__init__.py` 再导出，
  按「先请求后响应」顺序插入 settings.MIDDLEWARE。
  ⚠️ 访问日志中间件为永久强制模块，不可删除、破坏。
- **新增异步任务**：`blog/tasks.py` 用 `@shared_task`（异常兜底），需周期则在
  `CELERY_BEAT_SCHEDULE` 注册；任务须能在 Windows solo 池运行。
- **新增文案**：统一进 `services/site_messages.py::MESSAGES`（`<域>.<语义>`，萌系口吻），
  视图 `msg()`、模板 `MSG`、前端 `moeMsg()`；跑 `messages_audit`，禁止新写中文字面量提示。
- **新增前端样式 / 脚本**：优先在原 CSS/JS 文件内修改，避免模板内联；只引用 CSS 变量
  自动适配明暗；完成后 `refresh_assets --only <改动文件>` 并硬刷新。
- **新增主题**：在 `:root[data-theme="..."]` 增加令牌集合并在切换器登记。
- **新增徽章 / 成就**：`Badge` 配置条件与获取文案，触发点调用 `check_and_award_badges`。
- **注释要求**：自有 py / css / js 注释行数须大于代码行数，
  用 `docs/refactor_tools/comment_audit.py` 复核。
- **彩蛋 / 美化**：不改核心架构、不破坏日志与信号前提下可自由新增。

---

## 12. 安全约定

- 安全测试（约 40~51 项）通过、无漏洞回归；访问日志模块纳入安全测试，防信息泄露与注入。
- 评论 / 富文本用 bleach 白名单清洗；前端插入外部内容优先 `textContent`，防 XSS。
- 不记录密码、令牌等敏感信息；错误页不泄露堆栈与内部路径。
- 表单带 CSRF；权限页严格校验；`@csrf_exempt` 仅限明确必要接口。
- 依赖固定版本并及时升级；`DEBUG=False` 上线。

---

## 13. 工单变更历史

| 工单 | 主要内容 |
| --- | --- |
| **大规模重构（最新）** | ①常量收拢 settings.py 并注释来源/含义；②models.py 拆为 15 文件包（51 模型，`__init__` 统一导出，表结构不变、无新迁移）；③blog 根散落文件归入 services/utils 并修正跨模块 import；④三用户全流程 UI 视觉验收（亮/暗黑、按钮三态、Chrome+Edge、8 视口）；⑤所有自有 py/css/js 注释行数 > 代码行数；⑥README 完整重构；⑦全量回归 |
| views 包重构 | 单文件 views.py 按功能拆为 views/ 包，`__init__` 再导出兼容旧导入；修复 `content-visibility` 与窄屏溢出；三角色全流程 + 视口矩阵 + 安全测试全绿 |
| Bug9 | 定时投稿可见性与状态流转；徽章成就面板；文案后端变量化；路由 / 视图审计；按钮三态 |
| Bug8 | 注册内联校验；推广系统执行状态；访问日志三层降级；移动端底部操作条 |
| 更早 | 置顶 / 精华 / 热度权限与审核流；Round3~Round6 迭代；17 项 Bug + 健壮性增强 |

**已归档的无功能实现**：批量 echo 占位桩、自动生成的占位路由、无凭据第三方登录占位、
调试路由等，统一归档于 `docs/` 下归档目录（保留可追溯，不占产品代码）。

---

## 14. 常见问题 FAQ

**Q：改了 CSS/JS 页面没变化？**
A：模板引用 `.min` 文件，运行 `python manage.py refresh_assets` 并强刷（构建号自动更新）。

**Q：作者访问看板被弹回首页且无提示？**
A：已由 `staff_required_moe` 修复——非员工见萌系 403，游客跳登录。

**Q：定时文章没上线？**
A：确认 Worker / beat；未启动时 Web 兜底扫描，也可手动 `process_due_articles`。

**Q：访问日志会丢吗？**
A：不会。Celery 异步 → Redis 兜底队列（`accesslog_queue --drain`）→ 极端才同步入库。

**Q：Windows 下 Celery 报错？**
A：使用 solo 池：`celery -A DjangoBlog worker -l info -P solo`。

---

> 维护提示：访问日志中间件与 Django 信号为全局永久模块，任何重构都不得删除或破坏；
> 核心数据结构 / 底层架构变更需提前评估并配套迁移与回归。

🌸 愿这个小站也能让你写得开心、逛得治愈喵~
