class Node(object):
    def __init__(self, data):
        self.data = data
        self.next = None
        self.pre = None


class DoubleLinkList(object):

    def __init__(self):
        self.__head = None

    def is_empty(self):
        return self.__head is None

    def length(self):
        cur = self.__head
        count = 0
        while cur is not None:
            count += 1
            cur = cur.next

        return count

    def travel(self):
        cur = self.__head
        while cur is not None:
            print(cur.data)
            cur = cur.next

    def add(self, data):
        node = Node(data)

        if self.is_empty():
            self.__head = node

        else:
            node.next = self.__head
            self.__head.pre = node

            self.__head = node

    def append(self, data):

        node = Node(data)
        if self.is_empty():
            self.__head = node
        else:
            cur = self.__head
            while cur.next is not None:
                cur = cur.next

            cur.next = node
            node.pre = cur

    def insert(self,index,data):
        # 插入。根据index 进行分类。
        if index <=0:
            self.add(data)
        elif index > self.length()-1:
            self.append(data)

        else:
            # 找到index 的前一个位置
            node = Node(data)
            cur = self.__head
            count = 0
            while count<index-1:
                cur = cur.next
                count+=1

            # 自己的顺序  先处理 node 和 node后面的 节点的双向连接。
            # node.next = cur.next
            # cur.next.pre = node

            # 再处理node 前面节点和node节点的双向连接。
            # cur.next = node
            # node.pre = cur

            # 简单点的顺序为
            # 1. 先处理Node 节点   处理pre  next
            node.pre = cur
            node.next = cur.next
            # 2. 再处理 node 后面节点的 pre  然后处理 node 前面节点的 next
            cur.next.pre = node
            cur.next = node

    def delete(self,index):
        if index<0:
            raise Exception('位置小于0')

        elif index ==0:
            self.__head = self.__head.next

        elif index > self.length()-1:
            raise Exception('超出链表长度')

        else:

            # 找到index 本来的位置
            cur = self.__head
            count = 0
            while count<index:
                count+=1
                cur = cur.next
            cur.pre.next = cur.next
            cur.next.pre = cur.pre




if __name__ == '__main__':
    dll = DoubleLinkList()

    print('是否为空 ', dll.is_empty())
    dll.add(1)
    dll.add(2)
    dll.add(3)
    dll.append(4)
    print('是否为空 ', dll.is_empty())
    print('length is ', dll.length())
    dll.travel()

    print('-------------')
    dll.insert(3,9)
    dll.travel()

    print('-----***********--------')
    dll.delete(3)
    dll.travel()