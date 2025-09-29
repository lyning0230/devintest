#!/usr/bin/env python3

import os
import base64
import json
from vision_infer import analyze_image

def encode_image_to_data_url(image_path):
    """Convert local image file to data URL format for OpenAI API"""
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_image}"

def main():
    print("Testing multifood.jpg with vision analysis...")
    
    multifood_path = "img/multifood.jpg"
    if not os.path.exists(multifood_path):
        print(f"Error: {multifood_path} not found")
        return
    
    try:
        image_data_url = encode_image_to_data_url(multifood_path)
        result = analyze_image(image_data_url)
        
        print("\n=== MULTIFOOD VISION ANALYSIS RESULT ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print("\n=== ANALYSIS OF RESULT STRUCTURE ===")
        if isinstance(result, dict):
            if "items" in result:
                print(f"Number of items detected: {len(result['items'])}")
                for i, item in enumerate(result['items']):
                    print(f"Item {i+1}: {item.get('name', 'Unknown')}")
            if "meal_name" in result:
                print(f"Meal name: {result['meal_name']}")
        
    except Exception as e:
        print(f"\n=== FAILURE ===")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
