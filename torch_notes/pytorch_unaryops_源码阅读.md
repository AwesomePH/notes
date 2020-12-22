`unaryops`定义了一系列unary操作，比如neg,sqrt,squar...

需要清楚的是，unary操作只有一个操作数，比如neg就是取负数的意思

详细看一下是如何包装&实现的：

# 以neg为例
```cpp
Tensor neg(const Tensor& self) { return unary_op_impl(self, at::neg_out); }
```
调用 unary_op_impl：

```cpp
template <typename OutImpl>
static inline Tensor unary_op_impl(const Tensor& self, OutImpl& out_impl) {
  Tensor result = at::empty({0}, self.options());
  return out_impl(result, self);
}
```
其返回的值是 `out_impl` 所返回的内容

而 `out_impl` 是 `at::neg_out`

也就是说，上面实际调用的是：

`at::neg_out(result, self)`

at::neg_out即：

完成动作： `result = - self`
```cpp
Tensor& neg_out(Tensor& result, const Tensor& self) {
  TORCH_CHECK(self.scalar_type() != kBool,
              "Negation, the `-` operator, on a bool tensor is not supported. "
              "If you are trying to invert a mask, use the `~` or `logical_not()` operator instead.");
  return unary_op_impl_out(result, self, neg_stub);
}
```
其返回的是 `unary_op_impl_out` 返回值

实际调用unary_op_impl_out，参数为 `neg_stub`:
回忆之前，`stub`接口分为cpu和cuda版本，这里同样是通过不同版本的实现来注册的

那么其实这个stub如何去实现就是不同设备之间的区别了，具体实现也就是更加细节的内容，这里不深究

#### neg_stub
实现：ATen/native/cpu/UnaryOpKernels.cpp

```cpp
REGISTER_DISPATCH(neg_stub, &neg_kernel);

static void neg_kernel(TensorIterator& iter) {
  AT_DISPATCH_ALL_TYPES_AND_COMPLEX(iter.dtype(), "neg_cpu", [&]() {
    cpu_kernel_vec(
        iter,
        [=](scalar_t a) -> scalar_t { return -a; },
        [=](Vec256<scalar_t> a) { return a.neg(); });
  });
}
```
这里 `cpu_kernel_vec` 是一个wrapper，负责对iter执行后面两个func，所以func是实际的内容（这里包的层次太多，是挺精妙，但是这种算法只对cpu有效）

上面传入的func
- scalar 就直接返回 -a
- 是向量就调用向量的算法 `Vec256::neg()`

#### unary_op_impl_out
```cpp
template <typename Stub>
static inline Tensor& unary_op_impl_out(Tensor& result, const Tensor& self, Stub& stub) {
  auto iter = TensorIterator::unary_op(result, self,
    /*check_mem_overlap=*/true);
  stub(iter.device_type(), iter);
  return result;
}
```
`unary_op_impl_out` 返回值 是其接受的第一个参数 `result`

回溯到最上面，返回值就是 `unary_op_impl(self,...)` 所传入的 `self`，契合 `unary_op`的含义，即对自己进行操作