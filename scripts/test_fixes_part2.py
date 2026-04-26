# -*- coding: utf-8 -*-
"""Test fixes for Word template system issues"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.template_path_manager import get_template_path_manager
from src.core.template_engine import TemplateEngine
from src.utils.logger import get_logger
import logging

# Setup logging
logger = get_logger()
logger.setLevel(logging.DEBUG)

# Add console handler
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def test_template_scanning_no_category():
    """Test template library scanning without category"""
    print("=" * 60)
    print("Test 1: Template Library Scanning (No Category)")
    print("=" * 60)

    manager = get_template_path_manager()

    # Test scanning without category (should scan all subdirectories)
    templates = manager.get_available_templates()

    print(f"\nFound {len(templates)} templates (all categories):")
    categories = {}
    for template in templates:
        cat = template['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(template['name'])

    for cat, names in sorted(categories.items()):
        print(f"\n  Category '{cat}': {len(names)} templates")
        for name in names[:3]:
            print(f"    - {name}")
        if len(names) > 3:
            print(f"    ... and {len(names) - 3} more")

    if len(templates) == 0:
        print("[FAIL] No templates found")
        return False
    else:
        print(f"\n[PASS] Found {len(templates)} templates total")
        return True


def test_template_scanning_with_category():
    """Test template library scanning with category"""
    print("\n" + "=" * 60)
    print("Test 2: Template Library Scanning (With Category 'civil')")
    print("=" * 60)

    manager = get_template_path_manager()

    # Test scanning with civil category
    templates = manager.get_available_templates("civil")

    print(f"\nFound {len(templates)} templates in 'civil' category:")
    for template in templates[:5]:
        print(f"  - {template['name']}")
    if len(templates) > 5:
        print(f"  ... and {len(templates) - 5} more")

    if len(templates) == 0:
        print("[FAIL] No templates found")
        return False
    else:
        print(f"\n[PASS] Found {len(templates)} templates in civil category")
        return True


def test_variable_replacement_none_values():
    """Test that None values preserve variable placeholders"""
    print("\n" + "=" * 60)
    print("Test 3: Variable Replacement with None Values")
    print("=" * 60)

    engine = TemplateEngine()

    # Test data with some None values
    test_values = {
        "委托人姓名": "张三",
        "案号": None,  # This should preserve {{案号}}
        "案由": "合同纠纷",
        "对方当事人": None,  # This should preserve {{对方当事人}}
        "受理法院": "北京市朝阳区人民法院",
        "承办律师": "",  # Empty string should also preserve {{承办律师}}
        "收案日期": "2026年2月25日"
    }

    print("\nInput values:")
    for key, value in test_values.items():
        print(f"  {key}: {repr(value)}")

    # Call _prepare_context
    context = engine._prepare_context(test_values)

    print(f"\nContext after _prepare_context():")
    for key, value in context.items():
        print(f"  {key}: {repr(value)}")

    # Verify that None and empty values are NOT in context
    should_be_missing = ["案号", "对方当事人", "承办律师"]
    all_good = True

    for key in should_be_missing:
        if key in context:
            print(f"\n[FAIL] {key} should NOT be in context (was {repr(context[key])})")
            all_good = False
        else:
            print(f"\n[OK] {key} correctly excluded from context (will preserve {{{{{key}}}}})")

    # Verify that non-None values ARE in context
    should_be_present = ["委托人姓名", "案由", "受理法院", "收案日期"]
    for key in should_be_present:
        if key not in context:
            print(f"\n[FAIL] {key} should be in context")
            all_good = False
        elif not context[key]:
            print(f"\n[FAIL] {key} has empty value in context: {repr(context[key])}")
            all_good = False
        else:
            print(f"[OK] {key} = {repr(context[key])}")

    if all_good:
        print("\n[PASS] None and empty values correctly excluded from context")
    else:
        print("\n[FAIL] Some values not handled correctly")

    return all_good


def test_variable_replacement_all_values():
    """Test that all non-None values are correctly processed"""
    print("\n" + "=" * 60)
    print("Test 4: Variable Replacement with All Values")
    print("=" * 60)

    engine = TemplateEngine()

    # Test data with all values provided
    test_values = {
        "委托人姓名": "李四",
        "案号": "(2026)京0105民初1234号",
        "案由": "民间借贷纠纷",
        "对方当事人": "王五",
        "受理法院": "北京市海淀区人民法院",
        "承办律师": "赵律师",
        "收案日期": "2026年2月25日"
    }

    print("\nInput values:")
    for key, value in test_values.items():
        print(f"  {key}: {repr(value)}")

    # Call _prepare_context
    context = engine._prepare_context(test_values)

    print(f"\nContext after _prepare_context():")
    for key, value in context.items():
        print(f"  {key}: {repr(value)}")

    # All values should be in context
    all_good = True
    for key, expected_value in test_values.items():
        if key not in context:
            print(f"\n[FAIL] {key} not in context")
            all_good = False
        elif context[key] != expected_value:
            print(f"\n[FAIL] {key}: expected {repr(expected_value)}, got {repr(context[key])}")
            all_good = False

    if all_good:
        print("\n[PASS] All values correctly included in context")
    else:
        print("\n[FAIL] Some values missing or incorrect")

    return all_good


def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("Word Template System Fix Verification")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Template Scanning (No Category)", test_template_scanning_no_category()))
    results.append(("Template Scanning (With Category)", test_template_scanning_with_category()))
    results.append(("Variable Replacement (None Values)", test_variable_replacement_none_values()))
    results.append(("Variable Replacement (All Values)", test_variable_replacement_all_values()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{name}: {status}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed")


if __name__ == "__main__":
    main()
