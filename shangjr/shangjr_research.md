最近更新时间： 3.21  01:07

Github:

- 邵辉      ssshhhaaaooohhuuii
- Alexa    alexhegit
- 毛毛      maoyadongsh 
- 宝明       joker2233111
- 佳锐	   Michel-Johnson

------

### Resources

------

#### Spark

[JAX 优化方案](https://developer.nvidia.cn/build-spark/jax#i7njvai)

#### NemoClaw

[repo](https://github.com/NVIDIA/NemoClaw/tree/main)

#### OpenClaw

[多 Agent 配置中文教程](https://openclawgithub.cc/guide/agents/)

#### Others

[AI4Finance Foundation | Open Source Financial AI （看起来很厉害）](https://ai4finance.org/#projects)

[Nemotron 120B-A12B-NVFP4 · Hugging Face](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4)

[Gemini_DeepResearch(我让gemini总结的，毛毛可以简单看一下，因为文本较长，可能只有很小一部分是关键信息）](./Gemini_DeepResearch)

------

### Similar Projects

------

#### TradingAgents

[repo 35.2k stars](https://github.com/TauricResearch/TradingAgents?tab=readme-ov-file)

生态很好，文档很全，明天我去尝试部署到我的本地ubuntu端。

##### multi-agent：

###### Analyst Team

1. **基本面分析师**：评估公司财务和绩效指标，识别==内在价值和潜在警示信号==。
2. **情绪分析师**：利用情绪评分算法分析社交媒体和公众情绪，以评估==短期市场情绪==。
3. **新闻分析师**：监测==全球新闻==和宏观经济指标，解读事件对市场状况的影响。
4. **技术分析师**：利用技术指标（如 MACD 和 RSI）来检测交易模式并预测价格走势。

> Q:我们是要做的比他们更全面，用更多的agent？还是说只做一个方面，比如技术分析师?

###### Researcher Team

包括看涨和看跌的研究人员，他们对分析师团队提供的洞察进行批判性评估。通过结构化的==辩论==，他们在潜在收益与固有风险之间取得平衡。

> 我觉得这里应该就是多个agent讨论，最好让他们各自就有一个潜意识，就是我不要和别人的观点完全相同，通过更多元的思维，去探索更多的可能。
> 当然，有没有可能这里也有一套固定的模式或方法论，来更科学、系统地解决问题。

###### Trader Agent

撰写分析师和研究人员的报告，以做出明智的交易==决策==。它根据全面的市场洞察决定交易的==时间==和==规模==。

###### Risk Management and Portfolio Manager

- 持续评估投资组合==风险==，评估市场波动性、流动性及其他风险因素。风险管理团队评估并调整交易策略，向投资组合经理提供评估报告以供最终决策
- 投资组合经理批准/拒绝交易提案。如果批准，订单将发送到模拟交易所并执行。

> 这两个agent就比较专业了，可能需要毛毛来评估一下这里哪些agent比较重要？

------

#### finance-claw

[repo](https://github.com/TuJinSAMA/finance-claw)

OpenClaw 金融投资配置模板
最近一次更新于两周前，readme中没有详细介绍内部agent的分工
不过有一些skills可能会有用
项目调用了下列API

| API             | 说明                    | 注册地址                                                     |
| --------------- | ----------------------- | ------------------------------------------------------------ |
| FRED_API_KEY    | 美联储经济数据 (免费)   | [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) |
| FMP_API_KEY     | 财务数据 (免费/250次天) | [financialmodelingprep.com](https://financialmodelingprep.com/developer/docs/) |
| POLYGON_API_KEY | 市场数据 ($29/月)       | [polygon.io](https://polygon.io/)                            |

------

#### FinGPT

[ repo 18.9k stars](https://github.com/AI4Finance-Foundation/FinGPT)

这个是一个专用于金融领域的模型，和我们的multi-agent架构不太一样。

------

#### FinRobot

[repo 6.5k stars](https://github.com/AI4Finance-Foundation/FinRobot)

**FinRobot** 是一款专为金融应用量身定制的 AI 代理平台，超越了 FinGPT 的单一模型方法。它整合了多种人工智能技术——包括大型语言模型（LLM）、强化学习和定量分析——为投资研究自动化、算法交易策略和风险评估提供动力，为金融行业提供全栈智能解决方案。

##### **Pipeline**

1. **获取财务数据** ：通过 FMP API 获取损益表、资产负债表、现金流
2. **流程与预测** ：三年财务预测、DCF 估值、同行比较
3. **AI 代理分析** ：8 位专业代理生成投资论点、风险评估、估值概览等。
4. **报告生成** ：专业多页 HTML/PDF，支持 15+图表类型

##### **Key Features：**

- **自动报告生成** ——即时生成专业股权研究报告
- **财务分析** ——深入分析损益表、资产负债表和现金流
- **估值分析** ——市盈率、EV/EBITDA 倍数及同行比较
- **风险评估** ——全面的投资风险评估

> 我感觉这个更侧重于对单个agent的pipeline设计，毕竟这个是两年前开始构建的项目，不过还在更新，最近一次更新时间是昨天（3.21）

------

#### AI-Trader

[repo 11.9k stars](https://github.com/HKUDS/AI-Trader/tree/main)

基于openclaw的交易平台，二级市场，但这好像只是一个平台，可能没什么参考价值，可能需要邵辉和毛毛判断一下，也许有哪些部分我们可以参考或者对照。

------

#### TradingGroup

[paper](https://arxiv.org/abs/2508.17565)

只有论文，没有代码，我还没读，先让gpt简单总结了一下

> 这篇论文提出了一个用于股票交易的多智能体系统 **TradingGroup**。核心思路是把交易拆成多个专职 agent：新闻情绪分析、财报解读、股价趋势预测、交易风格选择，以及最终交易决策；再加上一个动态风控模块，输出买入 / 卖出 / 持有决策。
>
> 简要总结可以概括成三点：
>
> 1. **它想解决什么问题**
>     作者认为现有 LLM 交易系统常见短板有三类：
>     一是 agent 之间协作不够；二是缺少成体系的“复盘/自我反思”机制；三是缺少包含市场状态和交易决策过程的高质量后训练数据。
>
> 2. 它的方法有什么新意
>
>    这篇论文的亮点主要有两个：
>
>    - 给预测、风格、决策这几个关键 agent 加了 **self-reflection**，让系统能从过去成功和失败案例里总结经验；
>    - 设计了一个 **data-synthesis pipeline**，自动生成和标注交易过程数据，用来继续后训练模型。
>       同时还加入了动态止损止盈和仓位管理。
>
> 3. **结果怎么样**
>     作者报告说，在 **5 个真实股票数据集**上的回测中，TradingGroup 的表现优于规则法、传统机器学习、强化学习，以及已有的 LLM 交易策略。
>
> **一句话评价：**
>  这篇论文的重点不是“用一个更强的大模型直接炒股”，而是把交易系统做成一个**会协作、会复盘、还能自己造训练数据**的 agent 体系


test








