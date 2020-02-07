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

### 成员变量
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

### 成员函数