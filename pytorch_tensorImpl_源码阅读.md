# 文档介绍
`c10::TensorImpl` 是对Tensor的底层表示，包含了 
- 指向`Storage/StorageImpl`的指针
    - 允许多个Tensor指向同一块内存，但是可以有不同的`view`
- metadata-元数据，是Tensor **view-specific** 的内容 ，view-specific 是指这个Tensor独有的`view`，即如何去“看”（访问）这块内存
    - sizes
    - strides
    - offset
    - ...

#### 侵入式计数的
作用：
- Tensor内存的释放
- 对原始指针进行引用计数操作，在跨语言使用时方便

#### 未初始化状态
- 内存未初始化
    - 表现：storage是空指针
    - 通常出现在 Resize() FreeMemory() 之后
    - 原因：caffe2采用的是 lazy内存分配：使用时（即调用 `mutable_data<T>()` ） 才分配

- 数据类型未初始化
    - 通常如果构造的时候没有指明，则直到 `mutable_data<T>()` 调用时才初始化

##### TIP! 未初始化的内存不能share
> Most functions are not designed to work if given a storage-UNINITIALIZED, dtype-UNINITIALIZED tensor.

# 代码

## TensorImpl定义
`struct C10_API TensorImpl : public c10::intrusive_ptr_target`

继承自 `intrusive_ptr_target` 即实现了 “侵入式计数”

## 成员变量
- Storage `storage_`;
- std::unique_ptr<c10::AutogradMetaInterface> `autograd_meta_`
- SmallVector<int64_t,5> `sizes_`;
- SmallVector<int64_t,5> `strides_`;
- int64_t `storage_offset_`
- PyObject* `pyobj_`
    - 一个表示这个tensor的PyObject的弱引用(weak reference)
- int64_t `numel_` = 1
- caffe2::TypeMeta `data_type_`
    - 当storage不为空时，这里应该和 storage 的 dtype 相同
- bool `is_contiguous_` = true
- bool `is_channels_last_`
    - 这个属性有待研究
- bool `is_channels_last_contiguous_`
- bool `allow_tensor_metadata_change_`
    - 调用 `t1_detached = t1.detach()` 之后，不允许改变元数据（无意义）

#### 成员变量定义的顺序：影响内存
由于Tensor会在代码中出现很多个，所以Tensor的大小对于系统内存占用可能产生很大的影响。

## 成员函数

### 构造函数 & operator=
这两个接口都可以从另一个对象进行创建，但是TensorImpl做了限制：
- 不能复制另一个非临时的TensorImpl

```cpp
TensorImpl(const TensorImpl&) = delete;
```
可以从右值进行复制构造
```cpp
TensorImpl(TensorImpl&&) = default;
```

赋值运算符：

赋值运算符的语义要考虑增加refcount，所以我理解不能从右值进行赋值？
```cpp
TensorImpl& operator=(const TensorImpl&) = delete;
TensorImpl& operator=(TensorImpl&&) = default;
```

### 判断内存是否连续

##### stride
要先理解 `strides_`, 简单来说它表示：
`某一维的两个相邻元素之间的距离`

举个例子：

```
t=torch.randn(2,3,4)

t:
tensor([[[-0.1764, -0.2497, -0.0716, -0.3136],
         [ 0.4080, -0.3170,  2.1451, -0.0537],
         [ 0.4694,  0.0412,  1.3702, -1.2787]],

        [[-0.0882,  1.0424,  1.8374,  0.3812],
         [ 0.8166, -0.0772,  0.9059, -2.2847],
         [ 1.2406,  0.5354, -0.8181, -0.8614]]])

t.flatten():
tensor([-0.1764, -0.2497, -0.0716, -0.3136,  0.4080, -0.3170,  2.1451, -0.0537, 0.4694,  0.0412,  1.3702, -1.2787, -0.0882,  1.0424,  1.8374,  0.3812, 0.8166, -0.0772,  0.9059, -2.2847,  1.2406,  0.5354, -0.8181, -0.8614])
```
则：
- 第0维，t[0][0][0] 和 t[1][0][0] 相差 12
- 第1维，t[0][0][0] 和 t[0][1][0] 相差 4
- 第2维，t[0][0][0] 和 t[1][0][1] 相差 1

