import sys
with open(sys.argv[1], 'r') as f:
    lines = f.readlines()
with open(sys.argv[1], 'w') as f:
    for line in lines:
        if line.startswith('pick '):
            f.write(line.replace('pick ', 'reword '))
        else:
            f.write(line)
