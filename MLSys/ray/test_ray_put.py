import time

import torch
import torch.nn as nn
import uniscale
from uniscale._internal.rpc import _get, _put

# from uniscale.apis.storage import set_async


def ray_perf(nums, param, ray_address=None):
    print("Ray")
    if ray_address:
        uniscale.init(ray_address=ray_address)
    else:
        uniscale.init()
    ref_ray = []
    # params = []
    # for _ in range(nums):
    #     params.append(param)
    time_start_put = time.time()
    # ref_ray = _put(params)
    for _ in range(nums):
        ref = _put(param)
        ref_ray.append(ref)
    for ref in ref_ray:
        obj=uniscale.get(ref)
    ray_put_time = time.time() - time_start_put
    uniscale.shutdown()
    print("Ray put time:{}".format(ray_put_time))


def multi_node_transer_ref(nums, param, ray_address=None):
    print("Pure bucketmanager")
    if ray_address:
        uniscale.init(ray_address=ray_address)
    else:
        uniscale.init()
    ref_ray = []
    time_start_put = time.time()
    for _ in range(nums):
        ref = uniscale.put(param)
        ref_ray.append(ref)
    for ref in ref_ray:
        obj=uniscale.get(ref)

    pure_bm_time = time.time() - time_start_put
    uniscale.shutdown()
    print("multi_node_transer_ref put time:{}".format(pure_bm_time))


def multi_node_transer_ref_async(nums, param, ray_address=None):
    print("Async bucketmanager actor")
    if ray_address:
        uniscale.init(ray_address=ray_address)
    else:
        uniscale.init()
    key_uniscale = []
    params = []
    for _ in range(nums):
        params.append(param)

    time_start_put = time.time()
    key_uniscale = uniscale.put(params)
    obj=uniscale.get(key_uniscale)
    async_bm_time = time.time() - time_start_put

    uniscale.shutdown()
    print("multi_node_transer_ref_async put time:{}".format(async_bm_time))


if __name__ == "__main__":
    nums = 1
    param = nn.Parameter(torch.rand(1024, 4096, 10), requires_grad=False)
    # "ray://10.140.0.73:10001"
    ray_perf(nums, param)
    ray_perf(nums, param, ray_address="ray://10.140.1.17:10001")
    # multi_node_transer_ref(nums, param)
    multi_node_transer_ref_async(nums, param)
    # multi_node_transer_ref_async(nums, param, ray_address="ray://10.140.0.73:10001")
