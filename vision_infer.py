# vision_infer.py
import json
import base64
from openai import OpenAI
client = OpenAI()

PROMPT = """あなたは栄養推定用アシスタントです。
画像に写る料理について、JSONで出力してください。
fields: items[{name, quantity: {value, unit}, confidence}], meal_name
- quantityは推定で可。単位は g/ml/個/切/大さじ/小さじ 等を優先。
"""

def analyze_image(image_url: str) -> dict:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",  # Vision対応の軽量モデル例
        messages=[
            {"role":"system","content":"Return JSON strictly."},
            {"role":"user","content":[
                {"type":"text","text":PROMPT},
                {"type":"image_url","image_url":{"url": image_url}}
            ]}
        ],
        temperature=0
    )
    # レスポンスからJSON文字列を抽出→dict化（バリデーションはpydanticで）
    import json
    content = resp.choices[0].message.content
    
    if content.startswith("```json"):
        content = content[7:]  # Remove ```json
    if content.startswith("```"):
        content = content[3:]   # Remove ```
    if content.endswith("```"):
        content = content[:-3]  # Remove trailing ```
    
    content = content.strip()
    if not content:
        raise ValueError("Empty response from OpenAI API")
    
    return json.loads(content)
