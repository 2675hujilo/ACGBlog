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
    'brand.copyright': '© {} 萌语博客 · 用心记录每一天喵~',

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
    'auth.welcome_back': '欢迎回来喵~{}🌸',
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
    'auth.register_form_error': '注册信息还要再检查一下喵~共 {} 处需要修改',
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
    'err.game_score': '得分：{}',
    'err.game_best': '最高分：{}',
    'err.game_start': '开始接樱花喵~',
    # API 错误信封（/api/ 请求）
    'err.api_400': '请求参数有误喵',
    'err.api_403': '没有权限哦喵',
    'err.api_404': '接口不存在喵',
    'err.api_500': '服务器开小差了喵',
    'err.api_generic': '出错了喵',
    # 模板渲染失败时的内联兜底页标记
    'err.inline_mark': '出错了喵（{}）',
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
    'form.upload_ok': '上传成功喵~',

    # ------------------------------------------------------------------
    # article · 文章发布 / 编辑 / 状态
    # ------------------------------------------------------------------
    'article.published': '文章已发布喵~✨',
    'article.submitted_review': '文章已提交审核，通过后就会和大家见面喵~ ⏳',
    'article.saved': '修改已保存啦~🌸',
    'article.trashed': '文章已收进回收站，需要时还能找回喵~ 🗑️',
    'article.restored': '《{}》已从回收站找回啦~ ✨',
    'article.approved': '《{}》已通过并发布~ 🌸',
    'article.rejected': '《{}》已退回作者修改~ 📝',
    'article.hard_deleted': '《{}》已彻底删除，无法找回了哦~ 🔥',
    'article.save_failed': '文章保存失败，请稍后再试喵~',
    'article.scheduled_banner': ('这是一篇<strong>定时投稿</strong>：当前状态为「{}」，'
                                 '计划于 <strong>{}</strong> 自动发布（约 {}）。'
                                 '只有<strong>你本人与管理员</strong>能看到，'
                                 '到点后按站点审核设置转为「待审核」或「已发布」喵~'),
    'article.scheduled_due': ('这篇定时投稿已到发布时间（{}），系统将在 30 秒内自动流转为'
                              '「待审核 / 已发布」，稍后刷新即可；当前仍为「{}」，'
                              '只有<strong>你本人与管理员</strong>可见喵~'),
    'article.review_pending_banner': ('这篇内容正在等待管理员审核，'
                                      '<strong>目前只有作者本人和管理员能看到</strong>，'
                                      '审核通过后才会公开喵~'),
    'article.draft_badge': '草稿',
    'article.pending_badge': '⏳ 待审核',
    'article.scheduled_badge': '🕐 {} 定时',

    # ------------------------------------------------------------------
    # comment · 评论
    # ------------------------------------------------------------------
    'comment.empty_content': '评论内容不能为空喵~ 📝',
    'comment.posted': '评论成功喵~ 💬',
    'comment.post_failed': '评论发送失败了，稍后再试喵~',
    'comment.pending_banner': '评论已提交，等待审核通过后公开喵~ ⏳',
    'comment.recalled': '评论已撤回喵~',
    'comment.recall_failed': '撤回失败，可能已超过可撤回时间喵~',
    'comment.restored': '评论 #{} 已恢复显示~ ✨',
    'comment.hard_deleted': '评论 #{} 已彻底删除，无法找回了哦~ 🔥',
    'comment.reply_placeholder': '回复 @{} 喵~',
    'comment.placeholder': '说点什么吧，友善发言喵~',
    'comment.reported': '举报已提交，管理员会尽快处理喵~',
    'comment.report_dismissed': '已标记举报不成立，评论予以保留~',
    'comment.hidden_backup': '违规评论 #{} 已隐藏，已备份至 {}',
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

    # ------------------------------------------------------------------
    # promo · 置顶 / 精华 / 热门
    # ------------------------------------------------------------------
    'promo.pin': '置顶',
    'promo.feature': '精华',
    'promo.hot': '热门',
    'promo.apply_pin': '📌 申请置顶',
    'promo.apply_feature': '⭐ 申请精华',
    'promo.apply_hot': '🔥 申请热门',
    'promo.applied': '已经{}',
    'promo.pending': '⏳ {}审核中',
    'promo.already_applied': '这篇文章已经{}啦，不用再申请喵~',
    'promo.duplicate': '已经提交过申请，正在审核中哦~',
    'promo.reason_required': '请填写申请理由喵~',
    'promo.submitted': '申请已提交，等待管理员审核喵~',
    'promo.only_own': '只能给自己的文章申请哦~',
    'promo.bad_kind': '申请类型不正确',
    'promo.limit_reached': '置顶已达上限（{} 篇）喵~',
    'promo.limit_cancel': '置顶最多 {} 篇哦~这篇没有置顶喵📌',
    'promo.limit_warn': ('当前置顶名额已满（{}/{} 篇），即使审核通过系统也可能暂时无法置顶喵~'),
    'promo.limit_hint': '📌 置顶名额已满（{}/{}），审核通过也可能暂不生效喵~',
    'promo.approved_ok': '已通过{}申请并已生效~ 🌸',
    'promo.approved_not_applied': '已通过{}申请，但{}，本次未生效。',
    'promo.rejected': '已驳回{}申请~',
    'promo.toggle_ok': '已{}{}~',
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
    'search.result_count': '找到 {} 条与「{}」相关的内容喵~',
    'search.no_keyword': '还没有输入关键词喵~',
    'search.history_cleared': '搜索历史已清空喵~',

    # ------------------------------------------------------------------
    # user · 用户中心
    # ------------------------------------------------------------------
    'user.center': '个人中心',
    'user.profile_of': '{} 的主页',
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
    'notify.new_comment': '{} 评论了你的文章',
    'notify.new_reply': '{} 回复了你的评论',
    'notify.mention': '{} 在评论中提到了你',

    # ------------------------------------------------------------------
    # badge · 徽章与成就（Bug9 任务「1」个人中心可视化面板）
    # ------------------------------------------------------------------
    'badge.panel_title': '🏅 我的徽章与成就',
    'badge.panel_subtitle': '每一枚徽章都是你在这里留下的足迹喵~',
    'badge.obtained': '已获得',
    'badge.locked': '未获得',
    'badge.obtained_prefix': '已获得',
    'badge.obtained_suffix': '枚',
    'badge.expand_locked_prefix': '展开未获得的徽章（',
    'badge.expand_locked_suffix': ' 枚）',
    'badge.collapse_locked': '收起未获得的徽章',
    'badge.how_to_get': '如何获得',
    'badge.progress': '进度 {}/{}',
    'badge.obtained_at': '{} 获得',
    'badge.new_toast': '🎉 恭喜解锁新徽章「{}」！',
    'badge.none_yet': '还没有获得徽章喵~ 看看下面的获取方式，去解锁第一枚吧！',
    'badge.earned_on': '{} 获得',

    # ------------------------------------------------------------------
    # misc · 其他
    # ------------------------------------------------------------------
    'misc.under_construction': '这里还在建设中喵~',
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
}


# ======================================================================
# 访问接口
# ======================================================================
def msg(key, *args, **kwargs):
    """按 key 取文案并可选格式化；缺 key 时返回可见的占位而不是抛错。

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

    Args:
        prefix: 域名，如 ``'auth'``。

    Returns:
        dict: ``{'login_failed': '...', ...}``
    """
    head = prefix + '.'
    return {k[len(head):]: v for k, v in MESSAGES.items() if k.startswith(head)}


def as_context():
    """构造注入模板的 ``MSG`` 命名空间（按域分组 + 支持点号全路径访问）。

    返回的字典同时提供两种访问方式：
    - ``MSG.auth.login_failed``：按域分组（推荐，语义清晰）；
    - ``MSG['auth.login_failed']``：全路径（便于模板里动态拼接 key）。
    """
    ctx = {'_raw': dict(MESSAGES)}
    domains = {k.split('.', 1)[0] for k in MESSAGES}
    for dom in domains:
        ctx[dom] = namespace(dom)
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
