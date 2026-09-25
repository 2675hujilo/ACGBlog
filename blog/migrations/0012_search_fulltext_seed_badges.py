"""第5轮迁移：MySQL FULLTEXT 全文索引 + 初始成就徽章种子数据。

本迁移做两件事：
1. 用 RunSQL 对 blog_article 的 (title, excerpt_field, content) 建 FULLTEXT 索引
   （MySQL 5.6+ InnoDB 原生支持），用于搜索相关性排序；reverse SQL 对应 DROP INDEX。
2. 用 RunPython 写入初始徽章定义（发文/评论/获赞/注册天数四档），reverse 清空。
"""
from django.db import migrations


# 初始徽章种子数据：(名称, 说明, 图标, 条件类型, 阈值)
INITIAL_BADGES = [
    # 发文数徽章
    ('初露锋芒', '发表第一篇文章', '✍️', 'articles', 1),
    ('笔耕不辍', '累计发表 10 篇文章', '📝', 'articles', 10),
    ('著作等身', '累计发表 50 篇文章', '📚', 'articles', 50),
    # 评论数徽章
    ('热心读者', '累计发表 10 条评论', '💬', 'comments', 10),
    ('论道纵横', '累计发表 50 条评论', '🗣️', 'comments', 50),
    ('评论大师', '累计发表 100 条评论', '🎤', 'comments', 100),
    # 获赞数徽章
    ('小有名气', '文章累计获得 10 个赞', '👍', 'likes', 10),
    ('广受喜爱', '文章累计获得 100 个赞', '❤️', 'likes', 100),
    ('万众瞩目', '文章累计获得 500 个赞', '🏆', 'likes', 500),
    # 注册天数徽章
    ('一周之友', '注册满 7 天', '🌱', 'days', 7),
    ('月度老友', '注册满 30 天', '🌿', 'days', 30),
    ('年度忠粉', '注册满 365 天', '🌳', 'days', 365),
]


def seed_badges(apps, schema_editor):
    """写入初始徽章（get_or_create 幂等，重复迁移不产生重复行）。"""
    Badge = apps.get_model('blog', 'Badge')
    for name, desc, icon, ctype, value in INITIAL_BADGES:
        Badge.objects.get_or_create(
            name=name,
            defaults={
                'description': desc,
                'icon': icon,
                'condition_type': ctype,
                'condition_value': value,
            },
        )


def unseed_badges(apps, schema_editor):
    """回滚：按名称删除本迁移写入的徽章。"""
    Badge = apps.get_model('blog', 'Badge')
    Badge.objects.filter(name__in=[b[0] for b in INITIAL_BADGES]).delete()


class Migration(migrations.Migration):
    """第5轮全文索引 + 徽章种子迁移。"""

    dependencies = [
        ('blog', '0011_badge_shortlink_article_dislike_count_comment_image_and_more'),
    ]

    operations = [
        # 1. 文章标题/摘要/正文 FULLTEXT 索引（MySQL InnoDB 5.6+ 支持）
        migrations.RunSQL(
            sql="ALTER TABLE blog_article ADD FULLTEXT INDEX ft_search (title, excerpt_field, content);",
            reverse_sql="ALTER TABLE blog_article DROP INDEX ft_search;",
        ),
        # 2. 初始徽章种子数据
        migrations.RunPython(seed_badges, unseed_badges),
    ]
