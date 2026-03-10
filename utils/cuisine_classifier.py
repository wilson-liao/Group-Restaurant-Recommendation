import re

# A static dictionary you maintain in your backend
CUISINE_KEYWORDS = {
    "Mexican": ["mexican", "taco", "burrito", "al pastor", "salsa", "taqueria", "cantina", "mariscos", "tex mex", "southwestern us", "latin american"],
    "Italian": ["italian", "pasta", "pizza", "napoletana", "trattoria", "pizzeria"],
    "Japanese": ["japanese", "sushi", "ramen", "izakaya", "udon", "teppanyaki", "katsu", "teriyaki", "yakitori", "japanese curry"],
    "Thai": ["thai", "pad thai", "thai curry"],
    "American": ["american", "burger", "hamburger", "steak", "steakhouse", "barbecue", "bbq", "hot dog", "chicken wings", "soul food", "cajun"],
    "Taiwanese": ["taiwanese", "boba"],
    "Chinese": ["chinese", "dim sum", "dumpling", "sichuan", "cantonese", "hot pot", "chinese noodle", "asian fusion"],
    "Korean": ["korean", "kbbq", "bulgogi", "kimchi", "bibimbap", "korean barbecue"],
    "Vietnamese": ["vietnamese", "pho", "banh mi"],
    "Asian": ["asian", "pan-asian", "burmese", "filipino"],
    "Mediterranean": ["mediterranean", "greek", "falafel", "gyro", "kebab", "shawarma", "lebanese", "turkish", "middle eastern", "persian", "afghani"],
    "Indian": ["indian", "indian curry", "tikka", "masala", "north indian", "south indian", "pakistani", "tibetan"],
    "French": ["french", "crepe", "brasserie"],
    "Seafood": ["seafood", "fish", "oyster", "crab", "poke", "shrimp", "lobster", "fish and chips", "salmon"],
    "European": ["spanish", "tapas", "british", "irish", "german", "danish", "scandinavian", "hungarian"],
    "Other / Global": ["cuban", "caribbean", "colombian", "south american", "argentinian", "peruvian", "brazilian", "african", "ethiopian", "australian"],
    "Cafe / Bakery": ["cafe", "bakery", "coffee", "dessert", "pastry", "donut", "ice cream", "gelato"],
    "Bar / Pub / Brewery": ["bar", "pub", "brewery", "cocktail", "tavern", "wine", "distillery"],
    "Hawaiian": ["hawaiian", "poke", "luau"],
    "Fast Food / Casual": ["fast food"]
}

def get_cuisines_for_restaurant(display_name: str, types: list) -> list:
    """
    Classify a restaurant into one or more cuisines based on its name and Google Places types.
    
    Args:
        display_name (str): The display name of the restaurant.
        types (list): A list of strings representing the restaurant's types.
        
    Returns:
        list: A list of matched cuisine categories.
    """
    if not display_name:
        display_name = ""
    if not types:
        types = []
        
    # Standardize input for keyword matching
    text_to_search = (display_name + " " + " ".join(types)).lower()
    
    # Clean non-alphabetical characters to match whole words easier
    text_to_search_clean = re.sub(r'[^a-z0-9\s]', ' ', text_to_search)
    words = set(text_to_search_clean.split())
    
    matched_cuisines = set()
    
    for cuisine, keywords in CUISINE_KEYWORDS.items():
        for kw in keywords:
            kw_lower = kw.lower()
            # If the keyword is a multi-word phrase, check if it's in the full string
            if " " in kw_lower:
                if kw_lower in text_to_search:
                    matched_cuisines.add(cuisine)
                    break
            # Otherwise, check if the exact word is in the set of words
            else:
                # also allow fuzzy matched substrings just in case (e.g. 'mexican_restaurant' type)
                if kw_lower in words or any(kw_lower in t.lower() for t in types):
                    matched_cuisines.add(cuisine)
                    break
                    
    # Ensure distinct matches
    if not matched_cuisines:
        matched_cuisines.add("Others")
        
    return sorted(list(matched_cuisines))

if __name__ == '__main__':
    import json
    with open("sd_restaurants.json", "r", encoding="utf-8") as f:
        restaurants = json.load(f)
        
    print(f"Found {len(restaurants)} restaurants. Beginning seed process...")

    types = [
      "taiwanese_restaurant",
      "dumpling_restaurant",
      "chinese_restaurant",
      "restaurant",
      "food",
      "point_of_interest",
      "establishment"
    ]
    name = 'Din Tai Fung'
    cuisines = get_cuisines_for_restaurant(name, types)
    print(f'name: {name}, types: {types}, cuisines: {cuisines}', end = '\n\n')

    # for i, r in enumerate(restaurants):
    #     if i > 20:
    #         break
    #     name = r.get("displayName", {}).get("text", "Unknown")
    #     types = r.get("types", [])        
    
    #     cuisines = get_cuisines_for_restaurant(name, types)
    #     print(f'name: {name}, types: {types}, cuisines: {cuisines}', end = '\n\n')