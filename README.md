# 🌸 萌语博客 · MoeBlog

> 一个粉紫蓝萌系的二次元个人小站，记录技术与生活的碎碎念喵~
> 技术栈：**Django 5.2 + Django REST Framework + MySQL 8 + Celery/Redis + WhiteNoise + Live2D + PWA**

柔和圆润、清新通透，自带看板娘、樱花花瓣、暗色模式与一堆体验彩蛋；内置完整的**投稿—审核—发布—软删除—回收站**运营闭环。

---

## 目录

1. [项目定位与设计语言](#1-项目定位与设计语言)
2. [功能特性一览](#2-功能特性一览)
3. [技术架构](#3-技术架构)
4. [目录结构](#4-目录结构)
5. [核心数据模型](#5-核心数据模型)
6. [关键实现细节](#6-关键实现细节)
7. [环境要求与部署方法](#7-环境要求与部署方法)
8. [运维手册](#8-运维手册)
9. [如何拓展](#9-如何拓展)
10. [测试与验收](#10-测试与验收)

---

## 1. 项目定位与设计语言

**定位**：二次元轻量萌系个人博客 / 内容社区。

| 维度 | 约定 |
| --- | --- |
| 主色 | 粉 `#ff8fb1`、紫 `#a06cd5`、蓝 `#6ea8fe`，点缀樱花粉 |
| 形态 | 大圆角（卡片 18px、胶囊 999px）、柔和投影、半透明玻璃拟态 |
| 质感 | 清新通透、留白充足、渐变克制 |
| 文案 | 全站中文 + 语气词「喵~」，错误页 / 空状态 / 表单验证均为萌系表达 |
| 动效 | 樱花飘落、入场淡入、卡片悬浮、按钮回弹、看板娘互动 |
| 主题 | 明 / 暗双主题，一键切换并持久化 |
| 响应式 | 三栏（桌面）→ 单栏（移动），覆盖 360~1920 共 8 档视口 |

设计令牌（Design Token）统一以 CSS 自定义属性维护，明暗主题分别在 `:root` 与
`:root[data-theme="dark"]` 下定义，全站组件只引用变量、不写死颜色。

---

## 2. 功能特性一览

### 内容与阅读
- 文章列表（最新 / 热门排序）、置顶、精华（NEW / HOT / 精华徽章）
- 文章详情：目录 TOC、阅读进度条、字数 / 阅读时长、上一篇 / 下一篇
- 专注阅读模式、阅读设置（字号 / 行距 / 主题）、TTS 朗读
- 文章导出：全文复制、Markdown、PDF、打印；分享卡片 + 二维码 + 短链
- 封面图智能布局：**封面 → 正文首图 → 无图文字填充**，预览图固定在卡片右侧
- 分类、标签（标签云可自由拖动 + 标签索引 + 排行榜）、系列（连载）、归档

### 互动社区
- 多级评论（楼中楼，仅第一层缩进、后续层级不重复右移）、评论点赞 / 表情回应
- 评论 5 分钟内可撤回（软删除）；评论举报
- 文章点赞 / 踩、收藏（收藏夹）、关注（用户 / 分类 / 标签）
- @提及、回复通知、站内通知中心（铃铛下拉 + 独立页面）
- 徽章 / 成就、积分体系、用户主页、个性签名、黑名单与静音

### 运营与治理（本轮重点）
- **投稿审核闭环**：普通用户投稿进入「待审核」，管理员通过 / 驳回（驳回退回草稿并通知作者）
- **软删除 + 回收站**：文章 / 评论删除先进回收站，可恢复或彻底删除
- **审核日志 ModerationLog**：提交 / 通过 / 驳回 / 软删 / 恢复 / 彻底删除全程留痕
- 运营看板：实时统计、14 天访问趋势、热门文章 Top、分类分布、待办计数
- **站点设置（SiteInfo 单例）**：站名 / Logo / 副标题 / SEO 描述关键词 / 页脚文案在线编辑，保存后全站立即生效（带实时预览）
- 访问日志中间件：Celery 异步入库（含 404 / 500），broker 故障时同步兜底，自动剔除静态资源
- 一键刷新静态压缩与缓存（管理命令 + 看板按钮 + API）

### 前端体验
- Live2D 看板娘（多套模型 / 服装、对话气泡、工具栏）
- 樱花花瓣、粒子背景、Konami 彩蛋、404「接樱花」小游戏
- 全站统一 `moeToast` 轻提示与 `moeConfirm` 弹窗（**零原生 alert/confirm**）
- PWA：manifest、Service Worker、可安装、可离线
- 静态资源自动压缩（CSS/JS minify、去注释）、构建号缓存破除

### 工单 5（本轮，17 项 Bug + 健壮性增强）
- 修复：全局选中态、首页预览图占满、回到顶部箭头、封面选择器、文章访问密码、推荐图规则、
  只看楼主、嵌套评论缩进与撤回、代码块折叠、看板开方刻度柱图、分类名不换行、左下快捷菜单、
  站点状态仅管理员、页脚排版、站点信息 DB 化、头像下拉定位、标签云居中聚簇。
- **关键修复**：`theme.js` 命名 IIFE 多余括号导致整脚本语法错误、主题切换此前实际失效，已修复。
- **新增** `blog/html_safety.py`：共享 `MoeCSSSanitizer`（bleach CSS 白名单），消除 `NoCssSanitizerWarning`。
- **清理**：11 个无鉴权 feature echo 桩归档至 `docs/archived_feature_stubs/`，下线 `/api/features/`。
- **健壮性**：DEBUG 下 `BUILD_TOKEN` 每请求重读，打包后无需重启即可更新静态资源版本号。
- 详见 `docs/bugfix_ticket5/CHANGELOG_AND_FEATURES.md` 与 `docs/bugfix_ticket5/VERIFICATION_REPORT.md`。

---

## 3. 技术架构

```
┌────────────────────────────────────────────────────────────┐
│                       浏览器 Chrome / Edge                  │
│  base.html · 明暗主题 · Live2D · 樱花 · PWA(SW)            │
└───────────────▲───────────────────────────┬────────────────┘
                │  HTML / JSON              │  /static /media
┌───────────────┴───────────────────────────▼────────────────┐
│                    Django 5.2 (WSGI)                        │
│  Middleware: Security → WhiteNoise → AccessLog → Session →  │
│              Common → CSRF → Auth → ...                     │
│                                                             │
│  URL Router ──► Views(blog/views.py)                        │
│                    │   函数视图 + DRF API 视图               │
│                    ▼                                         │
│   Templates(Django Template) │ DRF Serializers              │
└───────┬───────────────────────────┬──────────────┬──────────┘
        ▼                           ▼              ▼
   MySQL 8 (数据)            LocMem Cache     Static/Media 磁盘
        ▲                                            ▲
        │                                  WhiteNoise(生产托管)
┌───────┴──────────────┐
│ Celery Worker(可选)   │  Broker/Result: Redis 6379/0
│  异步任务 tasks.py    │  （访问日志经 broker 排队，worker 消费后入库）
└──────────────────────┘
```

### 技术选型

| 层 | 技术 | 版本 | 说明 |
| --- | --- | --- | --- |
| Web 框架 | Django | 5.2.17 | 单 app（`blog`）承载全部业务 |
| API | djangorestframework | 3.15.2 | 通知 / 评论 / 点赞 / 功能开关等 JSON API |
| 数据库 | mysqlclient + MySQL 8 | 2.2.7 | 字符集 utf8mb4 |
| 异步 | Celery + Redis | 5.3.1 / 5.2.1 | broker `redis://127.0.0.1:6379/0` |
| 缓存 | Django LocMem | 内置 | 默认 5 分钟；**Redis 仅作 Celery broker** |
| 静态托管 | WhiteNoise | 6.12.0 | 生产压缩 + 长缓存 |
| 图片 | Pillow | 10.3.0 | 封面 / 缩略图 |
| HTML 净化 | bleach | 6.4.0 | 评论 / 富文本白名单清洗 |
| 搜索 / 导出 | pypinyin, html2text, qrcode, xhtml2pdf | — | 拼音搜索、MD/PDF、二维码 |
| 富文本 | CKEditor 4（本地静态） | — | 无需 pip 安装 |
| 看板娘 | Live2D（本地静态） | — | `static/assets/live2d` |

---

## 4. 目录结构

```
Blog/
├── manage.py                     # Django 入口
├── requirements.txt              # 精确固定的依赖
├── README.md                     # 本文档
├── DjangoBlog/                   # 项目配置
│   ├── settings.py               # 全局设置（安全 / DB / 缓存 / 静态 / Celery）
│   ├── urls.py                   # 根路由
│   └── wsgi.py / asgi.py
├── blog/                         # 主应用
│   ├── models.py                 # 全部数据模型（40+）
│   ├── views.py                  # 页面视图 + API（含审核 / 看板 / 回收站）
│   ├── urls.py                   # 应用路由
│   ├── serializers.py            # DRF 序列化器
│   ├── middleware/               # 中间件包（slow_query/access_log/online_status/
│   │                             #   cute_error_pages/site_info；__init__ 再导出兼容）
│   ├── context_processors.py     # 注入 BUILD_TOKEN / ENABLE_SW / site_info 等
│   ├── tasks.py                  # Celery 异步任务
│   ├── signals.py                # 信号
│   ├── admin.py                  # 后台注册（含 SiteInfo 单例）
│   ├── html_safety.py            # 统一 HTML/CSS 安全净化（MoeCSSSanitizer，bleach CSS 白名单）
│   ├── features_live2d.py        # 看板娘真实功能端点 /api/live2d/
│   ├── features_round5/          # round5 功能开关管理（真实开关 /api/round5/features/）
│   ├── management/commands/      # data_maintain / diag / refresh_assets / security_test /
│   │                             #   seed_demo_stats（演示访问日志回填）
│   ├── migrations/               # 数据库迁移（最新 0015：SiteInfo 站点变量）
│   └── templatetags/             # 自定义模板标签
├── templates/
│   ├── base.html                 # 全站骨架（导航 / 弹窗 / Live2D / SW）
│   ├── 404.html / 500.html       # 萌系错误页
│   ├── partials/                 # 文章卡 / 评论项等可复用片段
│   └── blog/                     # index / detail / edit / tags / console /
│                                 #   moderation / notifications ...
├── static/assets/
│   ├── css/                      # 源样式（base/components/blog/ui_polish…）
│   ├── js/                       # 源脚本（common / features / tag-cloud-layout…）
│   ├── live2d/                   # 看板娘模型与脚本
│   ├── ckeditor/                 # 本地富文本编辑器
│   └── .build_token              # 构建号（用于 ?v= 缓存破除）
├── staticfiles/                  # collectstatic 产物（生产）
├── media/                        # 用户上传（covers / uploads）
└── docs/
    ├── qa_screenshots/            # 浏览器实测截图矩阵（chrome/ 20、edge/ 20、staff/ 6）
    ├── archived_feature_stubs/    # 已归档的 11 个无实现 feature echo 桩（工单 17）
    ├── bug5_extract/              # 工单 5 提取件 / 采集与补丁脚本 / 服务日志
    ├── bugfix_ticket5/            # 工单 5：CHANGELOG_AND_FEATURES.md / VERIFICATION_REPORT.md
    ├── bugfix_20260924/          # 上一轮 Bug 单：工单提取件 / 补丁脚本 / 截图
    ├── CHANGELOG_AND_FEATURES.md # 文案替换清单 + 新增功能说明（历史）
    └── VERIFICATION_REPORT.md    # 独立验证报告（历史）
```

---

## 5. 核心数据模型

全部模型定义于 `blog/models.py`，核心如下：

| 模型 | 职责 |
| --- | --- |
| `User` | 自定义用户（继承 AbstractUser，含昵称 / 头像等） |
| `Category` / `Tag` | 分类 / 标签（标签含文章数、热度） |
| `Article` | 文章（状态机、软删除、封面、统计计数） |
| `Comment` | 评论（多级 parent、软删除、点赞数） |
| `ModerationLog` | **审核 / 删除操作日志（本轮新增）** |
| `SiteInfo` | **站点变量单例（站名 / Logo / 副标题 / SEO / 页脚文案，迁移 `0015`）** |
| `CommentReport` | 评论举报 |
| `Notification` | 站内通知（reply/mention/like/article/system） |
| `Favorite(Folder)` / `Rating` | 收藏 / 评分 |
| `Series` | 连载系列 |
| `AccessLog` | 访问日志（PV/UV/UA 解析） |
| `Badge` / `UserBadge` / `UserPoint` | 徽章 / 成就 / 积分 |
| `ShortLink` / `ArticleShare` | 短链 / 分享记录 |
| 其余 | 关注、书签、历史、API Key、Webhook、定时发布、主题预设等 |

### ⚠️ 本轮数据结构变更（Bug 8，已迁移 `0014`）

1. **文章状态新增「待审核」**
   ```python
   class Article(models.Model):
       class Status(models.TextChoices):
           DRAFT     = 'draft',     '草稿'
           PENDING   = 'pending',   '待审核'   # 新增
           PUBLISHED = 'published', '已发布'
   ```
2. **文章 / 评论新增软删除字段**
   ```python
   is_deleted = BooleanField(default=False)
   deleted_at = DateTimeField(null=True, blank=True)
   ```
   - `ArticleQuerySet` 增加 `pending()` / `alive()` / `dead()` 便捷查询。
   - **不在管理器层全局过滤软删除**（避免误伤 Django Admin），改在前台公共视图显式叠加
     `is_deleted=False`。
3. **新增审核日志 `ModerationLog`**（表名 `blog_moderation_log`）
   - 动作 `Action`：`SUBMIT / APPROVE / REJECT / SOFT_DELETE / RESTORE / HARD_DELETE`
   - 字段：审核人（FK，SET_NULL）、动作、对象类型（article/comment）、关联文章 / 评论、
     对象标题、理由、时间；带 `(对象类型,时间)`、`(文章,时间)`、`(动作)` 索引，按时间倒序。

> 以上仅为新增状态 / 字段与新表，**不影响既有表结构与核心架构**，迁移向后兼容。

### 🆕 站点变量单例（Bug 15，迁移 `0015`）

- 新增 **`SiteInfo`**（表名 `blog_site_info`，单例 pk 强制 1）：承载站名、Logo emoji、
  副标题 / 一句话介绍、SEO 描述与关键词、页脚「关于」文案、备案号等。
- `SiteInfo.load()` 用 `get_or_create` + 缓存（键 `site_info_singleton`，TTL 3600），
  `save()` 自动清缓存；经 `SiteInfoMiddleware` 与 `context_processors.site_info_ctx`
  注入全站模板（排序最后以覆盖旧常量）。
- 管理员在 `/console/site-settings/` 可视化修改，保存后全站立即生效，带实时预览。
- 配套将原单文件 `blog/middleware.py` 拆为 **`blog/middleware/` 包**（slow_query /
  access_log / online_status / cute_error_pages / site_info），`__init__.py` 再导出
  全部类，`blog.middleware.X` 旧导入路径完全兼容。

> 该变更为新增表 + 中间件文件拆分，未改动既有核心数据结构与调用契约。

---

## 6. 关键实现细节

### 6.1 投稿—审核—发布闭环
- 普通用户在 `article_new` 投稿：强制 `status=PENDING`，写 `SUBMIT` 日志，提示
  「提交后进入待审核，管理员通过后才会公开喵~」。
- 审核队列 `moderation_queue` 提供四个标签页：**待审文章 / 待处理举报 / 审核历史 / 回收站**。
- `moderate_article`：
  - **通过** → `PUBLISHED` + `APPROVE` 日志；
  - **驳回** → 退回 `DRAFT`（保留内容）+ `REJECT` 日志（含理由），并向作者发系统通知。
- 待审文章支持按「提交时间 / 分类 / 标签」排序；三类列表各自分页。

### 6.2 软删除、回收站与计数一致性
- 文章删除（作者 / 管理员）与评论删除（撤回 / 审核）均为**软删除**（置 `is_deleted`、
  `deleted_at`），写 `SOFT_DELETE` 日志。
- 回收站支持 **♻️ 恢复（RESTORE）** 与 **🔥 彻底删除（HARD_DELETE，二次确认）**。
- 评论计数（`Article.comment_count`）在删除 / 恢复 / 举报处理三处统一改为
  **按 Comment 表实际存活数重算**，杜绝 `F(±1)` 在重复提交下的计数漂移。

### 6.3 访问日志中间件（Bug 10）
- 现 `process_response` 通过 Celery 异步任务 `save_access_log.delay()` 投递入库，
  **不再在请求线程同步 INSERT**；任务先进入 Redis broker 队列，由 worker 消费后写库。
- worker 暂未启动时任务停留在队列中不丢失（broker 在线即可）；**broker 不可用导致投递
  失败时，降级为同步 `AccessLog.objects.create()` 入库并记录错误日志**，避免整天缺数据。
- IP 合法性校验保留在 `save_access_log` 任务内，代理给出的非法 IP 会置空后入库。
- `_is_asset()` 短路剔除 `/static/`、`/media/`、`favicon`、`robots.txt`，避免污染统计。
- 本地开发需同时启动 Celery worker（Windows 用 solo 池），与 `runserver` 各占一个终端：
  `D:\Python\python.exe -m celery -A DjangoBlog worker --pool=solo -l info`。

### 6.4 通知中心（Bug 9）
- 独立页面 `/notifications/`：全部 / 未读、类型图标、点击已读并跳转、分页、空状态。
- 导航铃铛：懒加载最近 6 条、单条已读、全部已读、未读徽标同步、外部点击 / Esc 关闭。

### 6.5 标签云拖动与选中态（Bug 15）
- 标签 `<a class="chip">` 可自由拖动；移动超过 4px 判定为拖动，mouseup 后用
  **click 捕获阶段一次性守卫** `preventDefault`，确保「拖动不跳转、普通点击正常跳转」。
- 排行榜 / 标签索引模式按钮、排序 tab、分页当前页统一为**粉紫渐变 + 白字**高对比选中态，
  明暗主题均可一眼辨别。

### 6.6 全站统一弹窗与静态压缩
- `common.js` 提供 `moeToast(msg,type)` 与 `moeConfirm({...})`，并对 `[data-confirm]`
  做声明式委托；全站移除原生 `alert/confirm`。
- `refresh_assets` 管理命令：压缩全部 CSS/JS、剥离注释、写 `.build_token`、清 Django 缓存。
- 静态 URL 通过 `BUILD_TOKEN` 追加 `?v=` 破除浏览器缓存；改前端后必须刷新并硬重载。

### 6.7 前端合成层「首帧冻结」应对
在特定显卡 + Chrome 下，服务端首帧渲染的激活元素可能只绘制基础态。当前策略：
- **激活元素**：早期的 `bakeActiveStates()`（捕获 computed → 置 transparent → 双 rAF
  回写内联）会批量误烘焙多个元素，导致导航 / tab「多紫、闪烁、白字白底」，**现已停用
  为空操作桩**；选中态完全交给 CSS（`:active` / `.active` / `aria-current`），只保留一个
  激活项，稳定无闪烁。
- **加载后浮层（弹窗 / 下拉）**：仍 relocate 进 `<main id="main-content">` 合成面并按
  触发点 fixed 定位（见 `header-menus.js`）。

### 6.8 评论真实层级与「只看楼主」
- 新建评论沿 `parent_comment` 链计算**真实深度（上限 3）**，与评论树构建口径一致；
  评论项根节点带 `depth-N / is-op`，展示 **badge-op 楼主徽标**与「↪ 回复 @被回复人」。
- 「只看楼主」复选框由 `interaction.js` 过滤非 `.is-op` 评论，`MutationObserver`
  保证新插入评论自动遵守过滤。

### 6.9 代码折叠、封面选择器与标签云
- **代码折叠**：折叠态保留 56px 预览（不再塌缩为 0），点预览区或展开按钮均可展开。
- **封面选择器**：编辑页用虚线拖拽风萌系选择器替代原生「选择文件」，选中后文件名联动。
- **标签云布局**：正态分布标准差收紧到容器 1/6.2、提高重试次数，**越界直接重试而非
  贴边钳制**，实现大标签居中、小标签围绕、四角自然留白。

### 6.10 看板娘避让与移动端适配
- `waifu-footer-avoid.js`：页脚统计带进视口时看板娘淡出、离开恢复，统计卡不被遮挡。
- `waifu-mobile.js`：因看板娘初始化写了内联 `display:block !important; transform:none
  !important`（样式表无法覆盖），改由 JS 直接改写内联——≤600px 隐藏、601~760px 缩至
  65%、更宽恢复，并监听 resize / scroll。
- 头部在 ≤980px 收纳为两行（导航第二行横向滚动、搜索按钮图标化）；首页 ≤760px 隐藏
  左右侧栏、761~980px 两列（200px 左栏 + 文章流）。

### 6.11 文章详情页片段缓存与调试工具
- **片段缓存**：详情页只缓存「所有用户可见且一致」的共享数据，key 统一带版本前缀
  （`blog/cache_keys.py` 集中管理）：
  - `v{ver}:article:{pk}` 文章对象（仅已发布 + 未软删除 + 无密码，TTL 300s）；
  - `v{ver}:comment_tree:{pk}` 评论树（已通过且未删除的评论列表，TTL 300s）；
  - `v{ver}:related:{pk}` / `v{ver}:rel_weighted:{pk}` 两组相关文章（TTL 300s）；
  - `v{ver}:prevnext:{pk}` 上一篇 / 下一篇（TTL 300s）；
  - `v{ver}:missing:{pk}` 404 墓碑（TTL 60s）。
- **每用户态不缓存**：收藏 / 评分 / 点赞 / 可编辑按钮与阅读量自增（`F('views')+1`）
  仍在请求内实时处理，防止登录状态串号。
- **失效由信号统一驱动**（`signals.py`）：Article / Comment 的 `post_save` /
  `post_delete` 全部收敛到 `invalidate_article(pk)`；新建 / 删除文章额外
  `purge_prevnext()`。定时自动发布走 bulk `update()` 不触发信号，已在
  `check_scheduled_articles` 任务内手动失效。
- **开发调试工具**：
  - `python manage.py cache_bump [--show] [--set vN]`：bump 缓存版本号，所有 key
    前缀整体变化 → 服务端缓存即刻全局失效（重启 runserver 后生效，旧 key 由 TTL 清理）；
  - `python manage.py diag --cache-keys [前缀]`：列出缓存 key 与剩余 TTL（LocMemCache
    为进程内缓存，diag 独立进程看不到 runserver 的缓存，需用下方 DEBUG 端点）；
  - `GET /__debug_cache/`（仅 DEBUG、本机访问）：浏览器直接查看进程内缓存快照
    （key / TTL / 命中统计）；
  - `?debug_cache=1`（仅 DEBUG）：详情页底部输出本次各片段 key 的缓存状态；
  - 响应头 `X-Cache: HIT/MISS`：详情页顶层文章片段是否命中缓存。
- 注意：当前缓存后端为 LocMemCache（进程内）；多进程部署请切换 Redis 缓存后端，
  代码零改动（Django cache API 透明）。

---

## 7. 环境要求与部署方法

### 7.1 环境要求
- Python **3.10+**（推荐 3.10/3.11）
- MySQL **8.x**，数据库字符集 `utf8mb4`
- Redis **6/7**（仅异步任务需要；不使用 Celery 可暂不启动）
- 现代浏览器 Chrome / Edge（含移动端）

### 7.2 本地开发

```powershell
# 1) 创建虚拟环境并安装依赖
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2) 创建数据库（MySQL）
mysql -u root -p -e "CREATE DATABASE Blog_new CHARACTER SET utf8mb4;
                     CREATE USER IF NOT EXISTS 'blog'@'127.0.0.1' IDENTIFIED BY '你的密码';
                     GRANT ALL ON Blog_new.* TO 'blog'@'127.0.0.1'; FLUSH PRIVILEGES;"

# 3) 配置环境变量（可选，也可用默认值）
$env:DJANGO_DEBUG='1'
$env:DJANGO_MYSQL_HOST='127.0.0.1'
$env:DJANGO_MYSQL_DATABASE='Blog_new'
$env:DJANGO_MYSQL_USER='blog'
$env:DJANGO_MYSQL_PASSWORD='你的密码'

# 4) 迁移 + 收集静态 + 建超级用户
python manage.py migrate
python manage.py refresh_assets        # 压缩静态、写构建号、清缓存
python manage.py createsuperuser

# 5) 启动开发服务器
python manage.py runserver 127.0.0.1:8321
#   访问 http://127.0.0.1:8321/

# 6) 另开一个终端启动 Celery worker，消费异步任务（Windows 用 solo 池；须与 runserver 同时运行）
D:\Python\python.exe -m celery -A DjangoBlog worker --pool=solo -l info
```

> 注意：`DJANGO_DEBUG` 默认值为 '1'（开发态）；生产请显式置 '0'。

### 7.3 生产部署

```powershell
# 环境变量
$env:DJANGO_DEBUG='0'
$env:DJANGO_SECRET_KEY='换成足够随机的长字符串'
$env:DJANGO_MYSQL_*='生产数据库信息'

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py refresh_assets
```

推荐以 **WSGI + 反向代理** 运行（Gunicorn / uWSGI + Nginx），Nginx 负责 TLS、
静态 / 媒体文件与转发；WhiteNoise 也可直接托管静态。最小 gunicorn 示例：

```bash
gunicorn DjangoBlog.wsgi:application --bind 127.0.0.1:8000 --workers 3 \
    --timeout 60 --access-logfile -
```

Nginx 片段：

```nginx
server {
    listen 443 ssl;
    server_name example.com;
    # ssl_certificate ...

    location /static/  { alias /path/to/Blog/staticfiles/; expires 30d; add_header Cache-Control "public"; }
    location /media/   { alias /path/to/Blog/media/; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

生产环境务必：`DEBUG=0`、强随机 `SECRET_KEY`、配置 TLS 与安全响应头、限制 `ALLOWED_HOSTS`、
定期备份数据库与 `media/`。

---

## 8. 运维手册

### 8.1 管理命令

| 命令 | 作用 |
| --- | --- |
| `python manage.py refresh_assets` | 重压缩 CSS/JS、写构建号、清缓存；`--collect` 同时 collectstatic，`--no-css/--no-js/--no-cache` 跳过对应步骤 |
| `python manage.py data_maintain` | 数据维护（重建计数 / 清理临时数据等） |
| `python manage.py diag` | 环境与配置诊断；`--cache-keys [前缀]` 列出缓存 key 与 TTL，`--cache-stats` 输出缓存统计 |
| `python manage.py cache_bump` | 缓存版本号管理（bump 后详情页缓存整体失效，调试用） |
| `python manage.py security_test` | 40 项安全自检 |
| `python manage.py migrate` | 应用 / 回滚迁移 |

### 8.2 一键刷新静态与缓存（Bug 14）
- 看板 `/console/` 顶部「♻️ 刷新静态缓存」按钮 → 确认后调用
  `POST /api/refresh-assets/`（仅 staff），成功后自动重载。
- 发布前端改动的标准流程：
  1. 修改 `static/assets` 源文件 / 模板（脚本引用务必带 `?v={{ BUILD_TOKEN }}`）；
  2. 执行 `refresh_assets`（或点看板按钮）；
  3. 浏览器硬刷新（Ctrl+F5）以加载新构建号资源。

### 8.3 日常巡检
- 看板 `/console/`：实时查看已发布 / 待审核 / 草稿 / 评论 / 举报 / 在线 / 趋势。
- 审核后台 `/console/moderation/`：处理待审文章与举报、查看历史、管理回收站。
- 关注：服务进程、Celery worker、Redis、MySQL 磁盘、`media/` 体积、错误日志。

### 8.4 备份
- **数据库**：`mysqldump --single-transaction Blog_new > blog_$(date +%F).sql`
- **上传文件**：定期备份 `media/`（封面与用户上传）。
- 恢复：建库导入 SQL，回灌 `media/`，执行 `migrate` 与 `refresh_assets`。

---

## 9. 如何拓展

### 9.1 新增一个页面 / 视图
1. 在 `blog/views.py` 增加视图（页面用 `render`，接口用 DRF）。
2. 在 `blog/urls.py` 注册路由并命名。
3. 在 `templates/blog/` 新增模板，`{% extends 'base.html' %}`。
4. 需要导航入口则在 `base.html` 导航项加入；选中态用 `aria-current="page"`。

### 9.2 新增模型 / 字段
1. 在 `blog/models.py` 增加模型或字段，并在 `admin.py` 注册。
2. `python manage.py makemigrations blog` → `migrate`。
3. 对外暴露走 DRF：补 `serializers.py` 与视图。
4. **核心数据结构 / 底层架构变更前先评审影响面**；纯新增字段 / 表向后兼容可直接迭代。

### 9.3 新增前端功能与样式
- 组件样式优先放入对应 CSS（通用组件 `components.css`，页面增强 `ui_polish.css`），
  只引用 CSS 变量以自动适配明暗主题。
- 交互脚本放入 `static/assets/js/`（通用逻辑进 `common.js`），并加 UTF-8 中文注释。
- 新增激活控件：选中态直接用 CSS（`.active` / `aria-current`），无需再加入烘焙逻辑
  （`bakeActiveStates` 已停用）。
- 新增浮层：节点放进 `<main id="main-content">` 并 fixed 定位，保证正常绘制。
- 完成后执行 `refresh_assets` 并硬刷新。

### 9.4 新增功能开关
- round6：在对应 `blog/features_<域>.py` 登记开关；
- round5 管理端点：`GET /api/round5/features/`、`POST /api/round5/features/<id>/toggle/`（staff）。

### 9.5 新增徽章 / 成就 / 主题
- 徽章：在 `Badge` 表配置图标与达成条件，触发点写 `UserBadge` 并发通知。
- 主题：在 `:root[data-theme="..."]` 增加令牌集合，主题切换器中登记。

---

## 10. 测试与验收

- **系统检查**：`python manage.py check`（含 `python -W default manage.py check`）→
  **0 错误 0 警告**；requests / urllib3 版本告警已通过锁定兼容版本消除。
- **安全测试**：`python manage.py security_test` → **40/40 全部通过，0 失败**。
- **核心功能无回退**：首页列表、文章详情、评论、搜索、分类、置顶精华、暗色模式均正常。
- **浏览器实测**：Chrome + Edge，明暗双主题，桌面（1366 / 1920）+ 移动（390 / 360）
  共 40 帧矩阵 + 登录态 6 帧，逐张肉眼复核，布局 / 样式无异常（截图见 `docs/qa_screenshots/`）。
- 工单 5 的逐条修复、补丁与采集脚本、`CHANGELOG_AND_FEATURES.md` 与
  `VERIFICATION_REPORT.md` 见 `docs/bugfix_ticket5/`（工单提取件见 `docs/bug5_extract/`）。
- **数据缺口说明**：9/23 等日期访问日志为 Celery broker / worker 宕机期间缺失、无法
  回填；中间件已加同步兜底防止未来缺口（详见验证报告）。

---

## 11. 工单 6（本轮，12 项）变更说明

本轮在不改动核心架构前提下完成 12 项工单，并在测试中发现、修复 2 个真实缺陷。
逐条报告见 `docs/bug1/`、`docs/bug11/`、`docs/bug12/`，截图见 `docs/bug12/shots/`。

### 11.1 置顶 / 精华 / 热度权限与审核流（核心数据结构变更，已迁移 `0016`）

- **Article** 新增显式字段 `is_featured`（精华）、`is_hot`（热门），并加复合索引
  `idx_art_feat_ct`、`idx_art_hot_ct`（`is_pinned` 已存在）。
- 新增 **`PromotionRequest`**：统一承载置顶 / 精华 / 热门申请（Kind=pin/feature/hot，
  Status=pending/approved/rejected），含申请人、理由、处理人、处理时间。
- 新增 **`ModerationSettings`** 单例（pk=1）：`require_article_review`、`require_comment_review`、
  `comment_recall_minutes`、`max_pinned`，在审核页可视化保存。
- `ModerationLog.Action` 新增 PIN/UNPIN/FEATURE/UNFEATURE/HOT/UNHOT，审核历史可按这些动作筛选。
- **权限规则**：写文章页一律不能设置推广标记；管理员可在编辑页 / 详情页直接设置；
  作者在详情页发起申请、弹窗填理由；审核页「✨推广申请」标签审批，通过后字段生效、
  写日志并向申请人发站内通知；置顶数量受 `max_pinned` 约束。
- **信号钩子**：Article/Comment 的 post_save 统一失效详情片段 / 侧边栏 / 热门 / 页脚缓存、
  按存活评论重算计数，覆盖草稿→待审核→发布、编辑、软删 / 恢复全部状态流转。

### 11.2 本轮其他工单

- 系列创建页按钮二次元化并接入封面选择器（Bug2）；评论父子同框、子评论可折叠、
  缩进最多比父多一级（Bug3）；主评论富文本、子评论纯文本、表情面板可用（Bug4）；
  首页热门「本周 / 本月 / 总榜」筛选真实生效（Bug5）；清理无功能后端文件、
  枚举 180 路由无空壳（Bug6/7）；看板柱形图常驻数量、悬浮柱高亮（Bug8）；
  全局工具提示与悬浮态改为浅色高对比（Bug9/10）；全量 CSS/JS/PY 补详细注释（Bug11）。

### 11.3 Bug12 三用户全流程测试中发现并修复的 2 个缺陷

1. **定时发文永不自动发布**：原逻辑在「新文章需审核」开启时把定时投稿置为 PENDING，
   而 `check_scheduled_articles` 只发布 DRAFT，导致定时文章永远无法到点自动发布。
   已调整判定顺序：带未来发布时间一律先存 DRAFT，到点由定时任务发布（已端到端验证）。
2. **访问日志静默丢失**：原中间件仅在 broker 连不上时同步兜底；当 Redis 正常、
   却没有 Celery worker 消费时，`.delay()` 不抛错、任务被丢弃（实测近 3 小时日志缺失）。
   访问日志是单条廉价 INSERT，已改为**同步直写**，任何环境都能完整记录用户 / 时间 / 路由。

### 11.4 本轮验收结论

- `python manage.py check`：**0 错误 0 警告**，无 requests 版本告警；
- `python manage.py security_test`：**40/40 通过**；
- Chrome 桌面 / 移动 × 亮 / 暗矩阵 + Edge 桌面（首页 / 标签 / 详情）实测，布局样式无异常；
- 核心功能（首页、详情、评论、搜索、分类、置顶精华、暗黑、审核流）无回退。


🌸 愿这个小站也能让你写得开心、逛得治愈喵~
