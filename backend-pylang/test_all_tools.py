"""
Comprehensive LangChain Tools Test Suite

Tests all 13 LangChain tools to ensure they're working correctly.
Identifies issues and provides fixes.

Usage:
    python test_all_tools.py
    python test_all_tools.py --tool search_products  # Test specific tool
    python test_all_tools.py --verbose               # Detailed output
"""

import asyncio
import sys
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime
import traceback

from app.modules.assistant.tools import get_langchain_tools, CURRENT_SESSION_ID
from app.modules.assistant.session_store import get_session_store
from app.core.config import get_settings


class ToolTester:
    """Comprehensive tool testing framework"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = []
        self.tools = get_langchain_tools()
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.settings = get_settings()
        
        # Create test session
        self.session_store = get_session_store()
        self.test_session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def log(self, message: str, level: str = "INFO"):
        """Log message with optional verbose mode"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "TEST": "🧪"
        }.get(level, "  ")
        
        if self.verbose or level in ["SUCCESS", "ERROR", "WARNING"]:
            print(f"[{timestamp}] {prefix} {message}")
    
    async def test_tool(self, tool_name: str, test_args: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single tool with given arguments"""
        self.log(f"Testing tool: {tool_name}", "TEST")
        
        result = {
            "tool": tool_name,
            "status": "unknown",
            "success": False,
            "error": None,
            "response": None,
            "execution_time": 0,
            "issues": []
        }
        
        try:
            tool = self.tool_map.get(tool_name)
            if not tool:
                result["status"] = "not_found"
                result["error"] = f"Tool '{tool_name}' not found"
                return result
            
            # Set session context
            CURRENT_SESSION_ID.set(self.test_session_id)
            
            # Execute tool
            start_time = datetime.now()
            response = await tool.ainvoke(test_args)
            end_time = datetime.now()
            
            result["execution_time"] = (end_time - start_time).total_seconds()
            result["response"] = response
            
            # Validate response
            validation = self._validate_response(tool_name, response)
            result["success"] = validation["valid"]
            result["status"] = "passed" if validation["valid"] else "failed"
            result["issues"] = validation.get("issues", [])
            
            if result["success"]:
                self.log(f"  ✓ {tool_name} passed ({result['execution_time']:.2f}s)", "SUCCESS")
            else:
                self.log(f"  ✗ {tool_name} failed: {', '.join(result['issues'])}", "ERROR")
                
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            result["success"] = False
            result["traceback"] = traceback.format_exc()
            self.log(f"  ✗ {tool_name} error: {str(e)}", "ERROR")
            
            if self.verbose:
                print(result["traceback"])
        
        self.results.append(result)
        return result
    
    def _validate_response(self, tool_name: str, response: Any) -> Dict[str, Any]:
        """Validate tool response based on tool type"""
        issues = []
        
        if not response:
            issues.append("Empty response")
            return {"valid": False, "issues": issues}
        
        # Tool-specific validations
        if tool_name == "search_products":
            if not isinstance(response, dict):
                issues.append("Response should be a dict")
            elif "products" not in response:
                issues.append("Missing 'products' key")
            elif not isinstance(response.get("products"), list):
                issues.append("'products' should be a list")
            elif "total" not in response:
                issues.append("Missing 'total' key")
                
        elif tool_name in ["get_product_specs", "check_availability"]:
            if isinstance(response, dict) and response.get("error"):
                # Error responses are valid if product not found
                if "not found" in response.get("error", "").lower():
                    return {"valid": True, "issues": []}
                issues.append(f"Tool returned error: {response.get('error')}")
            elif not isinstance(response, dict):
                issues.append("Response should be a dict")
            elif "product_id" not in response:
                issues.append("Missing 'product_id' key")
                
        elif tool_name == "compare_products":
            if not isinstance(response, dict):
                issues.append("Response should be a dict")
            elif "products" not in response and "error" not in response:
                issues.append("Missing 'products' or 'error' key")
                
        elif tool_name == "update_cart":
            if not isinstance(response, dict):
                issues.append("Response should be a dict")
            elif "success" not in response:
                issues.append("Missing 'success' key")
            elif "cart" not in response and "error" not in response:
                issues.append("Missing 'cart' or 'error' key")
                
        elif tool_name in ["get_policy_info", "get_contact_info"]:
            if not isinstance(response, dict):
                issues.append("Response should be a dict")
            elif not response:
                issues.append("Empty response dict")
                
        elif tool_name == "calculate_shipping":
            if not isinstance(response, dict):
                issues.append("Response should be a dict")
            elif "shipping_cost" not in response:
                issues.append("Missing 'shipping_cost' key")
            elif "total" not in response:
                issues.append("Missing 'total' key")
                
        elif tool_name in ["find_similar_products", "search_small_space"]:
            if not isinstance(response, dict):
                issues.append("Response should be a dict")
            elif "products" not in response and "error" not in response:
                issues.append("Missing 'products' or 'error' key")
                
        elif tool_name == "check_product_fit":
            if not isinstance(response, dict):
                issues.append("Response should be a dict")
            elif "fits" not in response and "error" not in response:
                issues.append("Missing 'fits' or 'error' key")
                
        elif tool_name in ["build_bundle", "build_cheapest_bundle"]:
            if not isinstance(response, dict):
                issues.append("Response should be a dict")
            # Bundle tools may have various response formats
        
        return {"valid": len(issues) == 0, "issues": issues}
    
    async def run_all_tests(self):
        """Run tests for all tools"""
        self.log(f"\n{'='*80}", "INFO")
        self.log(f"  LANGCHAIN TOOLS COMPREHENSIVE TEST SUITE", "INFO")
        self.log(f"{'='*80}\n", "INFO")
        
        self.log(f"Configuration:", "INFO")
        self.log(f"  • Total tools: {len(self.tools)}", "INFO")
        self.log(f"  • Test session: {self.test_session_id}", "INFO")
        self.log(f"  • Verbose mode: {self.verbose}", "INFO")
        self.log(f"  • Environment: {self.settings.ENVIRONMENT}\n", "INFO")
        
        # Define test cases for each tool
        test_cases = [
            # 1. search_products
            {
                "tool": "search_products",
                "args": {"query": "office chair", "limit": 3},
                "description": "Search for office chairs"
            },
            # 2. get_product_specs
            {
                "tool": "get_product_specs",
                "args": {"product_id": "test_sku_001"},
                "description": "Get product specifications"
            },
            # 3. check_availability
            {
                "tool": "check_availability",
                "args": {"product_id": "test_sku_001"},
                "description": "Check product availability"
            },
            # 4. compare_products
            {
                "tool": "compare_products",
                "args": {"product_ids": ["test_sku_001", "test_sku_002"]},
                "description": "Compare multiple products"
            },
            # 5. update_cart - view
            {
                "tool": "update_cart",
                "args": {"action": "view", "session_id": self.test_session_id},
                "description": "View cart contents"
            },
            # 6. update_cart - add
            {
                "tool": "update_cart",
                "args": {
                    "action": "add",
                    "product_id": "test_sku_001",
                    "quantity": 2,
                    "session_id": self.test_session_id,
                    "skip_sync": True  # Don't sync with Node.js during tests
                },
                "description": "Add item to cart"
            },
            # 7. update_cart - remove
            {
                "tool": "update_cart",
                "args": {
                    "action": "remove",
                    "product_id": "test_sku_001",
                    "session_id": self.test_session_id,
                    "skip_sync": True
                },
                "description": "Remove item from cart"
            },
            # 8. get_policy_info
            {
                "tool": "get_policy_info",
                "args": {"policy_type": "returns"},
                "description": "Get return policy"
            },
            # 9. get_contact_info
            {
                "tool": "get_contact_info",
                "args": {"info_type": "all"},
                "description": "Get contact information"
            },
            # 10. calculate_shipping
            {
                "tool": "calculate_shipping",
                "args": {"order_total": 150.00, "postcode": "2000"},
                "description": "Calculate shipping cost"
            },
            # 11. find_similar_products
            {
                "tool": "find_similar_products",
                "args": {"product_id": "test_sku_001", "limit": 3},
                "description": "Find similar products"
            },
            # 12. check_product_fit
            {
                "tool": "check_product_fit",
                "args": {
                    "product_id": "test_sku_001",
                    "space_length": 150.0,
                    "space_width": 80.0
                },
                "description": "Check if product fits in space"
            },
            # 13. search_small_space
            {
                "tool": "search_small_space",
                "args": {
                    "category": "desk",
                    "space_length": 120.0,
                    "space_width": 60.0,
                    "limit": 3
                },
                "description": "Search for products that fit small space"
            },
            # 14. build_bundle
            {
                "tool": "build_bundle",
                "args": {
                    "request": "5 office chairs under $1000",
                    "budget_total": 1000.0
                },
                "description": "Build product bundle"
            },
            # 15. build_cheapest_bundle (if exists)
            {
                "tool": "build_cheapest_bundle",
                "args": {
                    "request": "cheapest 3 office chairs",
                },
                "description": "Build cheapest bundle"
            },
        ]
        
        # Run all tests
        for i, test_case in enumerate(test_cases, 1):
            self.log(f"\n[{i}/{len(test_cases)}] {test_case['description']}", "TEST")
            result = await self.test_tool(test_case["tool"], test_case["args"])
            
            if self.verbose and result.get("response"):
                print(f"      Response preview: {str(result['response'])[:200]}...")
        
        # Generate summary
        self.print_summary()
    
    async def test_single_tool(self, tool_name: str):
        """Test a specific tool"""
        self.log(f"\n{'='*80}", "INFO")
        self.log(f"  TESTING TOOL: {tool_name}", "INFO")
        self.log(f"{'='*80}\n", "INFO")
        
        # Find test case for this tool
        test_args = self._get_default_args(tool_name)
        result = await self.test_tool(tool_name, test_args)
        
        # Print detailed result
        self.print_tool_details(result)
        
        return result
    
    def _get_default_args(self, tool_name: str) -> Dict[str, Any]:
        """Get default test arguments for a tool"""
        defaults = {
            "search_products": {"query": "office chair", "limit": 5},
            "get_product_specs": {"product_id": "test_sku_001"},
            "check_availability": {"product_id": "test_sku_001"},
            "compare_products": {"product_ids": ["test_sku_001", "test_sku_002"]},
            "update_cart": {"action": "view", "session_id": self.test_session_id},
            "get_policy_info": {"policy_type": "returns"},
            "get_contact_info": {"info_type": "all"},
            "calculate_shipping": {"order_total": 150.00},
            "find_similar_products": {"product_id": "test_sku_001", "limit": 5},
            "check_product_fit": {
                "product_id": "test_sku_001",
                "space_length": 150.0,
                "space_width": 80.0
            },
            "search_small_space": {
                "category": "desk",
                "space_length": 120.0,
                "space_width": 60.0,
                "limit": 5
            },
            "build_bundle": {
                "request": "5 office chairs under $1000",
                "budget_total": 1000.0
            },
            "build_cheapest_bundle": {
                "request": "cheapest 3 office chairs"
            }
        }
        return defaults.get(tool_name, {})
    
    def print_tool_details(self, result: Dict[str, Any]):
        """Print detailed information about a tool test result"""
        print(f"\n{'='*80}")
        print(f"  TOOL TEST RESULT: {result['tool']}")
        print(f"{'='*80}\n")
        
        print(f"Status: {result['status'].upper()}")
        print(f"Success: {'✅ Yes' if result['success'] else '❌ No'}")
        print(f"Execution Time: {result['execution_time']:.3f}s")
        
        if result.get("error"):
            print(f"\nError: {result['error']}")
            if result.get("traceback"):
                print(f"\nTraceback:\n{result['traceback']}")
        
        if result.get("issues"):
            print(f"\nIssues Found:")
            for issue in result['issues']:
                print(f"  • {issue}")
        
        if result.get("response") and self.verbose:
            print(f"\nResponse:")
            import json
            try:
                print(json.dumps(result['response'], indent=2, default=str))
            except:
                print(result['response'])
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n\n{'='*80}")
        print(f"  TEST SUMMARY")
        print(f"{'='*80}\n")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = sum(1 for r in self.results if not r["success"])
        errors = sum(1 for r in self.results if r["status"] == "error")
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"⚠️  Errors: {errors}")
        
        avg_time = sum(r["execution_time"] for r in self.results) / total if total > 0 else 0
        print(f"\nAverage Execution Time: {avg_time:.3f}s")
        
        # Failed tools
        failed_tools = [r for r in self.results if not r["success"]]
        if failed_tools:
            print(f"\n{'='*80}")
            print(f"  FAILED TOOLS")
            print(f"{'='*80}\n")
            
            for result in failed_tools:
                print(f"❌ {result['tool']}")
                print(f"   Status: {result['status']}")
                if result.get("error"):
                    print(f"   Error: {result['error']}")
                if result.get("issues"):
                    for issue in result['issues']:
                        print(f"   • {issue}")
                print()
        
        # Recommendations
        print(f"\n{'='*80}")
        print(f"  RECOMMENDATIONS")
        print(f"{'='*80}\n")
        
        if passed == total:
            print("✅ All tools are working correctly!")
            print("   No action required.")
        else:
            print("⚠️  Some tools need attention:")
            print("   1. Review error messages above")
            print("   2. Check that product data exists in catalog")
            print("   3. Ensure Node.js backend is running (for cart operations)")
            print("   4. Run: python -m app.modules.assistant.cli index-catalog")
            print("   5. Check network connectivity for external services")
        
        print(f"\n{'='*80}\n")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Test LangChain tools")
    parser.add_argument("--tool", help="Test specific tool only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--list", "-l", action="store_true", help="List all tools")
    
    args = parser.parse_args()
    
    tester = ToolTester(verbose=args.verbose)
    
    if args.list:
        print("\nAvailable Tools:")
        print("=" * 50)
        for i, tool in enumerate(tester.tools, 1):
            print(f"{i:2d}. {tool.name}")
        print()
        return
    
    if args.tool:
        result = await tester.test_single_tool(args.tool)
        sys.exit(0 if result["success"] else 1)
    else:
        await tester.run_all_tests()
        
        # Exit with error code if any tests failed
        failed = sum(1 for r in tester.results if not r["success"])
        sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
