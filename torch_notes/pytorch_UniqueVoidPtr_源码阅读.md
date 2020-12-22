# UniqueVoidPtr

## 成员变量

```cpp
class UniqueVoidPtr {
 private:
  // Lifetime tied to ctx_
  void* data_;
  std::unique_ptr<void, DeleterFnPtr> ctx_;
```
`UniqueVoidPtr` 包含了 数据指针 data_ 还有 ctx_;

为什么这样设计呢？

代码里的注释是这样写的：

> UniqueVoidPtr solves a common problem for allocators of tensor data, which
is that the data pointer (e.g., float*) which you are interested in, is not
the same as the context pointer (e.g., DLManagedTensor) which you need
to actually deallocate the data.  Under a conventional deleter design, you
have to store extra context in the deleter itself so that you can actually
delete the right thing.  Implementing this with standard C++ is somewhat
error-prone: if you use a std::unique_ptr to manage tensors, the deleter will
not be called if the data pointer is nullptr, which can cause a leak if the
context pointer is non-null (and the deleter is responsible for freeing both
the data pointer and the context pointer)

如果直接使用智能指针 `unique_ptr` 来管理 `tensor`, 则如果 `data_ptr` 为 nullptr，便不会去 delete tensor, 而如果 ctx_ptr 不为空，就造成了内存泄漏

我依然不是很理解为什么要这样设计

#### 成员ctx_

`ctx_` 是一个 `std::unique_ptr` 智能指针管理的类

在构造的时候可以传入 ctx 和 对应的 deleter，默认是 空

```cpp
  UniqueVoidPtr() : data_(nullptr), ctx_(nullptr, &deleteNothing) {}
  explicit UniqueVoidPtr(void* data)
      : data_(data), ctx_(nullptr, &deleteNothing) {}
  UniqueVoidPtr(void* data, void* ctx, DeleterFnPtr ctx_deleter)
      : data_(data), ctx_(ctx, ctx_deleter ? ctx_deleter : &deleteNothing) {}
```


