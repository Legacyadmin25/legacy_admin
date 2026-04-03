import os
import sys

def clean_file(file_path):
    """Remove null bytes from a file."""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Check if the file has null bytes
        if b'\x00' in content:
            print(f"Cleaning {file_path}...")
            # Remove null bytes
            clean_content = content.replace(b'\x00', b'')
            
            # Create backup
            backup_path = file_path + '.bak'
            with open(backup_path, 'wb') as f:
                f.write(content)
            
            # Write the cleaned content
            with open(file_path, 'wb') as f:
                f.write(clean_content)
            
            return True
        return False
    except Exception as e:
        print(f"Error cleaning {file_path}: {str(e)}")
        return False

def clean_directory(directory):
    """Clean all Python files in a directory and its subdirectories."""
    cleaned_files = 0
    skipped_files = 0
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if clean_file(file_path):
                    cleaned_files += 1
                else:
                    skipped_files += 1
    
    return cleaned_files, skipped_files

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python clean_all_python_files.py <directory>")
        sys.exit(1)
    
    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        sys.exit(1)
    
    print(f"Scanning and cleaning Python files in {directory} and subdirectories...")
    cleaned, skipped = clean_directory(directory)
    print(f"Done! Cleaned {cleaned} files, skipped {skipped} files (no null bytes found).")
