import json
from collections import Counter

def analyze():
    with open("sd_restaurants.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    types_counter = Counter()
    primary_types_counter = Counter()
    name_words_counter = Counter()
    
    for r in data:
        for t in r.get("types", []):
            types_counter[t] += 1
        
        pt = r.get("primaryType")
        if pt:
            primary_types_counter[pt] += 1
            
        name = r.get("displayName", {}).get("text", "")
        for word in name.lower().split():
            name_words_counter[word] += 1
            
    print("Top Types:")
    for t, c in types_counter.most_common(30):
        print(f"  {t}: {c}")
        
    print("\nTop Primary Types:")
    for t, c in primary_types_counter.most_common(30):
        print(f"  {t}: {c}")
        
analyze()
