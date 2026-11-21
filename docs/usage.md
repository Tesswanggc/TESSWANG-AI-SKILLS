# 使用说明

## 环境要求

- Python 3.10+（仅标准库，无需第三方依赖）
- 可访问 `https://www.tesswang.com` 的网络环境

## 阶段一：构建商品主表

```bash
# 1. 拉取原始数据（公开只读接口）
curl -sSL "https://www.tesswang.com/products.json?limit=250" -o data/raw/tess_products.json

# 2. 生成主表
python3 scripts/build_product_master.py \
  data/raw/tess_products.json \
  data/product_master/product_master.csv \
  data/product_master/products_normalized.json
```

输出：
- `product_master.csv`：UTF-8 BOM 编码，可用 Excel/Numbers 直接打开。
- `products_normalized.json`：含规格、图片、变体的完整结构化数据。

## 运行测试

```bash
python3 tests/test_parser.py
```

测试使用 `tests/sample_products.json` 独立夹具，不读取真实业务数据。

## 恢复执行

每次启动先读 `state/status.json` 与 `state/run.log`，从“下一步”继续，不重复已完成步骤。
