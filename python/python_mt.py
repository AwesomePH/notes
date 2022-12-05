from threading import Thread,Lock
import random

class Path:
    def reset():
        Path.counter=0
    def __init__(self) -> None:
        lock = Lock()

        lock.acquire()          # 这里有读+写两步操作，所以可能会冲突
        self.id=Path.counter
        Path.counter+=1
        lock.release()

        self.val=random.random()

    def __str__(self) -> str:
        return f"id: {self.id}, val: {self.val}"

def sample_path(child_ind, results):
    child = Path()
    print("child ind: ", child_ind)
    results[child_ind]=child

def func():
    Path.reset()
    paths=[]
    paths_dict = {}             # 这里作为线程的输入，为什么不会冲突--因为cpython的dict操作是原子的，虽然也许不应该依赖
    child_num = 80
    threads = []
    for child_ind in range(child_num):
        threads.append(Thread(target=sample_path, args=[child_ind, paths_dict]))
        threads[-1].start()
    for t in threads:
        t.join()
    for i in range(child_num):
        print(paths_dict[i])

func()