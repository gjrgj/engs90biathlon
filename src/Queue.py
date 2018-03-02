class Queue(object):
    def __init__(self, queue=None):
        if queue is None:
            self.queue = []
        else:
            self.queue = list(queue)
    def get(self):
        return self.queue.pop(0)
    def put(self, element):
        self.queue.append(element)
    def empty(self):
        if len(self.queue) == 0:
            return True
        else:
            return False
    def size(self):
        return len(self.queue)