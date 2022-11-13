import ray

@ray.remote
class GlobalVarActor:
    def __init__(self):
        self.global_var = 3
        self.path_cnt=0

    def set_global_var(self, var):
        self.global_var = var

    def get_global_var(self):
        return self.global_var
    
    def inc_path_cnt(self):
        self.path_cnt+=1
        print(f"path_cnt inced to: {self.path_cnt}")
        return self.path_cnt


@ray.remote
class MyActor:
    def __init__(self, global_var_actor):
        self.global_var_actor = global_var_actor
        self.cnt_ref = global_var_actor.inc_path_cnt.remote()

    def f(self):
        print(f"glb_cnt: {ray.get(self.cnt_ref)}")
        return ray.get(self.global_var_actor.get_global_var.remote()) + 3


global_var_actor = GlobalVarActor.remote()
actor = MyActor.remote(global_var_actor)
ray.get(global_var_actor.set_global_var.remote(4))
# This returns 7 correctly.
assert ray.get(actor.f.remote()) == 7
actor2 = MyActor.remote(global_var_actor)
actor3 = MyActor.remote(global_var_actor)
ray.get(actor2.f.remote())
ray.get(actor3.f.remote())

"""
(GlobalVarActor pid=9836) path_cnt inced to: 1
(MyActor pid=9837) glb_cnt: 1
(GlobalVarActor pid=9836) path_cnt inced to: 2
(MyActor pid=10243) glb_cnt: 2
(GlobalVarActor pid=9836) path_cnt inced to: 3
(MyActor pid=10245) glb_cnt: 3
"""