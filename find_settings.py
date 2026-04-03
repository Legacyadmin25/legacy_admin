import os

def find_settings():
    for root, dirs, files in os.walk('.'):
        if 'settings.py' in files:
            print(f"Found settings.py at: {os.path.join(root, 'settings.py')}")
        if 'settings' in dirs:
            for f in os.listdir(os.path.join(root, 'settings')):
                if f.endswith('.py') and not f.startswith('__'):
                    print(f"Found settings module: {os.path.join(root, 'settings', f)}")

if __name__ == "__main__":
    find_settings()
