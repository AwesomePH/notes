# TensorIterator的使用


在实现一些基本的 binary&unary op 的时候，常常以iterator作为参数传入`stub`

binary op：
- 输入a,b
- 输出 out
```cpp
TensorIterator TensorIterator::binary_op(Tensor& out, const Tensor& a,
    const Tensor& b, bool check_mem_overlap) {
  auto iter = TensorIterator();
  iter.set_check_mem_overlap(check_mem_overlap);
  iter.add_output(out);
  iter.add_input(a);
  iter.add_input(b);
  iter.allow_cpu_scalars_ = true;
  iter.promote_common_dtype();
  iter.build();
  return iter;
}
```
unary op：
- 输入a
- 输出 out
```cpp
TensorIterator TensorIterator::unary_op(Tensor& out, const Tensor& a,
    bool check_mem_overlap) {
  auto iter = TensorIterator();
  iter.set_check_mem_overlap(check_mem_overlap);
  iter.add_output(out);
  iter.add_input(a);
  iter.num_outputs_ = 1;
  iter.build();
  return iter;
}
```
Iterator的使用者：

```cpp
static void neg_kernel(TensorIterator& iter) {
  AT_DISPATCH_ALL_TYPES_AND_COMPLEX(iter.dtype(), "neg_cpu", [&]() {
    cpu_kernel_vec(
        iter,
        [=](scalar_t a) -> scalar_t { return -a; },
        [=](Vec256<scalar_t> a) { return a.neg(); });
  });
}

template <typename func_t, typename vec_func_t>
void cpu_kernel_vec(TensorIterator& iter, func_t&& op, vec_func_t&& vop) {
  using traits = function_traits<func_t>;
  TORCH_INTERNAL_ASSERT(iter.ntensors() >= traits::arity + 1);

  iter.for_each([&](char** data, const int64_t* strides, int64_t n) {
    if (is_contiguous<traits>(strides)) {
      return vectorized_loop(data, n, 0, std::forward<func_t>(op), std::forward<vec_func_t>(vop));
    } else {
      using Indices = std::make_index_sequence<traits::arity>;
      unroll_contiguous_scalar_checks<traits>(strides, Indices{}, [&](size_t idx) {
        if (idx) {
          vectorized_loop(data, n, idx, std::forward<func_t>(op), std::forward<vec_func_t>(vop));
        } else {
          basic_loop(data, strides, 0, n, std::forward<func_t>(op));
        }
      });
    }
  });
  iter.cast_outputs();
}
```
这个。。也包的太深了