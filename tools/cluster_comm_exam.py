import os
import subprocess

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP


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
        print(node_list)
        addr = subprocess.getoutput(
            f"scontrol show hostname {node_list} | head -n1")
        # specify master port
        if port is not None:
            os.environ["MASTER_PORT"] = str(port)
        elif "MASTER_PORT" not in os.environ:
            os.environ["MASTER_PORT"] = "20087"
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

def test_allreduce():
    print("start test all_reduce")

    tensor = (torch.ones(10,30)*dist.get_rank()).cuda()
    dist.all_reduce(tensor)
    print(tensor[1][1])
    print("test all_reduce passed")


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
    test_allreduce()
    test_model_ddp()
