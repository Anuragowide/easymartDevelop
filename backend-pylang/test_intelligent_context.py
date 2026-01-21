"""
Test intelligent context understanding system.
Verifies that LLM-based context analysis works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from app.modules.assistant.intelligent_context import get_intelligent_context_handler


async def test_context_recovery():
    """Test intelligent context recovery with various scenarios."""
    handler = get_intelligent_context_handler()
    
    print("\n" + "="*80)
    print("INTELLIGENT CONTEXT UNDERSTANDING TEST")
    print("="*80)
    
    test_cases = [
        {
            "name": "Follow-up: 'you choose' after puppy supplies",
            "previous_context": "puppy supplies $250",
            "current_message": "you choose",
            "conversation": [
                {"role": "user", "content": "puppy supplies $250"},
                {"role": "assistant", "content": "Which items do you need?"}
            ],
            "expected_needs_context": True
        },
        {
            "name": "Follow-up: 'give me bundle' after puppy supplies",
            "previous_context": "puppy supplies $250",
            "current_message": "give me bundle",
            "conversation": [
                {"role": "user", "content": "puppy supplies $250"},
                {"role": "assistant", "content": "Which items?"}
            ],
            "expected_needs_context": True
        },
        {
            "name": "New query: 'show me office chairs' (independent)",
            "previous_context": "puppy supplies $250",
            "current_message": "show me office chairs",
            "conversation": [
                {"role": "user", "content": "puppy supplies $250"},
                {"role": "assistant", "content": "Which items?"}
            ],
            "expected_needs_context": False
        },
        {
            "name": "Follow-up: 'yes' after question",
            "previous_context": "cat supplies under $200",
            "current_message": "yes",
            "conversation": [
                {"role": "user", "content": "cat supplies under $200"},
                {"role": "assistant", "content": "Should I create a starter bundle?"}
            ],
            "expected_needs_context": True
        },
        {
            "name": "Specific query: 'red dog bed' (independent)",
            "previous_context": "puppy supplies",
            "current_message": "show me red dog beds under $100",
            "conversation": [
                {"role": "user", "content": "puppy supplies"},
                {"role": "assistant", "content": "Which items?"}
            ],
            "expected_needs_context": False
        },
        {
            "name": "Follow-up: 'make one' after bundle discussion",
            "previous_context": "office setup $1500",
            "current_message": "make one",
            "conversation": [
                {"role": "user", "content": "office setup $1500"},
                {"role": "assistant", "content": "I can create a bundle with desk, chair, and storage. Should I proceed?"}
            ],
            "expected_needs_context": True
        },
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        print(f"\n{'='*80}")
        print(f"TEST: {test_case['name']}")
        print(f"{'='*80}")
        print(f"Previous context: \"{test_case['previous_context']}\"")
        print(f"Current message: \"{test_case['current_message']}\"")
        
        result = await handler.should_apply_previous_context(
            current_message=test_case['current_message'],
            previous_shopping_context=test_case['previous_context'],
            recent_conversation=test_case['conversation']
        )
        
        print(f"\nResult:")
        print(f"  Needs context: {result['needs_context']}")
        print(f"  Combined query: \"{result['combined_query']}\"")
        print(f"  Reasoning: {result['reasoning']}")
        
        expected = test_case['expected_needs_context']
        actual = result['needs_context']
        
        if expected == actual:
            print(f"\n✅ PASS - Context decision correct")
            passed += 1
        else:
            print(f"\n❌ FAIL - Expected needs_context={expected}, got {actual}")
            failed += 1
    
    print(f"\n{'='*80}")
    print(f"CONTEXT RECOVERY TEST SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Passed: {passed}/{len(test_cases)}")
    print(f"❌ Failed: {failed}/{len(test_cases)}")
    print(f"{'='*80}\n")


async def test_response_analysis():
    """Test intelligent response type analysis."""
    handler = get_intelligent_context_handler()
    
    print("\n" + "="*80)
    print("INTELLIGENT RESPONSE ANALYSIS TEST")
    print("="*80)
    
    test_cases = [
        {
            "name": "Product listing with prices",
            "user_query": "office chairs",
            "assistant_response": "Here are some chairs:\n\n1. Chair A – $402\n2. Chair B – $275\n\nWould you like more?",
            "expected_is_clarification": False,
            "expected_is_showing_products": True
        },
        {
            "name": "Clarification question with options",
            "user_query": "puppy supplies",
            "assistant_response": "Which items do you need?\n- Bed\n- Bowl\n- Leash\n- Toys",
            "expected_is_clarification": True,
            "expected_is_showing_products": False
        },
        {
            "name": "Bundle presentation",
            "user_query": "cat supplies $200",
            "assistant_response": "Here's a bundle:\n\n1. Cat Bed – $57\n2. Litter Box – $13\n\nTotal: $70",
            "expected_is_clarification": False,
            "expected_is_showing_products": True
        },
        {
            "name": "Simple clarification",
            "user_query": "furniture",
            "assistant_response": "What type of furniture are you looking for?",
            "expected_is_clarification": True,
            "expected_is_showing_products": False
        },
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        print(f"\n{'='*80}")
        print(f"TEST: {test_case['name']}")
        print(f"{'='*80}")
        print(f"Query: \"{test_case['user_query']}\"")
        print(f"Response: \"{test_case['assistant_response'][:100]}...\"")
        
        result = await handler.analyze_response_type(
            assistant_response=test_case['assistant_response'],
            user_query=test_case['user_query']
        )
        
        print(f"\nResult:")
        print(f"  Is clarification: {result['is_clarification']}")
        print(f"  Is showing products: {result['is_showing_products']}")
        print(f"  Reasoning: {result['reasoning']}")
        
        expected_clarif = test_case['expected_is_clarification']
        actual_clarif = result['is_clarification']
        expected_products = test_case['expected_is_showing_products']
        actual_products = result['is_showing_products']
        
        if expected_clarif == actual_clarif and expected_products == actual_products:
            print(f"\n✅ PASS - Response type correctly identified")
            passed += 1
        else:
            print(f"\n❌ FAIL - Expected clarif={expected_clarif}/products={expected_products}, got clarif={actual_clarif}/products={actual_products}")
            failed += 1
    
    print(f"\n{'='*80}")
    print(f"RESPONSE ANALYSIS TEST SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Passed: {passed}/{len(test_cases)}")
    print(f"❌ Failed: {failed}/{len(test_cases)}")
    print(f"{'='*80}\n")


async def main():
    await test_context_recovery()
    await test_response_analysis()


if __name__ == "__main__":
    asyncio.run(main())
