#!/usr/bin/env python3

import base64
import os
from typing import Dict, List, Optional

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class NutritionHTMLGenerator:
    """Dynamic HTML generator for nutrition reports supporting single and multiple dishes"""
    
    def __init__(self):
        self.css_styles = """
        body { font-family: 'Hiragino Sans', 'Yu Gothic', sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        h3 { color: #e74c3c; margin-top: 25px; margin-bottom: 15px; }
        .meal-title { font-size: 1.2em; color: #e74c3c; font-weight: bold; text-align: center; margin: 20px 0; }
        .dish-title { font-size: 1.1em; color: #2c3e50; font-weight: bold; margin: 20px 0 10px 0; padding: 10px; background-color: #ecf0f1; border-left: 4px solid #3498db; }
        .original-image { text-align: center; margin: 20px 0; }
        .original-image img { max-width: 400px; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border: 1px solid #ddd; }
        th { background-color: #3498db; color: white; font-weight: bold; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        tr:hover { background-color: #e8f4fd; }
        .food-name { font-weight: bold; color: #2c3e50; }
        .quantity { color: #e67e22; font-weight: bold; }
        .confidence { color: #27ae60; }
        .nutrient-value { text-align: right; font-weight: bold; }
        .total-row { background-color: #ecf0f1 !important; font-weight: bold; }
        .total-table th { background-color: #e74c3c; }
        .status-error { color: #e74c3c; font-style: italic; }
        .dish-section { margin-bottom: 30px; }
        """
    
    def resize_image(self, image_path: str, max_width: int = 400) -> Optional[str]:
        """Resize image and convert to base64 for embedding in HTML"""
        if not PIL_AVAILABLE:
            print("Warning: PIL not available, using original image")
            return self._image_to_base64(image_path)
        
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                if width > max_width:
                    ratio = max_width / width
                    new_height = int(height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                import io
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='JPEG', quality=85)
                img_bytes.seek(0)
                
                base64_image = base64.b64encode(img_bytes.read()).decode('utf-8')
                return f"data:image/jpeg;base64,{base64_image}"
                
        except Exception as e:
            print(f"Error resizing image: {e}")
            return self._image_to_base64(image_path)
    
    def _image_to_base64(self, image_path: str) -> Optional[str]:
        """Convert image to base64 without resizing"""
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                return f"data:image/jpeg;base64,{base64_image}"
        except Exception as e:
            print(f"Error converting image to base64: {e}")
            return None
    
    def _generate_image_section(self, image_path: str) -> str:
        """Generate HTML section for original image display"""
        if not image_path or not os.path.exists(image_path):
            return ""
        
        image_data = self.resize_image(image_path)
        if not image_data:
            return ""
        
        return f"""
        <div class="original-image">
            <h3>元の写真</h3>
            <img src="{image_data}" alt="Original food image" />
        </div>
        """
    
    def _generate_dish_table(self, dish_data: Dict, dish_name: str = None) -> str:
        """Generate HTML table for a single dish"""
        html = []
        
        if dish_name:
            html.append(f'<div class="dish-title">料理: {dish_name}</div>')
        
        html.append("""
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
        
        items = dish_data.get("items", [])
        for item in items:
            html.append("                <tr>")
            html.append(f'                    <td class="food-name">{item.get("name_jp", item.get("name", "Unknown"))}</td>')
            html.append(f'                    <td class="quantity">{item["quantity"]["value"]}{item["quantity"]["unit"]}</td>')
            html.append(f'                    <td class="confidence">{item["confidence"]}</td>')
            
            if item.get("fdc_id") and "actual_nutrients" in item:
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
        </table>""")
        
        return "\n".join(html)
    
    def _generate_summary_table(self, total_nutrition: Dict) -> str:
        """Generate HTML table for nutrition summary"""
        if not total_nutrition:
            return ""
        
        html = []
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
            <tbody>""")
        
        for jp_name, nutrient_data in total_nutrition.items():
            html.append("                <tr class=\"total-row\">")
            html.append(f'                    <td>{jp_name}</td>')
            html.append(f'                    <td class="nutrient-value">{nutrient_data["value"]}</td>')
            html.append(f'                    <td>{nutrient_data["unit"]}</td>')
            html.append("                </tr>")
        
        html.append("""
            </tbody>
        </table>""")
        
        return "\n".join(html)
    
    def generate_html_report(self, nutrition_data: Dict, image_path: str = None) -> str:
        """Generate complete HTML report for nutrition data"""
        html = []
        
        html.append(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>栄養情報レポート</title>
    <style>
        {self.css_styles}
    </style>
</head>
<body>
    <div class="container">
        <h1>栄養情報レポート</h1>""")
        
        if image_path:
            html.append(self._generate_image_section(image_path))
        
        if "dishes" in nutrition_data:
            html.append('<div class="meal-title">複数料理の栄養情報</div>')
            
            for i, dish in enumerate(nutrition_data["dishes"]):
                dish_name = dish.get("dish_name", f"料理 {i+1}")
                html.append(f'<div class="dish-section">')
                html.append(self._generate_dish_table(dish, dish_name))
                html.append('</div>')
            
            if "total_nutrition" in nutrition_data:
                html.append(self._generate_summary_table(nutrition_data["total_nutrition"]))
                
        else:
            meal_name = nutrition_data.get("meal_name", "料理")
            html.append(f'<div class="meal-title">料理名: {meal_name}</div>')
            html.append('<h2>各食材の栄養情報</h2>')
            html.append(self._generate_dish_table(nutrition_data))
            
            if "total_nutrition" in nutrition_data:
                html.append(self._generate_summary_table(nutrition_data["total_nutrition"]))
        
        html.append("""
    </div>
</body>
</html>""")
        
        return "\n".join(html)
