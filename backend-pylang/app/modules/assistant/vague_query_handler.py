"""
Vague Query Handler for EasyMart Assistant

Identifies and interprets vague, indirect, or slang-based user queries
and translates them into actionable search parameters or clarification requests.

Categories handled:
1. Symptom & Problem Solving - "My back hurts" -> ergonomic chair
2. Spatial & Physical Constraints - "shoe box apartment" -> compact furniture
3. Subjective & Slang - "boujee stuff" -> luxury items
4. Usage & Lifestyle Context - "starting a streaming channel" -> gaming setup
5. Negation & Complexity - "desks that aren't wood" -> metal/glass desks
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.modules.observability.logging_config import get_logger
from app.modules.assistant.category_intelligence import get_category_intelligence

logger = get_logger(__name__)


class VagueCategory(Enum):
    """Categories of vague queries"""
    SYMPTOM_PROBLEM = "symptom_problem"
    SPATIAL_CONSTRAINT = "spatial_constraint"
    SUBJECTIVE_SLANG = "subjective_slang"
    LIFESTYLE_CONTEXT = "lifestyle_context"
    NEGATION_COMPLEXITY = "negation_complexity"
    SENTIMENT_ACTION = "sentiment_action"
    CLEAR = "clear"  # Not vague


@dataclass
class VagueQueryResult:
    """Result of vague query analysis"""
    is_vague: bool
    category: VagueCategory
    original_query: str
    interpreted_intent: str
    suggested_query: str
    suggested_filters: Dict[str, Any]
    suggested_tool: str
    tool_args: Dict[str, Any]
    clarification_needed: bool
    clarification_message: Optional[str]
    confidence: float  # 0.0 to 1.0


# ============================================================================
# PATTERN MAPPINGS
# ============================================================================

# Category 1: Symptom & Problem Solving Patterns
SYMPTOM_PATTERNS = {
    # Back pain -> ergonomic chairs (expanded patterns)
    r"\b(back\s*(is\s*)?(killing|hurting|aching|pain|sore|hurt|hurts)|lower\s*back|back\s*pain|bad\s*posture|posture\s*(issue|problem)|sitting\s*(all\s*day|too\s*(long|much)))\b": {
        "intent": "User needs ergonomic support for back pain",
        "query": "ergonomic office chair lumbar support",
        "filters": {"category": "chairs"},
        "tool": "search_products"
    },
    # Clutter/organize -> storage (expanded)
    r"\b(clutter(ed)?|messy|disorganized|no\s*space|stuff\s*everywhere|too\s*much\s*stuff|organize|need.*organiz|storage\s*solution)\b": {
        "intent": "User needs storage/organization solutions",
        "query": "storage cabinet bookshelf organizer",
        "filters": {"category": "storage"},
        "tool": "search_products"
    },
    # Spills -> water resistant
    r"\b(spill(ing|s)?|water\s*damage|stain(s|ed)?|coffee\s*(ring|stain)|waterproof)\b": {
        "intent": "User wants water/stain resistant furniture",
        "query": "water resistant desk stain proof easy clean",
        "filters": {"material": "glass"},
        "tool": "search_products"
    },
    # Glare/sunlight -> lighting control
    r"\b(sun\s*(is\s*)?(glare|glaring|bright|in\s*my\s*eyes)|screen\s*glare|too\s*bright|glare\s*on\s*(my\s*)?(screen|monitor)|light\s*in\s*(my\s*)?eyes|glaring)\b": {
        "intent": "User needs lighting control solutions",
        "query": "blackout curtains desk lamp adjustable",
        "filters": {},
        "tool": "search_products"
    },
    # Neck pain -> monitor/desk height
    r"\b(neck\s*(pain|hurts|aching|strain)|looking\s*down|screen\s*too\s*low)\b": {
        "intent": "User needs monitor stand or adjustable desk",
        "query": "monitor stand adjustable height desk riser",
        "filters": {"category": "office"},
        "tool": "search_products"
    },
    # Cold feet -> rugs/heating
    r"\b(cold\s*feet|floor(s)?\s*(is\s*)?(cold|freezing)|feet\s*(are\s*)?(cold|freezing))\b": {
        "intent": "User needs floor covering for warmth",
        "query": "area rug floor mat cozy",
        "filters": {},
        "tool": "search_products"
    },
    # Can't sleep -> bed/mattress
    r"\b(can'?t\s*sleep|insomnia|tossing\s*(and\s*)?turning|bad\s*sleep|sleep\s*(issues?|problems?)|nap\s*(a\s*lot|often|lover))\b": {
        "intent": "User needs better bed or mattress",
        "query": "comfortable mattress bed frame quality",
        "filters": {"category": "bedroom"},
        "tool": "search_products"
    },
    # Just moved -> starter furniture
    r"\b(just\s*moved|moving\s*in|new\s*(apartment|place|home)|first\s*(apartment|place)|empty\s*(apartment|room))\b": {
        "intent": "User needs starter furniture for new place",
        "query": "essential furniture starter living room bedroom",
        "filters": {},
        "tool": "search_products"
    },
}

# Category 2: Spatial & Physical Constraints
SPATIAL_PATTERNS = {
    # Tiny space
    r"\b(shoe\s*box|tiny|cramped|small\s*(space|apartment|room|studio)|micro\s*(apartment|studio)|no\s*room)\b": {
        "intent": "User has very limited space, needs compact furniture",
        "query": "space saving compact folding furniture",
        "filters": {"size": "compact"},
        "tool": "search_products"
    },
    # Large family
    r"\b(family\s*of\s*(\d+)|(\d+)\s*people|big\s*family|large\s*family|seat\s*(\d+))\b": {
        "intent": "User needs large furniture for family",
        "query": "large dining table family seating",
        "filters": {"category": "tables"},
        "tool": "search_products",
        "extract_number": True
    },
    # Corner space
    r"\b(awkward\s*corner|corner\s*space|empty\s*corner|that\s*corner|corner\s*of\s*(the\s*)?(room|office))\b": {
        "intent": "User has corner space to fill",
        "query": "corner desk corner shelf l-shaped",
        "filters": {"descriptor": "l shape"},
        "tool": "search_products"
    },
    # Tall person
    r"\b((\d)['\"]?\s*(\d+)[\"']?|tall\s*person|i'?m\s*tall|extra\s*long|too\s*short\s*for\s*me)\b": {
        "intent": "User is tall, needs larger furniture",
        "query": "extra long king size tall",
        "filters": {"size": "large"},
        "tool": "search_products"
    },
    # Wide doorways
    r"\b(narrow\s*(door(way)?|hall(way)?|stairs)|won'?t\s*fit|too\s*wide|measure)\b": {
        "intent": "User has space constraints for delivery",
        "query": "modular easy assembly compact",
        "filters": {},
        "tool": "search_products",
        "clarification": "What are the dimensions of your doorway/space? I can help find furniture that fits."
    },
    # Outdoor space
    r"\b(balcony|patio|deck|backyard|outdoor|garden|terrace)\b": {
        "intent": "User needs outdoor furniture",
        "query": "outdoor furniture weather resistant patio",
        "filters": {"category": "outdoor"},
        "tool": "search_products"
    },
}

# Category 3: Subjective & Slang Terms
SLANG_PATTERNS = {
    # Luxury/expensive (exclude "not expensive" - handled in negation patterns)
    r"\b(boujee|bougie|fancy|luxur(y|ious)|high\s*end|premium|upscale|classy)\b": {
        "intent": "User wants luxury/premium items",
        "query": "premium luxury high quality",
        "filters": {"sort_by": "price_high", "material": "leather"},
        "tool": "search_products"
    },
    # Budget conscious (expanded to catch "no money", "I have no money")
    r"\b(broke|poor|student|budget|cheap(est)?|affordable|don'?t\s*have\s*much|limited\s*budget|tight\s*budget|(have\s*)?no\s*money|on\s*a\s*budget|not\s*(too\s*)?expensive)\b": {
        "intent": "User has strict budget constraints",
        "query": "affordable budget value",
        "filters": {"sort_by": "price_low", "price_max": 200},
        "tool": "search_products"
    },
    # Industrial style
    r"\b(industrial|loft|warehouse|factory|raw|exposed)\b": {
        "intent": "User wants industrial style",
        "query": "industrial style metal wood rustic",
        "filters": {"style": "industrial", "material": "metal"},
        "tool": "search_products"
    },
    # Minimalist/Modern
    r"\b(apple\s*store|minimalist|minimal|clean\s*lines?|sleek|modern|scandinavian|simple)\b": {
        "intent": "User wants minimalist/modern style",
        "query": "minimalist modern sleek simple design",
        "filters": {"style": "modern", "color": "white"},
        "tool": "search_products"
    },
    # Cozy/Warm
    r"\b(cozy|cosy|warm|hygge|comfortable|snug|homey|welcoming)\b": {
        "intent": "User wants cozy/comfortable furniture",
        "query": "cozy comfortable soft plush",
        "filters": {"material": "fabric"},
        "tool": "search_products"
    },
    # Rustic/Farmhouse
    r"\b(rustic|farmhouse|country|cottage|barn|reclaimed|vintage)\b": {
        "intent": "User wants rustic/farmhouse style",
        "query": "rustic farmhouse wood natural country",
        "filters": {"style": "rustic", "material": "wood"},
        "tool": "search_products"
    },
    # Mid-century
    r"\b(mid\s*century|retro|60s|70s|vintage\s*modern|atomic)\b": {
        "intent": "User wants mid-century modern style",
        "query": "mid century modern retro vintage",
        "filters": {"style": "mid-century"},
        "tool": "search_products"
    },
    # Dark/Moody
    r"\b(dark|moody|gothic|dramatic|noir|black\s*everything)\b": {
        "intent": "User wants dark aesthetic",
        "query": "dark black matte",
        "filters": {"color": "black"},
        "tool": "search_products"
    },
}

# Category 4: Lifestyle & Usage Context
LIFESTYLE_PATTERNS = {
    # Gaming/Streaming
    r"\b(stream(ing|er)?|twitch|youtube(r)?|gam(ing|er)|esports|rgb|setup)\b": {
        "intent": "User is a gamer/streamer, needs gaming setup",
        "query": "gaming desk gaming chair RGB",
        "filters": {"category": "office", "style": "gaming"},
        "tool": "search_products"
    },
    # Pet owners (expanded to catch "I have a dog/cat" and variations)
    r"\b((i\s*have\s*(a\s*)?(cat|dog|pet|puppy|kitten))|(cat|dog|pet|puppy)\s*(scratch(es|ing)?|chew(s|ing)?|fur|hair|mess|friendly|proof|resistant)|pet\s*proof|pet\s*friendly)\b": {
        "intent": "User has pets, needs pet-friendly furniture",
        "query": "pet friendly scratch resistant easy clean durable",
        "filters": {"material": "leather"},
        "tool": "search_products"
    },
    # Standing work
    r"\b(stand(ing)?\s*(up|desk)?|sit\s*stand|not\s*sitting|on\s*my\s*feet)\b": {
        "intent": "User works standing, needs standing desk",
        "query": "adjustable standing desk sit stand height adjustable",
        "filters": {"category": "desks"},
        "tool": "search_products"
    },
    # Man cave / Entertainment
    r"\b(man\s*cave|game\s*room|theater|cinema|entertainment|movie\s*night)\b": {
        "intent": "User wants entertainment room furniture",
        "query": "recliner leather tv stand entertainment",
        "filters": {"room_type": "living", "color": "black"},
        "tool": "search_products"
    },
    # Work from home (expanded)
    r"\b(work(ing)?\s*from\s*home|wfh|home\s*office|remote\s*work(er)?|zoom\s*calls?|remote\s*employee|hybrid\s*work)\b": {
        "intent": "User works from home, needs office setup",
        "query": "home office desk ergonomic chair professional",
        "filters": {"room_type": "office"},
        "tool": "search_products"
    },
    # Parties/Entertaining
    r"\b(party|parties|entertaining|dinner\s*party|host(ing)?|social\s*gathering)\b": {
        "intent": "User hosts parties, needs entertaining furniture",
        "query": "dining table large bar cart serving",
        "filters": {},
        "tool": "search_products"
    },
    # Kids/Children
    r"\b(kid(s|'s)?|child(ren)?|toddler|baby|nursery|playroom)\b": {
        "intent": "User needs child-friendly furniture",
        "query": "kids furniture safe rounded edges child friendly",
        "filters": {},
        "tool": "search_products"
    },
    # Fitness/Gym
    r"\b(home\s*gym|workout|exercise|fitness|training|weights)\b": {
        "intent": "User needs home gym equipment/furniture",
        "query": "gym equipment fitness training home gym",
        "filters": {"category": "fitness"},
        "tool": "search_products"
    },
    # Guest room
    r"\b(guest(s)?|spare\s*room|visitor|in-laws?|overnight)\b": {
        "intent": "User needs guest room furniture",
        "query": "guest bed sofa bed foldable mattress",
        "filters": {"category": "bedroom"},
        "tool": "search_products"
    },
}

# Category 5: Negation & Complex Queries
NEGATION_PATTERNS = {
    # Not wood
    r"\b(not|no|without|isn'?t|aren'?t|don'?t\s*want)\s*(made\s*of\s*)?(wood(en)?)\b": {
        "intent": "User wants non-wood materials",
        "query": "metal glass plastic",
        "filters": {"material": "metal"},
        "tool": "search_products",
        "exclude": ["wood"]
    },
    # No wheels
    r"\b(no|without|don'?t\s*want)\s*wheels?\b": {
        "intent": "User wants stationary furniture without wheels",
        "query": "stationary no wheels sled base fixed",
        "filters": {},
        "tool": "search_products"
    },
    # Not leather
    r"\b(not|no|without|isn'?t|aren'?t|don'?t\s*want)\s*leather\b": {
        "intent": "User wants non-leather materials",
        "query": "fabric mesh velvet",
        "filters": {"material": "fabric"},
        "tool": "search_products",
        "exclude": ["leather"]
    },
    # No plastic
    r"\b(not|no|without|don'?t\s*want)\s*plastic\b": {
        "intent": "User wants non-plastic materials",
        "query": "wood metal glass natural",
        "filters": {"material": "wood"},
        "tool": "search_products",
        "exclude": ["plastic"]
    },
    # No fabric
    r"\b(not|no|without|anything\s*but)\s*fabric\b": {
        "intent": "User wants non-fabric materials",
        "query": "leather metal wood",
        "filters": {"material": "leather"},
        "tool": "search_products",
        "exclude": ["fabric"]
    },
    # Not expensive
    r"\b(not\s*(too\s*)?expensive|reasonably\s*priced)\b": {
        "intent": "User wants moderately priced items",
        "query": "affordable mid range value",
        "filters": {"sort_by": "price_low"},
        "tool": "search_products"
    },
    # Multi-product budget
    r"\b((\w+)\s*and\s*(\w+)\s*(for\s*)?(under|below|less\s*than|within)\s*\$?(\d+))\b": {
        "intent": "User wants multiple items within total budget",
        "query": "",
        "filters": {},
        "tool": "build_bundle",
        "is_bundle": True
    },
}

# Category 6: Sentiment & Action Implied
SENTIMENT_PATTERNS = {
    # Hate/Return
    r"\b(hate|hated?|terrible|awful|worst|return|refund|money\s*back|regret)\b": {
        "intent": "User is unhappy with purchase, may want return",
        "query": "",
        "filters": {},
        "tool": "get_policy_info",
        "tool_args": {"policy_type": "returns"},
        "clarification": "I'm sorry to hear that. Would you like information about our return policy?"
    },
    # Delivery concerns
    r"\b(when\s*(will|does)|how\s*long|delivery|shipping|arrive|eta|track(ing)?)\b": {
        "intent": "User asking about delivery/shipping",
        "query": "",
        "filters": {},
        "tool": "get_policy_info",
        "tool_args": {"policy_type": "shipping"}
    },
    # Payment/Financing
    r"\b(payment\s*plan|installment|afterpay|zip\s*pay|lay\s*by|finance|pay\s*later)\b": {
        "intent": "User asking about payment options",
        "query": "",
        "filters": {},
        "tool": "get_policy_info",
        "tool_args": {"policy_type": "payment"}
    },
}


class VagueQueryHandler:
    """
    Handles vague, indirect, or slang-based user queries.
    Translates them into actionable search parameters or clarification requests.
    Uses CategoryIntelligence for grounding in actual catalog categories.
    """
    
    def __init__(self):
        self.all_patterns = {
            VagueCategory.SYMPTOM_PROBLEM: SYMPTOM_PATTERNS,
            VagueCategory.SPATIAL_CONSTRAINT: SPATIAL_PATTERNS,
            VagueCategory.SUBJECTIVE_SLANG: SLANG_PATTERNS,
            VagueCategory.LIFESTYLE_CONTEXT: LIFESTYLE_PATTERNS,
            VagueCategory.NEGATION_COMPLEXITY: NEGATION_PATTERNS,
            VagueCategory.SENTIMENT_ACTION: SENTIMENT_PATTERNS,
        }
        
        # Compile all patterns for efficiency
        self.compiled_patterns = {}
        for category, patterns in self.all_patterns.items():
            self.compiled_patterns[category] = {
                re.compile(pattern, re.IGNORECASE): config
                for pattern, config in patterns.items()
            }
        
        # Initialize category intelligence for smart category mapping
        self.category_intel = get_category_intelligence()
    
    def analyze(self, query: str) -> VagueQueryResult:
        """
        Analyze a query for vagueness and return interpretation.
        
        Args:
            query: User's input query
            
        Returns:
            VagueQueryResult with interpretation and suggested action
        """
        query_lower = query.lower().strip()
        
        # First, try CategoryIntelligence for vague phrase translation
        vague_translation = self.category_intel.translate_vague_query(query)
        if vague_translation.get("confidence") == "high" and vague_translation.get("categories"):
            # We have a high-confidence match from category intelligence
            detected_phrase = vague_translation.get("detected_phrase", "")
            categories = vague_translation.get("categories", [])
            search_terms = vague_translation.get("search_terms", [])
            
            logger.info(f"[VAGUE] CategoryIntelligence matched: '{detected_phrase}' -> categories: {categories}")
            
            return VagueQueryResult(
                is_vague=True,
                category=VagueCategory.LIFESTYLE_CONTEXT,
                original_query=query,
                interpreted_intent=f"Looking for products related to: {detected_phrase}",
                suggested_query=" ".join(search_terms) if search_terms else query,
                suggested_filters={"categories": categories},
                suggested_tool="search_products",
                tool_args={
                    "query": " ".join(search_terms) if search_terms else query,
                    "filters": {"categories": categories}
                },
                clarification_needed=False,
                clarification_message=None,
                confidence=0.85
            )
        
        # Check each category of patterns
        best_match = None
        best_category = VagueCategory.CLEAR
        best_confidence = 0.0
        matched_pattern = None
        
        for category, patterns in self.compiled_patterns.items():
            for pattern, config in patterns.items():
                match = pattern.search(query_lower)
                if match:
                    # Calculate confidence based on match coverage
                    match_length = match.end() - match.start()
                    coverage = match_length / len(query_lower)
                    confidence = min(0.5 + coverage, 0.95)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = config
                        best_category = category
                        matched_pattern = match
        
        if not best_match:
            # Check if it's a clear product query
            if self._is_clear_product_query(query_lower):
                return VagueQueryResult(
                    is_vague=False,
                    category=VagueCategory.CLEAR,
                    original_query=query,
                    interpreted_intent="Clear product search",
                    suggested_query=query,
                    suggested_filters={},
                    suggested_tool="search_products",
                    tool_args={"query": query},
                    clarification_needed=False,
                    clarification_message=None,
                    confidence=1.0
                )
            
            # Unknown vague query - ask for clarification
            return VagueQueryResult(
                is_vague=True,
                category=VagueCategory.CLEAR,
                original_query=query,
                interpreted_intent="Unable to determine intent",
                suggested_query=query,
                suggested_filters={},
                suggested_tool="none",
                tool_args={},
                clarification_needed=True,
                clarification_message=self._generate_clarification(query),
                confidence=0.3
            )
        
        # Build the result
        suggested_query = best_match.get("query", query)
        suggested_filters = best_match.get("filters", {}).copy()
        suggested_tool = best_match.get("tool", "search_products")
        tool_args = best_match.get("tool_args", {}).copy()
        clarification = best_match.get("clarification")
        
        # Extract numbers if needed (e.g., "family of 8")
        if best_match.get("extract_number") and matched_pattern:
            numbers = re.findall(r'\d+', matched_pattern.group())
            if numbers:
                num = int(numbers[0])
                if num >= 6:
                    suggested_query = f"large dining table {num} seater"
                    suggested_filters["size"] = "large"
        
        # Handle bundle requests
        if best_match.get("is_bundle"):
            suggested_tool = "build_bundle"
            items, budget = self._extract_bundle_info(query)
            if items and budget:
                tool_args = {
                    "request": query,
                    "items": items,
                    "budget_total": budget
                }
        
        # Build tool args for search
        if suggested_tool == "search_products" and not tool_args:
            tool_args = {
                "query": suggested_query,
                **suggested_filters
            }
        
        return VagueQueryResult(
            is_vague=True,
            category=best_category,
            original_query=query,
            interpreted_intent=best_match.get("intent", "Unknown intent"),
            suggested_query=suggested_query,
            suggested_filters=suggested_filters,
            suggested_tool=suggested_tool,
            tool_args=tool_args,
            clarification_needed=clarification is not None,
            clarification_message=clarification,
            confidence=best_confidence
        )
    
    def _is_clear_product_query(self, query: str) -> bool:
        """Check if query is a clear, non-vague product search."""
        clear_product_words = [
            "desk", "chair", "table", "sofa", "couch", "bed", "mattress",
            "shelf", "bookshelf", "cabinet", "drawer", "wardrobe", "dresser",
            "lamp", "rug", "curtain", "mirror", "ottoman", "bench",
            "treadmill", "dumbbell", "weight", "scooter", "bike",
            "dog bed", "cat tree", "pet", "cage", "kennel"
        ]
        
        query_words = query.lower().split()
        for word in clear_product_words:
            if word in query.lower():
                return True
        
        return False
    
    def _generate_clarification(self, query: str) -> str:
        """Generate a clarification question for unclear queries."""
        return (
            f"I'd like to help you find what you're looking for. "
            f"Could you tell me more about what type of furniture or product you need? "
            f"For example, are you looking for seating, storage, a desk, or something else?"
        )
    
    def _extract_bundle_info(self, query: str) -> Tuple[List[Dict], Optional[float]]:
        """Extract items and budget from a bundle request."""
        items = []
        budget = None
        
        # Extract budget
        budget_match = re.search(r'\$?(\d+(?:\.\d+)?)', query)
        if budget_match:
            budget = float(budget_match.group(1))
        
        # Extract items (simple extraction)
        item_words = ["desk", "chair", "table", "sofa", "bed", "shelf", "cabinet"]
        for word in item_words:
            if word in query.lower():
                items.append({"type": word, "quantity": 1})
        
        return items, budget
    
    def get_translation_prompt(self, result: VagueQueryResult) -> str:
        """
        Generate a prompt explaining the translation for the LLM.
        
        Args:
            result: VagueQueryResult from analyze()
            
        Returns:
            Explanation string for the LLM
        """
        if not result.is_vague:
            return ""
        
        category_names = {
            VagueCategory.SYMPTOM_PROBLEM: "symptom/problem description",
            VagueCategory.SPATIAL_CONSTRAINT: "spatial/physical constraint",
            VagueCategory.SUBJECTIVE_SLANG: "subjective/slang term",
            VagueCategory.LIFESTYLE_CONTEXT: "lifestyle/usage context",
            VagueCategory.NEGATION_COMPLEXITY: "negation or complex constraint",
            VagueCategory.SENTIMENT_ACTION: "sentiment implying action",
        }
        
        category_name = category_names.get(result.category, "vague query")
        
        return (
            f"VAGUE QUERY DETECTED ({category_name}):\n"
            f"- Original: \"{result.original_query}\"\n"
            f"- Interpreted as: {result.interpreted_intent}\n"
            f"- Suggested search: \"{result.suggested_query}\"\n"
            f"- Suggested filters: {result.suggested_filters}\n"
            f"- Confidence: {result.confidence:.0%}\n"
            f"- Recommended tool: {result.suggested_tool}\n"
        )


# Singleton instance
_handler: Optional[VagueQueryHandler] = None


def get_vague_query_handler() -> VagueQueryHandler:
    """Get the singleton VagueQueryHandler instance."""
    global _handler
    if _handler is None:
        _handler = VagueQueryHandler()
    return _handler


def analyze_vague_query(query: str) -> Dict[str, Any]:
    """
    Convenience function to analyze a vague query.
    
    Args:
        query: User's input query
        
    Returns:
        Dictionary with analysis results
    """
    handler = get_vague_query_handler()
    result = handler.analyze(query)
    
    return {
        "is_vague": result.is_vague,
        "category": result.category.value,
        "original_query": result.original_query,
        "interpreted_intent": result.interpreted_intent,
        "suggested_query": result.suggested_query,
        "suggested_filters": result.suggested_filters,
        "suggested_tool": result.suggested_tool,
        "tool_args": result.tool_args,
        "clarification_needed": result.clarification_needed,
        "clarification_message": result.clarification_message,
        "confidence": result.confidence,
    }
