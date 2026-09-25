# -*- coding: utf-8 -*-
"""全站提示词 / 文案统一登记表（Single Source of Truth）—— Bug9 任务「2」。

为什么需要它
------------
改造前，用户可见文案散落在 ``views.py``（flash 消息、JSON 提示）、模板
（错误页 / 空状态 / 按钮）、静态 JS（``moeToast`` 文案）三处，共 2000+ 处中文字符串，
导致：①同一语义文案在不同页面写法不一致；②调整语气（例如统一加「喵~」）需要全局
搜索替换，极易遗漏；③无法统计与审校文案覆盖度。

设计（对齐需求：**后端以变量形式存储，可参考 siteinfo 中间件**）
-----------------------------------------------------------------
1. 所有文案集中登记在本模块的 ``MESSAGES`` 字典中，键为语义化英文 key，
   值为「二次元萌系」中文文案；带占位符的用 ``str.format`` 语义（``{}`` / ``{name}``）。
2. 访问方式（三种，覆盖三种调用场景）：
   - Python：``msg('auth.login_failed')`` / ``msg('promo.limit_warn', n=3, m=5)``；
   - 模板：上下文处理器注入 ``MSG`` 命名空间，直接 ``{{ MSG.auth.login_failed }}``；
   - 静态 JS：``/api/site-messages/`` 端点 + ``window.SITE_MSG``（base.html 注入），
     由 ``MOE_MSG`` 前端适配层统一点取，避免 JS 里硬编码中文。
3. 前端侧「不可用后端变量」的少量动态文案（含运行时计算的），
   统一从 ``window.SITE_MSG`` 读取，取不到时回退到脚本内同名默认值，
   保证 JS 独立可用（不阻塞渲染）。
4. 审校工具：``python manage.py messages_audit`` 扫描全站硬编码中文，
   输出「已登记 / 未登记」清单，便于持续收敛（本模块为唯一登记处）。

命名规范
--------
``<域>.<语义>``，域包括：``brand`` 站点 / ``nav`` 导航 / ``btn`` 按钮 /
``auth`` 认证 / ``err`` 错误页 / ``empty`` 空状态 / ``form`` 表单 /
``article`` 文章 / ``comment`` 评论 / ``moderation`` 审核 / ``promo`` 推广 /
``interact`` 互动 / ``search`` 搜索 / ``user`` 用户中心 / ``notify`` 通知 /
``badge`` 徽章成就 / ``misc`` 其他 / ``js`` 前端脚本专用。
"""
import time

from django.utils.html import escape as _escape

