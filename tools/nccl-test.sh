#!/bin/bash
#SBATCH --job-name=nccl_test
#SBATCH --nodes=2
#SBATCH --ntasks=16
#SBATCH --gres=gpu:8
#SBATCH --ntasks-per-node=8


## -m set the minimum and maximum message length to be used in a benchmark. (bytes) min:max: to test the latency for a given data size, set min=max
## -M set per process maximum memory consumption (bytes)
## -f report additional statistics of the benchmark, such as min and max latencies and the number of iterations.
## -i can be used to set the number of iterations to run for each message length.
## -d TYPE accelerator device buffers can be of TYPE `cuda' or `openacc'


mpirun -np 16 ./build/all_reduce_perf -b 256M  -e 256M -f 2 -g 1 -n 40
