## compile only
g++ -c a.cpp
g++ -c b.cpp
g++ -c c.cpp

## link
g++ -o out a.o b.o

### link的参数

如果没有足够的文件聚合：
```
compiler/linking$ g++ -o out a.o a.o: In function `main':
a.cpp:(.text+0x18): undefined reference to `b_global_int'
collect2: error: ld returned 1 exit status
```

如果没有 main
```
compiler/linking$ g++ -o out b.o 
/usr/lib/gcc/x86_64-linux-gnu/7/../../../x86_64-linux-gnu/Scrt1.o: In function `_start':
(.text+0x20): undefined reference to `main'
collect2: error: ld returned 1 exit status
```

如果.o里面有多个main：
```
compiler/linking$ g++ -o outc c.o b.o  a.o
a.o: In function `main':
a.cpp:(.text+0xb): multiple definition of `main'
c.o:c.cpp:(.text+0x0): first defined here
collect2: error: ld returned 1 exit status
```
## 符号
查看符号：
```
compiler/linking$ nm a.o
0000000000000000 T _Z6a_funcv
                 U b_global_int
000000000000000b T main

compiler/linking$ nm b.o
0000000000000000 T _Z6func_bv
0000000000000004 d _ZZ6func_bvE8b_static
0000000000000000 D b_global_int

compiler/linking$ nm c.o
0000000000000000 B c_global
0000000000000000 T main
```

可以看到 `b_global_int` 出现在了a,b 两个文件中，在b中定义，所以有地址