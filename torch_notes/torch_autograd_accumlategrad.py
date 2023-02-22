import torch

import math

a = torch.linspace(0., 2. * math.pi, steps=25, requires_grad=True)
print(a)


b = torch.sin(a)
c=a+1
d=c*2

print(b)

print(b.grad_fn)                        # <SinBackward0 object at 0x7f8f3d76be20>
print(b.grad_fn.next_functions)         # ((<AccumulateGrad object at 0x7fb4d1163730>>, 0),)
print(b.grad_fn.next_functions[0][0].next_functions)    # ()

print(d.grad_fn)                        # <MulBackward0 object at 0x7f3a8eea2e20>
print(d.grad_fn.next_functions)         # ((<AddBackward0 object at 0x7f3a8eea2dc0>, 0), (None, 0))
print(d.grad_fn.next_functions[0][0].next_functions)    # ((<AccumulateGrad object at 0x7fb4d1137100>, 0), (None, 0))

