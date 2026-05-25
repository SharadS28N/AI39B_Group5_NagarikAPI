import sys
import importlib.metadata as m

print('PYTHON:', sys.executable)
count = 0
try:
    for i, d in enumerate(m.distributions()):
        try:
            name = d.metadata.get('Name') if d.metadata else getattr(d, 'name', str(d))
        except Exception as e:
            name = f'<meta-exc:{e}>'
        try:
            path = str(d._path)
        except Exception as e:
            path = f'<path-exc:{e}>'
        print(i, name, path)
        count += 1
        if count >= 500:
            break
except Exception as e:
    print('ITERATION-EXCEPTION:', e)
print('DONE, listed', count)
