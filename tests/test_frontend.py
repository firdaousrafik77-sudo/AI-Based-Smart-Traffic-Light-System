from pathlib import Path
frontend_path = Path('backend/main.py').parent.parent / 'frontend' / 'index.html'
print('Calculated path:', frontend_path)
print('Absolute path:', frontend_path.absolute())
print('Exists:', frontend_path.exists())
if frontend_path.exists():
    print('File size:', frontend_path.stat().st_size)
    try:
        with open(frontend_path, "r", encoding="utf-8") as f:
            content = f.read()
        print('Content length:', len(content))
        print('First 100 chars:', repr(content[:100]))
    except Exception as e:
        print('Error reading file:', e)