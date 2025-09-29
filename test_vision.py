#!/usr/bin/env python3

import os
import base64
from vision_infer import analyze_image

def encode_image_to_data_url(image_path):
    """Convert local image file to data URL format for OpenAI API"""
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_image}"

def main():
    image_path = "/home/ubuntu/repos/devintest/img/IMG_3443.jpg"
    
    if not os.path.exists(image_path):
        print(f"Error: Sample image not found at {image_path}")
        return
    
    print("Testing vision_infer.py with sample image...")
    print(f"Image path: {image_path}")
    
    try:
        image_data_url = encode_image_to_data_url(image_path)
        
        result = analyze_image(image_data_url)
        
        print("\n=== SUCCESS ===")
        print("JSON result received:")
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n=== FAILURE ===")
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
