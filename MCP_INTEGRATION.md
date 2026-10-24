# MCP 集成说明

## 使用的 MCP Server

- 服务：麦当劳中国官方 MCP Server
- 接入地址：https://mcp.mcd.cn
- 传输协议：Streamable HTTP
- 认证方式：请求头 Authorization，格式为 Bearer 加 Token，Token 只通过环境变量 MCD_MCP_TOKEN 传入
- 限流：官方说明每个 Token 每分钟最多 600 次请求，本项目一次完整调用只需要初始化、列工具、调一次工具共几次请求，远低于限流

## 实际使用的工具

| 工具 | 用途 | 是否写操作 |
| --- | --- | --- |
| list-nutrition-foods | 获取麦当劳常见餐品的营养成分数据，包括能量、蛋白质、脂肪、碳水化合物、钠等 | 否，只读 |

本项目在代码里只调用这一个工具。没有调用任何下单、领券、抽奖、兑换类工具，整个流程是只读的。

## 调用流程

1. 向 https://mcp.mcd.cn 发送 JSON-RPC 的 initialize 请求，带上 Authorization 请求头，拿到会话标识后，后续请求都带上它。
2. 发送 notifications/initialized 通知。
3. 调用 tools/list，确认 list-nutrition-foods 可用。
4. 调用 tools/call，传入 list-nutrition-foods，拿到营养列表。
5. 把返回结果归一化为统一字段：名称、能量千卡、蛋白质克、脂肪克、碳水化合物克、钠毫克、标签。
6. 把归一化数据交给 scripts/pick.py，用确定性算法挑组合，输出组合和营养合计。

实现见 scripts/mcp_client.py，标准库 urllib 实现，无第三方依赖，响应可能是 JSON 或 SSE 流两种形式，客户端都做了处理。

## 实测记录

- tools/list 实测返回 35 个工具，其中包括本项目使用的 list-nutrition-foods。
- list-nutrition-foods 实测返回 160 条餐品记录，但格式不是 JSON 列表，而是一段带表头的类 CSV 文本，表头顺序为 productName、nutritionDescription、energyKj、energyKcal、protein、fat、carbohydrate、sodium、calcium，pick.py 里的 parse_csv_text 就是按这个实测格式解析的，不是按猜测写的。
- 用实测数据跑 pick.py，目标 600 千卡、上限 700 千卡可以凑出正好 600 千卡的组合，目标 500 千卡、上限 550 千卡可以凑出正好 500 千卡的组合，说明归一化和挑选逻辑在真实数据上是通的。

## 业务价值

取数交给 MCP，算术交给代码，表达交给 Agent。MCP 保证热量数字来自官方营养数据而不是模型现编；确定性挑选保证同一个输入、同一份数据，算出来的组合是可复现的；只读设计保证这个 Skill 再怎么用，也不会替用户花钱或动账户里的积分和券。

## 演示与真实数据的区别

- 演示模式：python3 scripts/pick.py --demo，数据来自 examples/demo_foods.json，已明确标注为示例，不是官方实时数据，只用来跑通流程。
- 真实模式：python3 scripts/mcp_client.py 拉取真实营养列表，再交给 pick.py 挑选。真实模式需要你自己的 Token，Token 只走环境变量，仓库里只有占位符。
