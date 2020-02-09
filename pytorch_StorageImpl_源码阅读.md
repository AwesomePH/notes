# Storage
- 用户：TensorImpl

`Storage` 是对 `StorageImpl` 的包装，其成员变量为：
`c10::intrusive_ptr<StorageImpl> storage_impl_;`

# StorageImpl

## 成员变量

- caffe2::TypeMeta `data_type_`; 数据类型
- DataPtr `data_ptr_`; DataPtr 类型的数据指针
- int64_t `numel_`; 元素数量
- bool `resizable_`; 是否大小可变
- bool `received_cuda_`;
- Allocator* `allocator_`; 负责管理内存，最终依赖不同设备的allocator，比如CPU和Cuda都有自己的内存管理接口

StorageImpl本身没有太多的操作，依赖于 `DataPtr` 和 `Allocator` 做实际的工作

## 构造函数

```cpp
StorageImpl(
      caffe2::TypeMeta data_type,
      int64_t numel,
      at::Allocator* allocator,
      bool resizable)
      : StorageImpl(
            data_type,
            numel,
            allocator->allocate(data_type.itemsize() * numel),
            allocator,
            resizable) {}
```            
上面的构造函数接受 元素个数 & 数据类型，由 allocator->allocate 分配一块内存，返回的数据指针作为 `DataPtr` 传给下面的构造函数

```cpp
  StorageImpl(
      caffe2::TypeMeta data_type,
      int64_t numel,
      at::DataPtr data_ptr,
      at::Allocator* allocator,
      bool resizable)
      : data_type_(data_type),
        data_ptr_(std::move(data_ptr)),
        numel_(numel),
        resizable_(resizable),
        received_cuda_(false),
        allocator_(allocator) {
    if (resizable) {
      需要给定allocator
    }
    if (numel > 0) {
      需要初始化数据类型
      }
    }
  }
```

# Allocator

```cpp
struct C10_API Allocator {
  virtual ~Allocator() = default;

  virtual DataPtr allocate(size_t n) const = 0;
```
`Allocator::allocate`是一个纯虚函数，需要子类定义

CPU allocator：

```cpp
struct C10_API DefaultCPUAllocator final : at::Allocator {
  at::DataPtr allocate(size_t nbytes) const override {
    void* data = alloc_cpu(nbytes);
    if (FLAGS_caffe2_report_cpu_memory_usage && nbytes > 0) {
      getMemoryAllocationReporter().New(data, nbytes);
      return {data, data, &ReportAndDelete, at::Device(at::DeviceType::CPU)};
    }
    return {data, data, &free_cpu, at::Device(at::DeviceType::CPU)};
  }
```

# DataPtr

### 成员变量：

```cpp
class C10_API DataPtr {
 private:
  c10::detail::UniqueVoidPtr ptr_;
  Device device_;
```
其中 UniqueVoidPtr_ 包含了指向数据的指针

### get(), operator->
如果需要访问数据则通过 `UniqueVoidPtr::get()` 得到指针：
```cpp
  void* UniqueVoidPtr::get() const {
    return data_;
  }
```
DataPtr通过 `UniqueVoidPtr::get()`:
```cpp
  void* operator->() const {
    return ptr_.get();
  }
  void clear() {
    ptr_.clear();
  }
  void* get() const {
    return ptr_.get();
  }
```
### 构造
```cpp
  DataPtr() : ptr_(), device_(DeviceType::CPU) {}
  DataPtr(void* data, Device device) : ptr_(data), device_(device) {}
  DataPtr(void* data, void* ctx, DeleterFnPtr ctx_deleter, Device device)
      : ptr_(data, ctx, ctx_deleter), device_(device) {}
```
如果不传入 ctx 相关参数，则 UniqueVoidPtr 里面的 ctx 是void类型的

比较好奇使用的时候会怎样传入参数？

可以看到上面`DefaultCPUAllocator`返回的参数：
`{data, data, &free_cpu, at::Device(at::DeviceType::CPU)}`

也就是说：
- data_ = data
- ctx_ = data
- DeleteFnPtr = free_cpu
- device = at::Device(at::DeviceType::CPU)

ctx = data???