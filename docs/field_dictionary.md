# 商品主表字段字典（阶段一）

数据源：Shopify storefront 接口 `products.json`（公开只读）。一行 = 一个变体（variant）。

| 字段 | 来源 / 规则 | 缺失处理 |
|---|---|---|
| 商品名称 | products.title | 必有 |
| 系列 | 正文 Collection 标签；无则取 product_type | 留空注明 |
| 商品链接 | `https://www.tesswang.com/products/<handle>` | 必有 |
| SKU | variant.sku | 官网未提供则留空注明 |
| 材质 | 正文 Material → 正文材质关键词 → 标题关键词 → 标签“陶瓷” | 全部无法判定则留空注明 |
| 工艺 | 正文 Finish / Texture | 留空注明 |
| 花色/釉色 | 正文 Glaze | 留空注明 |
| 尺寸 | variant 选项（option1/2/3）；无则正文 Size/Diameter | 留空注明 |
| 套组件数 | 标题 N-Piece → 正文 Set includes → 正文 composed-of/set of → 开篇量词 | 套装未注明则留空；单件=1 |
| 件数依据 | 记录件数解析路径，便于追溯 | — |
| 销售单位 | set / piece，按词边界匹配，禁止子串误判 | — |
| 币种 | 经首页与商店配置核验为 USD | — |
| 展示价格 | variant.price（公开标价） | 必有 |
| MOQ | storefront 未公示 | 留空注明 |
| 库存状态 | variant.available 布尔值 | 精确数量无法取得时注明 |
| 运费与税费条件 | variant.taxable / requires_shipping 标志 | 具体费率未公示时注明 |
| 标签 | products.tags 原文，保留证据 | — |
| 主图 / 图片数 | products.images，首图为主图，按商品关联 | 无图则空 |
| 发布时间 | published_at | — |
| 采集时间 | 写入时北京时间（Asia/Shanghai） | 自动生成 |
| 缺失说明 | 逐商品列出全部缺失项与原因 | — |

## 口径规则

- 套装价格与单件价格分行存放，禁止把单件价格当作整套价格。
- 图片按商品维度关联，不跨商品混用。
- 多规格商品每个变体独立成行，各自带价格与尺寸。
