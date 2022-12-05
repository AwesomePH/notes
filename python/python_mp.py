import multiprocessing
from multiprocessing import Pool
from multiprocessing import Process

def f(x, rslt):
    rslt.append(x*x)
    print(rslt)
    return x*x

def test_process_vars():
    rslt=[]
    ps=[]
    for _ in range(3):
        p = Process(target=f, args=(3, rslt))
        p.start()
        ps.append(p)
    for p in ps:
        p.join()
    print("----")
    print(rslt)        # []

def test_process_return():
    rslt=[]
    ps=[]
    for _ in range(3):
        p = Process(target=f, args=(3, rslt))
        p.start()
        ps.append(p)
    for p in ps:
        rslt.append(p.join())
    print("----")
    print(rslt)    # [None, None, None]

def test_process_shared_mem():
    manager = multiprocessing.Manager()
    rslt=manager.list()
    ps=[]
    for i in range(3):
        p = Process(target=f, args=(i, rslt))
        p.start()
        ps.append(p)
    for p in ps:
        p.join()
    print("----")
    print(rslt)
    """
    [0]
    [0, 1]
    [0, 1, 4]
    ----
    [0, 1, 4]
    """

if __name__ == '__main__':
    test_process_shared_mem()
