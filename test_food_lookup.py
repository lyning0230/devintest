#!/usr/bin/env python3

import os
import json
from vision_infer import analyze_image
from food_lookup import search_food, get_food

FOOD_TRANSLATIONS = {
    "エビ": "shrimp",
    "ブロッコリー": "broccoli", 
    "ズッキーニ": "zucchini",
    "調味料": "seasoning",
    "エビとブロッコリーの炒め物": "shrimp and broccoli stir fry"
}

def translate_food_name(japanese_name: str) -> str:
    """Translate Japanese food name to English for FDC API"""
    return FOOD_TRANSLATIONS.get(japanese_name, japanese_name.lower())

def get_nutrition_info(vision_result: dict) -> dict:
    """Get nutrition information for foods identified by vision analysis"""
    nutrition_data = {
        "meal_name": vision_result["meal_name"],
        "meal_name_en": translate_food_name(vision_result["meal_name"]),
        "items": []
    }
    
    for item in vision_result["items"]:
        japanese_name = item["name"]
        english_name = translate_food_name(japanese_name)
        
        print(f"Searching FDC for: {english_name} (original: {japanese_name})")
        
        try:
            search_results = search_food(english_name)
            
            if search_results:
                fdc_id = search_results[0]["fdcId"]
                food_details = get_food(fdc_id)
                
                nutrients = {}
                if "foodNutrients" in food_details:
                    for nutrient in food_details["foodNutrients"]:
                        nutrient_name = nutrient.get("nutrient", {}).get("name", "")
                        nutrient_value = nutrient.get("amount", 0)
                        nutrient_unit = nutrient.get("nutrient", {}).get("unitName", "")
                        
                        if any(key in nutrient_name.lower() for key in ["energy", "protein", "carbohydrate", "fat", "fiber", "sodium"]):
                            nutrients[nutrient_name] = {
                                "value": nutrient_value,
                                "unit": nutrient_unit
                            }
                
                item_data = {
                    "name_jp": japanese_name,
                    "name_en": english_name,
                    "quantity": item["quantity"],
                    "confidence": item["confidence"],
                    "fdc_id": fdc_id,
                    "fdc_description": food_details.get("description", ""),
                    "nutrients": nutrients
                }
            else:
                item_data = {
                    "name_jp": japanese_name,
                    "name_en": english_name,
                    "quantity": item["quantity"],
                    "confidence": item["confidence"],
                    "fdc_id": None,
                    "fdc_description": "Not found in FDC database",
                    "nutrients": {}
                }
                
        except Exception as e:
            print(f"Error looking up {english_name}: {str(e)}")
            item_data = {
                "name_jp": japanese_name,
                "name_en": english_name,
                "quantity": item["quantity"],
                "confidence": item["confidence"],
                "fdc_id": None,
                "fdc_description": f"Error: {str(e)}",
                "nutrients": {}
            }
        
        nutrition_data["items"].append(item_data)
    
    return nutrition_data

def calculate_actual_nutrition(nutrition_data: dict) -> dict:
    """Calculate actual nutrition values based on estimated quantities"""
    nutrient_jp_names = {
        "Energy": "エネルギー",
        "Protein": "タンパク質", 
        "Total lipid (fat)": "脂質",
        "Carbohydrate, by difference": "炭水化物",
        "Fiber, total dietary": "食物繊維",
        "Sodium, Na": "ナトリウム",
        "Fatty acids, total saturated": "飽和脂肪酸",
        "Fatty acids, total trans": "トランス脂肪酸"
    }
    
    for item in nutrition_data["items"]:
        if item["fdc_id"] and item["nutrients"]:
            quantity_g = item["quantity"]["value"]  # Assuming all quantities are in grams
            item["actual_nutrients"] = {}
            
            for nutrient_name, nutrient_data in item["nutrients"].items():
                actual_value = (nutrient_data["value"] * quantity_g) / 100.0
                jp_name = nutrient_jp_names.get(nutrient_name, nutrient_name)
                
                item["actual_nutrients"][jp_name] = {
                    "value": round(actual_value, 2),
                    "unit": nutrient_data["unit"],
                    "original_name": nutrient_name
                }
    
    total_nutrition = {}
    for item in nutrition_data["items"]:
        if "actual_nutrients" in item:
            for jp_name, nutrient_data in item["actual_nutrients"].items():
                if jp_name not in total_nutrition:
                    total_nutrition[jp_name] = {
                        "value": 0,
                        "unit": nutrient_data["unit"]
                    }
                total_nutrition[jp_name]["value"] += nutrient_data["value"]
    
    for nutrient in total_nutrition.values():
        nutrient["value"] = round(nutrient["value"], 2)
    
    nutrition_data["total_nutrition"] = total_nutrition
    return nutrition_data

