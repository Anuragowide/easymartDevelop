"""
Smart Follow-up Question Generator
Generates contextual follow-up chips based on conversation context and product categories.
"""

from typing import Dict, List, Optional
import re


class FollowupGenerator:
    """Generate contextual follow-up suggestions as chips based on category context"""
    
    # Category-specific followups - ALL must be complete, actionable search queries
    CATEGORY_FOLLOWUPS = {
        # ============ SPORTS & FITNESS ============
        "treadmill": {
            "attributes": ["Show me folding treadmills", "Show me commercial treadmills", "Treadmills under $1000"],
            "related": ["Show me exercise bikes", "Show me rowing machines"],
        },
        "exercise bike": {
            "attributes": ["Show me spin bikes", "Show me recumbent bikes", "Exercise bikes under $500"],
            "related": ["Show me treadmills", "Show me rowing machines"],
        },
        "rowing": {
            "attributes": ["Show me magnetic rowers", "Show me water rowers", "Rowing machines under $800"],
            "related": ["Show me treadmills", "Show me exercise bikes"],
        },
        "dumbbell": {
            "attributes": ["Show me adjustable dumbbells", "Show me rubber dumbbells", "Show me dumbbell sets"],
            "related": ["Show me kettlebells", "Show me weight benches"],
        },
        "kettlebell": {
            "attributes": ["Show me cast iron kettlebells", "Show me vinyl kettlebells", "Show me kettlebell sets"],
            "related": ["Show me dumbbells", "Show me weight plates"],
        },
        "barbell": {
            "attributes": ["Show me Olympic barbells", "Show me EZ curl bars", "Show me barbell sets"],
            "related": ["Show me weight plates", "Show me squat racks"],
        },
        "weight plates": {
            "attributes": ["Show me Olympic weight plates", "Show me bumper plates", "Show me rubber plates"],
            "related": ["Show me barbells", "Show me weight racks"],
        },
        "gym bench": {
            "attributes": ["Show me adjustable benches", "Show me flat benches", "Show me incline benches"],
            "related": ["Show me dumbbells", "Show me barbells"],
        },
        "trampoline": {
            "attributes": ["Show me mini trampolines", "Show me large trampolines", "Trampolines with enclosure"],
            "related": ["Show me air tracks", "Show me gymnastics mats"],
        },
        "air track": {
            "attributes": ["Show me 4m air tracks", "Show me 6m air tracks", "Show me tumbling mats"],
            "related": ["Show me trampolines", "Show me gymnastics equipment"],
        },
        
        # Boxing & MMA
        "boxing": {
            "attributes": ["Show me boxing gloves", "Show me punching bags", "Show me focus pads"],
            "related": ["Show me MMA gear", "Show me protective equipment"],
        },
        "boxing gloves": {
            "attributes": ["Show me training gloves", "Show me sparring gloves", "Boxing gloves under $100"],
            "related": ["Show me focus pads", "Show me hand wraps"],
        },
        "boxing bag": {
            "attributes": ["Show me heavy bags", "Show me free standing bags", "Show me speed bags"],
            "related": ["Show me boxing gloves", "Show me bag gloves"],
        },
        "punching bag": {
            "attributes": ["Show me heavy punching bags", "Show me free standing bags", "Show me ceiling mount bags"],
            "related": ["Show me boxing gloves", "Show me bag stands"],
        },
        "mma": {
            "attributes": ["Show me MMA gloves", "Show me MMA shorts", "Show me rashguards"],
            "related": ["Show me boxing gloves", "Show me grappling gear"],
        },
        "mma gloves": {
            "attributes": ["Show me MMA sparring gloves", "Show me grappling gloves", "MMA gloves under $80"],
            "related": ["Show me MMA shorts", "Show me hand wraps"],
        },
        "focus pads": {
            "attributes": ["Show me curved focus pads", "Show me straight focus pads", "Show me focus pad pairs"],
            "related": ["Show me boxing gloves", "Show me kick shields"],
        },
        "kick shields": {
            "attributes": ["Show me Thai pads", "Show me curved kick shields", "Show me belly pads"],
            "related": ["Show me focus pads", "Show me boxing gloves"],
        },
        "martial arts": {
            "attributes": ["Show me martial arts uniforms", "Show me training weapons", "Show me martial arts belts"],
            "related": ["Show me boxing gear", "Show me protective equipment"],
        },
        
        # Yoga & Relaxation
        "yoga": {
            "attributes": ["Show me yoga mats", "Show me yoga blocks", "Show me yoga straps"],
            "related": ["Show me pilates equipment", "Show me foam rollers"],
        },
        "yoga mat": {
            "attributes": ["Show me thick yoga mats", "Show me travel yoga mats", "Show me non-slip mats"],
            "related": ["Show me yoga blocks", "Show me yoga straps"],
        },
        "massage": {
            "attributes": ["Show me massage guns", "Show me foam rollers", "Show me massage balls"],
            "related": ["Show me recovery equipment", "Show me yoga accessories"],
        },
        "foam roller": {
            "attributes": ["Show me high density rollers", "Show me vibrating rollers", "Show me textured rollers"],
            "related": ["Show me massage balls", "Show me yoga mats"],
        },
        "fitness": {
            "attributes": ["Show me resistance bands", "Show me exercise mats", "Fitness equipment under $200"],
            "related": ["Show me gym equipment", "Show me cardio machines"],
        },
        
        # Other Sports
        "rugby": {
            "attributes": ["Show me rugby balls", "Show me tackle bags", "Show me rugby training equipment"],
            "related": ["Show me sports gear", "Show me protective equipment"],
        },
        "basketball": {
            "attributes": ["Show me basketball hoops", "Show me portable hoops", "Show me basketball stands"],
            "related": ["Show me sports equipment", "Show me outdoor games"],
        },
        
        # ============ ELECTRIC SCOOTERS ============
        "scooter": {
            "attributes": ["Show me adult scooters", "Show me kids scooters", "Scooters under $500"],
            "related": ["Show me scooter accessories", "Show me helmets"],
        },
        "electric scooter": {
            "attributes": ["Show me folding scooters", "Show me long range scooters", "Electric scooters under $800"],
            "related": ["Show me scooter accessories", "Show me safety gear"],
        },
        
        # ============ OFFICE FURNITURE ============
        "chair": {
            "attributes": ["Show me ergonomic chairs", "Show me mesh chairs", "Chairs under $300"],
            "related": ["Show me office desks", "Show me monitor arms"],
        },
        "office chair": {
            "attributes": ["Show me ergonomic office chairs", "Show me mesh back chairs", "Office chairs under $400"],
            "related": ["Show me standing desks", "Show me monitor arms"],
        },
        "gaming chair": {
            "attributes": ["Show me racing style gaming chairs", "Gaming chairs with footrest", "Gaming chairs under $500"],
            "related": ["Show me gaming desks", "Show me monitor stands"],
        },
        "executive chair": {
            "attributes": ["Show me leather executive chairs", "Show me high back chairs", "Chairs with lumbar support"],
            "related": ["Show me executive desks", "Show me office storage"],
        },
        "desk": {
            "attributes": ["Show me standing desks", "Show me corner desks", "Desks under $500"],
            "related": ["Show me office chairs", "Show me monitor arms"],
        },
        "standing desk": {
            "attributes": ["Show me electric standing desks", "Show me manual crank desks", "Standing desks under $800"],
            "related": ["Show me ergonomic chairs", "Show me monitor arms"],
        },
        "computer desk": {
            "attributes": ["Show me desks with drawers", "Show me L-shaped desks", "Computer desks under $400"],
            "related": ["Show me office chairs", "Show me desk accessories"],
        },
        "filing cabinet": {
            "attributes": ["Show me 2 drawer cabinets", "Show me 3 drawer cabinets", "Show me mobile pedestals"],
            "related": ["Show me office desks", "Show me storage solutions"],
        },
        "bookcase": {
            "attributes": ["Show me tall bookcases", "Show me bookcases with doors", "Bookcases under $300"],
            "related": ["Show me office storage", "Show me shelving"],
        },
        
        # ============ HOSPITALITY FURNITURE ============
        "bar stool": {
            "attributes": ["Show me adjustable bar stools", "Show me bar stools with backrest", "Show me bar stool sets"],
            "related": ["Show me bar tables", "Show me kitchen stools"],
        },
        "cafe chair": {
            "attributes": ["Show me stackable cafe chairs", "Show me outdoor cafe chairs", "Cafe chairs under $100"],
            "related": ["Show me cafe tables", "Show me restaurant furniture"],
        },
        
        # ============ HOME FURNITURE ============
        "sofa": {
            "attributes": ["Show me 2 seater sofas", "Show me 3 seater sofas", "Show me corner sofas"],
            "related": ["Show me coffee tables", "Show me ottomans"],
        },
        "couch": {
            "attributes": ["Show me 2 seater couches", "Show me 3 seater couches", "Show me L-shaped couches"],
            "related": ["Show me coffee tables", "Show me TV units"],
        },
        "bed": {
            "attributes": ["Show me queen size beds", "Show me king size beds", "Show me beds with storage"],
            "related": ["Show me mattresses", "Show me bedside tables"],
        },
        "mattress": {
            "attributes": ["Show me memory foam mattresses", "Show me spring mattresses", "Show me queen mattresses"],
            "related": ["Show me bed frames", "Show me bed sheets"],
        },
        "bedside table": {
            "attributes": ["Show me bedside tables with drawers", "Show me modern bedside tables", "Bedside table sets"],
            "related": ["Show me beds", "Show me table lamps"],
        },
        "tv unit": {
            "attributes": ["Show me wall mounted TV units", "Show me TV units with storage", "TV units under $400"],
            "related": ["Show me coffee tables", "Show me entertainment units"],
        },
        "coffee table": {
            "attributes": ["Show me round coffee tables", "Show me coffee tables with storage", "Coffee tables under $300"],
            "related": ["Show me sofas", "Show me side tables"],
        },
        "dining table": {
            "attributes": ["Show me 4 seater dining tables", "Show me 6 seater dining tables", "Show me extendable tables"],
            "related": ["Show me dining chairs", "Show me buffets"],
        },
        "ottoman": {
            "attributes": ["Show me storage ottomans", "Show me round ottomans", "Show me velvet ottomans"],
            "related": ["Show me sofas", "Show me armchairs"],
        },
        
        # ============ PET PRODUCTS ============
        "dog": {
            "attributes": ["Show me dog beds", "Show me dog kennels", "Show me dog toys"],
            "related": ["Show me pet supplies", "Show me dog accessories"],
        },
        "dog kennel": {
            "attributes": ["Show me large dog kennels", "Show me outdoor kennels", "Show me kennels with doors"],
            "related": ["Show me dog beds", "Show me dog cages"],
        },
        "dog cage": {
            "attributes": ["Show me small dog cages", "Show me large dog cages", "Show me foldable cages"],
            "related": ["Show me dog kennels", "Show me dog beds"],
        },
        "dog bed": {
            "attributes": ["Show me large dog beds", "Show me washable dog beds", "Show me orthopedic dog beds"],
            "related": ["Show me dog kennels", "Show me dog blankets"],
        },
        "dog pram": {
            "attributes": ["Show me small dog prams", "Show me large dog prams", "Show me foldable dog prams"],
            "related": ["Show me dog carriers", "Show me pet accessories"],
        },
        "cat": {
            "attributes": ["Show me cat trees", "Show me cat beds", "Show me scratching posts"],
            "related": ["Show me cat toys", "Show me cat carriers"],
        },
        "cat tree": {
            "attributes": ["Show me tall cat trees", "Show me cat trees with hammock", "Show me multi-level cat trees"],
            "related": ["Show me scratching posts", "Show me cat beds"],
        },
        "cat litter": {
            "attributes": ["Show me covered litter boxes", "Show me self cleaning litter boxes", "Show me large litter boxes"],
            "related": ["Show me cat supplies", "Show me litter scoops"],
        },
        "bird cage": {
            "attributes": ["Show me large bird cages", "Show me bird cages with stand", "Show me parrot cages"],
            "related": ["Show me bird accessories", "Show me bird feeders"],
        },
        "aquarium": {
            "attributes": ["Show me aquarium pumps", "Show me aquarium filters", "Show me fish tank kits"],
            "related": ["Show me fish tank accessories", "Show me aquarium lights"],
        },
        "aquarium pump": {
            "attributes": ["Show me aquarium air pumps", "Show me submersible pumps", "Show me quiet pumps"],
            "related": ["Show me aquarium filters", "Show me fish tanks"],
        },
        "pet": {
            "attributes": ["Show me dog supplies", "Show me cat supplies", "Show me pet accessories"],
            "related": ["Show me pet beds", "Show me pet carriers"],
        },
    }
    
    # Intent-specific followups (when no category context) - ALL must be complete queries
    FOLLOWUPS_BY_INTENT = {
        "product_search": {
            "with_results": [
                "Tell me about option 1",
                "Is option 1 in stock?",
                "Add option 1 to cart",
            ],
            "no_results": [
                "Search for office chairs",
                "Search for gym equipment",
                "Search for pet supplies",
            ]
        },
        "product_spec_qa": [
            "Add this to my cart",
            "Is this item in stock?",
            "Show me similar products",
        ],
        "check_availability": [
            "Add this to my cart",
            "Show me similar products",
            "Show me other options",
        ],
        "cart_add": [
            "View my cart",
            "Search for more products",
            "Proceed to checkout",
        ],
        "cart_show": [
            "Clear my cart",
            "Search for more products",
            "Proceed to checkout",
        ],
        "cart_clear": [
            "Search for office chairs",
            "Search for gym equipment",
            "Search for pet supplies",
        ],
        "comparison": [
            "Add option 1 to cart",
            "Add option 2 to cart",
            "Tell me more about option 1",
        ],
        "return_policy": [
            "What is your shipping policy?",
            "How do I contact support?",
            "Search for products",
        ],
        "shipping_info": [
            "What is your return policy?",
            "How do I contact support?",
            "Search for products",
        ],
        "contact_info": [
            "What is your return policy?",
            "What is your shipping policy?",
            "Search for products",
        ],
        "greeting": [
            "Search for office chairs",
            "Search for gym equipment", 
            "Search for pet supplies",
        ],
        "general": [
            "Search for office furniture",
            "Search for gym equipment",
            "Search for pet supplies",
        ],
        "out_of_scope": [
            "Search for office chairs",
            "Search for gym equipment",
            "Search for pet supplies",
        ],
    }
    
    def _extract_category_from_query(self, query: str) -> Optional[str]:
        """Extract the main category/product type from a query"""
        if not query:
            return None
            
        query_lower = query.lower()
        
        # Check for exact category matches (in order of specificity)
        category_priority = [
            # Specific product types first
            "aquarium pump", "aquarium filter", "exercise bike", "boxing gloves", 
            "boxing bag", "punching bag", "mma gloves", "focus pads", "kick shields",
            "dog kennel", "dog cage", "dog bed", "dog pram", "cat tree", "cat litter",
            "bird cage", "yoga mat", "foam roller", "bar stool", "cafe chair",
            "standing desk", "computer desk", "gaming chair", "executive chair",
            "office chair", "electric scooter", "gym bench", "weight plates",
            "bedside table", "coffee table", "dining table", "tv unit",
            # Then broader categories
            "treadmill", "rowing", "dumbbell", "kettlebell", "barbell", "trampoline",
            "air track", "boxing", "mma", "martial arts", "yoga", "massage", "fitness",
            "rugby", "basketball", "scooter", "chair", "desk", "sofa", "couch", "bed",
            "mattress", "ottoman", "bookcase", "filing cabinet", "dog", "cat", "pet",
            "aquarium",
        ]
        
        for category in category_priority:
            if category in query_lower:
                return category
        
        return None
    
    def generate_followups(
        self,
        intent: str,
        products_count: int = 0,
        cart_count: int = 0,
        context: Dict = None
    ) -> List[str]:
        """Generate contextual follow-up suggestions based on category context"""
        
        followups = []
        category = None
        
        # Extract category from context (query)
        if context and context.get("query"):
            category = self._extract_category_from_query(context.get("query", ""))
        
        # If we have a category match, use category-specific followups
        if category and category in self.CATEGORY_FOLLOWUPS:
            cat_data = self.CATEGORY_FOLLOWUPS[category]
            
            if intent == "product_search" and products_count > 0:
                # Show attribute refinements + one related category
                followups = list(cat_data.get("attributes", []))[:2]
                if cat_data.get("related"):
                    # Related items are already complete queries like "Show me exercise bikes"
                    followups.append(cat_data["related"][0])
            elif intent == "product_search" and products_count == 0:
                # No results - suggest related categories (already complete queries)
                related = cat_data.get("related", [])
                followups = list(related[:2])
                followups.append("Search for something else")
            elif intent == "product_spec_qa":
                # Viewing product details - add to cart, similar, or refine
                followups = [
                    "Add this to my cart",
                    "Show me similar products",
                    cat_data.get("attributes", ["Show me more options"])[0],
                ]
            else:
                # Default: show category attributes
                followups = list(cat_data.get("attributes", []))[:3]
        else:
            # No category context - use intent-based followups
            intent_followups = self.FOLLOWUPS_BY_INTENT.get(intent, self.FOLLOWUPS_BY_INTENT["general"])
            
            if intent == "product_search":
                if products_count > 0:
                    followups = list(intent_followups.get("with_results", []))[:3]
                else:
                    followups = list(intent_followups.get("no_results", []))[:3]
            elif isinstance(intent_followups, list):
                followups = list(intent_followups)[:3]
            else:
                followups = list(intent_followups.get("with_results", self.FOLLOWUPS_BY_INTENT["general"]))[:3]
        
        # Add cart indicator if items in cart (but not on cart-related intents)
        if cart_count > 0 and intent not in ["cart_add", "cart_show", "cart_clear"]:
            # Replace last followup with cart view
            if len(followups) >= 3:
                followups[2] = f"View cart ({cart_count})"
            else:
                followups.append(f"View cart ({cart_count})")
        
        # Ensure we have at least 3 followups
        defaults = ["Search for office chairs", "Search for gym equipment", "Search for pet supplies"]
        seen = {f.lower() for f in followups}
        while len(followups) < 3:
            for d in defaults:
                if d.lower() not in seen:
                    followups.append(d)
                    seen.add(d.lower())
                    break
            else:
                break
        
        return followups[:3]
    
    def get_welcome_followups(self, is_returning: bool = False, cart_count: int = 0) -> List[str]:
        """Get follow-ups for welcome message"""
        
        if is_returning and cart_count > 0:
            return [
                f"View cart ({cart_count})",
                "Search for office chairs",
                "Search for gym equipment",
            ]
        else:
            return [
                "Search for office furniture",
                "Search for gym equipment",
                "Search for pet supplies",
            ]
    
    def get_error_followups(self, error_type: str) -> List[str]:
        """Get follow-ups after an error"""
        
        error_followups = {
            "search_empty": [
                "Try a different search",
                "Search for office chairs",
                "Browse all categories",
            ],
            "product_not_found": [
                "Search for similar products",
                "Browse office furniture",
                "Browse gym equipment",
            ],
            "cart_error": [
                "View my cart",
                "Contact support",
                "Continue shopping",
            ],
            "default": [
                "Search for office chairs",
                "Search for gym equipment",
                "Search for pet supplies",
            ],
        }
        
        return error_followups.get(error_type, error_followups["default"])
    
    def get_category_followups(self, category: str) -> List[str]:
        """Get followups for a specific category directly"""
        
        if category in self.CATEGORY_FOLLOWUPS:
            cat_data = self.CATEGORY_FOLLOWUPS[category]
            return cat_data.get("attributes", [])[:3]
        
        return self.FOLLOWUPS_BY_INTENT["general"]


# Global followup generator instance
followup_generator = FollowupGenerator()


def get_followup_generator() -> FollowupGenerator:
    """Get the global followup generator instance"""
    return followup_generator
