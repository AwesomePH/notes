import os
import subprocess

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
import time

def setup_distributed(backend="nccl", fn=None, port=None):
    """Initialize distributed training environment.
    support both slurm and torch.distributed.launch
    see torch.distributed.init_process_group() for more details
    """
    num_gpus = torch.cuda.device_count()

    if "SLURM_JOB_ID" in os.environ:
        rank = int(os.environ["SLURM_PROCID"])
        world_size = int(os.environ["SLURM_NTASKS"])
        node_list = os.environ["SLURM_NODELIST"]
        # if dist.get_rank()==0:
        # print(node_list)
        addr = subprocess.getoutput(
            f"scontrol show hostname {node_list} | head -n1")
        # specify master port
        if port is not None:
            os.environ["MASTER_PORT"] = str(port)
        elif "MASTER_PORT" not in os.environ:
            os.environ["MASTER_PORT"] = "39087"
        if "MASTER_ADDR" not in os.environ:
            os.environ["MASTER_ADDR"] = addr
        os.environ["WORLD_SIZE"] = str(world_size)
        os.environ["LOCAL_RANK"] = str(rank % num_gpus)
        os.environ["RANK"] = str(rank)
    else:
        rank = int(os.environ["RANK"])
        world_size = int(os.environ["WORLD_SIZE"])

    torch.cuda.set_device(rank % num_gpus)
    # if dist.get_rank()==0:
    print(f"world_size:{world_size}")

    dist.init_process_group(
        backend=backend,
        world_size=world_size,
        rank=rank,
    )

def train_func():
    op=torch.nn.Linear(2048, 2048).cuda()
    input = (torch.randn(2048)*1.5).cuda()
    s1=torch.cuda.Stream()
    with torch.cuda.stream(s1):
        for _ in range(100):
            input=op(input)


def test_allreduce():
    # print("start test all_reduce")

    ele_num = int(158*1e6)
    tensor = torch.randn(ele_num).half().cuda()
    dist.all_reduce(tensor)
    # print(tensor[1][1])
    dist.barrier()
    # print("test all_reduce passed")
    train_func()
    for num_repeat in [1, 5]:
        dist.barrier()
        beg=time.time()
        s1=torch.cuda.Stream()
        with torch.cuda.stream(s1):
            for _ in range(num_repeat):
                dist.all_reduce(tensor)
        dist.barrier()
        time_avg = (time.time()-beg)/num_repeat
        bw = (tensor.numel()*2/1e6)/time_avg # MB/s

        if dist.get_rank()==0:
            print(f"all_reduce repeat={num_repeat}, bandwidth:{bw} time_avg:{time_avg}, numel={tensor.numel()}")

def test_allgather(ele_num):
    # print("start test all_gather")

    # ele_num = int(403233088)
    tensor = torch.randn(ele_num).half().cuda()
    tensor_list = [torch.randn(ele_num).half().cuda() for _ in range(dist.get_world_size())]
    dist.all_gather(tensor_list, tensor)
    # print(tensor[1][1])
    dist.barrier()
    torch.cuda.synchronize()
    # train_func()
    bw=0
    for num_repeat in [1]:
        dist.barrier()
        torch.cuda.synchronize()
        beg=time.time()
        # s1=torch.cuda.Stream()
        # with torch.cuda.stream(s1):
        for _ in range(num_repeat):
            dist.all_gather(tensor_list, tensor)
        dist.barrier()
        torch.cuda.synchronize()
        time_avg = (time.time()-beg)/num_repeat
        bw = (tensor.numel()*2/1e6)/time_avg # MB/s

        if dist.get_rank()==0:
            print(f"all_gather repeat={num_repeat}, bandwidth:{bw} time_avg:{time_avg}, numel={tensor.numel()}")

    torch.cuda.synchronize()
    return bw




def test_model_ddp():
    print("start test ddp model")
    model=torch.nn.Conv2d(16, 33, 3, stride=2)
    model.cuda()
    inputs = torch.randn(20, 16, 50, 100).cuda()
    print(inputs.device, dist.get_rank(), dist.get_world_size())
    ddp_model=DDP(model)
    out=ddp_model(inputs)
    assert out is not None
    print("test ddp model passed")

if __name__=="__main__":
    setup_distributed()
    print("done setup")
    # test_allreduce()
    # test_allgather(403233088)
    test_allgather(12601034)
    test_allgather(25202068)
    test_allgather(50404136)
    test_allgather(100808272)
    test_allgather(201616544)
    # test_allgather(67205514)
    # test_allgather(67205512)
    # test_allgather(33602756)

    # base = 1048576
    # for n in [1,2,4,8,16,32,64,128,256,512,1024]:
    #     num=int(base*n)
    #     bw = test_allgather(num)
    #     if dist.get_rank()==0:
    #         print(n, bw)
    # test_model_ddp()
