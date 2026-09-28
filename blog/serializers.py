"""DRF 序列化器：文章 / 分类 / 标签 / 修改日志。"""
#: 导入模块「bleach」，供本文件后续使用
import bleach
#: 从模块「rest_framework」导入所需对象
from rest_framework import serializers

#: 从模块「.models」导入所需对象
from .models import Article, Category, EditLog, Tag
#: 从模块「.utils.html_safety」导入所需对象
from .utils.html_safety import MoeCSSSanitizer  # 与正文净化共用的内联 style 白名单净化器

# ---- 与视图层一致的内容净化白名单（模块级常量，保证两套入口净化口径一致）----
# 富文本正文允许标签：排版 / 语义 / 表格相关，剔除 script / iframe / 表单等危险标签。
#: 定义变量「ARTICLE_ALLOWED_TAGS」，保存对应数据（集合/元组）
ARTICLE_ALLOWED_TAGS = [
    #: 该行执行对应逻辑（结合上下文理解）
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'col', 'colgroup',
    #: 该行执行对应逻辑（结合上下文理解）
    'dd', 'del', 'div', 'dl', 'dt', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    #: 该行执行对应逻辑（结合上下文理解）
    'hr', 'i', 'img', 'ins', 'kbd', 'li', 'ol', 'p', 'pre', 'q', 's', 'samp',
    #: 该行执行对应逻辑（结合上下文理解）
    'small', 'span', 'strike', 'strong', 'sub', 'sup', 'table', 'tbody', 'td',
    #: 该行执行对应逻辑（结合上下文理解）
    'tfoot', 'th', 'thead', 'tr', 'tt', 'u', 'ul', 'figure', 'figcaption',
#: 该行执行对应逻辑（结合上下文理解）
]
#: 定义变量「ARTICLE_ALLOWED_ATTRIBUTES」，保存对应数据
ARTICLE_ALLOWED_ATTRIBUTES = {
    #: 配置项「a」：字典/模型的该键设置为对应值
    'a': ['href', 'title', 'target'],
    #: 配置项「img」：字典/模型的该键设置为对应值
    'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
    #: 该行执行对应逻辑（结合上下文理解）
    '*': ['class', 'style'],
#: 该行执行对应逻辑（结合上下文理解）
}
#: 定义变量「ARTICLE_ALLOWED_PROTOCOLS」，保存对应数据（集合/元组）
ARTICLE_ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


# 迭代#67: CategorySerializer类docstring完善
class CategorySerializer(serializers.ModelSerializer):
    """分类序列化：额外返回该分类下的文章数量 article_count。"""
    #: 定义变量「article_count」，保存对应数据
    article_count = serializers.IntegerField(source='articles.count', read_only=True)

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - model
          - fields
          - read_only_fields

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「model」，保存对应数据
        model = Category
        #: 定义变量「fields」，保存对应数据（集合/元组）
        fields = ['id', 'name', 'description', 'article_count', 'created_at']
        #: 定义变量「read_only_fields」，保存对应数据（集合/元组）
        read_only_fields = ['id', 'created_at']


# 迭代#68: TagSerializer类docstring完善
class TagSerializer(serializers.ModelSerializer):
    """标签序列化：额外返回该标签关联的文章数量 article_count。"""
    #: 定义变量「article_count」，保存对应数据
    article_count = serializers.IntegerField(source='articles.count', read_only=True)

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - model
          - fields
          - read_only_fields

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「model」，保存对应数据
        model = Tag
        #: 定义变量「fields」，保存对应数据（集合/元组）
        fields = ['id', 'name', 'article_count', 'created_at']
        #: 定义变量「read_only_fields」，保存对应数据（集合/元组）
        read_only_fields = ['id', 'created_at']


# 迭代#69: _AuthorSerializer类docstring完善
class _AuthorSerializer(serializers.Serializer):
    """作者信息只读序列化：文章列表/详情中嵌套展示作者基本信息。"""
    #: 定义变量「id」，保存对应数据
    id = serializers.IntegerField()
    #: 定义变量「username」，保存对应数据
    username = serializers.CharField()
    #: 定义变量「nickname」，保存对应数据
    nickname = serializers.CharField()


