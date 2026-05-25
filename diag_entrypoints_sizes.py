import importlib.metadata as m
import os

for d in m.distributions():
    p = getattr(d, '_path', None)
    if not p:
        continue
    ep = os.path.join(str(p), 'entry_points.txt')
    if os.path.exists(ep):
        try:
            sz = os.path.getsize(ep)
        except Exception as e:
            sz = f'ERR:{e}'
        print(str(p), sz)
