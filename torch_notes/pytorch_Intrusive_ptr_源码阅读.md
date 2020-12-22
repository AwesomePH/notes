# note
在前面Tensor,TensorImpl等代码中已经多次看到了 `intrusive_ptr` 的使用，比如：

```cpp
class CAFFE2_API Tensor {
    c10::intrusive_ptr<TensorImpl, UndefinedTensorImpl> impl_;
    ...
}
```
Tensor类的成员 impl_ 是一个 TensorImpl 类型的智能指针

而TensorImpl则是继承自 `intrusive_ptr_target` 类

他们是如何实现自动计数的呢？

# 文档介绍
`intrusive_ptr<T>` 比 `shared_ptr<T>` 有更好的性能，因为前者是侵入式计数

从`intrusive_ptr_target` 继承的类可以支持 `intrusive_ptr<T>` 用法

# intrusive_ptr_target 类

## 类成员
```cpp
class C10_API intrusive_ptr_target {
  mutable std::atomic<size_t> refcount_;
  mutable std::atomic<size_t> weakcount_;
```

`std::atomic` 使得对象可以避免数据竞争，多线程可以“同时”读写

### 友元 intrusive_ptr, weak_intrusive_ptr
```cpp
  template <typename T, typename NullType>
  friend class intrusive_ptr;
  friend inline void raw::intrusive_ptr::incref(intrusive_ptr_target* self);

  template <typename T, typename NullType>
  friend class weak_intrusive_ptr;
  friend inline void raw::weak_intrusive_ptr::incref(intrusive_ptr_target* self);
```

## 构造函数
将两个refcount置为0：
```cpp
constexpr intrusive_ptr_target() noexcept : refcount_(0), weakcount_(0) {}
```

### copy and assign

```cpp
  intrusive_ptr_target(intrusive_ptr_target&& other) noexcept : intrusive_ptr_target() {}
  intrusive_ptr_target& operator=(intrusive_ptr_target&& other) noexcept { return *this; }
  intrusive_ptr_target(const intrusive_ptr_target& other) noexcept : intrusive_ptr_target() {}
  intrusive_ptr_target& operator=(const intrusive_ptr_target& other) noexcept { return *this; }
```
看这段代码，复制和赋值都和other没有关系

# intrusive_ptr 类

## 成员变量
```cpp
TTarget* target_;
```
含有一个原始对象的指针

`intrusive_ptr` 只是对 TTarget 类型的对象进行操作，如 增加计数，释放资源，依赖于 TTarget 类型的成员实现

## 私有方法
增加计数：
- 指针不为空 && 原计数不为0
```cpp
  void retain_() {
    if (target_ != NullType::singleton()) {
      size_t new_refcount = ++target_->refcount_;
      TORCH_INTERNAL_ASSERT_DEBUG_ONLY(
          new_refcount != 1,
          "intrusive_ptr: Cannot increase refcount after it reached zero.");
    }
  }
```

reset(复位)：（析构函数调用）
- 指针不为空时：减少计数
- 如果计数减为0，则调用`release_resources`
- 减少 weak_count 计数，若减为0，则 `delete target_`
- 将自己的成员 target_ 置为 nullptr
```cpp
  void reset_() noexcept {
    if (target_ != NullType::singleton() && --target_->refcount_ == 0) {
      // justification for const_cast: release_resources is basically a destructor
      // and a destructor always mutates the object, even for const objects.
      const_cast<std::remove_const_t<TTarget>*>(target_)->release_resources();

      // See comment above about weakcount. As long as refcount>0,
      // weakcount is one larger than the actual number of weak references.
      // So we need to decrement it here.
      if (--target_->weakcount_ == 0) {
        delete target_;
      }
    }
    target_ = NullType::singleton();
  }
```

下面的私有构造函数从原始指针开始构造，不会增加引用计数，因此不能直接使用

用途：
- `make_intrusive()`, `weak_intrusive_ptr::lock()` 
```cpp
  explicit intrusive_ptr(TTarget* target) noexcept : target_(target) {}
```

## 构造 & 赋值

默认：
```cpp
  intrusive_ptr() noexcept : intrusive_ptr(NullType::singleton()) {}
```

移动构造函数：
- 接管rhs的 target_ 成员，原 target_ 置为 nullptr
```
  intrusive_ptr(intrusive_ptr&& rhs) noexcept : target_(rhs.target_) {
    rhs.target_ = NullType::singleton();
  }
```

复制构造函数：
- 复制-> 计数+1
```cpp
  intrusive_ptr(const intrusive_ptr& rhs) : target_(rhs.target_) {
    retain_();
  }
```

## 析构

```cpp
  ~intrusive_ptr() noexcept {
    reset_();
  }
```
为什么析构直接调用 reset? reset_ 不是直接 target_ = NullType::singleton() ? 

它这里修改的是当前这个智能指针的成员 target_，不影响其它指针 

## 计数机制

- 复制构造的时候，增加计数
- 当前指针销毁的时候，减少计数

### reclaim

`reclaim`新建一个 `intrusive_ptr` 对象，接管TTarget*，但不增加计数

参数owning_ptr **必须**来自 `intrusive_ptr::release()` 释放前任的管理
```cpp
  static intrusive_ptr reclaim(TTarget* owning_ptr) {
    return intrusive_ptr(owning_ptr);
  }
```

如果想从一个"non owning"(没有智能指针管理的)TTarget*指针创建 intrusive_ptr, 可以使用 `unsafe_reclaim_from_nonowning`

## 从原始参数创建智能指针
1. 从 Args 创建 TTarget*
2. 从 TTarget*创建 intrusive_ptr 对象
3. 增加 refcount & weakcount 计数 （这里计数是从0开始的，所以不用 retain())

```cpp
template <class... Args>
static intrusive_ptr make(Args&&... args) {
auto result = intrusive_ptr(new TTarget(std::forward<Args>(args)...));
// We can't use retain_(), because we also have to increase weakcount
// and because we allow raising these values from 0, which retain_()
// has an assertion against.
++result.target_->refcount_;
++result.target_->weakcount_;

return result;
}

template <
    class TTarget,
    class NullType = detail::intrusive_target_default_null_type<TTarget>,
    class... Args>
inline intrusive_ptr<TTarget, NullType> make_intrusive(Args&&... args) {
  return intrusive_ptr<TTarget, NullType>::make(std::forward<Args>(args)...);
}
```

# weak_intrusive_ptr 类
与 intrusive_ptr 类似而又不同的是：

`weak_intrusive_ptr` 类的操作只关注 `weak_count`
- retain 只增加 weakcount_
- reset_ 只判断 weakcount_
- 复制构造的时候增加 weakcount_

```cpp
void reset_() noexcept {
if (target_ != NullType::singleton() && --target_->weakcount_ == 0) {
    delete target_;
}
target_ = NullType::singleton();
}
```

## lock
和 `std::weak_ptr` 一样，返回一个非weak的 `intrutive_ptr`
```cpp
  intrusive_ptr<TTarget, NullType> lock() const noexcept {
    auto refcount = target_->refcount_.load();
    do {
      if (refcount == 0) {
        // 若为空则返回 nullptr
      }
    } while (!target_->refcount_.compare_exchange_weak(refcount, refcount + 1));    
    // 即 refcount_++
    // 返回intrusive_ptr 
    return intrusive_ptr<TTarget, NullType>(target_);
  }
```