# ======================================================================
# 文案总表：唯一登记处。修改文案只改这里，全站同步生效。
# ======================================================================
MESSAGES = {
    # ------------------------------------------------------------------
    # brand · 站点品牌与固定标语
    # ------------------------------------------------------------------
    'brand.name': '萌语博客',
    'brand.tagline': '记录技术与生活的二次元小站',
    'brand.slogan': '🌸 愿这个小站也能让你写得开心、逛得治愈喵~',
    'brand.footer_about': '一个粉紫蓝萌系的二次元个人小站，记录技术与生活的碎碎念喵~',
    # 页脚（footer）文案：整站每页可见，接入后可在文案总表统一修改
    'brand.stats_articles': '📝 文章',
    'brand.stats_comments': '💬 评论',
    'brand.stats_views': '👁 阅读',
    'brand.stats_days': '⏳ 运行天数',
    'brand.stats_aria': '网站统计',
    'brand.status_link': '💚 站点状态',
    'footer.quick_nav': '🧭 快速导航',
    'footer.nav_home': '🏠 首页',
    'footer.nav_categories': '📁 分类',
    'footer.nav_tags': '🏷 标签',
    'footer.nav_archive': '🗂 归档',
    'footer.nav_series': '📚 系列',
    'footer.nav_random': '🎲 随机一篇',
    'footer.friendly_links': '🔗 友情链接',
    'footer.friend_apply': '💌 想交换友链？',
    'footer.friend_mail': '邮件联系站长',
    'footer.subscribe': '📡 关注与订阅',
    'footer.rss': '📡 RSS 订阅',
    'footer.api_docs': '🧩 API 文档',

    # ------------------------------------------------------------------
    # a11y · 无障碍名称与工具提示（title / aria-label）
    # ------------------------------------------------------------------
    # 这些文案不直接显示，但读屏软件与悬浮提示会用到；集中登记后同样可在后台修改。
    'a11y.reading_progress': '阅读进度',
    'a11y.page_progress': '页面加载进度',
    'a11y.main_nav': '主导航',
    'a11y.random_article': '随机一篇文章',
    'a11y.site_search': '全站搜索',
    'a11y.global_search': '全局搜索',
    'a11y.submit_search': '提交搜索',
    'a11y.search_suggest': '搜索建议',
    'a11y.search_history': '🕐 搜索历史',
    'a11y.toolbox': '工具箱',
    'a11y.toolbox_tip': '工具箱喵',
    'a11y.toolbox_head': '🎛 工具箱喵',
    'a11y.theme_toggle': '切换明暗主题',
    'a11y.mouse_effect': '切换鼠标跟随特效',
    'a11y.mouse_effect_aria': '切换鼠标特效',
    'a11y.sakura_mode': '樱花飘落三档开关',
    'a11y.sakura_mode_aria': '切换樱花模式',
    'a11y.sound_toggle': '切换交互音效',
    'a11y.contrast_toggle': '切换高对比度',
    'a11y.shortcut_help': '键盘快捷键（按 ?）',
    'a11y.shortcut_help_aria': '打开键盘快捷键帮助面板',
    'a11y.notification_open': '打开通知中心',
    'a11y.notification_panel': '通知面板',
    'a11y.notification_mark_all': '全部标记已读',
    'a11y.notification_footer': '查看全部通知',
    'a11y.user_menu': '用户菜单',
    'a11y.close_notice': '关闭公告',
    'a11y.close_shortcut_panel': '关闭快捷键面板',
    'a11y.shortcut_list': '快捷键列表',
    'a11y.offline_hint': '离线提示',
    'a11y.online_status': '在线',
    'a11y.sync_offline': '同步离线数据',
    'a11y.offline_articles': '离线可用文章',
    'a11y.pending_sync': '待同步数量',
    'a11y.retry_all': '重试全部失败请求',
    'a11y.clear_queue': '清空待同步队列',
    'a11y.storage_used': '本地存储用量',
    'a11y.storage_limit': '本地存储上限',
    'a11y.reading_ring': '阅读进度环',
    'a11y.reading_ring_desc': '环形进度指示当前文章阅读百分比',
    'a11y.quick_menu': '展开快捷菜单',
    'footer.nav_aria': '快速导航',
    'footer.friend_aria': '友情链接',
    'footer.subscribe_aria': '关注与订阅',

    # ------------------------------------------------------------------
    # toolbox · 工具箱面板与快捷键说明
    # ------------------------------------------------------------------
    'toolbox.theme_label': '明暗主题',
    'toolbox.mouse_label': '鼠标跟随特效',
    'toolbox.sakura_label': '樱花飘落',
    'toolbox.sound_label': '交互音效',
    'toolbox.contrast_label': '高对比度',
    'toolbox.shortcut_label': '键盘快捷键',
    'toolbox.notification_head': '🔔 通知喵',
    'toolbox.notification_empty': '这里还没有通知喵~',
    'toolbox.notification_all': '查看全部通知 →',
    'toolbox.menu_head': '🐾 我的小站',
    'toolbox.menu_settings': '个人中心 / 设置',
    'toolbox.menu_badges': '我的徽章',
    'toolbox.menu_notifications': '通知中心',
    'toolbox.menu_favorites': '我的收藏',
    'toolbox.menu_history': '阅读历史',
    'toolbox.menu_liked': '我的点赞',
    'toolbox.menu_comments': '我的评论',
    'toolbox.menu_articles': '我的文章',
    'toolbox.menu_console': '运营看板',
    'toolbox.menu_site_settings': '站点设置',
    'toolbox.menu_write': '写新文章',
    'toolbox.shortcut_title': '⌨ 键盘快捷键喵',
    'toolbox.shortcut_search': '聚焦搜索喵',
    'toolbox.shortcut_panel': '打开本面板喵',
    'toolbox.shortcut_nav': '下一篇 / 上一篇喵',
    'toolbox.shortcut_top': '回到顶部喵',
    'toolbox.shortcut_focus': '切换专注模式喵',
    'toolbox.shortcut_new': '新建文章喵',
    'toolbox.shortcut_close': '关闭弹窗喵',
    'toolbox.shortcut_scroll': '滚动到顶部喵',
    'toolbox.easter_egg': '小提示：同时按下 ↑↓←→ B A 可以触发彩蛋喵~ 🌸',

    # ------------------------------------------------------------------
    # offline · PWA 离线与同步
    # ------------------------------------------------------------------
    'offline.loading': '加载中喵...',
    'offline.disconnected': '📡 网络已断开，当前为离线模式',
    'offline.sync': '🔄 同步',
    'offline.retry_all': '重试全部',
    'offline.clear_queue': '清空队列',

    # ------------------------------------------------------------------
    # nav · 导航与菜单
    # ------------------------------------------------------------------
    'nav.home': '🏠 首页',
    'nav.articles': '文章',
    'nav.notes': '笔记',
    'nav.pages': '独立页面',
    'nav.categories': '分类',
    'nav.tags': '标签',
    'nav.archive': '归档',
    'nav.series': '系列',
    'nav.random': '随机喵',
    'nav.login': '🔑 登录喵',
    'nav.register': '✨ 注册喵',
    'nav.console': '运营看板',
    'nav.moderation': '内容审核',
    'nav.notifications': '通知中心',
    'nav.settings': '个人设置',
    'nav.profile': '个人主页',
    'nav.write': '✍ 写新文章',
    'nav.logout': '🚪 退出登录',
    'nav.search_placeholder': '搜索点什么呢…（按 / 聚焦）',
    'nav.search_btn': '搜索喵',
    'nav.back_top': '回到顶部',
    'nav.quick_menu': '展开快捷菜单',

    # ------------------------------------------------------------------
    # btn · 全站按钮文案（含 aria-label 语义）
    # ------------------------------------------------------------------
    'btn.confirm': '确定喵',
    'btn.cancel': '再想想',
    'btn.save': '保存喵',
    'btn.submit': '提交喵',
    'btn.delete': '删除喵',
    'btn.edit': '编辑喵',
    'btn.back_home': '回到首页喵',
    'btn.back_prev': '← 返回上一页喵',
    'btn.home': '🏠 回首页喵',
    'btn.retry': '再试一次喵',
    'btn.close': '关闭',
    'btn.more': '导出/更多',
    'btn.loading': '加载中喵…',
    'btn.view_detail': '查看详情喵',

    # ------------------------------------------------------------------
    # auth · 注册 / 登录 / 账号
    # ------------------------------------------------------------------
    'auth.login_failed': '用户名或密码不对呢~再试试喵😿',
    'auth.login_required': '请先登录喵~',
    'auth.register_success': '注册成功啦~欢迎加入喵~🎉',
    'auth.logout_success': '已退出登录，下次再来玩喵~👋',
    'auth.register_title': '加入我们 🌸',
    'auth.login_title': '欢迎回来 🌸',
    'auth.username_empty': '用户名和密码都要填喵~📝',
    'auth.username_too_long': '用户名太长啦~ 最多 150 个字符哦',
    'auth.username_taken': '这个名字已经被别的小伙伴用了呢~换一个吧😢',
    'auth.password_mismatch': '两次密码不一样呢~再确认一下喵🔍',
    'auth.password_too_short': '密码至少要 8 位哦~为了安全嘛🔒',
    'auth.email_invalid': '邮箱格式不对呢~再检查一下喵~📧',
    'auth.field_username_hint': '3-50 位字母、数字或下划线',
    'auth.field_username_rule': '用户名需为 3-50 位字母、数字或下划线',
    'auth.password_hint': '密码（至少 8 位）',
    'auth.confirm_password': '确认密码',
    'auth.nickname_optional': '昵称（可选）',
    'auth.email_optional': '邮箱（可选，用于找回密码）',
    'auth.have_account': '已有账号？',
    'auth.no_account': '还没有账号？',
    'auth.go_login': '直接登录喵',
    'auth.go_register': '注册喵',
    'auth.logging_in': '登录中喵…',
    'auth.registering': '注册中喵…',
    'auth.password_ok_hint': '🎉 验证通过，可以注册啦',
    'auth.clear_form': '清空喵',
    'auth.network_error': '网络开小差了，稍后再试喵~',
    'auth.old_password_wrong': '旧密码不对呢~ 再试试喵~ 🔍',
    'auth.new_password_too_short': '新密码至少要 8 位哦~ 🔒',
    'auth.new_password_mismatch': '两次输入的新密码不一样呢~ 🔑',
    'auth.password_changed': '密码已修改成功喵~ 🔐',
    'auth.profile_updated': '基本资料已更新喵~ 🌸',
    'auth.avatar_updated': '头像已更新啦~ ✨',
    'auth.avatar_too_large': '头像不能超过 2MB 呢~ 太大了喵~ 📦',
    'auth.avatar_invalid_type': '只支持 jpg / png / gif / webp 格式的图片哦~ 🖼',
    'auth.avatar_not_image': '文件不是有效的图片呢~ 换一个吧喵~ 😿',
    'auth.avatar_choose': '请选择要上传的头像文件喵~ 📷',

    # ------------------------------------------------------------------
    # err · 错误页（404 / 403 / 400 / 500）
    # ------------------------------------------------------------------
    'err.404_title': '404 - 页面被喵喵吃了喵~',
    'err.404_heading': '页面被喵喵吃了喵~',
    'err.404_desc': '你找的内容好像跑到异次元去了…',
    'err.404_hint': '试试搜索，或者回到首页看看别的内容吧喵~',
    'err.403_title': '403 - 这里禁止进入喵',
    'err.403_heading': '这里禁止进入喵',
    'err.403_desc': '这扇门后面有喵喵守着，你的通行证不够哦…',
    'err.403_hint': '如果你是管理员，请先登录再试；否则回到首页逛逛吧喵~',
    'err.400_title': '400 - 请求有点奇怪喵',
    'err.400_heading': '请求有点奇怪喵',
    'err.400_desc': '这个请求喵喵看不懂，可能链接复制少了一段…',
    'err.400_hint': '重新从首页进入试试吧喵~',
    'err.500_title': '500 - 服务器酱宕机啦…',
    'err.500_heading': '服务器酱宕机啦…',
    'err.500_desc': '服务器酱累倒了，正在紧急抢救中，稍后再来看看吧喵~',
    'err.500_hint': '如果一直这样，请联系站长喵~',
    'err.search_placeholder': '搜索点什么呢…',
    'err.hot_articles': '🔥 热门文章，去看看吧喵',
    'err.play_game': '🌸 玩个小游戏吧喵（接樱花）',
    'err.game_start': '开始接樱花喵~',
    'err.game_score': '得分：',
    # API 错误信封（/api/ 请求）
    'err.api_400': '请求参数有误喵',
    'err.api_403': '没有权限哦喵',
    'err.api_404': '接口不存在喵',
    'err.api_500': '服务器开小差了喵',
    'err.api_generic': '出错了喵',
    # 模板渲染失败时的内联兜底页标记
    'err.not_found_short': '文章不存在喵~',
    'err.permission_denied': '喵？你没有权限删除这个呢~🚫',
    'err.only_own_article': '只能编辑自己的文章呢~😤',
    'err.method_not_allowed': '请用 POST 提交',
    'err.debug_only': '仅 DEBUG 模式可用',
    'err.admin_only': '仅管理员可操作',
    'err.bad_request': '操作不正确',
    'err.feature_not_found_short': '功能不存在喵~',

    # ------------------------------------------------------------------
    # empty · 空状态文案
    # ------------------------------------------------------------------
    'empty.articles': '还没有文章喵~ 快去写第一篇吧！',
    'empty.search': '没有找到相关内容喵…换个关键词试试？',
    'empty.comments': '还没有人评论，来抢沙发喵~',
    'empty.notifications': '暂时没有新通知喵~',
    'empty.favorites': '收藏夹还是空的喵~ 看到喜欢的文章点个收藏吧！',
    'empty.likes': '还没有点赞过任何文章喵~',
    'empty.history': '还没有阅读记录喵~ 去逛逛吧！',
    'empty.series': '还没有创建系列喵~ 系列可以把连载文章串起来哦！',
    'empty.tags': '还没有标签喵~',
    'empty.categories': '还没有分类喵~',
    'empty.moderation': '暂无待审核内容喵~',
    'empty.promotions': '暂无推广申请喵~',
    'empty.trash': '回收站是空的喵~',
    'empty.reports': '暂时没有待处理举报喵~',
    'empty.friendly_links': '暂无友链喵~',
    'empty.badges_locked': '继续加油就能解锁更多徽章喵~',
    'empty.related': '暂时没有相关文章喵~',

    # ------------------------------------------------------------------
    # form · 表单通用提示
    # ------------------------------------------------------------------
    'form.required': '这一项还没有填写喵~',
    'form.invalid': '这一项填写不正确喵~',
    'form.title_required': '标题不能为空喵~📝',
    'form.save_failed': '保存失败了，请稍后再试喵~',
    'form.unsaved_confirm': '还有未保存的内容，确定要离开吗喵？',
    'form.uploading': '上传中喵…',
    'form.content_label': '正文',
    'form.upload_ok': '上传成功喵~',
    # 表单字段标签与无障碍名称：这些文案在多个模板重复出现（登录 / 注册 / 设置 / 审核…），
    # 按「域」建键而不是按「文件」建键，避免同一个「用户名」出现五六个键各改一次。
    'form.username': '用户名',
    'form.username_aria': '用户名',
    'form.nickname': '昵称',
    'form.nickname_aria': '昵称',
    'form.email': '邮箱',
    'form.email_aria': '邮箱',
    'form.password': '密码',
    'form.password_aria': '密码',
    'form.password2': '确认密码',
    'form.password2_aria': '确认密码',
    'form.submit_login': '登录',
    'form.submit_register': '注册喵',
    'form.no_js_login': '🌸 登录表单可正常提交，但免刷新登录需要 JavaScript；当前将以普通方式提交。',
    'form.no_js_register': '🌸 注册表单可正常提交，但密码强度实时校验需要 JavaScript。',

    # ------------------------------------------------------------------
    # article · 文章发布 / 编辑 / 状态
    # ------------------------------------------------------------------
    'article.published': '文章已发布喵~✨',
    'article.submitted_review': '文章已提交审核，通过后就会和大家见面喵~ ⏳',
    'article.saved': '修改已保存啦~🌸',
    'article.trashed': '文章已收进回收站，需要时还能找回喵~ 🗑️',
    # 文章详情页（detail.html）：正文页是全站访问量最大的页面，逐块登记
    'article.no_js': '🌸 检测到 JavaScript 已禁用，本文目录 / 点赞 / 评论 / 评分等功能可能无法使用。',
    'article.cover_placeholder_alt': '文章封面占位',
    'article.pending_author_note': '这篇内容正在等待管理员审核，',
    'article.pending_author_note2': '目前只有作者本人和管理员能看到',
    'article.pending_author_note3': '，审核通过后才会公开喵~',
    'article.scheduled_visibility': '你本人与管理员',
    'article.published_at_aria': '发布时间',
    'article.edited_at_title': '最后编辑时间',
    'article.read_time_aria': '预计阅读时间',
    'article.like_title': '点赞',
    'article.delete_confirm': '真的要把这篇内容收进回收站吗？之后可在审核后台的回收站恢复喵~',
    'article.tag_list_aria': '文章标签',
    'article.tags_prefix': '🏷 标签：',
    'article.series_list_aria': '本系列文章',
    'article.edit_logs_aria': '修改记录',
    'article.edit_logs_list_aria': '文章修改记录',
    'article.snapshot_title': '版本快照对比',
    'article.snapshot_before': '🕒 修改前（快照）',
    'article.snapshot_now': '✨ 当前内容',
    'article.pager_aria': '文章上一篇下一篇导航',
    'article.prev': '← 上一篇',
    'article.prev_none': '已经是最早一篇啦~',
    'article.next': '下一篇 →',
    'article.next_none': '已经是最新一篇啦~',
    'article.related_aria': '相关推荐',
    'article.related_you_may_like': '🌸 你可能也喜欢喵',
    'article.related': '📖 相关推荐',
    'article.related_list_aria': '相关推荐文章列表',
    'article.author_home': '查看主页 →',
    'article.author_home_aria': '查看作者主页',

    # 阅读增强（阅读设置 / 朗读 / 专注模式 / 导出）
    'reading.sidebar_stats': '站点统计',
    'reading.stats_views_total': '总阅读',
    'reading.stats_today': '今日访问',
    'reading.online_tip': '最近5分钟活跃',
    'reading.tag_cloud': '标签云',
    'reading.clear_history_title': '清除阅读历史',
    'reading.focus_aria': '专注阅读模式',
    'reading.focus_btn': '专注喵',
    'reading.settings_open_aria': '打开阅读设置',
    'reading.tts_aria': '朗读本文',
    'reading.copy_all': '📋 全文复制喵',
    'reading.export_pdf': '📄 导出 PDF 喵',
    'reading.export_md': '📝 导出 Markdown 喵',
    'reading.print': '🖨 打印本文',
    'reading.rating_heading': '🌟 评分本文喵：',
    'reading.settings_title': '⚙️ 阅读设置喵',
    'reading.settings_close_aria': '关闭阅读设置',
    'reading.font_size': '字体大小',
    'reading.font_size_aria': '字体大小调节',
    'reading.font_minus_aria': '减小字体',
    'reading.font_plus_aria': '增大字体',
    'reading.line_height': '行高',
    'reading.line_height_aria': '行高调节',
    'reading.font_family': '字体',
    'reading.font_family_aria': '字体切换',
    'reading.font_sans': '黑体',
    'reading.font_serif': '宋体',
    'reading.font_mono': '等宽',
    'reading.theme_color': '主题色',
    'reading.theme_color_aria': '主题色选择',
    'reading.theme_default_aria': '默认紫粉',
    'reading.theme_blue_aria': '蓝绿主题',
    'reading.theme_orange_aria': '橙黄主题',
    'reading.theme_rose_aria': '玫瑰主题',
    'reading.a11y_mode': '辅助模式',
    'reading.eye_care': '👁 护眼',
    'reading.amoled': '🌑 纯黑',
    'reading.paper': '📜 纸张',
    'reading.tts_play': '🔊 朗读本文',
    'reading.tts_toggle': '▶ 播放 / 暂停',
    'reading.tts_stop': '■ 停止',
    'reading.tts_rate_aria': '朗读语速',
    'reading.tts_idle': '未开始朗读',
    'reading.body_aria': '文章正文',

    # 目录（TOC）与分享面板
    'article.toc_aria': '文章目录',
    'article.toc_title': '📖 目录',
    'article.toc_drag_aria': '拖拽移动目录',
    'article.toc_copy': '📋 复制目录',
    'article.toc_copy_aria': '复制目录到剪贴板',
    'article.toc_export': '📤 导出大纲喵',
    'article.toc_export_aria': '导出大纲为 Markdown',
    'article.share_panel_title': '📤 分享本文喵',
    'article.share_panel_aria': '关闭分享面板',
    'article.share_card': '🎴 生成分享卡片',
    'article.share_card_aria': '生成分享卡片',
    'article.share_qr_hint': '扫码阅读喵~',
    'article.shortlink_aria': '短链接',
    'article.copy': '复制',
    'article.copy_shortlink_aria': '复制短链接',
    'article.share_weibo': '🌊 微博',
    'article.share_weibo_title': '分享到微博',
    'article.share_twitter_title': '分享到 Twitter/X',
    'article.share_copy_title': '复制文章链接',
    'article.share_like_aria': '点赞这篇文章',
    'article.share_dislike_aria': '踩一下这篇文章',
    'article.share_fav_aria': '收藏这篇文章',
    'article.share_open_aria': '分享本文',
    'article.share_btn': '分享喵：',

    # 评论区（detail 页内的评论 UI）
    'comment.section_aria': '评论区',
    'comment.count_suffix': '条评论喵',
    'comment.toolbar_aria': '评论工具栏',
    'comment.sort_aria': '评论排序',
    'comment.sort_new': '最新',
    'comment.sort_new_aria': '按最新排序',
    'comment.sort_hot': '最热',
    'comment.sort_hot_aria': '按最热排序',
    'comment.search_aria': '搜索评论内容',
    'comment.search_placeholder': '搜索评论内容…',
    'comment.form_aria': '发表评论',
    'comment.format_aria': '评论格式工具栏',
    'comment.bold': '加粗喵',
    'comment.bold_aria': '加粗',
    'comment.italic': '斜体喵',
    'comment.italic_aria': '斜体',
    'comment.code': '行内代码喵',
    'comment.code_aria': '行内代码',
    'comment.link': '插入链接喵',
    'comment.link_aria': '插入链接',
    'comment.content_aria': '评论内容',
    'comment.placeholder': '说点什么吧~ 🌸（可用上方工具栏加粗/斜体/链接/代码，最多 10000 字）',
    'comment.emoji_aria': '表情喵',
    'comment.upload_aria': '上传评论图片',
    'comment.pick_image_aria': '选择评论图片',
    'comment.submit': '发表评论喵',
    'comment.md_help': '💡 Markdown 语法帮助',
    'comment.md_expand': '点击展开 ▾',
    'comment.md_bold': '加粗、',
    'comment.md_italic': '斜体、',
    'comment.list_aria': '评论列表',
    'comment.empty_alt': '还没有评论',
    'comment.empty': '还没有评论，快来抢沙发喵 🌸',

    # 推广申请弹窗（detail 页内）
    'promo.dialog_apply': '申请',
    'promo.dialog_reason': '申请理由',
    'promo.dialog_submit': '提交申请',

    # 缓存调试（仅 DEBUG）
    'article.cache_debug': '🐱 缓存调试（?debug_cache=1，仅 DEBUG 显示）',
    # 编辑页（edit.html）：表单标题、密码提示、提交按钮的两种状态
    'edit.heading_new': '✍ 写新内容',
    'edit.heading_edit': '📝 编辑文章',
    'edit.password_set': '已设置密码（留空则不修改）',
    'edit.password_unset': '设置后访问需输入密码',
    'edit.submit_new': '发布喵',
    'edit.submit_edit': '保存修改喵',
    'edit.submit_new_aria': '发布新文章',
    'edit.submit_edit_aria': '保存修改',
    'edit.no_excerpt': '（暂无摘要）',
    # 分页码：审核页 7 处复用同一句式，属于有语义的提示语（保留）
    'misc.anonymous': '匿名',
    'article.save_failed': '文章保存失败，请稍后再试喵~',
    'article.draft_badge': '草稿',
    'article.pending_badge': '⏳ 待审核',

    # ------------------------------------------------------------------
    # comment · 评论
    # ------------------------------------------------------------------
    'comment.empty_content': '评论内容不能为空喵~ 📝',
    'comment.posted': '评论成功喵~ 💬',
    'comment.post_failed': '评论发送失败了，稍后再试喵~',
    'comment.pending_banner': '评论已提交，等待审核通过后公开喵~ ⏳',
    'comment.recalled': '评论已撤回喵~',
    'comment.recall_failed': '撤回失败，可能已超过可撤回时间喵~',
    'comment.placeholder': '说点什么吧，友善发言喵~',
    'comment.reported': '举报已提交，管理员会尽快处理喵~',
    'comment.report_dismissed': '已标记举报不成立，评论予以保留~',
    'comment.op_badge': '楼主',
    'comment.only_op': '只看楼主',

    # ------------------------------------------------------------------
    # moderation · 审核流
    # ------------------------------------------------------------------
    'moderation.title': '🛡 内容审核',
    'moderation.admin_only_badge': '管理员限定',
    'moderation.settings_saved': '审核全局设置已保存喵~ ⚙️',
    'moderation.already_handled': '这条申请已经处理过啦~',
    'moderation.tab_articles': '📝 待审文章',
    'moderation.tab_reports': '🚩 待处理举报',
    'moderation.tab_promotions': '✨ 推广申请',
    'moderation.tab_history': '📜 审核历史',
    'moderation.tab_trash': '🗑 回收站',
    'moderation.exec_summary': '🛠 系统执行状态',
    'moderation.exec_success': '✅ 执行成功',
    'moderation.exec_skipped': '⏸ 已达上限未执行',
    'moderation.exec_failed': '⚠️ 执行失败',
    'moderation.exec_not_run': '⏳ 未执行',
    'moderation.scheduled_pending_badge': '⏰ 定时投稿·到点转入审核',
    # 文案总表管理页（/console/site-messages/）的保存 / 重置反馈
    'moderation.msg_no_change': '没有检测到改动喵~',

    # ------------------------------------------------------------------
    # promo · 置顶 / 精华 / 热门
    # ------------------------------------------------------------------
    'promo.pin': '置顶',
    'promo.feature': '精华',
    'promo.hot': '热门',
    'promo.apply_pin': '📌 申请置顶',
    'promo.apply_feature': '⭐ 申请精华',
    'promo.apply_hot': '🔥 申请热门',
    'promo.duplicate': '已经提交过申请，正在审核中哦~',
    'promo.reason_required': '请填写申请理由喵~',
    'promo.submitted': '申请已提交，等待管理员审核喵~',
    'promo.only_own': '只能给自己的文章申请哦~',
    'promo.bad_kind': '申请类型不正确',
    'promo.set': '设置',
    'promo.unset': '取消',
    'promo.reason_placeholder': '说说为什么这篇文章值得推荐给大家吧~',

    # ------------------------------------------------------------------
    # interact · 点赞 / 收藏 / 关注 / 评分
    # ------------------------------------------------------------------
    'interact.like': '点赞喵',
    'interact.liked': '已赞喵',
    'interact.dislike': '踩一下喵',
    'interact.disliked': '已踩喵',
    'interact.favorite': '收藏喵',
    'interact.favorited': '已收藏喵',
    'interact.follow': '关注喵',
    'interact.followed': '已关注喵',
    'interact.share': '分享喵',
    'interact.copy_link': '复制链接',
    'interact.link_copied': '链接已复制喵~ 🔗',
    'interact.rating_required': '评分必须是 1~5 星哦~⭐',
    'interact.rating_thanks': '感谢评分喵~ ⭐',
    'interact.login_first': '登录后才能操作哦~ 先去登录喵🔑',
    'interact.action_failed': '操作失败了，稍后再试喵~',

    # ------------------------------------------------------------------
    # search · 搜索
    # ------------------------------------------------------------------
    'search.title': '搜索结果',
    # 首页 / 列表页（index）文案：站点主浏览路径，接入后可在文案总表统一修改
    'search.crumb_aria': '面包屑',
    'index.no_js': '🌸 检测到浏览器已禁用 JavaScript，文章筛选 / 搜索 / 点赞等交互将不可用。',
    'index.main_aria': '文章列表主区域',
    'index.sidebar_aria': '侧边栏',
    'index.right_sidebar_aria': '右侧边栏',
    'index.sort': '🔀 排序',
    'index.sort_new': '🆕 最新',
    'index.sort_hot': '🔥 热门',
    'index.kind': '📚 内容类型',
    'index.kind_all': '🌈 全部',
    'index.kind_article': '📰 文章',
    'index.kind_note': '📝 笔记',
    'index.kind_page': '📄 独立页面',
    'index.cat_nav': '🗂 分类导航',
    'index.cat_nav_aria': '分类导航',
    'index.cat_empty': '还没有分类喵',
    'index.tag_cloud': '☁️ 标签云',
    'index.tag_empty': '还没有标签喵',
    'index.cat_quick_aria': '分类快速切换',
    'index.all': '全部',
    'index.avg_rating': '平均分',
    'index.write_default_kind': '文章',
    'index.no_result_alt': '没有找到相关内容',
    'index.no_result': '没有找到相关内容喵',
    'index.no_result_hint': '换个关键词试试喵~ 或者看看这些热门文章吧',
    'index.see_all': '✨ 看看全部文章',
    'index.hot_aria': '热门推荐',
    'index.hot': '🔥 热门推荐',
    'index.empty_alt': '这里还什么都没有',
    'index.empty': '这里还什么都没有喵',
    'index.empty_write': '来写第一篇吧',
    'index.empty_login': '登录后即可发布。',
    'index.hot_search': '🔍 热门搜索',
    'index.hot_articles': '🔥 热门文章',
    'index.hot_range_aria': '热门榜时间范围',
    'index.week': '本周',
    'index.week_aria': '本周热门',
    'index.month': '本月',
    'index.month_aria': '本月热门',
    'index.all_time': '总榜',
    'index.all_time_aria': '总热门',
    'index.hot_articles_aria': '热门文章',
    'search.no_keyword': '还没有输入关键词喵~',
    'search.history_cleared': '搜索历史已清空喵~',

    # ------------------------------------------------------------------
    # user · 用户中心
    # ------------------------------------------------------------------
    'user.center': '个人中心',
    'user.article_count': '文章',
    'user.views_total': '阅读',
    'user.followers': '粉丝',
    'user.following': '关注',
    'user.no_bio': '这位作者很神秘，还没有留下简介~',
    'user.my_articles': '我的文章',
    'user.my_collection': '我的收藏',

    # ------------------------------------------------------------------
    # notify · 通知
    # ------------------------------------------------------------------
    'notify.mark_all_read': '全部已读',
    'notify.empty': '暂时没有新通知喵~',

    # ------------------------------------------------------------------
    # badge · 徽章与成就（Bug9 任务「1」个人中心可视化面板）
    # ------------------------------------------------------------------
    'badge.panel_title': '🏅 我的徽章与成就',
    'badge.panel_subtitle': '每一枚徽章都是你在这里留下的足迹喵~',
    'badge.obtained': '已获得',
    'badge.locked': '未获得',
    'badge.obtained_prefix': '已获得',
    'badge.collapse_locked': '收起未获得的徽章',
    'badge.how_to_get': '如何获得',
    'badge.none_yet': '还没有获得徽章喵~ 看看下面的获取方式，去解锁第一枚吧！',

    # ------------------------------------------------------------------
    # misc · 其他
    # ------------------------------------------------------------------    'misc.under_construction': '这里还在建设中喵~',
    'misc.copy_ok': '已复制到剪贴板喵~ 📋',
    'misc.copy_failed': '复制失败了，请手动选择吧喵~',
    'misc.theme_light': '切换到亮色主题',
    'misc.theme_dark': '切换到暗色主题',
    'misc.back_home': '回到首页喵',
    'misc.series_created': '系列创建成功喵~现在写文章就能归入它啦✨',
    'misc.series_name_required': '系列名称不能为空喵~📝',
    'misc.site_saved': '站点信息已保存，全站立即生效喵~',

    # ------------------------------------------------------------------
    # live2d · 看板娘（Bug9 任务2：用户可见提示也统一登记）
    # ------------------------------------------------------------------
    'live2d.model_missing': '模型文件不存在喵~ 换一个看看吧',
    'live2d.bad_choice': '无效的选择，只能是石头 / 剪刀 / 布喵~',
    'live2d.switch_ok': '换好新衣服啦~好看吗？',
    'live2d.game_win': '耶！人家赢啦~',
    'live2d.game_lose': '呜…这局你赢了呢',
    'live2d.game_draw': '平局！再来一局吧喵~',

    # ------------------------------------------------------------------
    # js · 静态脚本专用（通过 /api/site-messages/ 下发到 window.SITE_MSG）
    # ------------------------------------------------------------------
    'js.network_error': '网络开小差了，稍后再试喵~',
    'js.confirm_default': '请确认喵~',
    'js.confirm_ok': '确定喵',
    'js.confirm_cancel': '再想想',
    'js.loading': '加载中喵…',
    'js.load_more': '加载更多喵~',
    'js.no_more': '没有更多了喵~',
    'js.copied': '已复制喵~ 📋',
    'js.offline': '当前处于离线状态喵~',
    'js.online_again': '网络恢复啦~ 🔄',
    'js.unsaved_leave': '有内容还没保存，真的要离开吗喵？',
    'js.delete_confirm': '确定要删除吗？删除后可以在回收站找回喵~',
    'js.generic_error': '出了点小问题喵，稍后再试~',

    # ======================================================
    # auto · 批量自动接入的文案
    # ------------------------------------------------------
    # 由 docs/bugfix_20260926_bug9/scripts/tools/batch_wire_templates.py
    # 自动登记：这些文案原先硬编码在模板里，接入后可在「文案总表」统一修改。
    # key 名保留中文是为了保证覆盖速度；如需规范命名可后续重命名
    # （重命名只影响注册表与映射，风险低）。
    # ======================================================
    'auto.200_字': '/200 字',
    'auto.404_数': '🚫 404 数：',
    'auto.amoled_纯黑模式': 'AMOLED 纯黑模式',
    'auto.javascript_已禁用_分类卡片的悬停动效': '🌸 JavaScript 已禁用，分类卡片的悬停动效不可用，点击仍可正常进入分类。',
    'auto.javascript_已禁用_归档时间轴的入场动': '🌸 JavaScript 已禁用，归档时间轴的入场动画将不播放，文章列表仍可正常浏览。',
    'auto.javascript_已禁用_标签云效果将降级为': '🌸 JavaScript 已禁用，标签云效果将降级为普通布局，点击标签仍可正常访问。',
    'auto.javascript_已禁用_樱花飘落动画与热门': '🌸 JavaScript 已禁用，樱花飘落动画与热门文章快捷跳转将降级。',
    'auto.javascript_已禁用_状态页的数据统计动': '🌸 JavaScript 已禁用，状态页的数据统计动画将不播放，服务健康信息仍以服务端渲染展示。',
    'auto.logo_表情': 'Logo 表情',
    'auto.meta_description_建议_8016': 'meta description，建议 80~160 字',
    'auto.一个粉紫蓝萌系的二次元小站': '一个粉紫蓝萌系的二次元小站…',
    'auto.上一页': '‹ 上一页',
    'auto.上一页喵': '上一页喵',
    'auto.上传封面图片': '上传封面图片',
    'auto.上传新头像': '上传新头像',
    'auto.上传系列封面': '上传系列封面',
    'auto.下一页': '下一页 ›',
    'auto.下一页喵': '下一页喵',
    'auto.不归属系列': '不归属系列',
    'auto.个人介绍': '个人介绍',
    'auto.举报不成立_保留': '🙆 举报不成立·保留',
    'auto.举报分页': '举报分页',
    'auto.举报理由': '举报理由：',
    'auto.举报这条评论': '举报这条评论',
    'auto.二次元': '二次元',
    'auto.仅支持_jpg_png_gif_webp_大小不': '仅支持 jpg / png / gif / webp，大小不超过 2MB，选好后可拖动裁剪喵~',
    'auto.介绍一下自己吧喵': '介绍一下自己吧喵~ 🌸',
    'auto.作者头像': '作者头像',
    'auto.例如_django_教程_踩坑记录': '例如：Django, 教程, 踩坑记录',
    'auto.保存修改喵': '保存修改喵',
    'auto.保存偏好喵': '保存偏好喵',
    'auto.保存即生效': '保存即生效',
    'auto.保存头像喵': '保存头像喵',
    'auto.保存设置': '💾 保存设置',
    'auto.修改密码': '🔐 修改密码',
    'auto.修改密码_2': '修改密码',
    'auto.先编辑': '✏ 先编辑',
    'auto.全站文案总表_提示词': '💬 全站文案总表（提示词）',
    'auto.全部动作': '全部动作',
    'auto.全部标签': '📑 全部标签',
    'auto.关于小站文案': '关于小站文案',
    'auto.关闭预览': '关闭预览',
    'auto.再次输入新密码': '再次输入新密码',
    'auto.写文章': '✍ 写文章',
    'auto.写文章时就可以把它归入一个系列啦': '写文章时就可以把它归入一个系列啦。',
    'auto.分类卡片': '分类卡片',
    'auto.分类文章分布': '📂 分类文章分布',
    'auto.分钟读完': '分钟读完',
    'auto.分页': '分页',
    'auto.创建文章系列': '✨ 创建文章系列',
    'auto.创建第一个系列喵': '✨ 创建第一个系列喵',
    'auto.创建系列': '创建系列',
    'auto.创建系列喵': '✨ 创建系列喵',
    'auto.创建系列表单': '创建系列表单',
    'auto.刷新静态缓存': '♻️ 刷新静态缓存',
    'auto.前端': '前端',
    'auto.加入于': '🌸 加入于',
    'auto.动作': '动作：',
    'auto.博客技术二次元': '博客,技术,二次元',
    'auto.即将对选中的': '即将对选中的',
    'auto.去写第一篇': '去写第一篇',
    'auto.去首页逛逛': '🏠 去首页逛逛',
    'auto.参数': '参数：',
    'auto.发布状态': '发布状态',
    'auto.发布的文章': '📖 发布的文章',
    'auto.发送喵': '发送喵',
    'auto.取消并返回': '取消并返回',
    'auto.名称': '🔤 名称',
    'auto.名称前的_emoji': '名称前的 Emoji',
    'auto.名额已满_新通过的置顶申请会标记为已达上限未执行': '（名额已满：新通过的置顶申请会标记为「已达上限未执行」）',
    'auto.后台运营面板': '后台运营面板',
    'auto.品牌实时预览': '品牌实时预览',
    'auto.品牌展示': '🌸 品牌展示',
    'auto.响应示例': '响应示例：',
    'auto.回复': '↪ 回复',
    'auto.回复内容': '回复内容',
    'auto.回复对象': '回复对象',
    'auto.回复这条评论': '回复这条评论',
    'auto.回收站文章分页': '回收站文章分页',
    'auto.回收站评论分页': '回收站评论分页',
    'auto.回收站里没有文章喵': '回收站里没有文章喵~',
    'auto.回收站里没有评论喵': '回收站里没有评论喵~',
    'auto.回看板': '← 回看板',
    'auto.回首页': '🏠 回首页',
    'auto.回首页逛逛': '← 回首页逛逛',
    'auto.在新标签页创建系列': '在新标签页创建系列',
    'auto.基本资料': '📝 基本资料',
    'auto.基本资料_2': '基本资料',
    'auto.填满圆形': '⭕ 填满圆形',
    'auto.备案号_选填': '备案号（选填）',
    'auto.大标签居中_小标签围绕_字体大小随排名变化': '（大标签居中，小标签围绕，字体大小随排名变化）',
    'auto.太棒啦_没有待审核的文章喵': '太棒啦，没有待审核的文章喵~',
    'auto.头像设置': '📷 头像设置',
    'auto.头像设置_2': '头像设置',
    'auto.字_约': '字 · 约',
    'auto.字体大小选择': '字体大小选择',
    'auto.完整显示': '🌸 完整显示',
    'auto.定时发布时间': '定时发布时间',
    'auto.定时发布时间_可选_草稿到点自动发布': '⏰ 定时发布时间（可选，草稿到点自动发布）',
    'auto.定时投稿': '定时投稿',
    'auto.实时检查本站各项服务的健康状况喵': '实时检查本站各项服务的健康状况喵~',
    'auto.实时预览': '实时预览',
    'auto.实时预览_2': '👁 实时预览',
    'auto.审批通过': '✅ 审批通过',
    'auto.审核全局设置': '⚙️ 审核全局设置',
    'auto.审核历史分页': '审核历史分页',
    'auto.审核待发布文章与用户举报_删除为软删除_可在回收': '审核待发布文章与用户举报；删除为软删除，可在回收站恢复喵~',
    'auto.密码强度': '密码强度',
    'auto.密码强度计量': '密码强度计量',
    'auto.密码强度进度': '密码强度进度',
    'auto.已删除文章': '📄 已删除文章',
    'auto.已删除评论': '💬 已删除评论',
    'auto.已发布': '✅ 已发布',
    'auto.已发布_2': '已发布',
    'auto.已发布文章': '已发布文章',
    'auto.已处理推广申请分页': '已处理推广申请分页',
    'auto.已处理申请_系统执行状态': '已处理申请 · 系统执行状态',
    'auto.已通过': '✅ 已通过',
    'auto.已驳回': '🚫 已驳回',
    'auto.平均耗时': '⏱ 平均耗时：',
    'auto.开放_api_文档': '🧩 开放 API 文档',
    'auto.当前在线': '当前在线',
    'auto.当前头像': '当前头像',
    'auto.当前头像预览': '当前头像预览',
    'auto.当前封面': '当前封面',
    'auto.当前封面_重新选择将覆盖旧图': '当前封面：重新选择将覆盖旧图',
    'auto.彻底删除': '🔥 彻底删除',
    'auto.彻底删除文章': '彻底删除文章',
    'auto.彻底删除评论': '彻底删除评论',
    'auto.待审文章分页': '待审文章分页',
    'auto.快去写下第一篇文章吧喵': '快去写下第一篇文章吧喵~ 🌸',
    'auto.快去创作第一篇吧喵': '快去创作第一篇吧喵~ 🌸',
    'auto.总浏览量': '总浏览量',
    'auto.总点赞数': '总点赞数',
    'auto.总访问量': '📊 总访问量：',
    'auto.总评论数': '总评论数',
    'auto.总阅读量': '👁 总阅读量',
    'auto.总阅读量_2': '总阅读量',
    'auto.我的文章列表': '我的文章列表',
    'auto.我的文章表格': '我的文章表格',
    'auto.我的点赞记录': '👍 我的点赞记录',
    'auto.我的评论列表': '我的评论列表',
    'auto.所属系列': '所属系列',
    'auto.手动摘要': '手动摘要',
    'auto.手动摘要_可选_留空自动截取正文前_180_字': '手动摘要（可选，留空自动截取正文前 180 字）',
    'auto.打开文案总表': '💬 打开文案总表',
    'auto.批量修改分类': '批量修改分类',
    'auto.把同主题文章整理成系列_按顺序阅读更系统喵': '把同主题文章整理成系列，按顺序阅读更系统喵~',
    'auto.把同主题的文章整理成一个系列_读者就能按顺序一口': '把同主题的文章整理成一个系列，读者就能按顺序一口气看完啦喵~',
    'auto.护眼模式': '护眼模式',
    'auto.拖动图片调整位置_滑块或滚轮缩放_完整显示可看全': '拖动图片调整位置，滑块或滚轮缩放；「完整显示」可看全整张图，头像会按圆形区域裁剪喵~',
    'auto.按分类': '📁 按分类',
    'auto.按动作筛选': '按动作筛选',
    'auto.按标签': '🏷 按标签',
    'auto.按状态筛选文章': '按状态筛选文章',
    'auto.排序': '排序：',
    'auto.排行榜': '排行榜',
    'auto.接口列表': '接口列表',
    'auto.接口文档': '接口文档',
    'auto.推广申请分页': '推广申请分页',
    'auto.提交后进入待审核_管理员通过后才会公开喵': '⏳ 提交后进入待审核，管理员通过后才会公开喵~',
    'auto.提交时间': '🕐 提交时间',
    'auto.搜索': '搜索',
    'auto.搜索引擎_seo': '🔍 搜索引擎（SEO）',
    'auto.搜索我的文章': '搜索我的文章',
    'auto.搜索我的文章标题': '搜索我的文章标题',
    'auto.撤回这条评论': '撤回这条评论',
    'auto.操作': '操作',
    'auto.收藏': '收藏',
    'auto.收藏数': '收藏数',
    'auto.收藏的文章': '收藏的文章',
    'auto.收藏的文章_2': '⭐ 收藏的文章',
    'auto.收进回收站': '收进回收站',
    'auto.教程': '教程',
    'auto.数据库': '数据库',
    'auto.数据统计': '📊 数据统计',
    'auto.文章': '文章：',
    'auto.文章总数': '📝 文章总数',
    'auto.文章总数_2': '文章总数',
    'auto.文章数': '📚 文章数',
    'auto.文章数_2': '文章数',
    'auto.文章标记': '文章标记',
    'auto.文章标题': '文章标题',
    'auto.文章系列': '文章系列',
    'auto.文章系列_2': '📚 文章系列',
    'auto.文章系列列表': '文章系列列表',
    'auto.文章编辑表单': '文章编辑表单',
    'auto.文章访问密码': '文章访问密码',
    'auto.文章评分': '文章评分',
    'auto.新密码': '新密码',
    'auto.新建系列': '＋新建系列',
    'auto.旧密码': '旧密码',
    'auto.显示在左上角_版权与浏览器标题': '显示在左上角、版权与浏览器标题',
    'auto.显示在网站底部关于小站区块': '显示在网站底部「关于小站」区块',
    'auto.暂无收藏': '暂无收藏',
    'auto.暂无点赞记录': '暂无点赞记录',
    'auto.暂无评论': '暂无评论',
    'auto.暂无阅读历史': '暂无阅读历史',
    'auto.更新时间': '更新时间',
    'auto.最多_500_字_不支持_html_标签': '最多 500 字，不支持 HTML 标签',
    'auto.最多_50_个字': '最多 50 个字',
    'auto.最新注册': '🧑‍🤝‍🧑 最新注册',
    'auto.最新评论': '💬 最新评论',
    'auto.最近_7_天访问量': '📈 最近 7 天访问量',
    'auto.最近_7_天访问量柱状图': '最近 7 天访问量柱状图',
    'auto.最近评论': '最近评论',
    'auto.最近评论_top10': '💬 最近评论 TOP10',
    'auto.服务健康状态': '服务健康状态',
    'auto.服务器错误': '服务器错误',
    'auto.服务器错误提示': '服务器错误提示',
    'auto.未分类_清空分类': '— 未分类（清空分类）—',
    'auto.未执行_已达上限': '⏸ 未执行·已达上限',
    'auto.未输入标题': '（未输入标题）',
    'auto.本站所有_restful_接口一览_支持前端搜索': '本站所有 RESTful 接口一览，支持前端搜索过滤喵~',
    'auto.权限提示': '权限提示',
    'auto.查看上下文': '查看上下文 →',
    'auto.查看分类文章': '查看分类文章',
    'auto.查看文章': '👁 查看文章',
    'auto.柱高采用开方刻度_弱化个别峰值日的挤压_柱顶常驻': '💡 柱高采用开方刻度（弱化个别峰值日的挤压），柱顶常驻当天真实访问次数；鼠标悬停柱子会高亮特显喵',
    'auto.标签_多个标签用英文逗号分隔': '标签（多个标签用英文逗号分隔）',
    'auto.标签_多个用逗号分隔': '标签，多个用逗号分隔',
    'auto.标签总数': '标签总数',
    'auto.标签排行榜': '🏆 标签排行榜',
    'auto.标签索引': '标签索引',
    'auto.标题': '标题',
    'auto.检测到_javascript_已禁用_本文目录_': '🌸 检测到 JavaScript 已禁用，本文目录 / 点赞 / 评论 / 评分等交互功能将不可用喵~',
    'auto.橙黄暖阳': '🍊 橙黄暖阳',
    'auto.正文': '正文',
    'auto.正文_富文本_支持图片上传_图文混排_表格插入与': '正文（富文本：支持图片上传、图文混排、表格插入与拖拽调整列宽）',
    'auto.正文内容': '正文内容',
    'auto.没有待处理的举报_社区很和谐喵': '没有待处理的举报，社区很和谐喵~',
    'auto.注册用户': '注册用户',
    'auto.浏览器分布': '🌐 浏览器分布',
    'auto.浏览量': '👁️ 浏览量',
    'auto.浏览量_2': '浏览量',
    'auto.浙icp备xxxx号': '浙ICP备xxxx号',
    'auto.清理该失效举报': '🧹 清理该失效举报',
    'auto.清空历史': '🗑 清空历史',
    'auto.点击选择封面图喵_可选_建议宽幅横图': '点击选择封面图喵（可选，建议宽幅横图）',
    'auto.点击选择系列封面喵_可选_建议方形或竖图': '点击选择系列封面喵（可选，建议方形或竖图）',
    'auto.点赞数': '❤️ 点赞数',
    'auto.点赞数_2': '点赞数',
    'auto.点赞的文章': '点赞的文章',
    'auto.点赞这条评论': '点赞这条评论',
    'auto.热门文章_top5': '🔥 热门文章 TOP5',
    'auto.热门文章侧边栏': '热门文章侧边栏',
    'auto.热门文章推荐': '热门文章推荐',
    'auto.版本信息': '🧩 版本信息',
    'auto.版本信息_2': '版本信息',
    'auto.版权归属_选填': '版权归属（选填）',
    'auto.状态': '状态',
    'auto.独立_ip': '🌐 独立 IP：',
    'auto.玫瑰粉恋': '🌹 玫瑰粉恋',
    'auto.理由_备注_会通知作者': '理由 / 备注（会通知作者）',
    'auto.用户发布的文章': '用户发布的文章',
    'auto.用户总数': '👤 用户总数',
    'auto.用户总数_2': '用户总数',
    'auto.用户统计': '用户统计',
    'auto.用户资料': '用户资料',
    'auto.申请理由': '申请理由：',
    'auto.留空则用网站名称': '留空则用网站名称',
    'auto.确认': '确认',
    'auto.确认操作': '确认操作',
    'auto.确认新密码': '确认新密码',
    'auto.禁止进入': '禁止进入',
    'auto.站内搜索': '站内搜索',
    'auto.站点核心统计': '站点核心统计',
    'auto.站点运营数据一览喵_数据实时统计_仅供管理员查看': '站点运营数据一览喵~ 数据实时统计，仅供管理员查看 ✨',
    'auto.第一篇文章正在路上喵': '第一篇文章正在路上喵~',
    'auto.简单介绍一下这个系列会写些什么吧': '简单介绍一下这个系列会写些什么吧~',
    'auto.简单描述一下改动吧': '简单描述一下改动吧~',
    'auto.篇文章执行分类变更': '篇文章执行分类变更：',
    'auto.精华文章': '精华文章',
    'auto.系列介绍': '系列介绍',
    'auto.系列内序号': '🔢 系列内序号',
    'auto.系列名称': '📚 系列名称',
    'auto.系列名称_2': '系列名称',
    'auto.系列封面_可选': '🖼️ 系列封面（可选）',
    'auto.系列文章列表': '系列文章列表',
    'auto.系列简介': '系列简介',
    'auto.系列简介_可选': '📝 系列简介（可选）',
    'auto.系统已执行': '✅ 系统已执行',
    'auto.系统执行_未执行': '⏳ 系统执行：未执行',
    'auto.系统执行状态总览': '系统执行状态总览',
    'auto.系统执行说明': '系统执行说明：',
    'auto.紫粉萌系': '🌸 紫粉萌系',
    'auto.累计浏览': '累计浏览',
    'auto.累计点赞': '累计点赞',
    'auto.给文章起个好听的名字吧': '给文章起个好听的名字吧~',
    'auto.给系列起个名字吧_例如_django_入坑日记': '给系列起个名字吧，例如：Django 入坑日记~',
    'auto.给自己起个可爱的昵称吧': '给自己起个可爱的昵称吧~',
    'auto.编辑资料': '✏️ 编辑资料',
    'auto.缩放头像': '缩放头像',
    'auto.网站关键词': '网站关键词',
    'auto.网站副标题_一句话介绍': '网站副标题 / 一句话介绍',
    'auto.网站名_logo_介绍与页脚文案都在这里修改_保': '网站名、Logo、介绍与页脚文案都在这里修改，保存后全站立即生效喵~ ✨',
    'auto.网站名称': '网站名称',
    'auto.网站描述': '网站描述',
    'auto.网站的整体介绍_会写入_meta_descrip': '网站的整体介绍，会写入 meta description…',
    'auto.网站运行状态': '💚 网站运行状态',
    'auto.置顶_精华_热门可在文章页点对应按钮申请喵': '📌 置顶 / ⭐ 精华 / 🔥 热门可在文章页点对应按钮申请喵~',
    'auto.置顶_精华_热门需发布后在文章页申请_或由管理员': '📌 置顶 / ⭐ 精华 / 🔥 热门需发布后在文章页申请，或由管理员设置喵~',
    'auto.置顶文章': '置顶文章',
    'auto.腾出置顶名额后_可在文章详情页手动置顶': '💡 腾出置顶名额后，可在文章详情页手动置顶',
    'auto.至少_8_位字符': '至少 8 位字符',
    'auto.英文逗号分隔_例如_博客技术二次元': '英文逗号分隔，例如 博客,技术,二次元',
    'auto.获赞': '获赞',
    'auto.萌系': '萌系',
    'auto.蓝绿清新': '🌊 蓝绿清新',
    'auto.被喵吃掉的页面': '被喵吃掉的页面',
    'auto.裁剪适配模式': '裁剪适配模式',
    'auto.裁剪预览': '裁剪预览',
    'auto.解锁阅读': '🔓 解锁阅读',
    'auto.访问密码': '访问密码',
    'auto.访问密码_可选_留空公开': '🔒 访问密码（可选，留空公开）',
    'auto.访问密码表单': '访问密码表单',
    'auto.评论总数': '💬 评论总数',
    'auto.评论总数_2': '评论总数',
    'auto.评论数': '💬 评论数',
    'auto.评论数_2': '评论数',
    'auto.该评论已不存在_可能已被处理': '该评论已不存在（可能已被处理）。',
    'auto.说点什么吧_可用上方工具栏加粗_斜体_链接_代码': '说点什么吧~ 🌸（可用上方工具栏加粗/斜体/链接/代码，最多 10000 字）',
    'auto.说点什么吧_比如哪里需要调整': '说点什么吧，比如哪里需要调整~',
    'auto.请求异常': '请求异常',
    'auto.请求示例': '请求示例：',
    'auto.请输入访问密码': '请输入访问密码…',
    'auto.账号设置': '⚙️ 账号设置',
    'auto.账号设置表单': '账号设置表单',
    'auto.输入密码查看强度': '输入密码查看强度',
    'auto.输入当前密码': '输入当前密码',
    'auto.输入方法_路径_说明关键词过滤': '🔍 输入方法 / 路径 / 说明关键词过滤…',
    'auto.过滤接口文档': '过滤接口文档',
    'auto.运行状态': '运行状态',
    'auto.近_14_天访问趋势': '📈 近 14 天访问趋势',
    'auto.近_5_分钟': '近 5 分钟',
    'auto.返回上一页': '返回上一页',
    'auto.返回看板': '🎛 返回看板',
    'auto.返回系列列表': '← 返回系列列表',
    'auto.返回首页': '返回首页',
    'auto.还没有发表过评论喵_去文章下面聊聊吧': '还没有发表过评论喵~ 去文章下面聊聊吧 🌸',
    'auto.还没有审核记录喵': '还没有审核记录喵~',
    'auto.还没有已处理的推广申请喵': '还没有已处理的推广申请喵~',
    'auto.还没有收藏任何文章喵_去发现好文吧': '还没有收藏任何文章喵~ 去发现好文吧 🌸',
    'auto.还没有文章呢': '还没有文章呢~',
    'auto.还没有文章系列呢': '还没有文章系列呢~',
    'auto.还没有点赞记录喵_看到喜欢的文章点个赞吧': '还没有点赞记录喵~ 看到喜欢的文章点个赞吧 🌸',
    'auto.还没有选择图片哦': '还没有选择图片哦~',
    'auto.还没有阅读记录_去读点什么吧': '还没有阅读记录，去读点什么吧~',
    'auto.还没有阅读记录喵_快去读点什么吧': '还没有阅读记录喵~ 快去读点什么吧 🌸',
    'auto.这个人很懒_什么都没写喵': '这个人很懒，什么都没写喵~ 🐾',
    'auto.这个榜单暂时还没有数据喵': '这个榜单暂时还没有数据喵~',
    'auto.这个系列还没有已发布的文章呢': '这个系列还没有已发布的文章呢~',
    'auto.这些是你最近读过的文章喵': '这些是你最近读过的文章喵~',
    'auto.这位小伙伴还没有发布文章呢': '这位小伙伴还没有发布文章呢~',
    'auto.这篇文章已上锁啦': '这篇文章已上锁啦~',
    'auto.这里还空空如也呢': '这里还空空如也呢~',
    'auto.选择图片喵': '选择图片喵',
    'auto.选择头像图片': '选择头像图片',
    'auto.选择新分类': '选择新分类：',
    'auto.选择系列后_序号会在保存时自动编排到系列末尾喵': '选择系列后，序号会在保存时自动编排到系列末尾喵~',
    'auto.通知筛选': '通知筛选',
    'auto.通过发布': '✅ 通过发布',
    'auto.重新压缩全部_css_js_写入新版本号并清空缓': '重新压缩全部 CSS/JS、写入新版本号并清空缓存',
    'auto.错误请求提示': '错误请求提示',
    'auto.阅读偏好': '🎨 阅读偏好',
    'auto.阅读历史列表': '阅读历史列表',
    'auto.阅读时长': '阅读时长',
    'auto.阅读量': '阅读量',
    'auto.隐藏违规评论': '隐藏违规评论',
    'auto.隐藏违规评论_2': '🗑 隐藏违规评论',
    'auto.页脚关于小站的介绍文案': '页脚「关于小站」的介绍文案…',
    'auto.页脚内容': '🐾 页脚内容',
    'auto.页面动效': '页面动效',
    'auto.预览': '👁 预览',
    'auto.预览_2': '预览',
    'auto.首页与导航处展示的一句话介绍': '首页与导航处展示的一句话介绍',
    'auto.驳回并退回作者': '驳回并退回作者',
    'auto.驳回推广申请': '驳回推广申请',
    'auto.驳回申请': '🗑 驳回申请',
    'auto.驳回退回': '🗑 驳回退回',
    'auto.高级后台': '⚙️ 高级后台',

    # ======================================================
    # auto · 含变量文案（模板侧用 |msgfmt:变量 填参）
    # 由 wire_variable_texts.py 自动登记；占位符数量与参数一一对应。
    # ======================================================

    # ======================================================
    # auto · 含变量文案（模板侧用 |msgfmt:变量 填参）
    # 由 wire_variable_texts.py 自动登记；占位符数量与参数一一对应。
    # ======================================================

    # ======================================================
    # adminmsg · 文案总表管理页自身
    # 后台界面文案，与前台同口径登记，便于统一维护。
    # ======================================================
    'adminmsg.breadcrumb': '面包屑',
    'adminmsg.home': '首页',
    'adminmsg.console': '运营看板',
    'adminmsg.title_page': '文案总表',
    'adminmsg.title': '💬 全站文案总表',
    'adminmsg.hint_1': '这里登记全站所有用户可见提示词（错误页 / 表单 / flash / 按钮 / 弹窗 / 空状态 / 徽章 …）。',
    'adminmsg.hint_2': '修改后保存即生效，无需改代码或重启；留空或改回默认值即等于不覆盖。',
    'adminmsg.hint_3': '本轮起不再使用占位符机制：带变量的位置由模板直接渲染，因此这里登记的都是固定文案。',
    'adminmsg.hint_label': '标注说明',
    'adminmsg.hint_dead': '表示该文案目前没有任何界面引用（属预留登记），改它不会有可见效果 — 需要先在模板 / 视图里接入才会生效；其余为已接入，改动会立即反映到界面。',
    'adminmsg.hint_strong': '没有任何界面引用',
    'adminmsg.search_placeholder': '搜索 key 或文案内容…',
    'adminmsg.search_aria': '搜索文案',
    'adminmsg.domain_aria': '按域筛选',
    'adminmsg.filter': '🔍 筛选',
    'adminmsg.clear_filter': '✕ 清除筛选',
    'adminmsg.save_all': '💾 保存全部改动',
    'adminmsg.chip_overridden': '已覆盖',
    'adminmsg.chip_same': '与默认相同',
    'adminmsg.chip_dead': '未接入',
    'adminmsg.chip_dirty': '待保存',
    'adminmsg.chip_same_title': '覆盖值与代码默认值相同，可点「恢复默认」清理',
    'adminmsg.chip_dead_title': '当前没有任何模板 / 视图 / 脚本引用该 key，改动不会有可见效果',
    'adminmsg.default_title': '代码默认值',
    'adminmsg.reset': '↺ 恢复默认',
    'adminmsg.reset_title': '删除该条覆盖，恢复代码默认文案',

    # 空状态补充（各列表页 / 看板）
    'empty.users': '还没有用户喵~',
    'empty.notifications_unread': '没有未读通知啦，都处理完了喵~',
    'empty.my_comments_prefix': '还没有发表过评论喵~ 去',
    'empty.my_comments_suffix': '下面聊聊吧 🌸',
    'empty.my_collection': '这里还什么都没有喵~',
    'empty.liked_articles': '还没有点赞记录喵~ 看到喜欢的文章点个赞吧！',

    # 空状态补充（系列 / 分类简介兜底）
    'empty.series_intro': '这个系列还没有介绍~',
    'empty.category_intro': '这个分类还没有介绍~',
    'empty.console_users': '还没有用户喵~',
    'auto.文章列表': '文章列表',
    'badge.expand_locked': '展开未获得的徽章',

    # 文案总表页：操作反馈与导航
    'adminmsg.reset_row_done': '已恢复该条默认文案',
    'adminmsg.reset_domain_done': '已恢复该域全部默认',
    'adminmsg.no_match': '没有匹配的文案喵~ 换个关键词试试。',
    'adminmsg.back_settings': '← 返回站点设置',

    # 文案总表页：操作反馈与导航
    'adminmsg.reset_domain': '恢复该域全部默认',
}


