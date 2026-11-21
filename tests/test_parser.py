#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段一解析逻辑测试：使用独立测试夹具，与真实业务数据完全分离。"""
import csv
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "build_product_master.py")
FIXTURE = os.path.join(HERE, "sample_products.json")
OUT_CSV = os.path.join(HERE, "out_test.csv")
OUT_JSON = os.path.join(HERE, "out_test.json")

subprocess.run(
    [sys.executable, SCRIPT, FIXTURE, OUT_CSV, OUT_JSON],
    check=True, capture_output=True, text=True,
)

d = json.load(open(OUT_JSON, encoding="utf-8"))
rows = list(csv.DictReader(open(OUT_CSV, encoding="utf-8-sig")))
checks = []


def check(name, cond):
    checks.append((name, bool(cond)))


check("商品数=2", d["product_count"] == 2)
check("变体行数=2", d["row_count"] == 2 and len(rows) == 2)

set_row = next(r for r in rows if "Set" in r["商品名称"])
single_row = next(r for r in rows if "Single" in r["商品名称"])

check("套装识别为set", set_row["销售单位"] == "set")
check("套装件数=3", set_row["套组件数"] == "3")
check("套装材质来自spec=Porcelain", set_row["材质"] == "Porcelain")
check("套装系列=Test Series", set_row["系列"] == "Test Series")
check("套装价格50.00 USD", set_row["展示价格"] == "50.00" and set_row["币种"] == "USD")
check("SKU留空并注明缺失", set_row["SKU"] == "" and "SKU" in set_row["缺失说明"])
check("MOQ留空并注明", set_row["MOQ"] == "" and "MOQ" in set_row["缺失说明"])
check("单件识别为piece", single_row["销售单位"] == "piece")
check("单件件数=1", single_row["套组件数"] == "1")
check("标签回退材质=Ceramic", single_row["材质"] == "Ceramic")
check("缺货状态unavailable", single_row["库存状态"] == "unavailable")
check("主图关联", set_row["主图"] == "https://example.com/a.jpg")

check("价格未被串改", float(set_row["展示价格"]) == 50.00
      and float(single_row["展示价格"]) == 12.50)

failed = [n for n, ok in checks if not ok]
for n, ok in checks:
    print(("PASS" if ok else "FAIL"), n)
print(f"\n{len(checks)-len(failed)}/{len(checks)} passed")
sys.exit(1 if failed else 0)
