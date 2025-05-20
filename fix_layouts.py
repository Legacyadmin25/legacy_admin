import os
import re

def fix_template_layouts(root_dir):
    """
    Find all HTML templates and update them to use full-width layouts
    by replacing container classes with w-full.
    """
    pattern = re.compile(r'<div class="container mx-auto[^"]*">')
    replacement = '<div class="w-full px-6 py-8">'
    
    count = 0
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if 'container mx-auto' in content:
                        new_content = pattern.sub(replacement, content)
                        if new_content != content:
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            count += 1
                            print(f"Updated: {filepath}")
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")
    
    print(f"Total files updated: {count}")

if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.abspath(__file__))
    fix_template_layouts(root_dir)
