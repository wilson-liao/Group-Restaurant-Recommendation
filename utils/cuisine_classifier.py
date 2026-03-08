import re

# A static dictionary you maintain in your backend
CUISINE_KEYWORDS = {
    "Mexican": ["mexican", "taco", "burrito", "al pastor", "salsa", "taqueria", "cantina", "mariscos"],
    "Italian": ["italian", "pasta", "pizza", "napoletana", "trattoria", "pizzeria"],
    "Japanese": ["japanese", "sushi", "ramen", "izakaya", "udon", "teppanyaki", "katsu", "teriyaki"],
    "Thai": ["thai", "pad thai", "curry"],
    "American": ["american", "burger", "hamburger", "steak", "steakhouse", "barbecue", "bbq", "diner", "grill"],
    "Chinese": ["chinese", "dim sum", "dumpling", "noodle", "sichuan", "cantonese"],
    "Korean": ["korean", "kbbq", "bulgogi", "kimchi", "tofu", "bibimbap"],
    "Vietnamese": ["vietnamese", "pho", "banh mi"],
    "Asian": ["asian", "pan-asian"],  # Generic fallback for asian
    "Mediterranean": ["mediterranean", "greek", "falafel", "gyro", "kebab", "shawarma", "lebanese"],
    "Indian": ["indian", "curry", "tikka", "masala"],
    "French": ["french", "crepe", "bistro", "brasserie"],
    "Seafood": ["seafood", "fish", "oyster", "crab", "poke", "shrimp", "lobster"],
    "Vegetarian / Vegan": ["vegetarian", "vegan", "plant based"],
    "Cafe / Bakery": ["cafe", "bakery", "coffee", "dessert", "pastry", "donut", "ice cream", "gelato"],
    "Breakfast / Brunch": ["breakfast", "brunch", "pancake", "waffle"],
    "Bar / Pub / Brewery": ["bar", "pub", "brewery", "cocktail", "tavern", "wine", "distillery"],
    "Hawaiian": ["hawaiian", "poke", "luau"]
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