# ======================================================================
# 数据库覆盖层（可选）：让文案可以在后台改，无需改代码 / 重启
# ----------------------------------------------------------------------
# 设计要点（回答「能不能放进数据库、性能影响大不大」）：
#
#   · **默认值仍在代码里**（上面的 MESSAGES）：进程启动即就绪，
#     数据库故障、迁移未跑、全新部署都能正常显示，不存在「文案表空了站点就崩」；
#   · **数据库只存覆盖项**（SiteMessage 表）：只放被运营改过的那几条，
#     一行 = 一个 key，通常个位数到几十行；
#   · **整表一次读取 + 进程内缓存**：所有覆盖项合并成一个 dict 缓存在 LocMemCache，
#     TTL 300s，保存时通过「版本号」立刻失效。热路径（每次取文案）是**字典查找**，
#     不会产生任何 SQL —— 与「把 286 条文案逐条查库」有本质区别；
#   · **异常安全**：读取失败（表不存在 / 数据库不可用）时静默回退代码默认值，
#     绝不让文案问题变成页面 500；
#   · 缓存 key 带版本号（与 cache_keys 统一风格），bump 后所有进程立即失效。
# ======================================================================

#: 覆盖层缓存 key（存整表 dict）
_OVERRIDE_CACHE_KEY = 'v1:site_messages:overrides'
#: 覆盖层版本号 key（保存时 +1，用于跨进程失效）
_OVERRIDE_VERSION_KEY = 'v1:site_messages:overrides_ver'
#: 覆盖层缓存时长（秒）
_OVERRIDE_TTL = 300

