Note：近日阅读Pytorch1.4代码，发现与1.0有些差异，而未能找到关于native这些算子的代码解析文章，于是便自己硬看。由于是初次接触，若有错误，还请指出。

# ATEN/native 简介
代码路径：
`pytorch/aten/src/ATEN/native`

区别于 aten/THNN （即TH系列）的库，引用官方文档的话，`native`是：

> ATen "native" functions are the modern mechanism for adding operators and functions to ATen (they are "native" in contrast to legacy functions, which are bound via TH/THC cwrap metadata). Native functions are declared in native_functions.yaml and have implementations defined in one of the cpp files in this directory.

即： `ATEN/native` 下的文件是使用C++实现的`operaters`(或者说"层")

### 特点
- 有C++和python API
    - 在C++中，namespace是 `at::`

## 关于自定义operator：

### 添加operator：
查阅 native 文件夹下的 Readme

### 自定义operator的自动微分
- 如果是使用其它（支持自动微分的）op拼起来的算子，则不需要实现backward函数
- 如果是自己实现的代码，需要实现 foo_backward 并添加至`tools/autograd/derivatives.yaml`

# 以 `activation` 为例：

## `native/Activation.cpp`
我理解这是一个‘入口’，将activation的各个实现包装起来
- hardtanh
- elu & celu & selu & rrelu & prelu
- softplus
- threshold
- hardshrink & softshrink
- 等等

以及上面算子的不同操作形式变体（inplace与否）

### 以 elu 为例

`native/Activation.cpp`定义了如下接口：

- elu : 前向
    - elu_ & elu_out ：inplace elu
- elu_backward : 反向
    - elu_backward_out : inplace

```cpp
Tensor elu(
    const Tensor& self,
    Scalar alpha,
    Scalar scale,
    Scalar input_scale) {
  Tensor result;
  auto iter = TensorIterator::unary_op(result, self);
  elu_stub(iter.device_type(), iter, alpha, scale, input_scale);
  return iter.output();
}
```
前向代码调用的是 `elu_stub`

定义：
- `native/cpu/Activation.cpp`: REGISTER_DISPATCH(elu_stub, &elu_kernel);
- `native/cuda/Activation.cu` : REGISTER_DISPATCH(elu_stub, &elu_kernel);

反向代码也类似，调用注册的 `_backward_stub`
``` cpp
Tensor elu_backward(
    const Tensor& grad_output,
    Scalar alpha,
    Scalar scale,
    Scalar input_scale,
    const Tensor& output) {
  Tensor result;
  auto iter = TensorIterator::binary_op(result, grad_output, output);
  elu_backward_stub(iter.device_type(), iter, alpha, scale, input_scale);
  return iter.output();
}
```

## `native/cpu/Activation.cpp`
该文件是激活函数的cpu代码实现：

```cpp
void elu_kernel(TensorIterator& it, Scalar alpha, Scalar scale, Scalar input_scale) {
  AT_DISPATCH_FLOATING_TYPES(it.dtype(), "elu_cpu", [&]() {
    auto negcoef = alpha.to<scalar_t>() * scale.to<scalar_t>();
    auto poscoef = scale.to<scalar_t>();
    auto negiptcoef = input_scale.to<scalar_t>();
    cpu_kernel(it, [=](scalar_t a) -> scalar_t {
      return a <= scalar_t(0) ? (std::exp(a * negiptcoef) - scalar_t(1)) * negcoef : a * poscoef;
    });
  });
}
```
前向：
- x > 0 : `x*scale`
- x <= 0 : `negcoef*(e^(x*neginputcoef) - 1)`

```cpp
void elu_backward_kernel(TensorIterator& it, Scalar alpha, Scalar scale, Scalar input_scale) {
  AT_DISPATCH_FLOATING_TYPES(it.dtype(), "elu_backward_cpu", [&]() {
    auto negcoef = alpha.to<scalar_t>() * scale.to<scalar_t>();
    auto poscoef = scale.to<scalar_t>();
    auto negiptcoef = input_scale.to<scalar_t>();
    cpu_kernel(it, [=](scalar_t a, scalar_t b) -> scalar_t {
      return b <= scalar_t(0) ? a * negiptcoef * (b + negcoef) : a * poscoef;
    });
  });
}
```
这里有a,b两个参数，分别应该是 grad_output, output

elu的梯度：
- output <= 0 : `grad_output*neginputcoef*output`
- output > 0 :  `output*scale`