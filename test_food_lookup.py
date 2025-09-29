#!/usr/bin/env python3

import os
import json
import base64
from vision_infer import analyze_image
from food_lookup import search_food, get_food
from nutrition_html_generator import NutritionHTMLGenerator

FOOD_TRANSLATIONS = {
    "エビ": "shrimp",
    "ブロッコリー": "broccoli", 
    "ズッキーニ": "zucchini",
    "調味料": "seasoning",
    "エビとブロッコリーの炒め物": "shrimp and broccoli stir fry",
    "卵": "egg",
    "キャベツ": "cabbage",
    "ニラ": "chinese chives",
    "もやし": "bean sprouts",
    "豚肉": "pork",
    "スープ": "soup",
    "味噌汁": "miso soup",
    "野菜炒め": "stir fried vegetables",
    "卵焼き": "tamagoyaki",
    "オムレツ": "omelet"
}

def translate_food_name(japanese_name: str) -> str:
    """Translate Japanese food name to English for FDC API"""
    return FOOD_TRANSLATIONS.get(japanese_name, japanese_name.lower())

def get_nutrition_info_for_items(items: list) -> list:
    """Get nutrition information for a list of food items"""
    nutrition_items = []
    
    for item in items:
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
                
                nutrition_item = {
                    "name_jp": japanese_name,
                    "name_en": english_name,
                    "quantity": item["quantity"],
                    "confidence": item["confidence"],
                    "fdc_id": fdc_id,
                    "fdc_description": food_details.get("description", ""),
                    "nutrients": nutrients
                }
            else:
                nutrition_item = {
                    "name_jp": japanese_name,
                    "name_en": english_name,
                    "quantity": item["quantity"],
                    "confidence": item["confidence"],
                    "fdc_id": None,
                    "fdc_description": "FDCで見つかりませんでした",
                    "nutrients": {}
                }
                
        except Exception as e:
            print(f"Error getting nutrition for {japanese_name}: {e}")
            nutrition_item = {
                "name_jp": japanese_name,
                "name_en": english_name,
                "quantity": item["quantity"],
                "confidence": item["confidence"],
                "fdc_id": None,
                "fdc_description": f"エラー: {str(e)}",
                "nutrients": {}
            }
        
        nutrition_items.append(nutrition_item)
    
    return nutrition_items

def get_nutrition_info(vision_result: dict) -> dict:
    """Get nutrition information for foods identified by vision analysis"""
    if "dishes" in vision_result:
        nutrition_data = {
            "meal_name": vision_result["meal_name"],
            "meal_name_en": translate_food_name(vision_result["meal_name"]),
            "dishes": []
        }
        
        for dish in vision_result["dishes"]:
            dish_items = get_nutrition_info_for_items(dish["items"])
            nutrition_data["dishes"].append({
                "dish_name": dish["dish_name"],
                "items": dish_items
            })
    else:
        nutrition_items = get_nutrition_info_for_items(vision_result["items"])
        nutrition_data = {
            "meal_name": vision_result["meal_name"],
            "meal_name_en": translate_food_name(vision_result["meal_name"]),
            "items": nutrition_items
        }
    
    return nutrition_data

def calculate_actual_nutrition_for_items(items: list) -> tuple:
    """Calculate actual nutrition values for a list of items"""
    
    NUTRIENT_TRANSLATIONS = {
        "Energy": "エネルギー",
        "Protein": "タンパク質",
        "Total lipid (fat)": "脂質",
        "Carbohydrate, by difference": "炭水化物",
        "Fiber, total dietary": "食物繊維",
        "Sodium, Na": "ナトリウム",
        "Fatty acids, total saturated": "飽和脂肪酸",
        "Fatty acids, total trans": "トランス脂肪酸"
    }
    
    dish_total = {}
    
    for item in items:
        if item["fdc_id"] and item["nutrients"]:
            quantity_g = item["quantity"]["value"]  # Assuming all quantities are in grams
            
            actual_nutrients = {}
            for nutrient_name, nutrient_data in item["nutrients"].items():
                per_100g_value = nutrient_data["value"]
                actual_value = (per_100g_value * quantity_g) / 100
                
                jp_name = NUTRIENT_TRANSLATIONS.get(nutrient_name, nutrient_name)
                actual_nutrients[jp_name] = {
                    "value": round(actual_value, 2),
                    "unit": nutrient_data["unit"],
                    "original_name": nutrient_name
                }
                
                if jp_name not in dish_total:
                    dish_total[jp_name] = {
                        "value": 0,
                        "unit": nutrient_data["unit"]
                    }
                dish_total[jp_name]["value"] += actual_value
            
            item["actual_nutrients"] = actual_nutrients
    
    for nutrient in dish_total:
        dish_total[nutrient]["value"] = round(dish_total[nutrient]["value"], 2)
    
    return items, dish_total

def calculate_actual_nutrition(nutrition_data: dict) -> dict:
    """Calculate actual nutrition values based on estimated quantities"""
    
    if "dishes" in nutrition_data:
        overall_total = {}
        
        for dish in nutrition_data["dishes"]:
            items, dish_total = calculate_actual_nutrition_for_items(dish["items"])
            dish["items"] = items
            dish["dish_nutrition"] = dish_total
            
            for jp_name, nutrient_data in dish_total.items():
                if jp_name not in overall_total:
                    overall_total[jp_name] = {
                        "value": 0,
                        "unit": nutrient_data["unit"]
                    }
                overall_total[jp_name]["value"] += nutrient_data["value"]
        
        for nutrient in overall_total:
            overall_total[nutrient]["value"] = round(overall_total[nutrient]["value"], 2)
        
        nutrition_data["total_nutrition"] = overall_total
    else:
        items, total_nutrition = calculate_actual_nutrition_for_items(nutrition_data["items"])
        nutrition_data["items"] = items
        nutrition_data["total_nutrition"] = total_nutrition
    
    return nutrition_data

