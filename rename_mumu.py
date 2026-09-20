import os
import re

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content.replace('WINTERBOY_PROJECT_ROOT', 'WINTERBOY_PROJECT_ROOT')
    new_content = new_content.replace('WinterboyStudio', 'WinterboyStudio')
    new_content = new_content.replace('Winterboy Studio', 'Winterboy Studio')
    new_content = new_content.replace('WINTERBOY STUDIO', 'WINTERBOY STUDIO')
    new_content = new_content.replace('.winterboy', '.winterboy')
    
    if content != new_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, _, files in os.walk(r'C:\Users\Administrator\.gemini\antigravity-ide\scratch\mumu_source'):
    if '.git' in root: continue
    for file in files:
        if file.endswith('.py'):
            replace_in_file(os.path.join(root, file))