# 迭代#70: ArticleListSerializer类docstring
class ArticleListSerializer(serializers.ModelSerializer):
    """列表序列化：正文降级为摘要。"""
    #: 定义变量「author」，保存对应数据
    author = _AuthorSerializer(read_only=True)
    #: 定义变量「category_name」，保存对应数据
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    #: 定义变量「tags」，保存对应数据
    tags = TagSerializer(many=True, read_only=True)
    #: 定义变量「excerpt」，保存对应数据
    excerpt = serializers.CharField(read_only=True)

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - model
          - fields

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「model」，保存对应数据
        model = Article
        #: 定义变量「fields」，保存对应数据（集合/元组）
        fields = [
            #: 该行执行对应逻辑（结合上下文理解）
            'id', 'title', 'excerpt', 'author', 'category', 'category_name',
            #: 该行执行对应逻辑（结合上下文理解）
            'tags', 'views', 'status', 'kind', 'created_at', 'updated_at',
        #: 该行执行对应逻辑（结合上下文理解）
        ]


# 迭代#71: ArticleSerializer类docstring
class ArticleSerializer(serializers.ModelSerializer):
    """详情 / 新增 / 修改序列化。

    tag_names 为只写标签名数组，自动 get_or_create；读侧返回标签对象数组。
    """
    #: 定义变量「author」，保存对应数据
    author = _AuthorSerializer(read_only=True)
    #: 定义变量「tags」，保存对应数据
    tags = TagSerializer(many=True, read_only=True)
    #: 定义变量「tag_names」，保存对应数据
    tag_names = serializers.ListField(
        #: 定义变量「child」，保存对应数据
        child=serializers.CharField(max_length=50), required=False, write_only=True)
    #: 定义变量「category_name」，保存对应数据
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - model
          - fields
          - read_only_fields

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「model」，保存对应数据
        model = Article
        #: 定义变量「fields」，保存对应数据（集合/元组）
        fields = [
            #: 该行执行对应逻辑（结合上下文理解）
            'id', 'title', 'content', 'author', 'category', 'category_name',
            #: 该行执行对应逻辑（结合上下文理解）
            'tags', 'tag_names', 'views', 'status', 'kind',
            #: 该行执行对应逻辑（结合上下文理解）
            'created_at', 'updated_at',
        #: 该行执行对应逻辑（结合上下文理解）
        ]
        #: 定义变量「read_only_fields」，保存对应数据（集合/元组）
        read_only_fields = ['id', 'author', 'views', 'created_at', 'updated_at']

    def validate_title(self, value):
        """
        功能：校验「title」。

        参数：
          - value：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        异常：可能抛出 ValidationError，调用方需处理。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 条件判断：条件成立时执行该分支
        if not value.strip():
            #: 主动抛出异常交由上层处理
            raise serializers.ValidationError('标题不能为空')
        # 与视图层一致：超长标题截断到 max_length=200，避免 MySQL Data too long
        #: 返回结果并结束当前函数
        return value.strip()[:200]

    # 迭代#72: serializers中验证异常处理
    # 迭代#73: serializers内容净化注释
    def validate_content(self, value):
        """富文本正文净化：DRF API 写入同样走 bleach，杜绝 XSS 入库。

        与 ``blog.views.sanitize_html`` 同一套白名单口径，
        保证通过表单提交与通过 API 提交的正文安全级别一致。
        """
        #: 条件判断：条件成立时执行该分支
        if not value:
            #: 返回结果并结束当前函数
            return value or ''
        #: 返回结果并结束当前函数
        return bleach.clean(
            #: 该行执行对应逻辑（结合上下文理解）
            value,
            #: 定义变量「tags」，保存对应数据
            tags=ARTICLE_ALLOWED_TAGS,
            #: 定义变量「attributes」，保存对应数据
            attributes=ARTICLE_ALLOWED_ATTRIBUTES,
            #: 定义变量「protocols」，保存对应数据
            protocols=ARTICLE_ALLOWED_PROTOCOLS,
            #: 定义变量「css_sanitizer」，保存对应数据
            css_sanitizer=MoeCSSSanitizer,
            #: 定义变量「strip」，保存对应数据
            strip=True,
        #: 该行执行对应逻辑（结合上下文理解）
        )

    def _apply_tags(self, instance, tag_names):
        """
        功能：应用「tags」。

        参数：
          - instance：传入参数，含义结合函数体与调用处
          - tag_names：传入参数，含义结合函数体与调用处

        返回：无显式返回（None），多以副作用为主。

        注意：含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: 定义变量「names」，保存对应数据
        names = {n.strip() for n in tag_names if n.strip()}
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        tags = [Tag.objects.get_or_create(name=name)[0] for name in names]
        #: 调用「instance.tags.set」执行相应逻辑
        instance.tags.set(tags)

    def create(self, validated_data):
        """
        功能：创建「create」。

        参数：
          - validated_data：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: 定义变量「tag_names」，保存对应数据
        tag_names = validated_data.pop('tag_names', [])
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        article = Article.objects.create(**validated_data)
        #: 调用「self._apply_tags」执行相应逻辑
        self._apply_tags(article, tag_names)
        #: 返回结果并结束当前函数
        return article

    def update(self, instance, validated_data):
        """
        功能：更新「update」。

        参数：
          - instance：传入参数，含义结合函数体与调用处
          - validated_data：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 定义变量「tag_names」，保存对应数据
        tag_names = validated_data.pop('tag_names', None)
        #: 循环遍历，逐个处理元素
        for attr, value in validated_data.items():
            #: 调用「setattr」执行相应逻辑
            setattr(instance, attr, value)
        #: 保存对象（INSERT/UPDATE），可能触发模型信号
        instance.save()
        #: 条件判断：条件成立时执行该分支
        if tag_names is not None:
            #: 调用「self._apply_tags」执行相应逻辑
            self._apply_tags(instance, tag_names)
        #: 返回结果并结束当前函数
        return instance


