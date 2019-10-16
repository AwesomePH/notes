# PINGPONG设计在异构计算中的一点应用

> 刚刚接触这块不久，被实际案例启发，察觉此方面资料较少，写下自己的体会

## 背景
假设硬件资源有CPU和一个ASIC，CPU会调用ASIC去进行大量的计算，最后获取计算结果

那么整个程序可以分为三步：
1. CPU准备数据
2. CPU Invoke ASIC 程序
3. CPU等待ASIC完成计算，获取结果

整个的程序这样执行是正确的，但是存在一个问题就是，当ASIC在进行大量计算的时候，CPU处于空闲的状态，这样稍微浪费了一点性能（因为毕竟大部分时间还是在ASIC计算上面）

## PINGPONG加速
简单一点就是：在ASIC进行计算的时候，CPU不处于等待的状态，而是先把下一波数据准备好，即进行步骤1和2

## 流水设计

```cpp

Queue queue[2];
Dtype Indata[2];
Dtype Outdata[2];
bool pong_ready=false;
while(true){
    // PING
    if(prepareData(Indata[0]) == false){
        break;  // if no more data, restart
    }
    // PING
    Invoke(queue[0]);
    // PONG
    if(pong_ready){
        Sync(queue[1]);
    }
    // PONG
    if(prepareData(Indata[1]) == false){
        break;  // if no more data, start
    }
    // PONG
    Invoke(queue[1]);
    pong_ready=true;

    // PING: CPU has done all thw work it can do, now wait for ASIC to finish
    Sync(queue[0]);

}
```
这个版本能实现基本的PINGPONG，功能还可以

但是有一点可以改进的地方：
- 如果当前队列没有数据，可以判断一下另一个队列是否Ready to Sync，如果是，那么可以调用Sync

```cpp
Queue queue[2];
Dtype Indata[2];
Dtype Outdata[2];
bool pong_ready=false;
while(true){
    // PING
    if(prepareData(Indata[0]) == false){
        if(pong_ready){
            Sync(queue[1]);
            pong_ready=false;
        }
        break;  // if no more data, restart
    }
    // PING
    Invoke(queue[0]);
    // PONG
    if(pong_ready){
        Sync(queue[1]);
        pong_ready=false;
    }
    // PONG
    if(prepareData(Indata[1]) == false){
        Sync(queue[0]);
        break;  // if no more data, start
    }
    // PONG
    Invoke(queue[1]);
    pong_ready=true;

    // PING: CPU has done all thw work it can do, now wait for ASIC to finish
    Sync(queue[0]);

}
```