#: 进程内兜底缓存：Redis/LocMemCache 都不可用时，避免每次请求都查库
_LOCAL_OVERRIDE_CACHE = {'ver': None, 'data': {}}

#: 跨进程变更戳：数据库侧 MAX(updated_at) + 上次检查时间（用于节流）
#: 为什么需要它：LocMemCache 是进程内缓存，「缓存失效」无法跨进程传播，
#: 必须靠数据库信号让其它进程感知覆盖已变更（详见 _load_overrides 的说明）。
_DB_STAMP = {'stamp': None, 'checked_at': 0.0}

#: 「验证探针」键前缀：接入状态验证脚本用它写入临时覆盖，读取时会被过滤。
#: 用前缀而不是「清空整表」是为了让探针与真实覆盖**共存**，避免互相覆盖数据。
PROBE_PREFIX = '__probe__.'


def _load_overrides():
    """读取数据库中的文案覆盖项，返回 ``{key: text}``（失败时返回空 dict）。

    **跨进程一致性（重要）**
    ----------------------
    本项目默认缓存后端是 ``LocMemCache``（进程内），因此「缓存版本号 / 缓存失效」
    **无法跨进程传播**：A 进程保存覆盖后，B 进程（例如 runserver）不会收到通知，
    仍会用它自己进程内的旧副本渲染页面 —— 表现为「在文案总表改了文案，
    刷新页面却没变化」，必须重启服务或手动打 ``/__dev_sync_state/`` 才生效。
    （实测踩过：真实服务器返回旧文案，同一进程内的测试客户端却返回新文案。）

    解决办法：用**数据库里的更新时间戳**作为跨进程变更信号：
      · 每次（受 ``SITE_MSG_DB_POLL_SECONDS`` 节流）查一次 ``MAX(updated_at)``
        —— 单表索引查询，代价极小；
      · 时间戳变了就丢弃进程内副本、重新读表；
      · 若同一秒内的改动恰好时间戳相同，仍有 ``_OVERRIDE_TTL`` 兜底。
    这样「保存后刷新页面立即可见」在单进程与多进程下都成立，
    也是本模块**不依赖共享缓存**的关键设计。
    """
    from django.conf import settings as _settings
    from django.core.cache import cache

    global _DB_STAMP

    # ---- 1) 节流的数据库变更检测（跨进程信号）----
    # 默认 1 秒：文案改动应当「保存后立刻可见」，节流只是为了挡住高频请求；
    # 可用 settings.SITE_MSG_DB_POLL_SECONDS 调整（设为 0 则每次请求都查，
    # 适合开发或极低频站点；设为更大值可进一步降低数据库压力）。
    poll = float(getattr(_settings, 'SITE_MSG_DB_POLL_SECONDS', 1.0))
    now = time.monotonic()
    if poll > 0 and (now - _DB_STAMP['checked_at']) >= poll:
        _DB_STAMP['checked_at'] = now
        try:
            from django.db.models import Max
            from .models import SiteMessage
            stamp = SiteMessage.objects.aggregate(m=Max('updated_at'))['m']
            stamp_key = str(stamp) if stamp else ''
            if stamp_key != _DB_STAMP['stamp']:
                # 数据库变了 → 丢弃所有层级的缓存，强制重读
                _DB_STAMP['stamp'] = stamp_key
                _LOCAL_OVERRIDE_CACHE.update({'ver': None, 'data': {}})
                cache.delete(_OVERRIDE_CACHE_KEY)
        except Exception:  # noqa: BLE001 表不存在 / 数据库不可用 → 走代码默认值
            pass

    try:
        version = cache.get(_OVERRIDE_VERSION_KEY, 0)
        # 版本号没变且本进程已缓存 → 直接用进程内副本，连缓存后端都不访问
        if _LOCAL_OVERRIDE_CACHE['ver'] == version and _LOCAL_OVERRIDE_CACHE['data']:
            return _LOCAL_OVERRIDE_CACHE['data']
        cached = cache.get(_OVERRIDE_CACHE_KEY)
        if cached is not None:
            _LOCAL_OVERRIDE_CACHE.update({'ver': version, 'data': cached})
            return cached
        from .models import SiteMessage
        data = {}
        for m in SiteMessage.objects.filter(is_enabled=True):
            # 「验证探针」记录：键形如 `__probe__.<真实key>`，文案是唯一标记。
            # 读取时**剥掉前缀**当作真实覆盖注入 —— 这样验证脚本可以只改自己的
            # 探针数据就完成「逐 key 改值」验证，而**完全不动**用户的真实覆盖
            # （早期实现是清空整表，会把用户刚保存的文案冲掉，实测踩过）。
            if m.key.startswith(PROBE_PREFIX):
                data[m.key[len(PROBE_PREFIX):]] = m.text
            else:
                data[m.key] = m.text
        cache.set(_OVERRIDE_CACHE_KEY, data, _OVERRIDE_TTL)
        _LOCAL_OVERRIDE_CACHE.update({'ver': version, 'data': data})
        return data
    except Exception:  # noqa: BLE001 任何异常都回退到代码默认值
        return {}


