from django.test import TestCase
import asyncio
# Create your tests here.


async  def main():
    print("hello ---")
    await asyncio.sleep(5)
    print("---world")

asyncio.run(main())