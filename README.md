# 🌸 萌语博客 · MoeBlog

> 一个粉紫蓝萌系的二次元个人博客 / 内容社区。
> **Django 5.2 · DRF · MySQL 8 · Celery/Redis · WhiteNoise · Live2D · PWA**

柔和圆润、清新通透，自带看板娘、樱花花瓣、明暗双主题与一堆体验彩蛋；
内置完整的 **投稿 → 审核 → 发布 → 软删除 → 回收站** 运营闭环，
以及一个**全局永久强制**的访问日志中间件（三层降级投递，保证日志不丢且不阻塞请求）。

---

## 目录

1. [项目定位与设计语言](#1-项目定位与设计语言)
2. [功能总览](#2-功能总览)
3. [技术栈与架构](#3-技术栈与架构)
4. [目录结构](#4-目录结构)
5. [数据结构（48 个模型）](#5-数据结构48-个模型)
6. [核心实现细节](#6-核心实现细节)
7. [API 一览](#7-api-一览)
8. [环境要求与部署](#8-环境要求与部署)
9. [运维手册](#9-运维手册)
10. [扩展指南](#10-扩展指南)
11. [测试与验收](#11-测试与验收)
12. [工单变更历史](#12-工单变更历史)

---

## 1. 项目定位与设计语言

**定位**：二次元轻量萌系个人博客 / 内容社区，单应用（`blog`）承载全部业务。

| 维度 | 约定 |
| --- | --- |
| 主色 | 粉 `#ff8fb1`、紫 `#a06cd5`、蓝 `#6ea8fe`，点缀樱花粉 |
| 形态 | 大圆角（卡片 18px、胶囊 999px）、柔和投影、半透明玻璃拟态 |
| 质感 | 清新通透、留白充足、渐变克制 |
| 文案 | 全站中文 + 语气词「喵~」；**全部集中在后端文案注册表**（见 6.4） |
| 动效 | 樱花飘落、入场淡入、卡片悬浮、按钮回弹、看板娘互动 |
| 主题 | 明 / 暗双主题（含 AMOLED 纯黑档），一键切换并持久化 |
| 响应式 | 三栏（桌面）→ 单栏（移动），覆盖 360~1920 共 8 档视口 |
| 无障碍 | 跳过导航链接、`aria-*` 语义、`:focus-visible` 焦点环、`prefers-reduced-motion` 降动效 |

设计令牌（Design Token）统一用 CSS 自定义属性维护，明暗主题分别在 `:root` 与
`:root[data-theme="dark"]` 下定义；全站组件只引用变量、不写死颜色。

---

## 2. 功能总览

### 内容与阅读
- 文章列表（最新 / 热门）、置顶 / 精华 / 热门徽章、NEW / HOT 角标
- 文章详情：目录 TOC（可拖动 / 可导出 Markdown）、阅读进度条、字数与预计阅读时长、上一篇 / 下一篇
- 专注阅读模式、阅读设置（字号 / 行距 / 配色）、TTS 朗读、阅读进度记忆
- 导出能力：全文复制、Markdown、PDF、打印；分享卡片 + 二维码 + 短链
- 封面图智能布局（封面 → 正文首图 → 无图文字填充），预览图固定在卡片侧
- 分类、标签（标签云可拖动 + 索引 + 排行榜）、系列（连载 + 序号）、归档
- 文章访问密码（哈希存储）、文章评分（1~5 星）

### 互动社区
- 多级评论（楼中楼：仅第一层缩进、后续层级不重复右移）、评论点赞 / 表情回应
- 评论可在设定时限内撤回（软删除）；评论举报与处理
- 文章点赞 / 踩、收藏（收藏夹分组）、关注（用户 / 分类 / 标签）、黑名单与静音
- @提及、回复通知、站内通知中心（铃铛下拉 + 独立页面）、评论摘要邮件（Celery 异步）
- 徽章 / 成就（**个人中心可视化面板**：已获得置顶、未获得折叠可展开、含获取方式与实时进度）
- 积分体系、用户主页、个性签名、用户笔记、阅读历史、登录历史、API Key

### 运营与治理
- **投稿审核闭环**：普通作者投稿进入「待审核」，管理员通过 / 驳回（驳回退回草稿并通知作者）
- **定时投稿**：预约未来时间 → 到点按审核开关流转为「待审核」或「已发布」；
  作者 / 管理员可预览定时内容（不 404），其他人与游客不可见
- **推广申请（置顶 / 精华 / 热门）**：作者发起申请 → 管理员审批 →
  **审批结论与「系统执行状态」分离记录**（名额已满时明确显示「未执行·已达上限」并通知作者）
- **软删除 + 回收站**：文章 / 评论删除先进回收站，可恢复或彻底删除
- **审核日志 `ModerationLog`**：提交 / 通过 / 驳回 / 软删 / 恢复 / 彻底删除全程留痕
- 运营看板：实时统计、14 天访问趋势、热门文章 Top、分类分布、待办计数
- **站点设置（`SiteInfo` 单例）**：站名 / Logo / 副标题 / SEO 描述关键词 / 页脚文案在线编辑
- 一键刷新静态压缩与缓存（管理命令 + 看板按钮 + API）
- **访问日志中间件**（全局永久强制模块）：异步优先 → Redis 兜底队列 → 极端同步

### 前端体验
- Live2D 看板娘：多套模型 / 服装、对话气泡、工具栏、猜拳小游戏；
  支持 `?waifu=off` 关闭，并尊重系统「减少动态效果」偏好
- 樱花花瓣、粒子背景、Konami 彩蛋、404「接樱花」小游戏
- 全站统一 `moeToast` 轻提示与 `moeConfirm` 确认弹窗（**零原生 alert / confirm**）
- PWA：manifest、Service Worker、可安装、可离线
- 静态资源自动压缩（CSS/JS minify、去注释）、构建号破缓存、`.gz` 预压缩（WhiteNoise 直发）
- 全站按钮交互骨架（hover 上浮 + 渐变描边 / active 下沉缩放 / 选中粉紫渐变白字 /
  禁用降饱和 / 键盘焦点环 / 触屏与降动效适配）

---

## 3. 技术栈与架构

### 3.1 技术选型

| 层 | 技术 | 版本 | 说明 |
| --- | --- | --- | --- |
| Web 框架 | Django | 5.2.17 | 单 app（`blog`）承载全部业务 |
| API | djangorestframework | 3.15.2 | 通知 / 评论 / 点赞 / 功能开关等 JSON API |
| 数据库 | mysqlclient + MySQL 8 | 2.2.7 | 库名 `Blog_new`，字符集 `utf8mb4`，严格模式 `STRICT_TRANS_TABLES` |
| 异步任务 | Celery + Redis | 5.3.1 / 5.2.1 | broker `redis://127.0.0.1:6379/0` |
| 缓存 | Django LocMemCache | 内置 | 默认 300s；**进程内**，多进程部署需换 Redis 缓存后端 |
| 静态托管 | WhiteNoise | 6.12.0 | 生产压缩（Manifest）+ 长期缓存 |
| 图片处理 | Pillow | 10.3.0 | 封面 / 头像裁剪 / 校验 |
| HTML 净化 | bleach | 6.4.0 | 富文本与评论白名单清洗（配合 `html_safety.py`） |
| 搜索 / 导出 | pypinyin / html2text / qrcode / xhtml2pdf | — | 拼音搜索、MD / PDF 导出、二维码 |
| 富文本 | CKEditor 4（本地静态） | — | 无需 pip 安装 |
| 看板娘 | Live2D（本地静态） | — | `static/assets/live2d` |

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
│  URL Router（page 路由 + /api/ 路由）                                 │
│        │                                                              │
│        ▼                                                              │
│  Views（blog/views.py：函数视图 + DRF 类视图）                        │
│        │                                                              │
│        ├──► Templates（42 个模板 + MSG 文案命名空间）                  │
│        ├──► DRF Serializers（JSON）                                   │
│        └──► 领域模块：scheduled_publishing / live2d / html_safety /   │
│                       site_messages / cache_keys                      │
└───────┬──────────────────────┬───────────────────────┬───────────────┘
        ▼                      ▼                       ▼
   MySQL 8 (48 张表)      LocMem Cache           Static / Media 磁盘
        ▲                  （分片 TTL）                  ▲
        │                                                 │
┌───────┴──────────────────────┐              WhiteNoise（生产托管 + .gz）
│ Celery Worker / Beat（可选）  │  Broker: Redis 6379/0
│  访问日志入库 / 定时投稿流转 / │  Result: Redis 6379/0
│  日志清理 / 邮件摘要 / 兜底补齐 │
└──────────────────────────────┘
```

**分层约定**

| 层 | 职责 | 位置 |
| --- | --- | --- |
| 中间件 | 横切关注点：日志采集、站点信息、文案注入、看板娘开关、错误页 | `blog/middleware/*.py`（一个中间件一个文件） |
| 上下文处理器 | 向所有模板注入公共数据（导航 / 侧栏 / 统计 / 文案 / 构建号） | `blog/context_processors.py` |
| 领域模块 | 可复用的业务逻辑，供视图与任务共用 | `blog/scheduled_publishing.py`、`blog/access_log_service.py`、`blog/html_safety.py`、`blog/site_messages.py`、`blog/live2d.py` |
| 视图 | 页面渲染与 API 响应 | `blog/views.py`（3683 → 约 5200 行，含审核 / 看板 / 回收站） |
| 异步任务 | 不阻塞请求的副作用 | `blog/tasks.py` |
| 信号 | 模型状态变化的副作用（缓存失效 / 计数重算 / 徽章 / 通知） | `blog/signals.py` |

---

## 4. 目录结构

```
ACGBlog/
├── manage.py                          # Django 入口
├── requirements.txt                   # 精确锁定的依赖
├── README.md                          # 本文档
├── DjangoBlog/                        # 项目配置包
│   ├── settings.py                    # 全局设置（安全 / DB / 缓存 / 静态 / Celery / 日志）
│   ├── urls.py                        # 根路由（挂载 blog.urls）
│   ├── celery.py                      # Celery 应用
│   └── wsgi.py / asgi.py
├── blog/                              # 唯一业务应用
│   ├── models.py                      # 48 个模型（1432 → 约 1900 行）
│   ├── views.py                       # 页面视图 + API + 审核 / 看板 / 回收站 / 功能开关注册表
│   ├── urls.py                        # 应用路由（页面 + /api/）
│   ├── serializers.py                 # DRF 序列化器
│   ├── middleware/                    # 中间件包（一个中间件一个文件）
│   │   ├── access_log.py              #   ★ 访问日志（全局永久强制模块，三层降级）
│   │   ├── site_messages.py           #   文案注入（request.msg）
│   │   ├── site_info.py               #   站点信息单例
│   │   ├── mascot.py                  #   看板娘开关（?waifu=on/off）
│   │   ├── cute_error_pages.py        #   萌系错误页 400/403/404/500
│   │   ├── online_status.py           #   在线状态
│   │   ├── slow_query.py              #   慢 SQL 日志过滤器
│   │   └── __init__.py                #   统一再导出（兼容 blog.middleware.X 写法）
│   ├── context_processors.py          # 导航 / 侧栏 / 页脚统计 / 偏好 / 文案 / 构建号
│   ├── site_messages.py               # ★ 全站文案注册表（286 条 / 19 域）
│   ├── scheduled_publishing.py        # ★ 定时投稿状态流转（任务 + 请求侧兜底扫描）
│   ├── access_log_service.py          # ★ 访问日志投递通道（Redis 兜底队列 + 熔断）
│   ├── cache_keys.py                  # 缓存 key 集中管理（带版本前缀）
│   ├── html_safety.py                 # 共享 HTML/CSS 净化（MoeCSSSanitizer）
│   ├── live2d.py                      # 看板娘端点 /api/live2d/
│   ├── deprecation_filters.py         # 消除 requests 依赖版本告警
│   ├── tasks.py                       # Celery 任务
│   ├── signals.py                     # 模型信号
│   ├── admin.py                       # 自定义后台（13 个模型 + 定制 AdminSite）
│   ├── features_live2d.py             # 【已删除】内容迁至 live2d.py
│   ├── features_round5/               # 【已删除】内容迁至 views.py / urls.py
│   ├── management/commands/           # 管理命令（见 9.1）
│   ├── migrations/                    # 18 个迁移（最新 0018）
│   └── templatetags/
│       ├── blog_extras.py             # is_new / time_ago / time_until / highlight /
│       │                              #   lazy_images / smart_page_range / body_first_image /
│       │                              #   file_url / portable_media
│       └── search_extras.py
├── templates/                         # 42 个模板
│   ├── base.html                      # 全站骨架（导航 / 弹窗 / 文案包 / 看板娘开关 / SW）
│   ├── 400.html 403.html 404.html 500.html   # 萌系错误页（文案取自 MSG）
│   ├── rss.xml / sitemap.xml          # 订阅与站点地图
│   ├── partials/                      # 可复用片段
│   │   ├── _article_card.html         #   文章卡片
│   │   ├── _comment_item.html         #   评论项（含楼中楼）
│   │   ├── _badge_panel.html          #   徽章 / 成就面板
│   │   ├── _auth_bg.html              #   认证页共享背景
│   │   ├── _hot_list.html             #   热门列表
│   │   ├── _pagination.html           #   分页器
│   │   └── _seo_meta.html             #   SEO meta
│   └── blog/                          # 27 个页面模板
│       ├── index.html detail.html edit.html password_gate.html
│       ├── categories.html tags.html archive.html
│       ├── series_list.html series_detail.html series_form.html
│       ├── login.html register.html
│       ├── user_profile.html user_settings.html
│       ├── console.html moderation.html site_settings.html status.html
│       ├── notifications.html favorites.html my_collection.html my_articles.html
│       ├── my_comments.html liked_articles.html reading_history.html reading_history_page.html
│       └── api_docs.html
├── static/assets/
│   ├── css/                           # 33 个源样式（编译产物 .min.css + .gz）
│   │   ├── ui_polish.css              #   页面增强 + 按钮交互骨架（最大，约 95KB）
│   │   ├── round6.css                 #   Round6 交互（含推广 / 审核状态样式）
│   │   ├── components.css             #   通用组件
│   │   ├── blog.css                   #   文章 / 列表布局
│   │   ├── base.css                   #   设计令牌与基础元素
│   │   ├── profile.css                #   个人中心（含徽章面板）
│   │   ├── moderation_inline.css      #   审核页
│   │   ├── error400/403/404/500.css   #   错误页（自包含，不依赖 base）
│   │   └── …
│   ├── js/                            # 52 个源脚本（44 个顶层 + 8 个 features/，编译产物 .min.js + .gz）│   │   ├── common.js                  #   ★ 核心：moeToast / moeConfirm / 通用工具
│   │   ├── moe-messages.js            #   ★ 文案访问层（window.SITE_MSG / moeMsg）
│   │   ├── auth_inline.js             #   ★ 认证表单免刷新 + 内联红字校验
│   │   ├── round6.js                  #   FAB 菜单 / 榜单切换 / 推广按钮三态
│   │   ├── comments.js / like.js / features.js / toc.js
│   │   ├── features/                  #   分域脚本（effects / interaction / reading /
│   │   │                              #     profile / search / tools / settings_prefs）
│   │   └── …
│   ├── icons/ images/ img/            # 图标与占位插图
│   ├── live2d/                        # 看板娘：引擎、模型、服装、初始化脚本
│   ├── ckeditor/                      # 本地富文本编辑器
│   └── .build_token                   # 构建号（模板 ?v={{ BUILD_TOKEN }} 破缓存）
├── staticfiles/                       # collectstatic 产物（生产）
├── media/                             # 用户上传（avatars / covers / uploads）
└── docs/                              # 全部文档与验收产物（临时文件统一放这里）
    ├── bugfix_20260926_bug9/          # 最新工单：修改清单 / 验证报告 / 脚本 / 截图
    ├── bugfix_20260925_bug8/          # 上一工单
    ├── bugfix_ticket5/ · bug1/ · bug11/ · bug12/  # 历史工单
    ├── archived_feature_stubs/        # 已归档的无功能占位实现
    ├── qa_profiles/ qa_screenshots/   # 历史浏览器验收 profile 与截图
    └── reference/                     # 参考实现
```

---

## 5. 数据结构（48 个模型）

全部模型位于 `blog/models.py`，自定义用户模型 `AUTH_USER_MODEL = 'blog.User'`。
按业务域分组如下（括号内为数据库表名）：

### 5.1 内容核心

| 模型 | 表 | 关键字段与说明 |
| --- | --- | --- |
| `Article` | `blog_article` | 28 字段。`title` / `content`(富文本) / `excerpt_field` / `kind`(article/note/page) / `status`(draft/pending/published) / `published_at`(定时) / `is_pinned`·`is_featured`·`is_hot` / `views`·`likes`·`dislikes`·`comment_count`·`share_count` / `cover_image` / `password`(访问密码哈希) / `series`+`series_order` / `is_deleted`+`deleted_at`(软删除)；索引 `idx_art_status_ct`、`idx_art_feat_ct`、`idx_art_hot_ct` |
| `Category` | `blog_category` | 名称 / 图标 / 描述 / 排序 |
| `Tag` | `blog_tag` | 标签名（唯一） |
| `Series` | `blog_series` | 系列标题 / 封面 / 简介 / 作者 |
| `Comment` | `blog_comment` | 13 字段。`parent_comment`(楼中楼) / `is_approved`(审核) / `is_deleted`+`deleted_at`(撤回/软删) / `reported` / `likes` / `image` / `floor`(楼层) |
| `EditLog` | `blog_edit_log` | 修改记录 + `content_snapshot`（版本对比） |
| `Rating` | `blog_rating` | 1~5 星，`unique_together(user, article)` |
| `ShortLink` | `blog_short_link` | 分享短链 |
| `ArticleShare` | `blog_article_share` | 分享渠道计数 |

### 5.2 互动与用户成长

| 模型 | 表 | 说明 |
| --- | --- | --- |
| `User` | `blog_user` | 29 字段。继承 `AbstractUser`；`nickname` / `avatar` / `introduction` / `last_active` / 偏好字段等 |
| `UserProfile` | `blog_user_profile` | 扩展资料 |
| `Favorite` / `FavoriteFolder` | `blog_favorite` / `blog_favorite_folder` | 收藏与收藏夹分组 |
| `ArticleBookmark` / `ArticleHistory` | — | 书签与阅读历史 |
| `ReadingList` | `blog_reading_list` | 阅读清单 |
| `Notification` | `blog_notification` | 站内通知（类型 / 已读 / 关联 URL） |
| `Badge` / `UserBadge` | `blog_badge` / `blog_user_badge` | 徽章定义（`condition_type` × `condition_value`）与获得记录 |
| `UserAchievement` / `UserPoint` / `PointLog` | — | 成就 / 积分余额 / 积分流水 |
| `UserFollow` / `CategoryFollow` / `TagFollow` | — | 关注关系 |
| `UserBlock` / `UserMute` | — | 黑名单 / 静音 |
| `UserNote` | `blog_user_note` | 用户笔记 |
| `UserActivity` | `blog_user_activity` | 行为流水 |
| `UserDevice` / `LoginHistory` | — | 设备与登录历史 |
| `UserAPIKey` / `Webhook` | — | 开放接口凭据与回调 |
| `UserWidget` / `ThemePreset` | — | 个人主页组件与主题预设 |
| `CommentReaction` | `blog_comment_reaction` | 评论表情回应 |
| `SearchHistory` | `blog_search_history` | 搜索历史 |
| `ExportJob` | `blog_export_job` | 导出任务 |

### 5.3 运营与治理

| 模型 | 表 | 说明 |
| --- | --- | --- |
| `ModerationLog` | `blog_moderation_log` | 审核动作留痕（SUBMIT / APPROVE / REJECT / SOFT_DELETE / RESTORE / HARD_DELETE / PIN / UNPIN / FEATURE / UNFEATURE / HOT / UNHOT） |
| `ModerationSettings` | `blog_moderation_settings` | **单例(pk=1)**：`require_article_review` / `require_comment_review` / `comment_recall_minutes` / `max_pinned`；读取走缓存 |
| `PromotionRequest` | `blog_promotion_request` | 推广申请：`kind`(pin/feature/hot) / `status`(pending/approved/rejected) / **`execution_status`**(not_run/success/skipped/failed) / `execution_note` / `executed_at` / `handled_by` / `handled_at` |
| `CommentReport` / `ContentReport` | — | 举报 |
| `ScheduledPost` | `blog_scheduled_post` | 定时发布辅助记录 |
| `SiteInfo` | `blog_site_info` | **单例**：站名 / Logo emoji / 副标题 / SEO 描述与关键词 / 页脚关于 / ICP / 版权方 |
| `SiteNotice` | `blog_site_notice` | 全站公告（可关闭，cookie 记忆） |
| `FriendlyLink` | `blog_friendly_link` | 友情链接 |
| `AccessLog` | `blog_access_log` | 18 字段：IP / 用户 / 会话 / 路径 / 完整 URL / 方法 / 状态码 / 耗时 / 来源 / UA / 浏览器 / 系统 / 视图名；索引在 `(created_at)`、`(path)`、`(user)` 上 |

---

## 6. 核心实现细节

### 6.1 访问日志中间件（全局永久强制模块）★

> **本模块不可删除、不可破坏。** 实现：`blog/middleware/access_log.py`（采集）、
> `blog/access_log_service.py`（投递通道）、`blog/tasks.py::save_access_log`（worker 落库）、
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
   │        （Celery beat 每 5 分钟自动跑 flush_access_log_queue 兜底补齐）
   │
   └─ 层3 极端降级（Redis 也写不进去）：同步 AccessLog.objects.create()
            仅此一层允许同步入库，并打 ERROR 告警；保证日志一条不丢
```

**性能约束（关键设计）**

| 参数 | 默认 | 作用 |
| --- | --- | --- |
| `ACCESS_LOG_REDIS_TIMEOUT` | 0.35s | 单次 Redis 操作 socket 超时 |
| `ACCESS_LOG_REDIS_COOLDOWN` | 20.0s | Redis 失败后的熔断窗口（避免每请求白等超时） |
| `ACCESS_LOG_BROKER_COOLDOWN` | 15.0s | **Broker 熔断窗口**：投递失败后直接走兜底队列，不再尝试连 broker |
| `ACCESS_LOG_FALLBACK_KEY` | `acgblog:access_log:fallback` | 兜底队列键名 |
| `ACCESS_LOG_FALLBACK_MAX_LEN` | 20000 | 兜底队列长度上限（`LTRIM` 保留最新） |
| `ACCESS_LOG_FALLBACK_REDIS_URL` | 同 broker | **兜底队列专用地址，建议独立实例 / db** |
| `ACCESS_LOG_DRAIN_BATCH` | 500 | 批量消费单批条数 |
| `ACCESS_LOG_ENABLED` | `1` | 总开关（强制模块，仅极端压测时临时关闭） |
| `CELERY_TASK_PUBLISH_RETRY` | `False` | 发布任务不重试，快速失败交给兜底队列 |
| `CELERY_BROKER_TRANSPORT_OPTIONS` | 0.4s | broker 连接 / 读写超时，超时不重试 |

> 实测：broker 宕机时单请求耗时从 **6218ms 降到 45ms**（未熔断 vs 熔断后），
> 且该期间数据库零写入、日志全部进入兜底队列。

`_is_asset()` 直接剔除 `/static/`、`/media/`、`favicon`、`robots.txt`，避免污染 PV/UV；
IP 合法性校验在 worker 与兜底消费两侧都做。

### 6.2 定时投稿状态机

```
作者填写未来发布时间 → 保存为 draft（published_at = 预约时间）
        │  Celery beat 每分钟 check_scheduled_articles
        │  或  请求侧兜底扫描 maybe_sweep_due_articles()（缓存锁 + 30s 最小间隔）
        ├─ 关闭「普通作者新文章需审核」→ published（直接发布）
        └─ 开启审核              → pending（待审核 + 写 ModerationLog）
                   │ 管理员通过（moderate_article）
                   └─ published（published_at 对齐实际通过时刻）

可见性（_base_qs）：作者 / 管理员预览 → 可见定时内容并显示状态条；
                   其他登录用户 / 游客 → 定时未到点、草稿、待审核一律 404
```

- 流转逻辑收敛在 `blog/scheduled_publishing.py::process_due_articles()`，任务与兜底共用；
- 逐条 `save()` 而非 bulk `update()`，保证 `post_save` 信号（缓存失效 / 搜索 / 徽章）照常触发；
- 即使部署环境**没启动 Celery beat**，到点文章最迟 30 秒内也会被请求侧扫描器流转。

### 6.3 推广申请：审批结论与系统执行分离 ★

| 审批 `status` | 系统执行 `execution_status` | 审核页展示 | 作者通知 |
| --- | --- | --- | --- |
| 通过 | `success` | ✅ 审批通过 + ✅ 系统已执行 | 「你的X申请已通过」 |
| 通过（名额已满 / 未落地） | `skipped` | ✅ 审批通过 + ⏸ 未执行·已达上限 + 执行说明 | 「已通过（暂未生效）」+ 原因 |
| 通过（写库异常） | `failed` | ✅ 审批通过 + ⚠️ 执行失败 | 「已通过（暂未生效）」 |
| 驳回 | `not_run` | 🚫 已驳回 + ⏳ 未执行 | 「你的X申请未通过」 |

- 待审阶段即显示「通过前预判」（名额是否充足）；
- 审核页顶部有「🛠 系统执行状态」总览条（三类计数 + 当前置顶 n/m）；
- 详情页申请按钮三态：`applied`（已经置顶，禁用）/ `pending`（审核中，禁用）/ `open`（可申请）；
  提交后前端立即切「审核中」，并调用 `GET /api/article/<pk>/promotion-status/` 与服务端对齐。

### 6.4 全站文案注册表 ★

**唯一登记处**：`blog/site_messages.py::MESSAGES`（**286 条 / 19 域**，键名 `<域>.<语义>`）。

| 层 | 用法 | 实现 |
| --- | --- | --- |
| 视图 | `msg('auth.login_failed')`、`msg('promo.limit_warn', 5, 5)`、`request.msg(...)` | `site_messages.msg()`；`SiteMessagesMiddleware` 注入 `request.msg` |
| 模板 | `{{ MSG.err.404_heading }}`、`{{ MSG.btn.back_home }}` | `context_processors.site_messages_ctx` 注入 `MSG`（按域分组 + 全路径） |
| 前端 | `window.moeMsg('network_error')`、`window.SITE_MSG.network_error` | `base.html` 内嵌 `json_script` 文案包 → `moe-messages.js`；离线可 `moeMsgRefresh()` 走 `/api/site-messages/` |

- 缺 key 时返回 `⟪key⟫` 占位并打 warning，**绝不因文案缺失导致 500**；
- 域分布：auth 39 / err 35 / promo 25 / nav 22 / empty 17 / article 15 / comment 15 /
  moderation 15 / interact 15 / badge 15 / btn 14 / js 13 / 其余（brand / form / search /
  user / notify / live2d / misc）。

### 6.5 缓存与失效

- 缓存键集中在 `blog/cache_keys.py`，统一带版本前缀（`v{ver}:...`），bump 版本即全局失效；
- 详情页片段缓存：`article` / `comment_tree` / `related` / `related_weighted` / `prevnext` /
  `missing`(404 墓碑，防穿透)；**只缓存「所有用户可见且一致」的数据**，
  登录态相关的点赞 / 收藏 / 评分 / 可编辑按钮实时判定；
- 失效由信号统一驱动：`Article` / `Comment` 的 `post_save` / `post_delete` 全部收敛到
  `invalidate_article(pk)`；新建 / 删除文章额外 `purge_prevnext()`；
- 分级 TTL：`CACHE_TTL_SHORT=60` / `MEDIUM=300` / `LONG=3600`。

### 6.6 内容安全

- 富文本入库前 `sanitize_html()`（bleach 白名单）；评论 `sanitize_comment()` 仅保留行内标签；
- `blog/html_safety.py` 提供共享 `MoeCSSSanitizer`（bleach CSS 白名单），
  消除 `NoCssSanitizerWarning`；
- 模板侧统一 `|escape` / `escapejs`；JSON-LD 通过 `_safe_jsonld()` 转义 `<` `>`；
- 头像上传用 Pillow 校验真实图片 + 扩展名白名单 + 大小上限（2MB）。

### 6.7 前端主题与交互

- `theme.js` + `base.html` 首帧内联脚本：`<html data-theme="dark">` 防闪烁；
  用户未手动选择时跟随系统 `prefers-color-scheme`；
- 全站统一 `moeToast(msg, type)` / `moeConfirm({...})`，并支持声明式
  `<form data-confirm="...">` 委托拦截（**零原生 alert/confirm**）；
- 按钮交互骨架：hover 上浮 1px + 渐变描边 + 柔和投影；
  active 下沉 1px + `scale(.98)`；选中粉紫蓝渐变实心白字 + 内发光（`!important` 兜底历史样式）；
  禁用降饱和 + `not-allowed`；`:focus-visible` 焦点环；
  `prefers-reduced-motion` 取消位移；`@media (hover: none)` 触屏用 `:active` 替代 hover；
- 看板娘：`<html data-waifu="on|off">` 由 `MascotToggleMiddleware` 依据
  `?waifu=off` 或 cookie `waifu_pref` 写入，`waifu-init-new.js` 判定为 off 时不初始化
  （不创建容器、不请求模型）；同时尊重「减少动态效果」偏好。

---

## 7. API 一览

**全站共 186 条路由**：89 条 admin、49 条 `/api/`、11 条 `/console/` 运营路由，其余为前台页面路由。

### 7.1 约定

| 项 | 约定 |
| --- | --- |
| 前缀 | `/api/`（版本边界，后续可加 `/api/v2/`） |
| 认证 | Session（浏览器）+ Basic（调试 / 客户端） |
| 权限 | 默认 `IsAuthenticatedOrReadOnly`；写操作按视图显式校验 |
| 分页 | `PageNumberPagination`，`PAGE_SIZE = 10` |
| 时间格式 | `%Y-%m-%d %H:%M:%S` |
| 错误信封 | `{'ok': False, 'code': 4xx/5xx, 'message': '…'}`（错误页中间件统一生成） |

### 7.2 端点分组（节选）

| 分组 | 代表端点 |
| --- | --- |
| 文章 | `/api/article/<pk>/like/`、`/comment/`、`/share/`、`/promotion-request/`、`/promotion-status/`、`/toggle-promotion/` |
| 分类 / 标签 | `/api/categories/`、`/api/categories/<pk>/`、`/api/tags/`、`/api/tags/<pk>/` |
| 通知 | `/api/notifications/`（列表 / 单条已读 / 全部已读） |
| 用户 | `/api/user/preferences/`、`/api/user/badges/`、`/api/online_users/` |
| 看板娘 | `/api/live2d/models/`、`/get/`、`/model/<model>/<skin>.json`、`/switch_model/`、`/rand_model/`、`/switch_skin/`、`/rand_skin/`、`/game/` |
| 功能开关 | `GET /api/round5/features/`、`POST /api/round5/features/<feature_id>/toggle/`（staff） |
| 站点 | `GET /api/site-messages/`（文案包）、`POST /api/refresh-assets/`（staff） |
| 搜索 | 搜索建议（支持拼音） |

> 完整路由清单可用 `python manage.py routes_audit --list` 打印，
> 或看机器可读报告 `docs/bugfix_20260926_bug9/routes_inventory.json`。

---

## 8. 环境要求与部署

### 8.1 环境要求

| 项 | 要求 |
| --- | --- |
| 操作系统 | Windows 10/11（开发）/ Linux（生产）均可 |
| Python | 3.10+（开发环境为 3.10） |
| MySQL | 8.x，字符集 `utf8mb4`，建议开启 `STRICT_TRANS_TABLES` |
| Redis | 6/7（访问日志异步投递、兜底队列、Celery broker 必需；未启动时中间件自动降级不丢日志） |
| 浏览器 | Chrome / Edge（含移动端） |

> **开发环境路径约定**（本机）：Python 解释器 `D:\Python\python.exe`，项目 `E:\Az_Code_E\ACGBlog`。

### 8.2 本地开发

```powershell
# 1) 安装依赖
D:\Python\python.exe -m pip install -r requirements.txt

# 2) 创建数据库（MySQL 8）
mysql -u root -p -e "CREATE DATABASE Blog_new CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 3) 可选：用环境变量覆盖默认连接参数（默认值见 settings.py）
$env:DJANGO_DEBUG='1'
$env:DJANGO_MYSQL_DATABASE='Blog_new'
$env:DJANGO_MYSQL_USER='root'
$env:DJANGO_MYSQL_PASSWORD='你的密码'
$env:DJANGO_MYSQL_HOST='127.0.0.1'
$env:DJANGO_MYSQL_PORT='3306'

# 4) 迁移 + 打包静态 + 建超级用户
D:\Python\python.exe manage.py migrate
D:\Python\python.exe manage.py refresh_assets      # 压缩 CSS/JS、写构建号、清缓存
D:\Python\python.exe manage.py createsuperuser

# 5) 启动（三个终端）
redis-server
D:\Python\python.exe manage.py runserver 127.0.0.1:8033
D:\Python\python.exe -m celery -A DjangoBlog worker --pool=solo -l info
# 可选：定时任务调度（定时投稿流转 / 兜底队列补齐 / 日志清理）
D:\Python\python.exe -m celery -A DjangoBlog beat -l info
```

访问 `http://127.0.0.1:8033/`；后台 `/admin/`，运营看板 `/console/`，内容审核 `/console/moderation/`。

### 8.3 环境变量清单

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | 内置开发值 | **生产必须覆盖**为强随机串 |
| `DJANGO_DEBUG` | `1` | 生产置 `0`（同时启用 Service Worker 与 WhiteNoise 压缩存储） |
| `DJANGO_ENV` | `development` | 环境标识 |
| `DJANGO_MYSQL_*` | 见 settings | 数据库连接（database / user / password / host / port） |
| `CELERY_BROKER_URL` | `redis://127.0.0.1:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | 同上 | 任务结果后端 |
| `ACCESS_LOG_FALLBACK_REDIS_URL` | 同 broker | **兜底队列专用 Redis，建议独立实例 / db** |
| `ACCESS_LOG_ENABLED` | `1` | 访问日志总开关（强制模块，不建议关闭） |

### 8.4 生产部署

```powershell
$env:DJANGO_DEBUG='0'
$env:DJANGO_SECRET_KEY='<强随机长串>'
$env:DJANGO_MYSQL_PASSWORD='<生产密码>'
$env:ALLOWED_HOSTS='your-domain.com'    # 建议把 settings 里的 ['*'] 改为具体域名

D:\Python\python.exe manage.py migrate
D:\Python\python.exe manage.py collectstatic --noinput
D:\Python\python.exe manage.py refresh_assets --collect
```

**Gunicorn + Nginx 示例**

```bash
# 应用进程（2~4 worker，按 CPU 核数）
gunicorn DjangoBlog.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 60
# Celery（Linux 可用默认 prefork 池）
celery -A DjangoBlog worker -l info
celery -A DjangoBlog beat -l info
```

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    # ssl_certificate / ssl_certificate_key ...

    client_max_body_size 25m;              # 与 DATA_UPLOAD_MAX_MEMORY_SIZE 对齐

    location /static/ { alias /srv/acgblog/staticfiles/; expires 30d; add_header Cache-Control "public, immutable"; }
    location /media/  { alias /srv/acgblog/media/;      expires 7d;  }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;   # 访问日志取真实 IP
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

生产检查清单：
`DEBUG=0` · 强随机 `SECRET_KEY` · `ALLOWED_HOSTS` 收紧 · TLS + 安全响应头 ·
MySQL 与 `media/` 定期备份 · Redis 持久化（AOF/RDB） · Celery worker 与 beat 常驻 ·
`ACCESS_LOG_FALLBACK_REDIS_URL` 与 broker 隔离。

---

## 9. 运维手册

### 9.1 管理命令

| 命令 | 作用 |
| --- | --- |
| `python manage.py refresh_assets` | 重压缩 CSS/JS、生成 `.gz`、写构建号、清缓存。`--only a.css,b.js` 只重压指定源文件；`--collect` 同时 collectstatic；`--no-css/--no-js/--no-cache/--no-gz` 跳过对应步骤；`--token-only` 只更新版本号 |
| `python manage.py accesslog_queue` | **访问日志兜底队列运维**：无参数=查看积压；`--drain` 批量入库；`--dry-run` 只统计；`--reset-circuit` 清 Redis/Broker 熔断；`--purge --yes` 清空队列（危险） |
| `python manage.py routes_audit` | **路由与视图审计**：`--list` 列全部路由；`--dead` 列未挂路由函数（区分工具函数与零引用死代码）；`--stub` 列占位视图；`--json` 导出报告 |
| `python manage.py messages_audit` | **文案收敛审计**：统计注册表规模；`--py/--tpl/--js` 分域列出未收编的硬编码中文；`--json` 导出报告 |
| `python manage.py security_test` | 安全自检（51 项）；`--category xss/sql/html/auth/boundary/accesslog` 只跑指定类别 |
| `python manage.py diag` | 综合诊断：`--all` 全跑；`--config` / `--deps`（含 requests 告警核验）/ `--permissions` / `--security` / `--db` / `--cache` / `--celery` / `--static` / `--templates` / `--urls` / `--models` / `--middleware` / `--views` / `--commands` / `--templatetags` / `--cache-stats` / `--cache-keys [前缀]` / `--static-size`（含体积预算超限标注）/ `--slow-queries` / `--db-stats` / `--n-plus-one` |
| `python manage.py data_maintain` | 数据维护：重建计数、清理临时数据、一致性修复 |
| `python manage.py cache_bump` | 缓存版本号管理（bump 后详情页缓存整体失效） |
| `python manage.py seed_demo_stats` | 演示用访问日志回填（本地看板趋势演示） |
| `python manage.py collectstatic` | 收集静态文件（生产） |
| `python manage.py migrate` | 应用 / 回滚迁移 |

### 9.2 Redis 与 Celery 启停

```powershell
# —— 启动顺序：Redis → MySQL → Web → Worker → Beat ——
redis-server                                        # 或作为 Windows 服务常驻
D:\Python\python.exe manage.py runserver 127.0.0.1:8033
D:\Python\python.exe -m celery -A DjangoBlog worker --pool=solo -l info   # Windows 必须 solo 池
D:\Python\python.exe -m celery -A DjangoBlog beat -l info

# —— 验证 worker 在线 ——
D:\Python\python.exe -m celery -A DjangoBlog inspect ping
D:\Python\python.exe -m celery -A DjangoBlog inspect active

# —— 停止：直接 Ctrl+C；或强制结束对应进程 ——
Get-Process python | Where-Object { $_.CommandLine -like '*celery*' } | Stop-Process -Force
```

**Beat 定时任务清单**（`settings.CELERY_BEAT_SCHEDULE`）

| 任务 | 频率 | 作用 |
| --- | --- | --- |
| `check_scheduled_articles` | 每分钟 | 定时投稿到点流转（待审核 / 已发布） |
| `flush_access_log_queue` | 每 5 分钟 | 访问日志兜底队列批量补齐 |
| `flush_buffered_views` | 每 5 分钟 | 阅读量缓冲批量落库 |
| `send_comment_digest` | 每 15 分钟 | 评论通知摘要邮件（每作者一封） |
| `update_article_views` | 每小时 | 阅读量统计 |
| `clean_old_logs` | 每天 03:00 | 清理 90 天前访问日志 |

### 9.3 访问日志降级演练（建议每季度一次）

```powershell
# 1) 制造 broker 故障：停掉 Redis，或临时改错 CELERY_BROKER_URL 后启动 Web
#    观察日志出现：
#    「[accesslog] Celery broker 投递失败（…），进入 15.0s 熔断窗口，后续请求直接走 Redis 兜底队列」
# 2) 查看兜底队列积压（Redis 可用时）
python manage.py accesslog_queue
# 3) 恢复 broker 后批量补录（beat 在线时也会每 5 分钟自动补齐）
python manage.py accesslog_queue --drain
# 4) 若 Redis 也被清空过导致熔断状态残留
python manage.py accesslog_queue --reset-circuit
```

判定标准：①请求耗时仍为毫秒级；②故障期间数据库零写入（层 2）；③恢复后探测日志 100% 入库。

### 9.4 日常巡检

| 频率 | 项目 |
| --- | --- |
| 每日 | 看板 `/console/`：待审核 / 待处理举报 / 回收站计数；访问趋势是否连续；`server*.log` 中是否有 `[accesslog]` ERROR（层 3 降级告警） |
| 每日 | `python manage.py accesslog_queue`（积压应为 0） |
| 每周 | `python manage.py check`、`python manage.py diag --all`、`python manage.py routes_audit`、`python manage.py messages_audit` |
| 每周 | `python manage.py security_test`（应 51/51） |
| 每月 | 磁盘（`media/` 体积）、MySQL 慢查询、Redis 内存、静态文件体积（`diag --static-size`） |
| 发布前 | `check` + `security_test` + `refresh_assets` + 浏览器验收（见第 11 章） |

### 9.5 内容运营

| 场景 | 操作入口 |
| --- | --- |
| 审核投稿 | `/console/moderation/?tab=articles` → 通过发布 / 驳回退回（支持按时间 / 分类 / 标签排序，分页参数 `page`） |
| 处理举报 | `/console/moderation/?tab=reports&rpage=N` → 保留 / 隐藏评论（隐藏前自动备份到 `docs/moderation_backup/`，文件名带时间戳 + 类型 + 主键） |
| 审批推广申请 | `/console/moderation/?tab=promotions` → 通过（含系统执行状态）/ 驳回 |
| 查看审核历史 | `/console/moderation/?tab=history` → `ModerationLog` 全量留痕（提交 / 通过 / 驳回 / 软删 / 恢复 / 彻底删除 / 置顶精华热度变更） |
| 全局审核设置 | 同页「审核全局设置」：文章审核开关、评论审核开关、评论可撤回时长、置顶上限（`max_pinned`） |
| 回收站 | `/console/moderation/?tab=trash` → 恢复 / 彻底删除（分页参数 `tpage`） |
| 站点信息 | `/console/site-settings/`（站名 / Logo / 副标题 / SEO / 页脚文案，含实时预览） |
| 一键刷新静态缓存 | 看板顶部「♻️ 刷新静态缓存」（等价于 `refresh_assets`） |

### 9.6 备份与恢复

```powershell
# 数据库
mysqldump --single-transaction --default-character-set=utf8mb4 Blog_new > blog_20260926.sql
# 上传文件
robocopy E:\Az_Code_E\ACGBlog\media D:\backup\media /MIR
# 恢复：建库 → 导入 SQL → 回灌 media → migrate → refresh_assets
```

### 9.7 故障排查速查

| 现象 | 排查方向 |
| --- | --- |
| 页面 500 | `docs/bugfix_*/server.out.log` 或运行终端 traceback；`manage.py check`；`diag --db` |
| 访问日志缺失 | `accesslog_queue` 是否积压；worker 是否在线（`celery inspect ping`）；日志中是否有层 3 告警 |
| 首页数据不更新 | LocMemCache 为进程内缓存，多进程下各自持有；`manage.py cache_bump` 或换 Redis 缓存后端 |
| 定时文章没自动发布 | beat 是否运行；`scheduled_publishing.process_due_articles()` 手动触发验证；文章 `published_at` 是否为空 |
| 静态资源没更新 | 是否执行 `refresh_assets`；浏览器是否硬刷新（构建号在 `.build_token`） |
| 修改文案不生效 | 文案在 `site_messages.py`，改完需重启 Web 进程（模块级常量） |
| 模板出现多余文字 | 检查是否有**跨行** `{# #}` 注释（`scripts/check_template_comments.py`） |
| requests 版本告警 | `manage.py diag --deps` 核验；requirements 锁定 + `deprecation_filters` 双保险 |

### 9.8 开发调试端点（仅 DEBUG 挂载）

| 端点 | 作用 |
| --- | --- |
| `GET /__debug_cache/` | 查看 **runserver 进程内** LocMemCache 快照（key / TTL / 片段命中统计）；本机或超级用户可用 |
| `GET /__dev_sync_state/` | 把外部脚本改过的数据库设置同步到服务进程（读桥接文件 → 清本进程缓存），供自动化验收消除「进程内缓存」导致的状态不一致；仅 DEBUG + 本机 |
| 详情页 `?debug_cache=1` | 页面底部输出各片段缓存状态；响应头 `X-Cache: HIT/MISS` |
| 详情页 `?waifu=off` | 关闭看板娘（写入 cookie），便于布局测量 |

---

## 10. 扩展指南

### 10.1 新增页面 / 视图
1. `blog/views.py` 增加视图（页面用 `render`，接口用 DRF）；
2. `blog/urls.py` 注册路由并命名（页面进 `urlpatterns`，接口进 `api_urlpatterns`）；
3. `templates/blog/` 新增模板，`{% extends 'base.html' %}`；
4. 需要导航入口则改 `base.html`；选中态用 `aria-current="page"`。

### 10.2 新增模型 / 字段
1. `blog/models.py` 增加模型或字段，在 `blog/admin.py` 注册（自定义站点 `blog_admin_site`）；
2. `python manage.py makemigrations blog` → `migrate`；
3. 对外暴露补 `serializers.py` 与视图；
4. **纯新增字段向后兼容可直接迭代；改动既有字段 / 表关系前先评审影响面**；
5. 若涉及缓存，记得在 `cache_keys.py` 补 key 并在信号中失效。

### 10.3 新增中间件
1. `blog/middleware/` 新建独立文件（一个中间件一个文件），写清「为什么需要它」；
2. 在 `blog/middleware/__init__.py` 再导出；
3. 在 `settings.MIDDLEWARE` 按「先请求后响应」的顺序插入；涉及模板变量时补上下文处理器。
4. ⚠️ **访问日志中间件是全局永久强制模块，不可删除、不可破坏。**

### 10.4 新增异步任务
1. `blog/tasks.py` 用 `@shared_task` 定义（返回值给运维看，异常要兜底）；
2. 需要定时则在 `settings.CELERY_BEAT_SCHEDULE` 注册；
3. 注意任务必须在 Windows solo 池下也能跑（避免依赖 fork 语义）。

### 10.5 新增功能开关
```python
from blog.views import Round5FeatureRegistry

@Round5FeatureRegistry.register('reading', 'focus_mode', '专注阅读模式')
def focus_mode_view(request):
    ...
```
- 查询：`GET /api/round5/features/`（列表 + 按域统计）；切换：`POST /api/round5/features/<id>/toggle/`（staff）；
- 运行时覆盖存 `settings.ROUND5_FEATURES`（进程内，重启回默认）；需持久化可落 `SiteInfo`。

### 10.6 新增徽章 / 成就
1. `Badge` 表配置：`icon`、`condition_type`（`articles`/`comments`/`likes`/`views`/`days`）、
   `condition_value`、`description`（将直接作为面板上的「如何获得」文案）；
2. 触发点调用 `check_and_award_badges(user)`；
3. 个人中心面板由 `_build_badge_panel()` 自动汇总，进度口径与发徽章一致；
   新增条件类型时需同步扩展 `_BADGE_UNITS` / `_BADGE_HOW_TO`。

### 10.7 新增文案（提示词）
1. 在 `blog/site_messages.py` 的 `MESSAGES` 按 `<域>.<语义>` 登记（保持萌系口吻）；
2. 视图用 `msg('域.键', 参数…)`，模板用 `{{ MSG.域.键 }}`，前端用 `window.moeMsg('键')`；
3. 跑 `python manage.py messages_audit` 校验，**禁止在代码里新写中文字面量提示**。

### 10.8 新增前端样式 / 脚本
- 样式放 `static/assets/css/`（通用组件 `components.css`，页面增强 `ui_polish.css`），
  只引用 CSS 变量以自动适配明暗主题；按钮交互沿用 6.7 的骨架类；
- 脚本放 `static/assets/js/`（通用逻辑进 `common.js`，页面级用 `<页面>_inline.js`），
  加 UTF-8 中文注释；
- 富文本样式改 `editor-content.css`（前台正文与编辑器共用）；
- 完成后执行 `refresh_assets --only <改动文件>`（会同步生成 `.min` 与 `.gz`）并硬刷新；
- **不要在模板里内联写样式 / 脚本**，除非确实无法外移。

### 10.9 新增主题
在 `:root[data-theme="..."]` 增加令牌集合，并在主题切换器中登记；
`theme.js` 会持久化到 `localStorage.theme`。

---

## 11. 测试与验收

### 11.1 硬性指标（每次交付必须全绿）

| 项目 | 命令 | 期望 |
| --- | --- | --- |
| 系统检查 | `python manage.py check` | 0 错误 0 警告 |
| 依赖告警 | `python manage.py diag --deps` | 无 `RequestsDependencyWarning` |
| 安全测试 | `python manage.py security_test` | 51/51 通过 |
| 路由审计 | `python manage.py routes_audit` | 0 占位视图、0 零引用死代码 |
| 文案审计 | `python manage.py messages_audit` | 核心用户可见文案 100% 收编 |
| 访问日志 | `python manage.py accesslog_queue` | 积压 0；三层降级演练全部通过 |
| 浏览器矩阵 | 见 11.2 | 8 视口 × 亮暗 × 6 页面，问题 0 项 |

### 11.2 浏览器验收矩阵

| 维度 | 取值 |
| --- | --- |
| 浏览器 | Chrome + Edge |
| 视口（8 档） | 1920×1080、1536×864、1366×768、1280×720、1024×768、768×1024、430×932、390×844 |
| 主题 | light / dark |
| 页面 | 首页、文章详情、内容审核、注册页、登录页、404 页 |
| 每帧断言 | 横向滚动 ≤2px、元素越界 0、文字裁切 0、控制台错误 0、资源加载失败 0、正文非空 |

验收脚本（零依赖：Node 内置 WebSocket 自研 CDP 客户端，不需要 puppeteer / playwright）：

```powershell
# 准备：Redis + runserver 在跑；先造 QA 账号与数据
cd docs\bugfix_20260926_bug9\scripts
node setup_qa_users.mjs          # QA 账号 qa_author(staff) / qa_plain，密码 QaPass12345

node verify_bug9_1.mjs           # 定时投稿可见性与状态流转
node verify_badge_panel.mjs      # 徽章 / 成就面板（四视口主题）
node verify_flow3.mjs            # 三用户全流程（管理员 / 作者 / 游客，独立浏览器实例）
node verify_accesslog_tiers.mjs  # 访问日志三层降级专项
node ui_matrix.mjs chrome        # 8 视口 × 亮暗 × 6 页面
node ui_matrix.mjs edge
```

### 11.3 最近一轮验收结果（工单 Bug9）

| 项目 | 结果 |
| --- | --- |
| `manage.py check` | 0 错误 0 警告（`-W error` 同） |
| `diag --deps` | 无 requests 版本告警 |
| `security_test` | **51/51** |
| `routes_audit` | 186 路由、0 占位视图、0 零引用死代码 |
| `messages_audit` | 注册表 286 条 / 19 域 |
| 访问日志三层降级 | **4/4**（异步 45ms / 兜底 42ms 且 DB 零写入 / 批量补录 6/6 / 极端同步 44ms） |
| 8 视口矩阵 | Chrome 96 帧 + Edge 96 帧，**问题 0 项** |
| 三用户全流程 | **25/25** |
| Bug9-1 可见性 | **8/8** |
| 徽章面板 | **9/9** |

详细产物见 `docs/bugfix_20260926_bug9/`（修改清单、验证报告、审计 JSON、192 帧截图）。

---

## 12. 工单变更历史

| 工单 | 主要内容 | 归档目录 |
| --- | --- | --- |
| **Bug9（最新）** | 定时投稿可见性与状态流转修复；个人中心徽章成就面板；全站文案后端变量化（286 条注册表 + 三层接入）；路由与视图审计（`routes_audit`）；`feature` / `round` 文件全部合并归档；按钮交互三态；三用户全流程验收；README 重写 | `docs/bugfix_20260926_bug9/` |
| Bug8 | 注册页内联红字校验；推广「系统执行状态」；访问日志重构为三层降级（异步优先 + 兜底队列 + 熔断）；移动端底部操作条修复 | `docs/bugfix_20260925_bug8/` |
| 工单 6 | 置顶 / 精华 / 热度权限与审核流（迁移 0016）；定时发文与访问日志两个真实缺陷修复 | `docs/bug1/`、`docs/bug11/`、`docs/bug12/` |
| 工单 5 | 17 项 Bug + 健壮性增强（`html_safety.py`、无功能 stub 归档、BUILD_TOKEN 热更新等） | `docs/bugfix_ticket5/` |
| 更早 | Round3 / Round4 / Round5 / Round6 迭代报告 | `docs/round*_report.md`、`docs/ROUND*_FINAL_REPORT.md` |

**已知历史数据缺口**：2026-09-23 前后部分日期的访问日志，为早期 broker / worker 宕机期间缺失，
无法回填；中间件现已实现三层降级 + `accesslog_queue` 批量补录 + beat 自动补齐，
从机制上杜绝再次缺口。

### 12.1 已归档的无功能实现

| 归档内容 | 原因 | 位置 |
| --- | --- | --- |
| `/api/features/` 下 1000 个 echo 占位桩（`features_*.py` × 10 + `features_urls.py`） | 仅回显请求体、无真实业务、前端零调用 | `docs/archived_feature_stubs/` |
| round5 自动生成的 11,606 个占位路由 | 视图全为元数据回显 stub，拖慢 URL 解析 | `docs/archive/round5_stubs/` |
| 第三方登录占位（GitHub / 微信 / 微博） | 无可用凭据、无真实 OAuth 流程 | `docs/archived_feature_stubs/social_login/` |
| `features_round5/`（功能开关注册表原实现） | 已并入 `views.py` + `urls.py` | `docs/archived_feature_stubs/round5_features/` |
| `/test-404/` 调试路由 + `test_404_page` | 非业务功能；404 页由中间件统一渲染 | `docs/archived_feature_stubs/debug_routes/` |

---

🌸 愿这个小站也能让你写得开心、逛得治愈喵~