##### 连续性判断
如果内存中元素是连续的，也就是说内存中元素的摆放就是按照**行优先**展开的，那么 `stride` 应该满足：
```
stride[i] = stride[i+1] * size[i+1]
```
下面的代码计算内存是否连续：(`compute_channels_last_contiguous`类似)
```cpp
bool TensorImpl::compute_contiguous() const {
  bool is_contiguous = true;
  if (is_empty())
    return is_contiguous;
  int64_t z = 1;
  for (int64_t d = dim() - 1; d >= 0; d--) {
    if (sizes_[d] != 1) {
      if (strides_[d] == z) {
        z *= sizes_[d];
      } else {
        is_contiguous = false;
        break;
      }
    }
  }
  return is_contiguous;
}
```
即从最低维度开始判断，需要满足
```
strides_[n-1] = 1
strides_[n-2] = size[n-1]
strides_[n-3] = size[n-1]*size[n-2]
...
```

### 改变metadata之 dim,size,strides
`resize_dim`
改变维度数
```cpp
  virtual void resize_dim(int64_t ndim) {
    TORCH_CHECK(allow_tensor_metadata_change(), "resize_dim ", err_msg_tensor_metadata_change_not_allowed);
    sizes_.resize(ndim, 0);
    strides_.resize(ndim, 0);
    refresh_numel();
    refresh_contiguous();
  }
```
这里的resize需要注意是C10::SmallVector的方法：
```cpp
void resize(size_type N, const T& NV) {
if (N < this->size()) {
    this->destroy_range(this->begin() + N, this->end());
    this->setEnd(this->begin() + N);
} else if (N > this->size()) {
    if (this->capacity() < N)
    this->grow(N);
    std::uninitialized_fill(this->end(), this->begin() + N, NV);
    this->setEnd(this->begin() + N);
}
}
```
也就是说，resize到新的长度，并把多出来的部分填充为给定的参数（上面给的是0）

所以`resize_dim`如果多出了维度，则新的维度的size和stride默认是0

所以后面一般需要设置新的size和stride

而类似的还有 set_size & set_stride，因此建议使用统一的接口，以免出错：

### set_sizes_and_strides
```cpp
  /**
   * Set the sizes and strides of a tensor.
   *
   * WARNING: This function does not check if the requested
   * sizes/strides are in bounds for the storage that is allocated;
   * this is the responsibility of the caller
   */
  void set_sizes_and_strides(IntArrayRef new_size, IntArrayRef new_stride) {
    TORCH_CHECK(allow_tensor_metadata_change(), "set_sizes_and_strides ", err_msg_tensor_metadata_change_not_allowed);
    TORCH_CHECK(
        new_size.size() == new_stride.size(),
        "dimensionality of sizes (",
        new_size.size(),
        ") must match dimensionality of strides (",
        new_stride.size(),
        ")");
    auto new_dim = new_size.size();

    sizes_.resize(new_dim);
    for (size_t dim = 0; dim < new_dim; ++dim) {
      sizes_[dim] = new_size[dim];
    }

    strides_.resize(new_dim);
    if (new_dim > 0) {
      for (size_t dim = new_dim - 1; ; dim--) {
        if (new_stride[dim] >= 0) {
          strides_[dim] = new_stride[dim];
        } else {
          // XXX: This behavior is surprising and may need to be removed to
          // support negative strides. Some pytorch functions rely on it:
          // for example, torch.cat (run TestTorch.test_cat_empty).
          if (dim == new_dim - 1) {
            strides_[dim] = 1;
          } else {
            // Keep stride monotonically increasing to match NumPy.
            strides_[dim] = std::max<int64_t>(sizes_[dim + 1], 1) * strides_[dim + 1];
          }
        }
        if (dim == 0) break;
      }
    }

    refresh_numel();
    refresh_contiguous();
  }
```
可以总结为如下几个步骤：
- 赋值sizes
- 赋值strides，其中有兼容strides=-1的用法
- 刷新 numel 和 contiguous 的计算

### Resize
`SetDimsTemplate`: 接受`Resize(2, 2)` & `Resize({2,2})` 两种传参方式

作用：设置`sizes_`属性，重新计算 numel_, strides_
```cpp
  template <
      typename T,
      typename = typename std::enable_if<std::is_integral<T>::value>::type>
  bool SetDimsTemplate(ArrayRef<T> src) {
    auto old_numel = numel_;
    sizes_.resize(src.size());
    int64_t new_numel = 1;
    for (size_t i = 0; i < src.size(); ++i) {
      new_numel *= src[i];
      sizes_[i] = src[i];
    }
    numel_ = new_numel;
    empty_tensor_restride(MemoryFormat::Contiguous);
    return numel_ != old_numel;
  }
```
返回值：如果`numel_`改变了，则返回true

`Resize`: 
- 设置新的size，并判断大小是否变化，大小变化之后要判断是否释放内存(分配内存则是lazy模式)
    - 如果变化：
        - 如果有 `reserved_`，则 仅在 `capacity < numel_` 的情况下 `FreeMemory()`
        - 如果没有 `reserved_`，则在以下两种情况下`FreeMemory()`:
            - 已经分配的内存小
            - capacity不够大 || `FLAGS_caffe2_keep_on_shrink!=true` || 缩小的值大于 `FLAGS_caffe2_max_keep_on_shrink_memory`
