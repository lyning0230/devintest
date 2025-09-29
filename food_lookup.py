# food_lookup.py（FDC）
import requests, os
FDC_API = "https://api.nal.usda.gov/fdc/v1"
KEY = os.environ["FDC_API_KEY"]

def search_food(q: str):
    r = requests.get(f"{FDC_API}/foods/search",
        params={"api_key": KEY, "query": q, "pageSize": 5})
    return r.json()["foods"]

def get_food(fdc_id: int):
    r = requests.get(f"{FDC_API}/food/{fdc_id}", params={"api_key": KEY})
    return r.json()