def encode_image_to_data_url(image_path):
    """Convert local image file to data URL format for OpenAI API"""
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_image}"

def process_vision_result(image_path: str) -> dict:
    """Process image with vision analysis and return structured result"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    image_data_url = encode_image_to_data_url(image_path)
    return analyze_image(image_data_url)

def detect_multiple_dishes(vision_result: dict) -> bool:
    """Detect if vision result contains multiple dishes"""
    meal_name = vision_result.get("meal_name", "").lower()
    items = vision_result.get("items", [])
    
    multiple_indicators = ["複数", "セット", "定食", "弁当", "盛り合わせ"]
    if any(indicator in meal_name for indicator in multiple_indicators):
        return True
    
    if len(items) > 4:
        return True
    
    return False

def group_items_by_dish(vision_result: dict) -> dict:
    """Group food items by dish for multiple dish scenarios"""
    if not detect_multiple_dishes(vision_result):
        return vision_result
    
    items = vision_result.get("items", [])
    
    main_dishes = []
    side_dishes = []
    soups = []
    
    for item in items:
        name = item.get("name", "").lower()
        if any(soup_word in name for soup_word in ["スープ", "汁", "味噌汁"]):
            soups.append(item)
        elif any(main_word in name for main_word in ["炒め", "焼き", "揚げ", "煮"]):
            main_dishes.append(item)
        else:
            side_dishes.append(item)
    
    dishes = []
    if main_dishes:
        dishes.append({
            "dish_name": "メイン料理",
            "items": main_dishes
        })
    if side_dishes:
        dishes.append({
            "dish_name": "副菜",
            "items": side_dishes
        })
    if soups:
        dishes.append({
            "dish_name": "汁物",
            "items": soups
        })
    
    if not dishes:
        return vision_result
    
    return {
        "meal_name": vision_result.get("meal_name", "複数料理"),
        "dishes": dishes,
        "original_items": items
    }

def format_nutrition_report(nutrition_data: dict) -> str:
    """Format nutrition data into a user-friendly report (text version for console)"""
    report = []
    report.append("=" * 70)
    report.append("栄養情報レポート")
    report.append("=" * 70)
    report.append(f"料理名: {nutrition_data['meal_name']}")
    report.append("")
    
    if "dishes" in nutrition_data:
        for dish_idx, dish in enumerate(nutrition_data["dishes"], 1):
            report.append(f"【{dish['dish_name']}】")
            for i, item in enumerate(dish["items"], 1):
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
    else:
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

def test_image_analysis(image_path: str, image_name: str):
    """Test complete pipeline with a specific image"""
    print(f"\n{'='*60}")
    print(f"Testing {image_name}: {image_path}")
    print('='*60)
    
    try:
        print("\n=== Step 1: Vision Analysis ===")
        vision_result = process_vision_result(image_path)
        print(f"Vision result: {json.dumps(vision_result, indent=2, ensure_ascii=False)}")
        
        print("\n=== Step 2: Dish Grouping ===")
        grouped_result = group_items_by_dish(vision_result)
        if "dishes" in grouped_result:
            print(f"Multiple dishes detected: {len(grouped_result['dishes'])} dishes")
            for i, dish in enumerate(grouped_result['dishes']):
                print(f"  Dish {i+1}: {dish['dish_name']} ({len(dish['items'])} items)")
        else:
            print("Single dish detected")
        
        print("\n=== Step 3: Getting nutrition information from FDC API ===")
        nutrition_data = get_nutrition_info(grouped_result)
        
        print("\n=== Step 4: Calculating actual nutrition values ===")
        nutrition_data = calculate_actual_nutrition(nutrition_data)
        
        print("\n=== Step 5: Generating reports ===")
        
        report = format_nutrition_report(nutrition_data)
        print("\n=== 栄養情報レポート (テキスト版) ===")
        print(report)
        
        html_generator = NutritionHTMLGenerator()
        html_report = html_generator.generate_html_report(nutrition_data, image_path)
        
        output_filename = f"nutrition_report_{image_name.replace('.jpg', '')}.html"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(html_report)
        print(f"\nHTMLレポートを {output_filename} に保存しました")
        
        print("\n=== Raw JSON Data (with calculations) ===")
        print(json.dumps(nutrition_data, indent=2, ensure_ascii=False))
        
        print(f"\n=== SUCCESS: {image_name} ===")
        return True
        
    except Exception as e:
        print(f"\n=== FAILURE: {image_name} ===")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    os.environ["FDC_API_KEY"] = "zORxyDT2r0DjFHGHYoNNYjBM41gS2y93mou1E7cL"
    
    print("Testing dynamic HTML generation with both single and multiple dish images...")
    
    test_images = [
        ("img/singlefood.jpg", "singlefood"),
        ("img/multifood.jpg", "multifood")
    ]
    
    success_count = 0
    total_tests = len(test_images)
    
    for image_path, image_name in test_images:
        if os.path.exists(image_path):
            if test_image_analysis(image_path, image_name):
                success_count += 1
        else:
            print(f"\nWarning: {image_path} not found, skipping...")
    
    print(f"\n{'='*60}")
    print(f"FINAL RESULTS: {success_count}/{total_tests} tests passed")
    print('='*60)
    
    if success_count == total_tests:
        print("All tests completed successfully!")
        print("Dynamic HTML generation with multiple dish support is working!")
    else:
        print("Some tests failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
