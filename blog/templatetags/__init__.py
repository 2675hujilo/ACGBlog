# -*- coding: utf-8 -*-
"""templatetags 包：自定义模板标签与过滤器。

主要标签库为 ``blog_extras``，并已在 settings 的模板 ``libraries`` 中注册为内置，
模板无需 ``{% load %}`` 即可使用其过滤器（如文案格式化、相对时间、正文首图提取等）。
"""
