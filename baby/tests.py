# import asyncio
# import time
#
#
# async def say_after(delay, what):
#     await asyncio.sleep(delay)
#     print(what)
#
#
# # async def main():
# #     task1 = asyncio.create_task(say_after(1, 'hello'))
# #     task2 = asyncio.create_task(say_after(2, 'world'))
# #
# #     print(f'start at {time.strftime('%X')}')
# #     await task1
# #     await task2
# #     print(f"finished at {time.strftime('%X')}")
#
#
# async def main():
#     async with asyncio.TaskGroup() as tg:
#         task1 = tg.create_task(say_after(1, 'hello'))
#         task2 = tg.create_task(say_after(2, 'world'))
#         print(f"started at {time.strftime('%X')}")
#     print(f"finished at {time.strftime('%X')}")
#
#     await task1,task2
#
#
# asyncio.run(main())

from decimal import Decimal, getcontext

getcontext().prec = 2
a = "60.23445"

b = Decimal(a)
print(type(b), b)
