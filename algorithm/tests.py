# def merge_sort(alist):
#     if len(alist) <= 1:
#         return alist
#     # 二分分解
#     num = len(alist) / 2
#     left = merge_sort(alist[:num])
#     right = merge_sort(alist[num:])
#     # 合并
#     return merge(left, right)
#
#
# def merge(left, right):
#     '''合并操作，将两个有序数组left[]和right[]合并成一个大的有序数组'''
#     # left与right的下标指针
#     l, r = 0, 0
#     result = []
#     while l < len(left) and r < len(right):
#         if left[l] < right[r]:
#             result.append(left[l])
#             l += 1
#         else:
#             result.append(right[r])
#             r += 1
#     result += left[l:]
#     result += right[r:]
#     return result


def mergeSort(arr):
    import math
    if (len(arr) < 2):
        return arr
    middle = math.floor(len(arr) / 2)
    left, right = arr[0:middle], arr[middle:]
    return merge(mergeSort(left), mergeSort(right))


def merge(left, right):
    result = []
    while left and right:
        if left[0] <= right[0]:
            result.append(left.pop(0))
        else:
            result.append(right.pop(0));
    while left:
        result.append(left.pop(0))
    while right:
        result.append(right.pop(0));
    return result


# alist = [54, 26, 93, 17, 77, 31, 44, 55, 20]
alist = [2, 3, 1, 3, 2, 7, 5, 4, 9, 0]
sorted_alist = mergeSort(alist)
print(sorted_alist)
