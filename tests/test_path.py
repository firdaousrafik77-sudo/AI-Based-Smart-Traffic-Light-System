from pathlib import Path
import sys

# Simulate what happens in main.py
main_file = Path('backend/main.py')
print('main_file:', main_file)
print('main_file.parent:', main_file.parent)
print('main_file.parent.parent:', main_file.parent.parent)
frontend_path = main_file.parent.parent / 'frontend' / 'index.html'
print('frontend_path:', frontend_path)
print('frontend_path.exists():', frontend_path.exists())
print('frontend_path.absolute():', frontend_path.absolute())

# Try to read the file like main.py does
try:
    with open(frontend_path, "r", encoding="utf-8") as f:
        content = f.read()
    print('File read successfully, length:', len(content))
    print('First 100 chars:', repr(content[:100]))
except Exception as e:
    print('Error reading file:', e)