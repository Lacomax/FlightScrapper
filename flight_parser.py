import os, re

def fix_unicode_arrows(path):
    """Replace Unicode arrows with ASCII alternatives in Python files"""
    if not os.path.exists(path): return False
    
    if os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"): fix_file(os.path.join(root, file))
    elif os.path.isfile(path) and path.endswith(".py"):
        fix_file(path)
    else: return False
    
    return True

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = re.sub(r'→', '->', content)
        new_content = re.sub(r'←', '<-', new_content)
        new_content = re.sub(r'⟶', '-->', new_content)
        
        if content != new_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Fixed Unicode arrows in {filepath}")
        
        return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    fix_unicode_arrows(path)
    print("Done.")