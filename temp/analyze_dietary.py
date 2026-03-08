import json
from collections import Counter

def analyze_dietary():
    with open("sd_restaurants.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    keys_found = Counter()
    
    # Let's see what keys exist on a typical restaurant that might indicate dietary info
    for r in data:
        for k in r.keys():
            keys_found[k] += 1
            
    print("All keys found in restaurant objects:")
    for k, count in keys_found.most_common():
        print(f"  {k}: {count}")
        
    # Let's count specific boolean fields if they exist
    dietary_fields = Counter()
    for r in data:
        for field in ["servesVegetarianFood", "servesVeganFood", "servesGlutenFreeFood", "servesHalalFood"]:
            if r.get(field):
                dietary_fields[field] += 1
                
    print("\nSpecific boolean fields found:")
    for k, count in dietary_fields.items():
        print(f"  {k}: {count}")

analyze_dietary()
