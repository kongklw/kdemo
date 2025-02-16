import pandas as pd
from itertools import groupby

origin = [{'id': 59, 'create_time': '2025-02-16', 'update_time': '2025-02-16', 'text': 'AD', 'done': True, 'user': 3},
          {'id': 60, 'create_time': '2025-02-16', 'update_time': '2025-02-16', 'text': '钙', 'done': False, 'user': 3},
          {'id': 61, 'create_time': '2025-02-16', 'update_time': '2025-02-16', 'text': '益生菌', 'done': False,
           'user': 3},
          {'id': 62, 'create_time': '2025-02-16', 'update_time': '2025-02-16', 'text': '大便', 'done': False,
           'user': 3}]

df = pd.DataFrame()

grouped = groupby(origin, key=lambda x: x["create_time"])

print(grouped)
for key,group in grouped:
    print(key,list(group))

#
# for item in grouped:
#     print(item)