# 迭代#74: EditLogSerializer类docstring完善
class EditLogSerializer(serializers.ModelSerializer):
    """轻量修改日志：仅修改人 + 修改时间。"""
    #: 定义变量「editor_name」，保存对应数据
    editor_name = serializers.CharField(source='editor.username', read_only=True)

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - model
          - fields

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「model」，保存对应数据
        model = EditLog
        #: 定义变量「fields」，保存对应数据（集合/元组）
        fields = ['id', 'editor_name', 'edited_at']



# ============================ 第2轮迭代#161-#170: 序列化器增强 ============================


# 第2轮迭代#161: 自定义字段——字数展示字段
class WordCountField(serializers.IntegerField):
    """只读字段：在序列化时实时计算文章字数。"""
    def to_representation(self, value):
        # value 为 Article 实例
        """
        功能：处理「to representation」相关逻辑。

        参数：
          - value：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return getattr(value, 'word_count', 0)


# 第2轮迭代#166: 动态字段序列化基类——通过 context['fields'] 控制输出字段子集
class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """支持按 context['fields'] 动态裁剪返回字段的 ModelSerializer 基类。"""
    def __init__(self, *args, **kwargs):
        """
        功能：初始化「init」。

        返回：无显式返回（None），多以副作用为主。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 调用「super」执行相应逻辑
        super().__init__(*args, **kwargs)
        #: 定义变量「fields」，保存对应数据
        fields = self.context.get('fields')
        #: 条件判断：条件成立时执行该分支
        if fields:
            #: 定义变量「allowed」，保存对应数据
            allowed = set(fields)
            #: 循环遍历，逐个处理元素
            for name in list(self.fields.keys()):
                #: 条件判断：条件成立时执行该分支
                if name not in allowed:
                    #: 调用「self.fields.pop」执行相应逻辑
                    self.fields.pop(name)


