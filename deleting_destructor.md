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


a special destructor created for by the compiler. It's called the deleting destructor and its existence is described by the Itanium C++ ABI:

deleting destructor of a class T - A function that, in addition to the actions required of a complete object destructor, calls the appropriate deallocation function (i.e,. operator delete) for T.
The ABI goes on to provide more details:

The entries for virtual destructors are actually pairs of entries. The first destructor, called the complete object destructor, performs the destruction without calling delete() on the object. The second destructor, called the deleting destructor, calls delete() after destroying the object.

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
