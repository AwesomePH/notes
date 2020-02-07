# at::Tensor

`TensorBody.h`定义了at::Tensor:
`class CAFFE2_API Tensor`

成员：
- `c10::intrusive_ptr<TensorImpl, UndefinedTensorImpl> impl_;`

## 成员函数（接口）：

访问属性基本是对TensorImpl的包装：
```cpp
int64_t dim() const {
    return impl_->dim();
}
int64_t storage_offset() const {
    return impl_->storage_offset();
}
```

### 重载的operator：
定义在 `ATen/TensorOperators.h` 中

普通操作
```cpp
inline Tensor Tensor::operator-() const {
  return neg();
}
```

inplace操作：
```cpp
inline Tensor& Tensor::operator+=(const Tensor & other) {
  return add_(other);
}
```

这些操作定义在 `ATen/native/UnaryOps.cpp`，比如

```cpp
Tensor neg(const Tensor& self) { return unary_op_impl(self, at::neg_out); }
```
> 关于具体的neg操作有另一篇介绍

