# 析构函数
代码：

```cpp
class Animal
{
public:
    Animal()
    {
    }
    virtual ~Animal()
    {
    }
};

int main()
{
    Animal animal;
}
```

`nm main.o | grep Animal`
得到:

> 0000000000407084 r .xdata$_ZN6AnimalC1Ev
0000000000407098 r .xdata$_ZN6AnimalD0Ev
000000000040708c r .xdata$_ZN6AnimalD1Ev

查看符号：
> $ c++filt.exe _ZN6AnimalC1Ev      
Animal::Animal()        
$ c++filt.exe _ZN6AnimalD0Ev        
Animal::~Animal()   
$ c++filt.exe _ZN6AnimalD1Ev    
Animal::~Animal()

可以发现有**两个析构函数**

# 编译器为什么会生成两个析构函数？
现象是，在有virtual destructor的类里面，会生成D0

可以理解为，如果有virtual，则在进行delete的时候，需要知道释放多大的内容

比如`Base *p; p = new Derived();`

编译器拿到的指针是 `base*` 类型的，它需要通过虚函数表找到真正的析构函数，这个析构函数**要完成delete的工作**

因为编译器在编译的时候不知道要delete释放多大的空间，这个delete的工作只能交给每个带virtual关键字的类自己来做

# deleting destructor

a special destructor created for by the compiler. It's called the deleting destructor and its existence is described by the Itanium C++ ABI:

`deleting destructor` of a class T 
- A function that, in addition to the actions required of a `complete object destructor`, calls the appropriate deallocation function (i.e,. operator delete) for T.

The ABI goes on to provide more details:

The entries for virtual destructors are actually pairs of entries. The first destructor, called the complete object destructor, performs the destruction without calling delete() on the object. The second destructor, called the deleting destructor, calls delete() after destroying the object.

D2 is the "base object destructor". It destroys the object itself, as well as data members and non-virtual base classes.

D1 is the "complete object destructor". It additionally destroys virtual base classes.

D0 is the "deleting object destructor". It does everything the complete object destructor does, plus it calls operator delete to actually free the memory.

## `deleting destructor`实例
打开上面代码的汇编代码，可以看到D0这个`deleting destructor`做了什么：

```asm
_ZN6AnimalD0Ev:
.LFB6:
	pushq	%rbp
	.seh_pushreg	%rbp
	movq	%rsp, %rbp
	.seh_setframe	%rbp, 0
	subq	$32, %rsp
	.seh_stackalloc	32
	.seh_endprologue
	movq	%rcx, 16(%rbp)
	movq	16(%rbp), %rcx
	call	_ZN6AnimalD1Ev
	movq	16(%rbp), %rcx
	call	_ZdlPv
```

可以看到 `_ZN6AnimalD0Ev` 调用了 `_ZN6AnimalD1Ev`, `_ZdlPv`
1. 调用D1
2. 调用delete

也就是说，deleting destructor 是 `complete object destructor + delete`

其中 `_ZdlPv` 可以看到是 `delete`

## 子类调用基类的哪个析构函数？
总结上面的内容：
- 如果有虚函数，则会生成虚函数表，也会生成D0类型的析构函数；如果没有虚函数则一般没有D0
- 如果没有虚函数&虚继承，则D1和D2是同一个

那么子类的D0会调用基类的哪个析构函数呢？D0还是D1还是D2？

可以这样理解：
比如C继承自B，B继承自A

最后由C完成delete，只有C是知道C的大小是多大的

则调用关系为：
- C::D0 -> C::D1 -> C::D2
- C::D2 -> B::D2
- B::D2 -> A::D2

>C::des     
B::des  
A::des  
C::delete

# 只有一个析构函数

`nm main.o` 结果：

> $ nm main.o | grep Animal     
000000000040506c p .pdata$_ZN6AnimalC1Ev
0000000000405078 p .pdata$_ZN6AnimalD1Ev
0000000000402d00 t .text$_ZN6AnimalC1Ev
0000000000402d10 t .text$_ZN6AnimalD1Ev
0000000000406084 r .xdata$_ZN6AnimalC1Ev
000000000040608c r .xdata$_ZN6AnimalD1Ev
0000000000402d00 T _ZN6AnimalC1Ev
0000000000402d10 T _ZN6AnimalD1Ev

此时只有两个符号：

> $ c++filt.exe _ZN6AnimalC1Ev  
Animal::Animal()        
$ c++filt.exe _ZN6AnimalD1Ev    
Animal::~Animal()
