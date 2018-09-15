import time
import threading
import queue
import re




text = 'this is shlo and shlo has a house in shlo town city'
#text = 'aösdlkfj öadsjf lasjdfl asdlfk adsf'
m = re.findall('shlo', text)
print(len(m))

print('')

exit()


class SomeWorker(threading.Thread):

    def __init__(self, Name):
        threading.Thread.__init__(self)
        self.Working = True
        self.Worker = Name

    def run(self):
        while self.Working:
            time.sleep(1)
            #print('Worker: ' + self.Worker)


class AWorker(SomeWorker):
    def __init__(self, Name):
        SomeWorker.__init__(self, Name)

    def transfer(self, Paket):
        q.put(Paket)


class BWorker(SomeWorker):
    def __init__(self, Name):
        SomeWorker.__init__(self, Name)

    def run(self):
        while self.Working:
            item = q.get()
            print(item)
            time.sleep(1)

MessageQueue = queue.Queue()

John = AWorker('John')
Peters = BWorker('Peters')
John.start()
Peters.start()

for i in range(10):
    print('send paket: ' + str(i))
    John.transfer('hotshit ' + str(i))

print('Queue: ', q.qsize())

time.sleep(20)


John.Working = False
Peters.Working = False
John.join()
Peters.join()

print('finished')
exit()

for Employee in Employees:
    EmpleyeeList.append(SomeWorker(Employee))

for idx in EmpleyeeList:
    idx.start()

time.sleep(10)

for idx in EmpleyeeList:
    idx.Working = False
