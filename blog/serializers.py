"""DRF 序列化器：文章 / 分类 / 标签 / 修改日志。"""
import bleach
from rest_framework import serializers

from .models import Article, Category, EditLog, Tag
from .html_safety import MoeCSSSanitizer  # 与正文净化共用的内联 style 白名单净化器

# ---- 与视图层一致的内容净化白名单（模块级常量，保证两套入口净化口径一致）----
# 富文本正文允许标签：排版 / 语义 / 表格相关，剔除 script / iframe / 表单等危险标签。
ARTICLE_ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'col', 'colgroup',
    'dd', 'del', 'div', 'dl', 'dt', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'hr', 'i', 'img', 'ins', 'kbd', 'li', 'ol', 'p', 'pre', 'q', 's', 'samp',
    'small', 'span', 'strike', 'strong', 'sub', 'sup', 'table', 'tbody', 'td',
    'tfoot', 'th', 'thead', 'tr', 'tt', 'u', 'ul', 'figure', 'figcaption',
]
ARTICLE_ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
    '*': ['class', 'style'],
}
ARTICLE_ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


# 迭代#67: CategorySerializer类docstring完善
class CategorySerializer(serializers.ModelSerializer):
    """分类序列化：额外返回该分类下的文章数量 article_count。"""
    article_count = serializers.IntegerField(source='articles.count', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'article_count', 'created_at']
        read_only_fields = ['id', 'created_at']


# 迭代#68: TagSerializer类docstring完善
class TagSerializer(serializers.ModelSerializer):
    """标签序列化：额外返回该标签关联的文章数量 article_count。"""
    article_count = serializers.IntegerField(source='articles.count', read_only=True)

    class Meta:
        model = Tag
        fields = ['id', 'name', 'article_count', 'created_at']
        read_only_fields = ['id', 'created_at']


# 迭代#69: _AuthorSerializer类docstring完善
class _AuthorSerializer(serializers.Serializer):
    """作者信息只读序列化：文章列表/详情中嵌套展示作者基本信息。"""
    id = serializers.IntegerField()
    username = serializers.CharField()
    nickname = serializers.CharField()


# 迭代#70: ArticleListSerializer类docstring
class ArticleListSerializer(serializers.ModelSerializer):
    """列表序列化：正文降级为摘要。"""
    author = _AuthorSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    tags = TagSerializer(many=True, read_only=True)
    excerpt = serializers.CharField(read_only=True)

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'excerpt', 'author', 'category', 'category_name',
            'tags', 'views', 'status', 'kind', 'created_at', 'updated_at',
        ]


