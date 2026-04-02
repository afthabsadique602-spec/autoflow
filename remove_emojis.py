import sys

emojis = ['📊', '📝', '📁', '🤖', '✅', '🔍', '⚠️', '📥', '✨', '❌', '🔥']

for filepath in ['templates/index.html', 'app.py']:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for ext in emojis:
            content = content.replace(ext + ' ', '')
            content = content.replace(ext, '')
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"Failed on {filepath}: {e}")
