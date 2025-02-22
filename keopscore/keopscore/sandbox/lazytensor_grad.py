# Test for gaussian kernel operation using LazyTensors.

import time

import math
import torch
from pykeops.torch import LazyTensor

M, N, D, DV = 1000, 1000, 3, 1

dtype = torch.float32

test_grad = True
test_grad2 = False
device_id = "cuda:0" if torch.cuda.is_available() else "cpu"

x = torch.rand(M, 1, D, requires_grad=test_grad, device=device_id, dtype=dtype)
y = torch.rand(1, N, 1, device=device_id, dtype=dtype)
b = torch.randn(N, DV, device=device_id, dtype=dtype)


def fun(x, y, b, backend):
    if "keops" in backend:
        x = LazyTensor(x)
        y = LazyTensor(y)
    # Kxy = ((x - 0.5).mod(1, 0.2) - y).sum(dim=2)
    Kxy = (x.cos() - y).sum(dim=2)
    out = Kxy @ b
    if device_id != "cpu":
        torch.cuda.synchronize()
    # print("out:",out.flatten()[:10])
    return out


backends = ["keops", "torch"]  # "keops_old"

out = []
for backend in backends:
    start = time.time()
    out.append(fun(x, y, b, backend).squeeze())
    end = time.time()
    print("time for " + backend + ":", end - start)

if len(out) > 1:
    print("relative error:", (torch.norm(out[0] - out[1]) / torch.norm(out[0])).item())

if test_grad:
    out_g = []
    for k, backend in enumerate(backends):
        start = time.time()
        out_g.append(
            torch.autograd.grad((out[k] ** 2).sum(), [x], create_graph=True)[0]
        )
        end = time.time()
        print("time for " + backend + " (grad):", end - start)

    if len(out_g) > 1:
        print(
            "relative error grad:",
            (torch.norm(out_g[0] - out_g[1]) / torch.norm(out_g[0])).item(),
        )
        # print(
        #    "absolute error grad:",
        #    (torch.norm(out_g[0] - out_g[1])).item(),
        # )

if test_grad2:
    out_g2 = []
    for k, backend in enumerate(backends):
        start = time.time()
        out_g2.append(torch.autograd.grad((out_g[k] ** 2).sum(), [x])[0])
        end = time.time()
        print("time for " + backend + " (grad):", end - start)

    if len(out_g2) > 1:
        print(
            "relative error grad:",
            (torch.norm(out_g2[0] - out_g2[1]) / torch.norm(out_g2[0])).item(),
        )

    if len(out_g) > 1:
        print(
            "relative error grad:",
            (torch.norm(out_g[0] - out_g[1]) / torch.norm(out_g[0])).item(),
        )