# 迭代#71: ArticleSerializer类docstring
class ArticleSerializer(serializers.ModelSerializer):
    """详情 / 新增 / 修改序列化。

    tag_names 为只写标签名数组，自动 get_or_create；读侧返回标签对象数组。
    """
    author = _AuthorSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=50), required=False, write_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'content', 'author', 'category', 'category_name',
            'tags', 'tag_names', 'views', 'status', 'kind',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'author', 'views', 'created_at', 'updated_at']

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError('标题不能为空')
        # 与视图层一致：超长标题截断到 max_length=200，避免 MySQL Data too long
        return value.strip()[:200]

    # 迭代#72: serializers中验证异常处理
    # 迭代#73: serializers内容净化注释
    def validate_content(self, value):
        """富文本正文净化：DRF API 写入同样走 bleach，杜绝 XSS 入库。

        与 ``blog.views.sanitize_html`` 同一套白名单口径，
        保证通过表单提交与通过 API 提交的正文安全级别一致。
        """
        if not value:
            return value or ''
        return bleach.clean(
            value,
            tags=ARTICLE_ALLOWED_TAGS,
            attributes=ARTICLE_ALLOWED_ATTRIBUTES,
            protocols=ARTICLE_ALLOWED_PROTOCOLS,
            css_sanitizer=MoeCSSSanitizer,
            strip=True,
        )

    def _apply_tags(self, instance, tag_names):
        names = {n.strip() for n in tag_names if n.strip()}
        tags = [Tag.objects.get_or_create(name=name)[0] for name in names]
        instance.tags.set(tags)

    def create(self, validated_data):
        tag_names = validated_data.pop('tag_names', [])
        article = Article.objects.create(**validated_data)
        self._apply_tags(article, tag_names)
        return article

    def update(self, instance, validated_data):
        tag_names = validated_data.pop('tag_names', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tag_names is not None:
            self._apply_tags(instance, tag_names)
        return instance


# 迭代#74: EditLogSerializer类docstring完善
class EditLogSerializer(serializers.ModelSerializer):
    """轻量修改日志：仅修改人 + 修改时间。"""
    editor_name = serializers.CharField(source='editor.username', read_only=True)

    class Meta:
        model = EditLog
        fields = ['id', 'editor_name', 'edited_at']



# ============================ 第2轮迭代#161-#170: 序列化器增强 ============================


# 第2轮迭代#161: 自定义字段——字数展示字段
class WordCountField(serializers.IntegerField):
    """只读字段：在序列化时实时计算文章字数。"""
    def to_representation(self, value):
        # value 为 Article 实例
        return getattr(value, 'word_count', 0)


# 第2轮迭代#166: 动态字段序列化基类——通过 context['fields'] 控制输出字段子集
class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """支持按 context['fields'] 动态裁剪返回字段的 ModelSerializer 基类。"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.context.get('fields')
        if fields:
            allowed = set(fields)
            for name in list(self.fields.keys()):
                if name not in allowed:
                    self.fields.pop(name)


# 第2轮迭代#165/#167/#168/#169/#170: 文章详情增强序列化器
class ArticleDetailV2Serializer(DynamicFieldsModelSerializer):
    """文章详情增强序列化器：含作者/分类/标签嵌套 + 方法字段 + 源字段 + 超链接。"""
    # 第2轮迭代#168: 序列化方法字段——友好阅读时长
    reading_time_display = serializers.SerializerMethodField()
    # 第2轮迭代#169: 源字段——直接映射模型属性
    cover_url = serializers.CharField(source='get_cover_url', read_only=True)
    # 第2轮迭代#167: 超链接字段——指向文章详情
    url = serializers.HyperlinkedIdentityField(view_name='api_article_detail')
    # 第2轮迭代#161: 自定义字段
    word_count = WordCountField(read_only=True)
    # 第2轮迭代#170: 只读字段在 Meta.read_only_fields 中声明

    class Meta:
        model = Article
        fields = ['id', 'title', 'excerpt', 'author', 'category', 'category_name',
                  'tags', 'views', 'likes', 'comment_count', 'status', 'kind',
                  'cover_url', 'reading_time_display', 'word_count', 'url',
                  'created_at', 'updated_at']
        # 第2轮迭代#170: 只读字段
        read_only_fields = ['id', 'author', 'views', 'likes', 'comment_count',
                            'created_at', 'updated_at']

    # 第2轮迭代#168: 方法字段实现
    def get_reading_time_display(self, obj):
        return obj.reading_time

    # 第2轮迭代#162: 自定义验证（对象级）
    def validate(self, attrs):
        title = (attrs.get('title') or '').strip()
        if not title:
            raise serializers.ValidationError('标题不能为空')
        return attrs

    # 第2轮迭代#163: 自定义 create——复用 ArticleSerializer 的标签处理
    def create(self, validated_data):
        tag_names = validated_data.pop('tag_names', [])
        article = Article.objects.create(**validated_data)
        if tag_names:
            names = {n.strip() for n in tag_names if n.strip()}
            article.tags.set([Tag.objects.get_or_create(name=n)[0] for n in names])
        return article

    # 第2轮迭代#164: 自定义 update
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
