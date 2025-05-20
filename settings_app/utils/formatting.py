# settings_app/utils/formatting.py

def title_case_name(name):
    return name.strip().title()

def normalize_phone_number(phone):
    return ''.join(filter(str.isdigit, phone))
