import re

# A static dictionary matching the RESTRICTION_OPTIONS in app.py
DIETARY_KEYWORDS = {
    "Vegan": ["vegan", "100% plant-based", "strictly plant-based"],
    "Vegetarian": ["vegetarian", "veg", "plant-based", "meatless"],
    "Halal": ["halal", "zabihah"],
    "Pescatarian": ["pescatarian", "seafood", "fish", "sushi", "poke"]
}

def get_dietary_restrictions_for_restaurant(display_name: str, types: list) -> list:
    """
    Classify a restaurant into one or more dietary restriction categories based on its name and Google Places types.
    
    Args:
        display_name (str): The display name of the restaurant.
        types (list): A list of strings representing the restaurant's types.
        
    Returns:
        list: A list of matched dietary categories. If none matched, returns an empty list.
    """
    if not display_name:
        display_name = ""
    if not types:
        types = []
        
    # Standardize input for keyword matching
    text_to_search = (display_name + " " + " ".join(types)).lower()
    
    # Clean non-alphabetical characters to match whole words easier (keep hyphens for things like gluten-free)
    text_to_search_clean = re.sub(r'[^a-z0-9\-\s]', ' ', text_to_search)
    words = set(text_to_search_clean.split())
    
    matched_restrictions = set()
    
    for restriction, keywords in DIETARY_KEYWORDS.items():
        for kw in keywords:
            kw_lower = kw.lower()
            # If the keyword is a multi-word phrase or has a hyphen, check if it's in the full string
            if " " in kw_lower or "-" in kw_lower:
                if kw_lower in text_to_search_clean:
                    matched_restrictions.add(restriction)
                    break
            # Otherwise, check if the exact word is in the set of words
            else:
                if kw_lower in words or any(kw_lower in t.lower() for t in types):
                    matched_restrictions.add(restriction)
                    break
                    
    return sorted(list(matched_restrictions))


# if __name__ == '__main__':
#     import json
#     with open("sd_restaurants.json", "r", encoding="utf-8") as f:
#         restaurants = json.load(f)
        
#     print(f"Found {len(restaurants)} restaurants. Beginning seed process...")
    
#     for i, r in enumerate(restaurants):
#         if i > 20:
#             break
#         name = r.get("displayName", {}).get("text", "Unknown")
#         types = r.get("types", [])        
    
#         restrictions = get_dietary_restrictions_for_restaurant(name, types)
#         print(f'name: {name}, types: {types}, restrictions: {restrictions}', end = '\n\n')