```cpp
  template <typename... Ts>
  void Resize(Ts... dim_source) {
    bool size_changed = SetDims(dim_source...);
    if (size_changed) {
      // If needed, we will free the data. the next mutable_data() call
      // will create the data storage.
      bool reset_tensor = false;
      if (reserved_) {
        // If tensor is reserved then don't claim its memeory unless capacity()
        // is smaller than new size
        reset_tensor = storage_.capacity() < (storage_offset_ + numel_) * storage_.itemsize();
      } else {
        reset_tensor = storage_.capacity() <
                (storage_offset_ + numel_) * storage_.itemsize() ||
            !FLAGS_caffe2_keep_on_shrink ||
            storage_.capacity() -
                    (storage_offset_ + numel_) * storage_.itemsize() >
                static_cast<size_t>(FLAGS_caffe2_max_keep_on_shrink_memory);
      }

      if (reset_tensor && storage_initialized()) {
        FreeMemory();
      }
    }
  }
```
### `Reshape`:不改变numel
和`resize`的区别：不改变内存，元素总数一致，仅改变 `sizes_` 成员

在改变 sizes_ 成员之后，调用 `empty_tensor_restride` 接口，重新计算stride

#### empty_tensor_restride
注意：这个接口只对如下内存格式有效，就是重新计算stride
- Contigous
- ChannelsLast


### TensorImpl的浅拷贝
用途：
- 两个`Variable`有相同的 tensor metadata, 但 autograd history 不一样

例子：
> 1. `var_detached = var.detach()` uses `shallow_copy_and_detach()` to create `var_detached` that shares the same tensor metadata with `var`, but with a completely new autograd history.
> 2. `var.set_data(tensor)` uses `shallow_copy_from()` to copy tensor metadata from `tensor` into `var`, while keeping `var`'s original AutogradMeta.

浅拷贝发生的动作：
- 拷贝 metadata 部分 ( size, strides, storage, ...)，copy之后两Tensor除了共享一个storage，互不影响
- 不拷贝 Autograd Metadata
- 不拷贝 Version Counter

在`shallow_copy_and_detach` & `copy_tensor_metadata` 中，传入参数 `allow_tensor_metadata_change` 来决定是否允许浅拷贝的impl改变自身（src）的 metadata
```cpp
  virtual c10::intrusive_ptr<TensorImpl> shallow_copy_and_detach(
      const c10::VariableVersion& version_counter,
      bool allow_tensor_metadata_change) const {
    auto impl = c10::make_intrusive<TensorImpl>(Storage(storage()), key_set_);
    copy_tensor_metadata(
      /*src_impl=*/this,
      /*dest_impl=*/impl.get(),
      /*version_counter=*/version_counter,
      /*allow_tensor_metadata_change=*/allow_tensor_metadata_change);
    impl->refresh_numel();
    impl->refresh_contiguous();
    return impl;
  }
```

在`shallow_copy_from`中，是否能够改变metadata是dest impl自己的成员决定的；

主要是考虑其用途：`var.set_data(tensor)`，这种情况下，var 是需要自己的metadata改变的，因此不需要check
```cpp
  virtual void shallow_copy_from(const c10::intrusive_ptr<TensorImpl>& impl) {
    copy_tensor_metadata(
      /*src_impl=*/impl.get(),
      /*dest_impl=*/this,
      /*version_counter=*/version_counter(),
      /*allow_tensor_metadata_change=*/allow_tensor_metadata_change());
    refresh_numel();
    refresh_contiguous();
  }
```

## channels_last 存储
注释里的解释：
> Tensor is stored in the channels last memory format, when dimensions
order is NCHW and C-strides < W-strides < H-strides < N-strides
(If size of any dimension is equal to 1, this dimension strides value
is not taken into account)

当channel这一维的stride最小的时候，将 channel 这一维存储在最里面？

看看对于`channels_last`存储方式的连续性判断：

```cpp
bool TensorImpl::compute_channels_last_contiguous() const {
  if (sizes_.size() == 4) {
    int64_t expected = 1;
    for (auto& d : {1, 3, 2, 0}) {
      if (sizes_[d] != 1) {
        if (strides_[d] == expected) {
          expected *= sizes_[d];
        } else {
          return false;
        }
      }
    }
    return true;
  }
  return false;
}
```
普通的是从n-1,n-2,..,0这样的顺序判断，而C维在最后的时候，就是从C维开始判断，所以顺序是 3,2,1,0 -> 1,3,2,0