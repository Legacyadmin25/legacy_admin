import sys

def clean_file(input_file, output_file):
    try:
        # Read the file in binary mode to handle all possible encodings
        with open(input_file, 'rb') as f:
            content = f.read()
        
        # Remove null bytes
        clean_content = content.replace(b'\x00', b'')
        
        # Write the cleaned content to a new file
        with open(output_file, 'wb') as f:
            f.write(clean_content)
            
        print(f"Successfully cleaned {input_file} -> {output_file}")
        return True
    except Exception as e:
        print(f"Error cleaning file: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python clean_file.py <input_file> <output_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    clean_file(input_file, output_file)
