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
#: 从模块「.user」导入所需对象
from .user import User

# ---- 2. 分类与标签（文章归属维度）----
#: 从模块「.catalog」导入所需对象
from .catalog import Category, Tag

# ---- 3. 系列（文章连载聚合）----
#: 从模块「.series」导入所需对象
from .series import Series

# ---- 4. 文章（核心主模型，依赖 User/Category/Tag/Series）----
#: 从模块「.article」导入所需对象
from .article import (
    #: 该行执行对应逻辑（结合上下文理解）
    Article,
    #: 该行执行对应逻辑（结合上下文理解）
    ArticleHistory,
    #: 该行执行对应逻辑（结合上下文理解）
    ArticleQuerySet,
    #: 该行执行对应逻辑（结合上下文理解）
    ArticleShare,
    #: 该行执行对应逻辑（结合上下文理解）
    ShortLink,
    #: 该行执行对应逻辑（结合上下文理解）
    ScheduledPost,
#: 该行执行对应逻辑（结合上下文理解）
)

# ---- 5. 评论（依赖 Article/User）----
#: 从模块「.comment」导入所需对象
from .comment import (
    #: 该行执行对应逻辑（结合上下文理解）
    Comment,
    #: 该行执行对应逻辑（结合上下文理解）
    CommentReaction,
    #: 该行执行对应逻辑（结合上下文理解）
    CommentReport,
#: 该行执行对应逻辑（结合上下文理解）
)

# ---- 6. 读者互动（依赖 Article/User）----
#: 从模块「.interaction」导入所需对象
from .interaction import (
    #: 该行执行对应逻辑（结合上下文理解）
    ArticleBookmark,
    #: 该行执行对应逻辑（结合上下文理解）
    Favorite,
    #: 该行执行对应逻辑（结合上下文理解）
    FavoriteFolder,
    #: 该行执行对应逻辑（结合上下文理解）
    Rating,
    #: 该行执行对应逻辑（结合上下文理解）
    ReadingList,
    #: 该行执行对应逻辑（结合上下文理解）
    UserNote,
#: 该行执行对应逻辑（结合上下文理解）
)

# ---- 7. 日志（访问 / 修改 / 登录）----
#: 从模块「.logs」导入所需对象
from .logs import (
    #: 该行执行对应逻辑（结合上下文理解）
    AccessLog,
    #: 该行执行对应逻辑（结合上下文理解）
    EditLog,
    #: 该行执行对应逻辑（结合上下文理解）
    LoginHistory,
#: 该行执行对应逻辑（结合上下文理解）
)

# ---- 8. 通知 ----
#: 从模块「.notification」导入所需对象
from .notification import Notification

# ---- 9. 徽章 / 成就 / 积分 ----
#: 从模块「.badge」导入所需对象
from .badge import (
    #: 该行执行对应逻辑（结合上下文理解）
    Badge,
    #: 该行执行对应逻辑（结合上下文理解）
    PointLog,
    #: 该行执行对应逻辑（结合上下文理解）
    UserAchievement,
    #: 该行执行对应逻辑（结合上下文理解）
    UserBadge,
    #: 该行执行对应逻辑（结合上下文理解）
    UserPoint,
#: 该行执行对应逻辑（结合上下文理解）
)

# ---- 10. 站点信息 / 公告 / 友情链接 ----
#: 从模块「.site」导入所需对象
from .site import (
    #: 该行执行对应逻辑（结合上下文理解）
    FriendlyLink,
    #: 该行执行对应逻辑（结合上下文理解）
    SiteInfo,
    #: 该行执行对应逻辑（结合上下文理解）
    SiteNotice,
#: 该行执行对应逻辑（结合上下文理解）
)

# ---- 11. 审核日志 / 设置 / 推广申请 ----
#: 从模块「.moderation」导入所需对象
from .moderation import (
    #: 该行执行对应逻辑（结合上下文理解）
    ModerationLog,
    #: 该行执行对应逻辑（结合上下文理解）
    ModerationSettings,
    #: 该行执行对应逻辑（结合上下文理解）
    PromotionRequest,
#: 该行执行对应逻辑（结合上下文理解）
)

# ---- 12. 全站文案覆盖 / 弃用文案 ----
#: 从模块「.messages」导入所需对象
from .messages import (
    #: 该行执行对应逻辑（结合上下文理解）
    SiteMessage,
    #: 该行执行对应逻辑（结合上下文理解）
    SiteMessageRetired,
#: 该行执行对应逻辑（结合上下文理解）
)

