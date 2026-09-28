# -*- coding: utf-8 -*-
"""
blog.models —— 模型包（由原单文件 ``blog/models.py`` 拆分而来）。

拆分原则
--------
按「业务领域」把约 2000 行的单文件拆为多个小文件，每个文件只承载一个领域，
并在本 ``__init__.py`` 中**按依赖顺序统一导入 / 导出**：

- 对外仍可使用 ``from blog.models import Article`` / ``from .models import User``
  等原有写法，**调用方无需任何改动**；
- 跨文件外键一律用字符串（如 ``'User'``），由 Django 在模型注册完成后解析，
  因此文件之间不存在循环导入；
- 所有表名、字段、choices、索引与拆分前完全一致，**不产生数据库结构变更，
  不需要新增迁移**。

领域文件一览
------------
- :mod:`user`        用户（认证与偏好核心表）
- :mod:`catalog`     分类 / 标签
- :mod:`series`      文章系列
- :mod:`article`     文章主模型 / 查询集 / 历史 / 分享 / 定时计划
- :mod:`comment`     评论 / 举报 / 表情反应
- :mod:`interaction` 收藏 / 评分 / 书签 / 阅读清单 / 笔记
- :mod:`logs`        访问日志 / 修改日志 / 登录历史
- :mod:`notification` 站内通知
- :mod:`badge`       徽章 / 成就 / 积分
- :mod:`site`        站点信息单例 / 公告 / 友情链接
- :mod:`moderation`  审核日志 / 审核设置 / 推广申请
- :mod:`messages`    全站文案覆盖 / 弃用文案
- :mod:`social`      关注 / 扩展资料 / 动态 / 拉黑禁言 / 内容举报
- :mod:`system`      API 密钥 / Webhook / 设备 / 主题预设 / 导出 / 小部件 / 搜索历史

维护注意点
----------
新增模型时：① 放入对应领域文件（或新建领域文件）；② 在本文件按依赖顺序
导入并加入 ``__all__``；③ 跨文件外键用字符串，避免循环导入。
"""

# ---- 1. 用户（被依赖最多，最先加载）----
from .user import User

# ---- 2. 分类与标签（文章归属维度）----
from .catalog import Category, Tag

# ---- 3. 系列（文章连载聚合）----
from .series import Series

# ---- 4. 文章（核心主模型，依赖 User/Category/Tag/Series）----
from .article import (
    Article,
    ArticleHistory,
    ArticleQuerySet,
    ArticleShare,
    ShortLink,
    ScheduledPost,
)

# ---- 5. 评论（依赖 Article/User）----
from .comment import (
    Comment,
    CommentReaction,
    CommentReport,
)

# ---- 6. 读者互动（依赖 Article/User）----
from .interaction import (
    ArticleBookmark,
    Favorite,
    FavoriteFolder,
    Rating,
    ReadingList,
    UserNote,
)

# ---- 7. 日志（访问 / 修改 / 登录）----
from .logs import (
    AccessLog,
    EditLog,
    LoginHistory,
)

# ---- 8. 通知 ----
from .notification import Notification

# ---- 9. 徽章 / 成就 / 积分 ----
from .badge import (
    Badge,
    PointLog,
    UserAchievement,
    UserBadge,
    UserPoint,
)

# ---- 10. 站点信息 / 公告 / 友情链接 ----
from .site import (
    FriendlyLink,
    SiteInfo,
    SiteNotice,
)

# ---- 11. 审核日志 / 设置 / 推广申请 ----
from .moderation import (
    ModerationLog,
    ModerationSettings,
    PromotionRequest,
)

# ---- 12. 全站文案覆盖 / 弃用文案 ----
from .messages import (
    SiteMessage,
    SiteMessageRetired,
)

# ---- 13. 社交关系 / 扩展资料 / 内容举报 ----
from .social import (
    CategoryFollow,
    ContentReport,
    TagFollow,
    UserActivity,
    UserBlock,
    UserFollow,
    UserMute,
    UserProfile,
)

# ---- 14. 系统扩展（API 密钥 / Webhook / 设备 / 主题 / 导出 / 小部件 / 搜索历史）----
from .system import (
    ExportJob,
    SearchHistory,
    ThemePreset,
    UserAPIKey,
    UserDevice,
    UserWidget,
    Webhook,
)

# 对外公开的模型名单：
# 1) 声明包的公共接口；2) 配合 ``from blog.models import *``；
# 3) 作为模型清单，新增模型时务必同步登记。
__all__ = [
    # 用户
    'User',
    # 分类 / 标签
    'Category', 'Tag',
    # 系列
    'Series',
    # 文章领域
    'Article', 'ArticleQuerySet', 'ArticleHistory',
    'ArticleShare', 'ScheduledPost', 'ShortLink',
    # 评论领域
    'Comment', 'CommentReport', 'CommentReaction',
    # 读者互动
    'Favorite', 'FavoriteFolder', 'Rating',
    'ArticleBookmark', 'ReadingList', 'UserNote',
    # 日志
    'AccessLog', 'EditLog', 'LoginHistory',
    # 通知
    'Notification',
    # 徽章 / 成就 / 积分
    'Badge', 'UserBadge', 'UserPoint', 'PointLog', 'UserAchievement',
    # 站点
    'SiteInfo', 'SiteNotice', 'FriendlyLink',
    # 审核
    'ModerationLog', 'ModerationSettings', 'PromotionRequest',
    # 文案
    'SiteMessage', 'SiteMessageRetired',
    # 社交
    'UserFollow', 'UserProfile', 'UserActivity',
    'UserBlock', 'UserMute', 'CategoryFollow', 'TagFollow', 'ContentReport',
    # 系统扩展
    'UserAPIKey', 'Webhook', 'UserDevice', 'ThemePreset',
    'ExportJob', 'UserWidget', 'SearchHistory',
]