def invalidate_overrides():
    """清空覆盖层缓存并 bump 版本号（SiteMessage 保存 / 删除时调用）。"""
    from django.core.cache import cache
    _LOCAL_OVERRIDE_CACHE.update({'ver': None, 'data': {}})
    try:
        cache.delete(_OVERRIDE_CACHE_KEY)
        # 版本号自增：其他进程发现版本变化后会重新读表，避免多进程脏读
        try:
            cache.incr(_OVERRIDE_VERSION_KEY)
        except ValueError:
            cache.set(_OVERRIDE_VERSION_KEY, 1, None)
    except Exception:  # noqa: BLE001 缓存不可用不影响正确性（下次直接读表）
        pass


def all_messages():
    """返回「代码默认值 + 数据库覆盖」合并后的完整文案表。

    合并策略：数据库里启用且非空的项覆盖代码默认值；其余保持代码默认值。
    """
    merged = dict(MESSAGES)
    overrides = _load_overrides()
    if overrides:
        for k, v in overrides.items():
            if v:
                merged[k] = v
    return merged


def pending_keys():
    """返回被数据库覆盖的 key 集合，供审计 / 排障查看「哪些文案被改过」。"""
    return set(_load_overrides().keys())


# ======================================================================
# 访问接口
# ======================================================================
def msg(key, *args, **kwargs):
    """按 key 取文案并可选格式化；缺 key 时返回可见的占位而不是抛错。

    取值顺序：**数据库覆盖 > 代码默认值**。
    设计原则：**文案缺失不能导致页面 500**。找不到 key 时返回 ``⟪key⟫`` 形式，
    既能让页面继续渲染，又能在视觉验收时一眼发现遗漏（同时打 warning 日志）。

    Args:
        key: ``MESSAGES`` 中的语义化键，如 ``'auth.login_failed'``。
        *args: 传给 ``str.format`` 的位置参数。
        **kwargs: 传给 ``str.format`` 的关键字参数。

    Returns:
        str: 最终文案（已格式化）。
    """
    template = MESSAGES.get(key)
    overrides = _load_overrides()
    if key in overrides and overrides[key]:
        template = overrides[key]
    if template is None:
        # 延迟导入避免模块级循环依赖
        import logging
        logging.getLogger(__name__).warning('site_messages: 缺少文案 key=%s', key)
        return '⟪%s⟫' % key
    if not args and not kwargs:
        return template
    try:
        return template.format(*args, **kwargs)
    except (IndexError, KeyError, ValueError):
        # 占位符与实参不匹配时返回原文，避免格式化异常影响页面
        return template


