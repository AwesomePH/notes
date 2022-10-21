import ray


def func():
    print(ray.get_runtime_context().job_id)
    print(ray.get_runtime_context().node_id)
    print(str(ray._private.services.get_node_ip_address()))
    # print(f"----start train func: rank: {dist.get_rank()}/{dist.get_world_size()} ---" + msg)

    # print(ray.get_node_id())

ray.init()
ray.remote(func).remote()
print('....')
ray.remote(func).remote()
