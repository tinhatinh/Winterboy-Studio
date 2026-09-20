import sys, re
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    content = f.read()
new_content = re.sub(r'(?i)mumustudio', 'Winterboy Studio', content)
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(new_content)
