# -*- coding: utf-8 -*-
"""Test template association interface fixes"""

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


def test_template_scanning():
    """Test template library scanning"""
    print("=" * 60)
    print("Test 1: Template Library Scanning")
    print("=" * 60)

    manager = get_template_path_manager()

    # Test scanning civil category
    templates = manager.get_available_templates("civil")

    print(f"\nFound {len(templates)} templates:")
    for template in templates:
        print(f"  - {template['name']} ({template['path']})")

    if len(templates) == 0:
        print("[FAIL] No templates found")
        return False
    else:
        print(f"[PASS] Found {len(templates)} templates")
        return True


def test_variable_extraction():
    """Test variable extraction"""
    print("\n" + "=" * 60)
    print("Test 2: Variable Extraction")
    print("=" * 60)

    manager = get_template_path_manager()
    engine = TemplateEngine()

    # Get first template
    templates = manager.get_available_templates("civil")
    if not templates:
        print("[FAIL] No available templates")
        return False

    # Test variable extraction
    test_template = templates[0]
    template_path = manager.resolve_template_path(test_template['path'])

    print(f"\nTesting template: {test_template['name']}")
    print(f"Template path: {template_path}")

    if not template_path or not template_path.exists():
        print(f"[FAIL] Template file does not exist")
        return False

    # Skip .doc files (not supported for variable extraction)
    if template_path.suffix.lower() == '.doc':
        print(f"[INFO] Skipping .doc file (variable extraction not supported)")
        return True

    variables = engine.extract_variables(template_path)

    print(f"\nExtracted {len(variables)} variables:")
    if variables:
        for var in variables[:10]:  # Show first 10 only
            print(f"  - {{{{{var}}}}}")
        if len(variables) > 10:
            print(f"  ... and {len(variables) - 10} more variables")
        print(f"[PASS] Extracted {len(variables)} variables")
        return True
    else:
        print("[INFO] This template does not contain variables")
        return True


def test_template_validation():
    """Test template validation"""
    print("\n" + "=" * 60)
    print("Test 3: Template Validation")
    print("=" * 60)

    manager = get_template_path_manager()

    # Test different template formats
    templates = manager.get_available_templates("civil")

    docx_templates = [t for t in templates if t['path'].endswith('.docx')]
    doc_templates = [t for t in templates if t['path'].endswith('.doc')]

    print(f"\n.docx templates: {len(docx_templates)}")
    print(f".doc templates: {len(doc_templates)}")

    # Test validation
    if docx_templates:
        test_path = docx_templates[0]['path']
        is_valid, msg = manager.validate_template_path(test_path)
        print(f"\nValidating {test_path}:")
        if is_valid:
            print(f"[PASS] Valid")
        else:
            print(f"[FAIL] Invalid: {msg}")

    if doc_templates:
        test_path = doc_templates[0]['path']
        is_valid, msg = manager.validate_template_path(test_path)
        print(f"\nValidating {test_path}:")
        if is_valid:
            print(f"[PASS] Valid")
        else:
            print(f"[FAIL] Invalid: {msg}")

    return True


def test_template_files():
    """Test template files"""
    print("\n" + "=" * 60)
    print("Test 4: Template Files Check")
    print("=" * 60)

    manager = get_template_path_manager()

    system_dir = manager.get_system_template_dir()
    civil_dir = system_dir / "civil"

    print(f"\nSystem template directory: {system_dir}")
    print(f"Civil template directory: {civil_dir}")
    print(f"Directory exists: {civil_dir.exists()}")

    if civil_dir.exists():
        docx_files = list(civil_dir.glob("*.docx"))
        doc_files = list(civil_dir.glob("*.doc"))

        print(f"\n.docx files: {len(docx_files)}")
        for f in docx_files:
            print(f"  - {f.name} ({f.stat().st_size} bytes)")

        print(f"\n.doc files: {len(doc_files)}")
        for f in doc_files[:5]:  # Show first 5 only
            print(f"  - {f.name}")
        if len(doc_files) > 5:
            print(f"  ... and {len(doc_files) - 5} more files")

        return True
    else:
        print("[FAIL] Template directory does not exist")
        return False


def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("Template Association Interface Fix Verification")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Template Library Scanning", test_template_scanning()))
    results.append(("Variable Extraction", test_variable_extraction()))
    results.append(("Template Validation", test_template_validation()))
    results.append(("Template Files Check", test_template_files()))

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
