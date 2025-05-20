#!/usr/bin/env python
"""
Simple test runner script for the Legacyadmin project.
"""
import os
import sys
import subprocess

def run_test_module(module_path):
    """Run a specific test module with proper Django settings."""
    print(f"Running tests for: {module_path}")
    cmd = [
        os.path.join('.venv', 'Scripts', 'python'),
        '-m', 'pytest',
        module_path,
        '-v',
        '--disable-warnings'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("ERRORS:")
        print(result.stderr)
    return result.returncode

def main():
    """Main entry point."""
    # Install any missing dependencies
    subprocess.run([
        os.path.join('.venv', 'Scripts', 'pip'),
        'install',
        'pytest',
        'pytest-django',
        'pytest-cov',
        'django-braces',
        'crispy-bootstrap5'
    ])
    
    # Test modules to run
    test_modules = [
        'members/tests/test_forms.py',
        'members/tests/test_models.py',
        'members/tests/test_views.py'
    ]
    
    # Run each test module
    exit_codes = []
    for module in test_modules:
        exit_code = run_test_module(module)
        exit_codes.append(exit_code)
        print(f"Exit code for {module}: {exit_code}")
    
    # Return overall status
    return 1 if any(exit_codes) else 0

if __name__ == '__main__':
    sys.exit(main())