def format_nutrition_report_html(nutrition_data: dict) -> str:
    """Format nutrition data into an HTML table report"""
    html = []
    
    html.append(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>栄養情報レポート</title>
    <style>
        body {{ font-family: 'Hiragino Sans', 'Yu Gothic', sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .meal-title {{ font-size: 1.2em; color: #e74c3c; font-weight: bold; text-align: center; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border: 1px solid #ddd; }}
        th {{ background-color: #3498db; color: white; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #e8f4fd; }}
        .food-name {{ font-weight: bold; color: #2c3e50; }}
        .quantity {{ color: #e67e22; font-weight: bold; }}
        .confidence {{ color: #27ae60; }}
        .nutrient-value {{ text-align: right; font-weight: bold; }}
        .total-row {{ background-color: #ecf0f1 !important; font-weight: bold; }}
        .total-table th {{ background-color: #e74c3c; }}
        .status-error {{ color: #e74c3c; font-style: italic; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>栄養情報レポート</h1>
        <div class="meal-title">料理名: {nutrition_data['meal_name']}</div>
        
        <h2>各食材の栄養情報</h2>
        <table>
            <thead>
                <tr>
                    <th>食材名</th>
                    <th>推定量</th>
                    <th>信頼度</th>
                    <th>エネルギー</th>
                    <th>タンパク質</th>
                    <th>脂質</th>
                    <th>炭水化物</th>
                    <th>食物繊維</th>
                    <th>ナトリウム</th>
                    <th>ステータス</th>
                </tr>
            </thead>
            <tbody>""")
    
    for item in nutrition_data["items"]:
        html.append("                <tr>")
        html.append(f'                    <td class="food-name">{item["name_jp"]}</td>')
        html.append(f'                    <td class="quantity">{item["quantity"]["value"]}{item["quantity"]["unit"]}</td>')
        html.append(f'                    <td class="confidence">{item["confidence"]}</td>')
        
        if item["fdc_id"] and "actual_nutrients" in item:
            nutrients = item["actual_nutrients"]
            energy = nutrients.get("エネルギー", {"value": "-", "unit": ""})
            protein = nutrients.get("タンパク質", {"value": "-", "unit": ""})
            fat = nutrients.get("脂質", {"value": "-", "unit": ""})
            carbs = nutrients.get("炭水化物", {"value": "-", "unit": ""})
            fiber = nutrients.get("食物繊維", {"value": "-", "unit": ""})
            sodium = nutrients.get("ナトリウム", {"value": "-", "unit": ""})
            
            html.append(f'                    <td class="nutrient-value">{energy["value"]}{energy["unit"]}</td>')
            html.append(f'                    <td class="nutrient-value">{protein["value"]}{protein["unit"]}</td>')
            html.append(f'                    <td class="nutrient-value">{fat["value"]}{fat["unit"]}</td>')
            html.append(f'                    <td class="nutrient-value">{carbs["value"]}{carbs["unit"]}</td>')
            html.append(f'                    <td class="nutrient-value">{fiber["value"]}{fiber["unit"]}</td>')
            html.append(f'                    <td class="nutrient-value">{sodium["value"]}{sodium["unit"]}</td>')
            html.append('                    <td>✓ 取得済み</td>')
        else:
            html.append('                    <td>-</td>' * 6)
            html.append(f'                    <td class="status-error">{item.get("fdc_description", "情報なし")}</td>')
        
        html.append("                </tr>")
    
    html.append("""
            </tbody>
        </table>
""")
    
    if "total_nutrition" in nutrition_data:
        total = nutrition_data["total_nutrition"]
        html.append("""
        <h2>料理全体の栄養合計</h2>
        <table class="total-table">
            <thead>
                <tr>
                    <th>栄養素</th>
                    <th>合計値</th>
                    <th>単位</th>
                </tr>
            </thead>
            <tbody>
""")
        
        for jp_name, nutrient_data in total.items():
            html.append("                <tr class=\"total-row\">")
            html.append(f'                    <td>{jp_name}</td>')
            html.append(f'                    <td class="nutrient-value">{nutrient_data["value"]}</td>')
            html.append(f'                    <td>{nutrient_data["unit"]}</td>')
            html.append("                </tr>")
        
        html.append("""
            </tbody>
        </table>
""")
    
    html.append("""
    </div>
</body>
</html>
""")
    
    return "\n".join(html)

def format_nutrition_report(nutrition_data: dict) -> str:
    """Format nutrition data into a user-friendly report (text version for console)"""
    report = []
    report.append("=" * 70)
    report.append("栄養情報レポート")
    report.append("=" * 70)
    report.append(f"料理名: {nutrition_data['meal_name']}")
    report.append("")
    
    report.append("【各食材の栄養情報】")
    for i, item in enumerate(nutrition_data["items"], 1):
        report.append(f"{i}. {item['name_jp']}")
        report.append(f"   推定量: {item['quantity']['value']}{item['quantity']['unit']}")
        report.append(f"   信頼度: {item['confidence']}")
        
        if item["fdc_id"] and "actual_nutrients" in item:
            report.append("   実際の栄養素:")
            for jp_name, nutrient_data in item["actual_nutrients"].items():
                report.append(f"     - {jp_name}: {nutrient_data['value']}{nutrient_data['unit']}")
        else:
            report.append(f"   ステータス: {item.get('fdc_description', '情報なし')}")
        
        report.append("")
    
    if "total_nutrition" in nutrition_data:
        report.append("【料理全体の栄養合計】")
        report.append("-" * 40)
        for jp_name, nutrient_data in nutrition_data["total_nutrition"].items():
            report.append(f"{jp_name}: {nutrient_data['value']}{nutrient_data['unit']}")
        report.append("")
    
    return "\n".join(report)

def main():
    os.environ["FDC_API_KEY"] = "zORxyDT2r0DjFHGHYoNNYjBM41gS2y93mou1E7cL"
    
    print("Testing food_lookup.py integration with vision_infer.py...")
    print("Using the shrimp and broccoli stir-fry image example")
    
    vision_result = {
        "meal_name": "エビとブロッコリーの炒め物",
        "items": [
            {
                "name": "エビ",
                "quantity": {"value": 150, "unit": "g"},
                "confidence": 0.9
            },
            {
                "name": "ブロッコリー", 
                "quantity": {"value": 100, "unit": "g"},
                "confidence": 0.85
            },
            {
                "name": "ズッキーニ",
                "quantity": {"value": 50, "unit": "g"},
                "confidence": 0.7
            },
            {
                "name": "調味料",
                "quantity": {"value": 10, "unit": "g"},
                "confidence": 0.6
            }
        ]
    }
    
    try:
        print("\n=== Getting nutrition information from FDC API ===")
        nutrition_data = get_nutrition_info(vision_result)
        
        print("\n=== Calculating actual nutrition values ===")
        nutrition_data = calculate_actual_nutrition(nutrition_data)
        
        print("\n=== 栄養情報レポート (テキスト版) ===")
        report = format_nutrition_report(nutrition_data)
        print(report)
        
        print("\n=== HTMLレポート生成 ===")
        html_report = format_nutrition_report_html(nutrition_data)
        with open("nutrition_report.html", "w", encoding="utf-8") as f:
            f.write(html_report)
        print("HTMLレポートを nutrition_report.html に保存しました")
        
        print("\n=== Raw JSON Data (with calculations) ===")
        print(json.dumps(nutrition_data, indent=2, ensure_ascii=False))
        
        print("\n=== SUCCESS ===")
        print("food_lookup.py integration test with nutrition calculations completed successfully!")
        
    except Exception as e:
        print(f"\n=== FAILURE ===")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
