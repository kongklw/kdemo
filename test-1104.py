


def bubble_sort(alist):
    for i in range(len(alist) - 1, 0, -1):
        for j in range(i):
            if alist[j] > alist[j + 1]:
                alist[j], alist[j + 1] = alist[j + 1], alist[j]


def quick_sort(alist, start, end):
    if start >= end:
        return

    cur1 = start
    cur2 = end
    mid = alist[cur1]

    while cur1 < cur2:

        while alist[cur2] >= mid and cur1 < cur2:
            cur2 -= 1

        alist[cur1] = alist[cur2]

        while alist[cur1] < mid and cur1 < cur2:
            cur1 += 1
        alist[cur2] = alist[cur1]

    alist[cur1] = mid

    quick_sort(alist, start, cur1 - 1)
    quick_sort(alist, cur1 + 1, end)


def select_sort(alist):
    for i in range(len(alist) - 1, 0, -1):
        max_index = 0
        for j in range(i + 1):
            if alist[j] >= alist[max_index]:
                max_index = j

        alist[i], alist[max_index] = alist[max_index], alist[i]


def merge(left, right):
    # sorted list and merge

    cur1 = 0
    cur2 = 0
    sorted_list = []
    while cur1 < len(left) and cur2 < len(right):
        if left[cur1] <= right[cur2]:
            sorted_list.append(left[cur1])
            cur1 += 1
        else:
            sorted_list.append(right[cur2])
            cur2 += 1

    if cur1 == len(left):
        sorted_list += right[cur2:]
    else:
        sorted_list += left[cur1:]
    sorted_list += left[cur1:]
    sorted_list += right[cur2:]


def merge_sort(alist):
    # divide a list into two  list till as one num
    if len(alist) <= 1:
        return alist

    '''
    first divide list end condition is length = 1
    merge list compare first item,till one list end.
    but how to connect above two steps.
    '''
    num = len(alist) // 2
    print("divided num is ", num)
    left = merge_sort(alist[:num])
    right = merge_sort(alist[num:])
    return merge(left, right)


class LinkNode(object):
    def __init__(self, data):
        self.data = data
        self.next = None


class SingleLinkedList(object):

    def __init__(self):
        self.head = None

    def is_empty(self):
        return self.head == None

    def length(self):
        count = 0
        cur = self.head
        while cur != None:
            cur = cur.next
            count += 1
        return count

    def travel(self):

        cur = self.head
        while cur != None:
            print(cur.data)
            cur = cur.next
        return 'HAHA'

    def add(self, data):
        node = LinkNode(data)
        node.next = self.head
        self.head = node

    def append(self, data):
        node = LinkNode(data)
        if self.is_empty():
            self.add(node)
        else:
            cur = self.head
            while cur.next != None:
                cur = cur.next

            cur.next = node
            # node.next = None


class Stack(object):

    def __init__(self):
        self.stack = []

    def is_empty(self):
        return len(self.stack) == 0

    def push(self, data):
        # first in last out
        # add a new item in the top position
        self.stack.append(data)

    def pop(self):
        # remove the top position item
        return self.stack.pop()

    def peek(self):
        # return top stack item
        return self.stack[len(self.stack) - 1]

    def size(self):
        return len(self.stack)


class Queue(object):

    def __init__(self):
        self.items = []

    def is_empty(self):
        return len(self.items) == 0

    def enqueue(self, item):
        self.items.append(item)

        return self.items

    def dequeue(self):
        # FIFO remove head item
        if self.is_empty():
            return
        self.items.pop(0)
        # return self.items.pop(0)
        return self.items

    def size(self):
        return len(self.items)


if __name__ == '__main__':
    alist = [2, 3, 1, 3, 2, 7, 5, 4, 9, 0]
    # alist = [2, 1, 9, 0]
    # bubble_sort(alist)
    # quick_sort(alist,0,len(alist)-1)

    '''
    [2, 9, 9, 9, 9, 9, 9, 9, 9, 9]
    this error reason: not swap the position
    
    [1, 2, 2, 3, 3, 4, 0, 5, 7, 9]
    this error reason:  if you have 3 numbers,you must check all num ,need 3 times compare not 2 times
    and 
    max_index should in the first inner cycle.
    '''
    # select_sort(alist)

    merge_sort(alist)
    print('sort algorithm result-----', alist)

    '''
    implement single link
    '''
    s = SingleLinkedList()
    s.add(3)
    s.add(9)
    s.add(5)
    s.append(10)
    print(s.length())
    print(s.is_empty())
    print(s.travel())

    print('--------------stack--------------')
    stack = Stack()
    print(stack.is_empty())
    stack.push(3)
    stack.push(9)
    stack.push(0)
    print(stack.size())
    print(stack.pop())
    print(stack.peek())
    print(stack.is_empty())

    queue = Queue()

    print(queue.is_empty())
    print(queue.enqueue(3))
    print(queue.enqueue(8))
    print(queue.enqueue(1))

    print(queue.dequeue())
    print(queue.dequeue())
    print(queue.dequeue())
    '''
    1,2,3,4,5,8,9
    3,4,5,6,7
    
    1233445567,89
    
    '''
