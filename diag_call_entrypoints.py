import importlib.metadata as m
import time
start = time.time()
try:
    eps = m.entry_points(group='alembic.plugins')
    print('Found', len(list(eps)))
except Exception as e:
    print('EXC', e)
print('Elapsed', time.time()-start)
