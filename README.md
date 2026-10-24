# 麦门热量搭配师 · mcd-kcal-picker

基于麦当劳中国官方 MCP 开发的热量搭配 Skill：你说一个目标热量，它就从官方营养数据里帮你凑出一顿主食加小食加饮料的组合，总热量尽量接近目标，又不超过你设的上限。

麦当劳程序员创意开发大赛参赛作品，由参赛者独立开发，非麦当劳官方产品。项目输出仅供参考，不构成医疗、营养或其他专业建议；餐品信息、价格及供应状态以麦当劳官方渠道的实时结果为准。

## 它解决什么问题

想吃麦当劳，又不想一顿吃超标，人工翻营养表很费劲。这个 Skill 把取数交给 MCP，把算术交给代码：先调官方工具拿到餐品营养列表，再用确定性算法挑组合，不靠大模型口算热量。

## 它只做什么，不做什么

只做：

- 调用官方 MCP 的只读工具 list-nutrition-foods，获取餐品营养信息
- 按目标热量和上限，用确定性算法挑出组合，并汇总能量、蛋白质、脂肪、碳水化合物、钠

不做：

- 不下单、不领券、不抽奖、不兑换积分，不调用任何写操作工具
- 不收集、不保存你的 MCP Token，Token 只通过环境变量传入，仓库里没有任何真实凭证

## 快速开始

### 演示模式，不需要 Token

```bash
python3 scripts/pick.py --demo --target 600 --max 700
```

演示模式使用 examples/demo_foods.json 里的示例数据，数据已明确标注为示例，不是官方实时数据，跑通流程用。

### 真实数据模式，需要你自己的 MCP Token

先按官方指南申请 Token，地址是麦当劳 MCP 开放平台，然后只在你自己的终端里设置环境变量，不要把 Token 写进任何文件，也不要发到公开场合：

```bash
export MCD_MCP_TOKEN=你的Token
python3 scripts/mcp_client.py --tool list-nutrition-foods --out /tmp/foods.json
python3 scripts/pick.py --foods /tmp/foods.json --target 600 --max 700
```

MCP 配置示例见 mcp-config.example.json，里面只有占位符。

## 使用示例

```bash
# 目标 600 千卡，上限 700 千卡
python3 scripts/pick.py --demo --target 600 --max 700

# 目标 500 千卡，上限 550 千卡，只要不吃辣的组合
python3 scripts/pick.py --demo --target 500 --max 550 --avoid 辣
```

输出包括组合里的每一项、每一项的热量、组合总热量，以及蛋白质、脂肪、碳水化合物、钠的合计。如果没有符合上限的组合，程序会直接说明，而不是硬凑一个超标的结果。

## 目录结构

- SKILL.md：给 Agent 用的 Skill 说明，触发条件、调用流程、输出格式
- MCP_INTEGRATION.md：实际使用的 MCP Server、工具、调用流程和业务价值
- scripts/mcp_client.py：最小的 Streamable HTTP MCP 客户端，只读，无第三方依赖
- scripts/pick.py：确定性热量组合挑选器，无第三方依赖
- examples/demo_foods.json：演示用示例数据
- mcp-config.example.json：MCP 配置示例，只有占位符
- CONTEST_DECLARATION.md：官方参赛声明，内容不可改动

## 目标用户

- 想吃麦当劳又想控制一顿热量的人
- 想了解商业 MCP 数据怎么落到一个具体小工具里的人
- 想参考 Skill 结构的人：SKILL.md 加 scripts 加 references 的组织方式

## 免责声明

本项目为麦当劳程序员节创意开发大赛参赛作品，由参赛者独立开发，非麦当劳官方产品。项目输出仅供参考，不构成医疗、营养或其他专业建议；餐品信息、价格及供应状态以麦当劳官方渠道的实时结果为准。