# ---- 13. 社交关系 / 扩展资料 / 内容举报 ----
#: 从模块「.social」导入所需对象
from .social import (
    #: 该行执行对应逻辑（结合上下文理解）
    CategoryFollow,
    #: 该行执行对应逻辑（结合上下文理解）
    ContentReport,
    #: 该行执行对应逻辑（结合上下文理解）
    TagFollow,
    #: 该行执行对应逻辑（结合上下文理解）
    UserActivity,
    #: 该行执行对应逻辑（结合上下文理解）
    UserBlock,
    #: 该行执行对应逻辑（结合上下文理解）
    UserFollow,
    #: 该行执行对应逻辑（结合上下文理解）
    UserMute,
    #: 该行执行对应逻辑（结合上下文理解）
    UserProfile,
#: 该行执行对应逻辑（结合上下文理解）
)

# ---- 14. 系统扩展（API 密钥 / Webhook / 设备 / 主题 / 导出 / 小部件 / 搜索历史）----
#: 从模块「.system」导入所需对象
from .system import (
    #: 该行执行对应逻辑（结合上下文理解）
    ExportJob,
    #: 该行执行对应逻辑（结合上下文理解）
    SearchHistory,
    #: 该行执行对应逻辑（结合上下文理解）
    ThemePreset,
    #: 该行执行对应逻辑（结合上下文理解）
    UserAPIKey,
    #: 该行执行对应逻辑（结合上下文理解）
    UserDevice,
    #: 该行执行对应逻辑（结合上下文理解）
    UserWidget,
    #: 该行执行对应逻辑（结合上下文理解）
    Webhook,
#: 该行执行对应逻辑（结合上下文理解）
)

# 对外公开的模型名单：
# 1) 声明包的公共接口；2) 配合 ``from blog.models import *``；
# 3) 作为模型清单，新增模型时务必同步登记。
#: 定义变量「__all__」，保存对应数据（集合/元组）
__all__ = [
    # 用户
    #: 该行执行对应逻辑（结合上下文理解）
    'User',
    # 分类 / 标签
    #: 该行执行对应逻辑（结合上下文理解）
    'Category', 'Tag',
    # 系列
    #: 该行执行对应逻辑（结合上下文理解）
    'Series',
    # 文章领域
    #: 该行执行对应逻辑（结合上下文理解）
    'Article', 'ArticleQuerySet', 'ArticleHistory',
    #: 该行执行对应逻辑（结合上下文理解）
    'ArticleShare', 'ScheduledPost', 'ShortLink',
    # 评论领域
    #: 该行执行对应逻辑（结合上下文理解）
    'Comment', 'CommentReport', 'CommentReaction',
    # 读者互动
    #: 该行执行对应逻辑（结合上下文理解）
    'Favorite', 'FavoriteFolder', 'Rating',
    #: 该行执行对应逻辑（结合上下文理解）
    'ArticleBookmark', 'ReadingList', 'UserNote',
    # 日志
    #: 该行执行对应逻辑（结合上下文理解）
    'AccessLog', 'EditLog', 'LoginHistory',
    # 通知
    #: 该行执行对应逻辑（结合上下文理解）
    'Notification',
    # 徽章 / 成就 / 积分
    #: 该行执行对应逻辑（结合上下文理解）
    'Badge', 'UserBadge', 'UserPoint', 'PointLog', 'UserAchievement',
    # 站点
    #: 该行执行对应逻辑（结合上下文理解）
    'SiteInfo', 'SiteNotice', 'FriendlyLink',
    # 审核
    #: 该行执行对应逻辑（结合上下文理解）
    'ModerationLog', 'ModerationSettings', 'PromotionRequest',
    # 文案
    #: 该行执行对应逻辑（结合上下文理解）
    'SiteMessage', 'SiteMessageRetired',
    # 社交
    #: 该行执行对应逻辑（结合上下文理解）
    'UserFollow', 'UserProfile', 'UserActivity',
    #: 该行执行对应逻辑（结合上下文理解）
    'UserBlock', 'UserMute', 'CategoryFollow', 'TagFollow', 'ContentReport',
    # 系统扩展
    #: 该行执行对应逻辑（结合上下文理解）
    'UserAPIKey', 'Webhook', 'UserDevice', 'ThemePreset',
    #: 该行执行对应逻辑（结合上下文理解）
    'ExportJob', 'UserWidget', 'SearchHistory',
#: 该行执行对应逻辑（结合上下文理解）
]
