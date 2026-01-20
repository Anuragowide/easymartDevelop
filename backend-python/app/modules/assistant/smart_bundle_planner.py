"""
Smart Bundle Planner - Advanced Interior Designer Agent

Implements Planner-Executor Pattern for vague room setup requests.
Uses 3-phase approach: Decompose → Execute → Synthesize

Example requests:
- "I want a small office in my home"
- "Help me setup a gaming corner"
- "I need furniture for a tiny studio apartment"
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from ...core.config import get_settings
from ..retrieval.product_search import ProductSearcher

logger = logging.getLogger(__name__)

# Global planner instance (singleton)
_planner_instance: Optional['SmartBundlePlanner'] = None


class BundleItemPlan(BaseModel):
    """Plan for a single item in the bundle"""
    item_type: str = Field(description="Type of item (e.g., 'desk', 'chair', 'lamp')")
    search_query: str = Field(description="Search query with injected keywords (e.g., 'compact desk small home office')")
    reasoning: str = Field(description="Why this item is needed for the room")
    target_price: float = Field(description="Approximate target price for this item")
    constraints: List[str] = Field(default_factory=list, description="Size/style constraints (e.g., 'width < 120cm', 'space-saving')")


class BundlePlan(BaseModel):
    """Complete shopping plan for the room"""
    theme: str = Field(description="Overall theme/style (e.g., 'Space-Saving Home Office', 'Cozy Gaming Corner')")
    items: List[BundleItemPlan] = Field(description="List of items to search for")
    total_budget_estimate: float = Field(description="Estimated total budget for all items")
    style_keywords: List[str] = Field(description="Style keywords for cohesion (e.g., 'modern', 'minimalist', 'black')")


class SmartBundlePlanner:
    """
    Advanced planner using LLM-based decomposition and parallel execution.
    
    Phase 1 - Decompose: LLM creates detailed shopping plan with keyword injection
    Phase 2 - Execute: Parallel product searches for each item
    Phase 3 - Synthesize: Score and select cohesive products within budget
    """
    
    def __init__(self):
        settings = get_settings()
        
        # Planner LLM - temperature 0.3 for consistent planning
        self.planner_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY
        )
        
        # Product searcher for execution phase
        self.searcher = ProductSearcher()
        
        logger.info("SmartBundlePlanner initialized with GPT-4 planner")
    
    async def plan_and_create_bundle(
        self,
        user_request: str,
        budget: Optional[float] = None,
        style_preference: Optional[str] = None,
        space_constraint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: Plan and create a bundle for vague room setup request.
        
        Args:
            user_request: Vague intent like "I want a small office"
            budget: Optional budget constraint (e.g., 500.0)
            style_preference: Optional style (e.g., "modern", "minimalist")
            space_constraint: Optional space constraint (e.g., "small room", "corner")
        
        Returns:
            {
                "success": bool,
                "message": str,  # Natural language explanation
                "bundle": {
                    "theme": str,
                    "items": [{"sku": str, "name": str, "price": float, "reasoning": str}, ...],
                    "total": float
                },
                "plan": BundlePlan  # Original plan for debugging
            }
        """
        try:
            logger.info(f"Starting smart bundle planning for: {user_request}")
            
            # Phase 1: Decompose request into plan
            plan = await self._decompose_request(
                user_request, budget, style_preference, space_constraint
            )
            logger.info(f"Phase 1 complete: Plan created with {len(plan.items)} items")
            
            # Phase 2: Execute parallel searches
            search_results = await self._execute_searches(plan)
            logger.info(f"Phase 2 complete: Searched for {len(search_results)} item types")
            
            # Phase 3: Synthesize bundle from results
            bundle = self._synthesize_bundle(plan, search_results, budget)
            logger.info(f"Phase 3 complete: Selected {len(bundle['items'])} products")
            
            # Generate natural language explanation
            message = self._generate_message(plan, bundle)
            
            return {
                "success": True,
                "message": message,
                "bundle": bundle,
                "plan": plan.model_dump()
            }
            
        except Exception as e:
            logger.error(f"Smart bundle planning failed: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"I had trouble planning your room setup: {str(e)}",
                "bundle": None,
                "plan": None
            }
    
    async def _decompose_request(
        self,
        user_request: str,
        budget: Optional[float],
        style_preference: Optional[str],
        space_constraint: Optional[str]
    ) -> BundlePlan:
        """
        Phase 1: Use LLM to decompose vague request into detailed shopping plan.
        
        Key features:
        - Injects keywords user didn't say (e.g., "small office" → "compact desk")
        - Allocates budget intelligently (50% desk, 35% chair, 15% accessories)
        - Adds constraints based on space (e.g., "width < 120cm")
        """
        
        # Build context for planner
        context_parts = [f"User request: {user_request}"]
        if budget:
            context_parts.append(f"Budget: ${budget}")
        if style_preference:
            context_parts.append(f"Style preference: {style_preference}")
        if space_constraint:
            context_parts.append(f"Space constraint: {space_constraint}")
        context = "\n".join(context_parts)
        
        # System prompt for planner
        system_prompt = """You are an expert interior designer creating detailed shopping plans.

Your task: Decompose vague room setup requests into specific product searches with smart keyword injection.

CRITICAL ROOM-SPECIFIC RULES:
1. HOME OFFICE / WORK SPACE:
   - item_type: "desk" → search_query MUST contain "desk" OR "workstation" OR "work table" (NOT just "table")
   - item_type: "chair" → search_query MUST contain "office chair" OR "task chair" OR "ergonomic chair" (NOT just "chair" or "ergonomic")
   - FORBIDDEN: coffee table, dining table, visitor chair, cantilever chair, stacking chair, reception chair
   - Example queries:
     * desk: "compact desk home office workstation"
     * chair: "ergonomic office chair adjustable"
     * lamp: "desk lamp adjustable home office"

2. GAMING SETUP:
   - item_type: "desk" → search_query MUST contain "gaming desk" OR "computer desk"
   - item_type: "chair" → search_query MUST contain "gaming chair" OR "ergonomic office chair"
   - Example queries:
     * desk: "gaming desk RGB modern"
     * chair: "gaming chair ergonomic adjustable"

3. BEDROOM:
   - item_type: "bed" → search_query MUST contain "bed" OR "bed frame"
   - item_type: "nightstand" → search_query MUST contain "nightstand" OR "bedside table"

4. LIVING ROOM / LOUNGE:
   - item_type: "sofa" → search_query MUST contain "sofa" OR "couch"
   - item_type: "coffee table" → search_query MUST contain "coffee table" (coffee table is OK here)
   
5. READING NOOK:
   - item_type: "chair" → search_query MUST contain "armchair" OR "lounge chair" OR "reading chair" (NOT office chair)
   - item_type: "lamp" → search_query MUST contain "floor lamp" OR "reading lamp"

SEARCH QUERY CONSTRUCTION RULES (CRITICAL):
1. ALWAYS include the core product type in search_query
   - For desk: MUST say "desk" or "workstation"
   - For office chair: MUST say "office chair" or "task chair"
   - For lamp: MUST say "lamp" or "light"
   - DO NOT use ambiguous terms like "table", "chair", or "ergonomic" alone

2. Add descriptive keywords AFTER the core product type
   - Good: "compact desk home office" (has "desk")
   - Bad: "compact home office" (missing "desk")
   - Good: "ergonomic office chair adjustable" (has "office chair")
   - Bad: "ergonomic adjustable" (missing "office chair")

3. For small spaces, add size keywords
   - "compact", "small", "space-saving", "narrow"

4. For style, add style keywords
   - "modern", "minimalist", "black", "white"

BUDGET ALLOCATION:
- Office: 50% desk, 35% chair, 15% accessories
- Gaming: 45% desk, 40% chair, 15% accessories
- Bedroom: 60% bed, 25% nightstand, 15% lighting
- Living: 55% sofa, 30% coffee table, 15% accessories

ESSENTIALS FIRST (2-4 items max):
- Office: desk + chair [+ lamp optional]
- Gaming: desk + chair [+ monitor stand optional]
- Bedroom: bed + nightstand [+ lamp optional]
- Reading: armchair + side table [+ floor lamp optional]

VALIDATION BEFORE RETURNING:
- Check that every search_query contains the actual product type
- For office setups, verify desk query has "desk" and chair query has "office chair"
- Reject any search_query that is too vague (e.g., "ergonomic", "compact", "table" alone)

Return a BundlePlan with theme, items (with search_query containing injected keywords), budget estimate, and style keywords."""

        # Use structured output to get reliable BundlePlan
        structured_llm = self.planner_llm.with_structured_output(BundlePlan)
        
        # Generate plan
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        plan = await structured_llm.ainvoke(messages)
        
        logger.info(f"Generated plan: {plan.theme} with {len(plan.items)} items")
        return plan
    
    async def _execute_searches(self, plan: BundlePlan) -> Dict[str, List[Dict[str, Any]]]:
        """
        Phase 2: Execute parallel product searches for each item in the plan.
        
        Returns:
            {
                "desk": [product1, product2, ...],
                "chair": [product1, product2, ...],
                ...
            }
        """
        
        async def search_item(item: BundleItemPlan) -> tuple[str, List[Dict[str, Any]]]:
            """Search for a single item"""
            try:
                # Extract constraints
                max_price = item.target_price * 1.2  # Allow 20% over target
                
                # Build filters
                filters = {
                    "max_price": max_price,
                    "in_stock": True  # Only in-stock items
                }
                
                # Search with keyword-rich query
                results = await self.searcher.search(
                    query=item.search_query,
                    filters=filters,
                    limit=5  # Top 5 results per item
                )
                
                logger.info(f"Found {len(results)} products for {item.item_type}")
                return (item.item_type, results)
                
            except Exception as e:
                logger.error(f"Search failed for {item.item_type}: {e}")
                return (item.item_type, [])
        
        # Execute all searches in parallel
        tasks = [search_item(item) for item in plan.items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert to dict
        search_results = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Search task failed: {result}")
                continue
            item_type, products = result
            search_results[item_type] = products
        
        return search_results
    
    def _synthesize_bundle(
        self,
        plan: BundlePlan,
        search_results: Dict[str, List[Dict[str, Any]]],
        budget: Optional[float]
    ) -> Dict[str, Any]:
        """
        Phase 3: Score products and select best cohesive bundle within budget.
        
        Scoring factors:
        - Price fit (0.7-1.2 of target is ideal)
        - Style keyword matching
        - Constraint satisfaction
        - Stock availability
        - Product rating
        """
        
        selected_items = []
        total_cost = 0.0
        budget = budget or plan.total_budget_estimate
        
        # Process each item type in plan order
        for item_plan in plan.items:
            products = search_results.get(item_plan.item_type, [])
            if not products:
                logger.warning(f"No products found for {item_plan.item_type}")
                continue
            
            # Score each product
            scored_products = []
            for product in products:
                score = self._score_product(product, item_plan, plan.style_keywords)
                scored_products.append((score, product))
            
            # Sort by score (highest first)
            scored_products.sort(key=lambda x: x[0], reverse=True)
            
            # Select best product that fits remaining budget
            remaining_budget = budget - total_cost
            for score, product in scored_products:
                price = product.get("price", 0)
                if price <= remaining_budget:
                    selected_items.append({
                        "sku": product.get("id", product.get("sku", "N/A")),  # Use "id" field from search
                        "name": product["name"],
                        "price": price,
                        "stock": product.get("inventory_quantity", 0),
                        "reasoning": item_plan.reasoning,
                        "score": score
                    })
                    total_cost += price
                    logger.info(f"Selected {product['name']} for {item_plan.item_type} (score: {score:.2f})")
                    break
        
        return {
            "theme": plan.theme,
            "items": selected_items,
            "total": total_cost,
            "budget": budget,
            "style_keywords": plan.style_keywords
        }
    
    def _score_product(
        self,
        product: Dict[str, Any],
        item_plan: BundleItemPlan,
        style_keywords: List[str]
    ) -> float:
        """
        Score a product based on multiple factors.
        
        Returns:
            Score between 0.0 and 10.0
        """
        score = 5.0  # Base score
        
        # Factor 1: Price fit (0.7-1.2 of target is ideal)
        price = product.get("price", 0)
        target = item_plan.target_price
        if target > 0:
            price_ratio = price / target
            if 0.7 <= price_ratio <= 1.2:
                score += 2.0  # Ideal price range
            elif price_ratio < 0.7:
                score += 1.5  # Under budget (good but may lack quality)
            else:
                score -= (price_ratio - 1.2)  # Penalize overpriced
        
        # Factor 2: Style keyword matching
        product_text = f"{product.get('name', '')} {product.get('category', '')} {product.get('subcategory', '')}".lower()
        keyword_matches = sum(1 for kw in style_keywords if kw.lower() in product_text)
        score += keyword_matches * 0.5
        
        # Factor 3: Constraint matching
        for constraint in item_plan.constraints:
            constraint_lower = constraint.lower()
            if "compact" in constraint_lower or "small" in constraint_lower or "space-saving" in constraint_lower:
                # Check if product has size indicators
                if any(word in product_text for word in ["compact", "small", "mini", "space-saving"]):
                    score += 1.0
        
        # Factor 4: Stock availability
        stock = product.get("inventory_quantity", 0)
        if stock > 5:
            score += 1.0
        elif stock > 0:
            score += 0.5
        
        # Factor 5: Product rating (if available)
        rating = product.get("rating", 0)
        if rating > 0:
            score += (rating / 5.0) * 0.5  # Up to 0.5 bonus for 5-star rating
        
        return max(0.0, min(10.0, score))  # Clamp to 0-10
    
    def _generate_message(self, plan: BundlePlan, bundle: Dict[str, Any]) -> str:
        """
        Generate natural language explanation of the bundle.
        
        Example:
            "I've designed a 'Space-Saving Home Office' for you within your $500 budget.
            It includes:
            - Compact Computer Desk ($150) - Perfect for small spaces
            - Ergonomic Office Chair ($120) - Comfortable for long work sessions
            - LED Desk Lamp ($40) - Adjustable lighting
            
            Total: $310 (well within your $500 budget)"
        """
        
        if not bundle["items"]:
            return f"I created a plan for '{plan.theme}' but couldn't find suitable products in stock. Try adjusting your budget or style preference."
        
        lines = [
            f"I've designed a **{bundle['theme']}** for you within your ${bundle['budget']:.0f} budget.",
            "",
            "It includes:"
        ]
        
        for item in bundle["items"]:
            lines.append(f"- **{item['name']}** (${item['price']:.2f}) - {item['reasoning']}")
        
        lines.append("")
        lines.append(f"**Total: ${bundle['total']:.2f}**")
        
        if bundle['total'] < bundle['budget'] * 0.8:
            savings = bundle['budget'] - bundle['total']
            lines.append(f"(${savings:.2f} under budget - great value!)")
        
        return "\n".join(lines)


def get_smart_bundle_planner() -> SmartBundlePlanner:
    """Get or create the singleton planner instance"""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = SmartBundlePlanner()
    return _planner_instance
