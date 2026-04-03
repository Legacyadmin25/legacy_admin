import re

with open('members/views_public_enrollment.py', 'r') as f:
    content = f.read()

content = re.sub(r"redirect\('public_enrollment_", "redirect('public_enrollment:", content)

with open('members/views_public_enrollment.py', 'w') as f:
    f.write(content)

print('✓ Fixed all redirect URLs to use namespace format')