# 第2轮迭代#165/#167/#168/#169/#170: 文章详情增强序列化器
class ArticleDetailV2Serializer(DynamicFieldsModelSerializer):
    """文章详情增强序列化器：含作者/分类/标签嵌套 + 方法字段 + 源字段 + 超链接。"""
    # 第2轮迭代#168: 序列化方法字段——友好阅读时长
    #: 定义变量「reading_time_display」，保存对应数据
    reading_time_display = serializers.SerializerMethodField()
    # 第2轮迭代#169: 源字段——直接映射模型属性
    #: 定义变量「cover_url」，保存对应数据
    cover_url = serializers.CharField(source='get_cover_url', read_only=True)
    # 第2轮迭代#167: 超链接字段——指向文章详情
    #: 定义变量「url」，保存对应数据
    url = serializers.HyperlinkedIdentityField(view_name='api_article_detail')
    # 第2轮迭代#161: 自定义字段
    #: 定义变量「word_count」，保存对应数据
    word_count = WordCountField(read_only=True)
    # 第2轮迭代#170: 只读字段在 Meta.read_only_fields 中声明

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - model
          - fields
          - read_only_fields

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「model」，保存对应数据
        model = Article
        #: 定义变量「fields」，保存对应数据（集合/元组）
        fields = ['id', 'title', 'excerpt', 'author', 'category', 'category_name',
                  #: 该行执行对应逻辑（结合上下文理解）
                  'tags', 'views', 'likes', 'comment_count', 'status', 'kind',
                  #: 该行执行对应逻辑（结合上下文理解）
                  'cover_url', 'reading_time_display', 'word_count', 'url',
                  #: 该行执行对应逻辑（结合上下文理解）
                  'created_at', 'updated_at']
        # 第2轮迭代#170: 只读字段
        #: 定义变量「read_only_fields」，保存对应数据（集合/元组）
        read_only_fields = ['id', 'author', 'views', 'likes', 'comment_count',
                            #: 该行执行对应逻辑（结合上下文理解）
                            'created_at', 'updated_at']

    # 第2轮迭代#168: 方法字段实现
    def get_reading_time_display(self, obj):
        """
        功能：获取「reading time display」。

        参数：
          - obj：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return obj.reading_time

    # 第2轮迭代#162: 自定义验证（对象级）
    def validate(self, attrs):
        """
        功能：校验「validate」。

        参数：
          - attrs：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        异常：可能抛出 ValidationError，调用方需处理。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 定义变量「title」，保存对应数据（集合/元组）
        title = (attrs.get('title') or '').strip()
        #: 条件判断：条件成立时执行该分支
        if not title:
            #: 主动抛出异常交由上层处理
            raise serializers.ValidationError('标题不能为空')
        #: 返回结果并结束当前函数
        return attrs

    # 第2轮迭代#163: 自定义 create——复用 ArticleSerializer 的标签处理
    def create(self, validated_data):
        """
        功能：创建「create」。

        参数：
          - validated_data：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: 定义变量「tag_names」，保存对应数据
        tag_names = validated_data.pop('tag_names', [])
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        article = Article.objects.create(**validated_data)
        #: 条件判断：条件成立时执行该分支
        if tag_names:
            #: 定义变量「names」，保存对应数据
            names = {n.strip() for n in tag_names if n.strip()}
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            article.tags.set([Tag.objects.get_or_create(name=n)[0] for n in names])
        #: 返回结果并结束当前函数
        return article

    # 第2轮迭代#164: 自定义 update
    def update(self, instance, validated_data):
        """
        功能：更新「update」。

        参数：
          - instance：传入参数，含义结合函数体与调用处
          - validated_data：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 循环遍历，逐个处理元素
        for attr, value in validated_data.items():
            #: 调用「setattr」执行相应逻辑
            setattr(instance, attr, value)
        #: 保存对象（INSERT/UPDATE），可能触发模型信号
        instance.save()
        #: 返回结果并结束当前函数
        return instance
