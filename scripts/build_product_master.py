#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESSWANG 阶段一：Shopify products.json -> 商品主表（CSV + 规范化 JSON）
仅使用标准库。缺失字段留空并在“缺失说明”注明原因。
"""
import csv
import html
import json
import re
import sys
from datetime import datetime, timezone, timedelta

SRC = sys.argv[1] if len(sys.argv) > 1 else "tess_products.json"
OUT_CSV = sys.argv[2] if len(sys.argv) > 2 else "product_master.csv"
OUT_JSON = sys.argv[3] if len(sys.argv) > 3 else "products_normalized.json"
BASE_URL = "https://www.tesswang.com"
CN_TZ = timezone(timedelta(hours=8))

WORD_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16,
}
WORDS = "|".join(WORD_NUM.keys())
MAT_BODY_RE = re.compile(
    r"\b(stoneware|porcelain|bone china|earthenware|ceramic|ceramics|glass)\b",
    re.I)
MAT_TITLE_RE = re.compile(
    r"\b(glass|ceramic|porcelain|stoneware|rosewood|wood|metal|brass|earthenware)\b",
    re.I)
SPEC_RE = re.compile(
    r"(?:<strong>|<li[^>]*>)\s*([A-Za-z][A-Za-z /()\-]*?):\s*</strong>?\s*(.*?)\s*"
    r"(?:<br\s*/?>|</li>)", re.I)
TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(s: str) -> str:
    return html.unescape(TAG_RE.sub(" ", s)).strip()


def parse_specs(body: str) -> dict:
    specs = {}
    if not body:
        return specs
    for m in SPEC_RE.finditer(body):
        key = html.unescape(m.group(1)).strip().lower()
        val = strip_tags(m.group(2))
        if val:
            specs[key] = val
    return specs


def first_spec(specs: dict, *keys):
    for k in keys:
        if k in specs:
            return specs[k]
    return ""


def resolve_material(p, specs):
    if specs.get("material"):
        return specs["material"], "spec"
    m = MAT_BODY_RE.search(p.get("body_html") or "")
    if m:
        return m.group(1).title(), "body_keyword"
    m = MAT_TITLE_RE.search(p["title"])
    if m:
        return m.group(1).title(), "title_keyword"
    if "陶瓷" in p.get("tags", []):
        return "Ceramic", "tag"
    return "", "unresolved"


def parse_piece_count(title, body, is_set_flag):
    t = title.lower()
    m = re.search(r"(\d+)\s*[- ]?piece", t)
    if m:
        return int(m.group(1)), "title:N-Piece"
    m = re.search(rf"\b({WORDS})\b[- ]?piece", t)
    if m:
        return WORD_NUM[m.group(1)], "title:word-Piece"
    inc = re.search(r"Set includes?:\s*(.*?)(?:</li>|<br|</p>)", body, re.I)
    if inc:
        items = [x for x in re.split(r"\s*\+\s*", strip_tags(inc.group(1))) if x.strip()]
        if items:
            total = 0
            for it in items:
                mm = re.match(r"\s*(\d+)\s*[x×]", it)
                total += int(mm.group(1)) if mm else 1
            return total, "body:Set includes"
    if is_set_flag:
        plain = strip_tags(body).lower()
        m = re.search(rf"(?:composed of|set of)\s+(\d+|{WORDS})\b", plain)
        if m:
            g = m.group(1)
            return (int(g) if g.isdigit() else WORD_NUM[g]), "body:composed-of"
        head = plain[:240]
        m = re.search(
            rf"\b(\d+|{WORDS})\s+(pieces?|plates?|items?|parts?|objects?)\b", head)
        if m:
            g = m.group(1)
            return (int(g) if g.isdigit() else WORD_NUM[g]), "body:prose"
        return None, "未注明件数"
    return 1, "default:single"


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    products = data["products"]
    collected_at = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S%z")
    rows, normalized = [], []
    mat_sources = {}
    unresolved_material = []

    for p in products:
        body = p.get("body_html", "")
        specs = parse_specs(body)
        tt_blob = f"{p['title']} {p.get('product_type','')}".lower()
        set_flag = (bool(re.search(r"\bset\b", tt_blob))
                    or "set includes" in body.lower()
                    or "composed of" in body.lower())
        sales_unit = "set" if set_flag else "piece"
        piece_count, piece_basis = parse_piece_count(p["title"], body, set_flag)
        collection = first_spec(specs, "collection") or p.get("product_type", "")
        material, mat_src = resolve_material(p, specs)
        mat_sources[mat_src] = mat_sources.get(mat_src, 0) + 1
        if not material:
            unresolved_material.append(p["title"])
        craft = " / ".join(filter(None, [
            first_spec(specs, "finish"), first_spec(specs, "texture")]))
        images = [{
            "url": im.get("src", ""), "width": im.get("width"),
            "height": im.get("height"), "alt": im.get("alt"),
        } for im in p.get("images", [])]
        primary_img = images[0]["url"] if images else ""

        miss = []
        if not material:
            miss.append("材质: 官网未明示且无法从标题/正文/标签判定")
        if all(not v.get("sku") for v in p.get("variants", [])):
            miss.append("SKU: 官网未提供")
        miss.append("MOQ: 官网未公示")
        miss.append("库存精确数量: storefront仅返回available布尔值")
        miss.append("具体运费税费标准: 官网未公示")
        if piece_count is None:
            miss.append("套组件数: 正文未注明")

        norm = {
            "product_id": p["id"], "title": p["title"],
            "collection": collection, "product_type": p.get("product_type", ""),
            "url": f"{BASE_URL}/products/{p['handle']}", "handle": p["handle"],
            "material": material, "material_source": mat_src,
            "craft": craft, "glaze_color": first_spec(specs, "glaze"),
            "piece_count": piece_count, "piece_count_basis": piece_basis,
            "sales_unit": sales_unit, "currency": "USD",
            "tags": p.get("tags", []), "specs": specs,
            "images": images, "primary_image": primary_img,
            "published_at": p.get("published_at", ""), "variants": [],
        }

        for v in p.get("variants", []):
            size = " / ".join(filter(None, [
                v.get("option1"), v.get("option2"), v.get("option3")])) or \
                first_spec(specs, "size", "diameter", "available sizes")
            rows.append({
                "商品名称": p["title"], "系列": collection,
                "商品链接": f"{BASE_URL}/products/{p['handle']}",
                "SKU": v.get("sku") or "", "材质": material,
                "材质依据": mat_src, "工艺": craft,
                "花色/釉色": first_spec(specs, "glaze"), "尺寸": size,
                "套组件数": "" if piece_count is None else piece_count,
                "件数依据": piece_basis, "销售单位": sales_unit,
                "币种": "USD", "展示价格": v.get("price", ""), "MOQ": "",
                "库存状态": "available" if v.get("available") else "unavailable",
                "运费与税费条件": (
                    "taxable=true;requires_shipping=true;具体运费税费官网未公示"
                    if v.get("taxable") else
                    "taxable=false;具体运费条件官网未公示"),
                "标签": "|".join(p.get("tags", [])),
                "主图": primary_img, "图片数": len(images),
                "发布时间": p.get("published_at", ""), "采集时间": collected_at,
                "缺失说明": "; ".join(miss),
            })
            norm["variants"].append({
                "variant_id": v["id"], "variant_title": v.get("title", ""),
                "size": size, "price": v.get("price", ""),
                "available": v.get("available", False),
                "grams": v.get("grams", 0), "sku": v.get("sku") or "",
            })
        normalized.append(norm)

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"collected_at": collected_at,
                   "product_count": len(products), "row_count": len(rows),
                   "products": normalized}, f, ensure_ascii=False, indent=2)

    print(f"products={len(products)} variant_rows={len(rows)}")
    print(f"material_sources={mat_sources}")
    print(f"unresolved_material={unresolved_material}")
    print(f"sets={sum(1 for r in rows if r['销售单位']=='set')}")
    print(f"unknown_piece_products={sum(1 for n in normalized if n['piece_count'] is None)}")
    print(f"images_total={sum(len(n['images']) for n in normalized)}")


if __name__ == "__main__":
    main()
