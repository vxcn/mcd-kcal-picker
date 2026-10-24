"""确定性热量组合挑选器，无第三方依赖。

输入是一份餐品营养数据，输出是总热量最接近目标、
且不超过上限的 2 到 4 项组合。算法是整数热量背包 DP，
同一个输入和同一份数据，算出来的结果是可复现的。
"""
import argparse
import json
import os
import re
import sys

NAME_KEYS = ["name", "foodName", "food_name", "productName", "title", "餐品名", "名称"]
KCAL_KEYS = ["kcal", "energy", "energyKcal", "calories", "热量", "能量"]
PROTEIN_KEYS = ["protein", "蛋白质"]
FAT_KEYS = ["fat", "脂肪"]
CARB_KEYS = ["carbohydrate", "carbs", "碳水化合物"]
SODIUM_KEYS = ["sodium", "钠"]


def parse_number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for key in ("value", "amount", "num"):
            if key in value:
                return parse_number(value[key])
        return None
    text = str(value)
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def first_value(item, keys):
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


def parse_csv_text(text):
    """解析 list-nutrition-foods 的真实返回格式。

    真实返回不是 JSON 列表，而是一段形如
    [160]{productName,nutritionDescription,energyKj,energyKcal,protein,
    fat,carbohydrate,sodium,calcium}:
      名称,null,千焦,千卡,蛋白质,脂肪,碳水,钠,钙
    的文本，字段顺序以花括号里的表头为准。
    """
    match = re.search(r"\{([^}]+)\}:\s*\n(.*)", text, re.DOTALL)
    if not match:
        return []
    headers = [h.strip() for h in match.group(1).split(",")]
    rows = []
    for line in match.group(2).splitlines():
        line = line.strip().strip(",").strip('"')
        if not line or line.startswith("#") or line.startswith("{"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < len(headers):
            continue
        row = {}
        for header, value in zip(headers, parts):
            row[header] = None if value in ("null", "") else value
        rows.append(row)
    return rows


def extract_from_text(text):
    if not isinstance(text, str):
        return []
    try:
        parsed = json.loads(text)
        found = find_food_list(parsed)
        if found:
            return found
    except (json.JSONDecodeError, TypeError):
        pass
    # text 里可能嵌了一段 Original Response 的 JSON，先把它抠出来
    start = text.find('{"success"')
    if start >= 0:
        try:
            parsed = json.loads(text[start:])
            found = find_food_list(parsed)
            if found:
                return found
            data = parsed.get("data") if isinstance(parsed, dict) else None
            if isinstance(data, str):
                rows = parse_csv_text(data)
                if rows:
                    return rows
        except (json.JSONDecodeError, TypeError):
            pass
    rows = parse_csv_text(text)
    if rows:
        return rows
    return []


def find_food_list(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("foods", "items", "data", "list", "result"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # data 字段本身可能是 CSV 文本
        if isinstance(data.get("data"), str):
            rows = extract_from_text(data["data"])
            if rows:
                return rows
        # MCP tools/call 的 content 结构：content 里有一段 text
        content = data.get("content")
        if isinstance(content, list):
            for entry in content:
                if isinstance(entry, dict) and entry.get("type") == "text":
                    found = extract_from_text(entry["text"])
                    if found:
                        return found
        # structuredContent 里也可能直接放列表
        structured = data.get("structuredContent")
        if structured:
            found = find_food_list(structured)
            if found:
                return found
    return []


def normalize(raw_items):
    foods = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        kcal = parse_number(first_value(item, KCAL_KEYS))
        if kcal is None:
            continue
        name = first_value(item, NAME_KEYS)
        if not name:
            continue
        tags = item.get("tags") or item.get("labels") or []
        if isinstance(tags, str):
            tags = [tags]
        foods.append({
            "name": str(name),
            "kcal": round(kcal),
            "protein": parse_number(first_value(item, PROTEIN_KEYS)) or 0,
            "fat": parse_number(first_value(item, FAT_KEYS)) or 0,
            "carbs": parse_number(first_value(item, CARB_KEYS)) or 0,
            "sodium": parse_number(first_value(item, SODIUM_KEYS)) or 0,
            "tags": [str(t) for t in tags],
        })
    return foods


def pick(foods, target, max_kcal):
    # dp[(总热量, 件数)] = 组合下标列表，只保留先到达的那一种，保证确定性
    dp = {(0, 0): []}
    for idx, food in enumerate(foods):
        kcal = food["kcal"]
        if kcal <= 0 or kcal > max_kcal:
            continue
        for (total, count), combo in list(dp.items()):
            if count >= 4:
                continue
            new_total = total + kcal
            if new_total > max_kcal:
                continue
            key = (new_total, count + 1)
            if key not in dp:
                dp[key] = combo + [idx]
    candidates = []
    for (total, count), combo in dp.items():
        if 2 <= count <= 4 and combo:
            candidates.append((abs(total - target), abs(count - 3), -total, total, combo))
    if not candidates:
        return None
    candidates.sort()
    _, _, _, total, combo = candidates[0]
    chosen = [foods[i] for i in combo]
    return {
        "items": [{"name": f["name"], "kcal": f["kcal"]} for f in chosen],
        "total_kcal": total,
        "target_kcal": target,
        "max_kcal": max_kcal,
        "diff_kcal": total - target,
        "protein_g": round(sum(f["protein"] for f in chosen), 1),
        "fat_g": round(sum(f["fat"] for f in chosen), 1),
        "carbs_g": round(sum(f["carbs"] for f in chosen), 1),
        "sodium_mg": round(sum(f["sodium"] for f in chosen), 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--foods", default="")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--target", type=int, default=600)
    parser.add_argument("--max", type=int, default=700)
    parser.add_argument("--avoid", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.demo:
        path = os.path.join(os.path.dirname(__file__), "..", "examples", "demo_foods.json")
    elif args.foods:
        path = args.foods
    else:
        print("请指定 --demo 或 --foods 数据文件。", file=sys.stderr)
        return 2
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    foods = normalize(find_food_list(data))
    if args.avoid:
        foods = [f for f in foods
                 if args.avoid not in f["name"]
                 and not any(args.avoid in t for t in f["tags"])]
    if not foods:
        print("没有可用的餐品数据。", file=sys.stderr)
        return 1
    result = pick(foods, args.target, args.max)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result else 1
    if not result:
        print(f"没有总热量不超过 {args.max} 千卡的组合，"
              f"建议放宽上限或降低目标。")
        return 1
    print(f"目标 {args.target} 千卡，上限 {args.max} 千卡，"
          f"共 {len(result['items'])} 项：")
    for item in result["items"]:
        print(f"- {item['name']}：{item['kcal']} 千卡")
    print(f"合计：{result['total_kcal']} 千卡，"
          f"离目标 {result['diff_kcal']:+d} 千卡；"
          f"蛋白质 {result['protein_g']} 克，脂肪 {result['fat_g']} 克，"
          f"碳水化合物 {result['carbs_g']} 克，钠 {result['sodium_mg']} 毫克。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
