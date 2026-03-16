# Easyget 极简重构与优化实施计划

## 目标
响应用户需求，对现有系统进行**大幅度做减法**。剥离所有复杂的 LLM 解析（动态表单、初始画像提取）以及依赖 LLM 的大一统打分/评估体系。
将系统核心收敛为最直接的工具闭环：**纯手动输入搜索条件 -> 自动爬取（带严格过滤） -> 判定墙人工清洗**。

## 阶段一：后端“刮骨疗毒”（移除冗余 AI 逻辑，只留核心）
**目标：** 抛弃花哨的动态分析，让系统变成纯粹的高级数据采集器。

1. **移除 LLM 解析与评估引擎**
   - **修改内容：** 
     - 停用 [backend/app/engines/analyzer/extractor.py](file:///e:/Exercise/VibeCode/Easyget/backend/app/engines/analyzer/extractor.py) (LLM结构化提取) 和 [backend/app/engines/analyzer/evaluator.py](file:///e:/Exercise/VibeCode/Easyget/backend/app/engines/analyzer/evaluator.py) (多维度打分)。
     - 修改 [backend/app/engines/analyzer/pipeline.py](file:///e:/Exercise/VibeCode/Easyget/backend/app/engines/analyzer/pipeline.py)：线索从 Collector 回来后，只做基础的基于关键词的**前置语义排重降噪**（使用 [feature_filter.py](file:///e:/Exercise/VibeCode/Easyget/backend/tests/test_feature_filter.py) 或轻量 Embedding），不再调用 LLM 进行深度结构化提取和打分。
2. **简化画像数据结构**
   - **修改内容：** `BusinessConstraint` 模型只保留最基础的手工字段：`company_name`, `core_business` (用作搜索主词), `geography_limits` (备用条件), `custom_urls` (定向抓取站)。

## 阶段二：增强核心引擎（加强采集与时效过滤）
**目标：** 在去除了 LLM 把关后，采集层必须自己把好关。

1. **绝对时效性过滤**
   - **修改内容：** 
     - 在 [GeneralSearchStrategy](file:///e:/Exercise/VibeCode/Easyget/backend/app/engines/collector/strategies.py#12-121) (Serper) 中追加时间和地区限制参数（如过去两周）。
     - 在 [BrowserSearchStrategy](file:///e:/Exercise/VibeCode/Easyget/backend/app/engines/collector/browser_search_strategy.py#11-123) (Baidu) 的查询 URL 中加入时间限定，阻断陈旧数据。
2. **门户网站智能爬取（轻量化）**
   - **修改内容：** 优化 [SiteSpecificStrategy](file:///e:/Exercise/VibeCode/Easyget/backend/app/engines/collector/playwright_strategy.py#12-169) 的 [_extract_detail_links](file:///e:/Exercise/VibeCode/Easyget/backend/app/engines/collector/playwright_strategy.py#53-83)，引入基于 CSS 大小的区块判定，或直接抽取列表区所有链接，通过更宽泛但排除了导航栏的模式匹配替换死板的“招标”字眼，从而提升现代政采网站的抓取率。

## 阶段三：前端全盘极简化 (UI 重塑)
**目标：** 干掉复杂的交互，只留极简工具形态。

1. **重构 Setup 页面为极简手动表单**
   - **修改文件：** [frontend/src/pages/SetupWizard.tsx](file:///e:/Exercise/VibeCode/Easyget/frontend/src/pages/SetupWizard.tsx) (或者直接叫 `ManualConfig.tsx`)
   - **重构方向：** 彻底干掉文件上传解析、动态生成表单的流程。页面只有一个全屏的简约卡片，提供：搜索主词（多行文本）、定向监控网址（多行）、启动按钮。
2. **精简 Dashboard**
   - **修改文件：** 取消 `MainGrid` 的多面板监控，取消所有侧边栏其他菜单。
   - **重构方向：** 点击“开始任务”后直接显示一个极简进度条，跑完直接跳转到 [DecisionWall](file:///e:/Exercise/VibeCode/Easyget/frontend/src/pages/DecisionWall.tsx#28-252)（判定墙）。判定墙只展示最原始的标题、摘要、出处链接和时间，供用户快速左右滑动清洗。

## 实施顺序
第一步：清洗前端代码（删除不需要的组件、修改路由，重做表单页）。
第二步：清理后端 API（干掉 `/parser/initial` 和 `/parser/form` 等）。
第三步：改造后端 [pipeline.py](file:///e:/Exercise/VibeCode/Easyget/backend/app/engines/analyzer/pipeline.py)（剥离 LLM 链路），加上防陈旧数据的强校验参数。