def namespace(prefix):
    """取出某个域下的全部文案，键去掉前缀，便于模板按域访问。

    注意：这里读的是**合并后**的表（含数据库覆盖），保证模板与 Python 取到同一份文案。

    Args:
        prefix: 域名，如 ``'auth'``。

    Returns:
        dict: ``{'login_failed': '...', ...}``
    """
    head = prefix + '.'
    return {k[len(head):]: v for k, v in all_messages().items() if k.startswith(head)}


def as_context():
    """构造注入模板的 ``MSG`` 命名空间（按域分组 + 支持点号全路径访问）。

    返回的字典同时提供两种访问方式：
    - ``MSG.auth.login_failed``：按域分组（推荐，语义清晰）；
    - ``MSG['auth.login_failed']``：全路径（便于模板里动态拼接 key）。
    """
    table = all_messages()
    ctx = {'_raw': dict(table)}
    domains = {k.split('.', 1)[0] for k in table}
    for dom in domains:
        head = dom + '.'
        ctx[dom] = {k[len(head):]: v for k, v in table.items() if k.startswith(head)}
    return ctx


def js_payload():
    """构造下发给前端的文案包（只含 ``js.`` 与 ``btn.`` / ``err.`` 常用项）。

    前端通过 ``window.SITE_MSG`` 取用，键去掉 ``js.`` 前缀（如
    ``js.network_error`` → ``SITE_MSG.network_error``），按钮 / 错误页文案
    以原名挂在 ``SITE_MSG.btn_*`` / ``SITE_MSG.err_*`` 上，方便 JS 复用。
    """
    payload = namespace('js')
    for dom in ('btn', 'misc'):
        for k, v in namespace(dom).items():
            payload['%s_%s' % (dom, k)] = v
    return payload


def html(key, *args, **kwargs):
    """取文案并做 HTML 转义（用于需要插入到 HTML 文本节点、又允许占位符的场景）。"""
    return _escape(msg(key, *args, **kwargs))