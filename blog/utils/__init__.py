# -*- coding: utf-8 -*-
"""
blog.utils —— 通用工具层（与具体业务无关、可全局复用的纯工具）。

本包收纳从 ``blog`` 根目录归类而来的「工具」模块：

- :mod:`html_safety`          bleach / tinycss2 的 HTML 与内联样式净化白名单；
- :mod:`cache_keys`           详情页缓存 key 规范、版本号与失效工具；
- :mod:`deprecation_filters`  第三方依赖（requests）版本告警的过滤消除。

与 :mod:`blog.services` 的边界
------------------------------
- ``utils`` 里的工具**不依赖具体业务模型语义**，换一个项目理论上也能复用；
- 一旦某段逻辑需要理解「文章 / 评论 / 审核」等业务概念，应放入 ``services``。

新增工具模块时请在本文件登记，并保证工具函数无副作用、可独立测试。
"""
