# 过度设计 max(a, b)

标题：Overengineering max(a, b)

日期：2025/10/28

作者：Jonathan Müller

链接：[https://www.youtube.com/watch?v=o2pNg7noCeQ](https://www.youtube.com/watch?v=o2pNg7noCeQ)

注意：此为 **AI 翻译生成** 的中文转录稿，详细说明请参阅仓库中的 [README](/README.md) 文件。

-------


### **1. 开场白：一个“不实用”的演讲**

我非常兴奋能做这次演讲。它关于我大约两年前实现的一个东西。我提交这个演讲主题本来是为了 C++ Now 2025，但去年 C++ Now 接受了我另一个更无聊、但实际上能教给人们一些有用东西的演讲，这让我很失望。但幸运的是，我又有机会再次展示它。我记得当我实现其中一些部分时，我曾怀疑自己是否做得太过火了。我的老板却说：“不，不，继续做。即使失败了，它也能成为一个很棒的 C++ Now 演讲。”所以，我真的很兴奋。

我也很喜欢这次演讲被安排在与 Brad 的“实用 CMake”演讲并行进行，因为我讲的这些东西，没有一样是实用的。

那么，这次演讲是关于什么的呢？我们将要实现 `max(a, b)`。在此过程中，我们将踏上一段关于偶然复杂性（accidental complexity）和本质复杂性（essential complexity）的旅程。我们还会审视 C++ 有史以来添加的最糟糕的特性。我心里已经有了一个答案，也许你们可以思考一下，C++ 最糟糕的特性是什么。

我们要实现的函数是这个：`max(a, b)` 函数，返回两个参数中较大的一个。这能有多难呢？


### **2. 最初的 `max(a, b)`：从简单开始**

因为，这很简单，对吧？`max` 函数接受两个 `int`，A 和 B，然后用一个 `if` 语句返回两者中较大的一个。

```cpp
/* 生成代码，仔细甄别 */

int max(int a, int b) {
    if (a < b) {
        return b;
    } else {
        return a;
    }
}
```

如果你觉得这代码太多，也可以用三元运算符。现在只有一行了。

```cpp
/* 生成代码，仔细甄别 */

int max(int a, int b) {
    return a < b ? b : a;
}
```

当然，为了做到绝对正确，你还得加上所有这些东西。

```cpp
/* 生成代码，仔细甄别 */

[[nodiscard]]
constexpr int max(int a, int b) noexcept {
    return a < b ? b : a;
}
```

在接下来的演讲中，我将忽略 `nodiscard`、`constexpr` 和 `noexcept` 这些细节。所以，这就是针对整数的 `max(a, b)`。


### **3. 泛型化与类型要求：严格弱序**

显而易见的第一步是，既然它适用于整数，那我们就让它变得泛型。这很简单，把它变成一个模板。

```cpp
/* 生成代码，仔细甄别 */

template<typename T>
const T& max(const T& a, const T& b) {
    // T 必须提供一个 operator<，其语义上实现了一个严格全序（Strict Total Order）
    return a < b ? b : a;
}
```

你可以添加 `template<typename T>`。我把所有东西都按 `const` 引用传递，因为在泛型代码中，拷贝开销可能很大。但是，正如 Sean Parent 在他的主题演讲中所说，泛型编程不仅仅是使用泛型进行编程。你必须问自己，**类型要求是什么？** 不要只是写一个模板，要思考类型要求。

在这里，我们既有**语法要求**，即 `T` 必须提供一个 `operator<`，其返回值可以被上下文转换为 `bool`。但当然，这还不够。我们还有**语义要求**。这个 `operator<` 必须有意义，它所代表的意义是实现了一个**严格全序（Strict Total Order）**。

这是一个数学术语。严格全序是在集合 S 上定义的一种二元关系，它关联了集合中的元素对。这个关系有三个属性：

1.  **非自反性 (Irreflexivity)**：对于所有 S 中的 a，`a < a` 都不成立。
2.  **传递性 (Transitivity)**：如果 `a < b` 且 `b < c`，那么必须有 `a < c`。
3.  **三歧性 (Trichotomy)**：对于所有 S 中的 a 和 b，`a < b`、`a == b`、`b < a` 这三者中，**恰好有一个**成立。

这些就是要求。我选择用注释来表达语义，我也可以用 concept，但语义部分反正也是注释，所以不如就用注释好了。

那么，我们现在完成了吗？

考虑这段代码：

```cpp
/* 生成代码，仔细甄别 */

struct Person {
    int id;
    std::string name;
};

// 通过名字比较 Person
struct CompareByName {
    bool operator()(const Person& a, const Person& b) const {
        return a.name < b.name;
    }
};

// ...
Person p1{1, "Zoe"};
Person p2{2, "Zoe"};

// max(p1, p2, CompareByName{}); ???
```

我们有一个 `Person` 结构体，每个人有唯一的 ID 和一个名字。我们想通过一个按名字比较的结构体来获取最大值，也就是说，我们想要名字“更大”的那个人。如果你有这样的代码，现在我们有两个 `Person` 对象，名字相同但 ID 不同，因为他们是不同的人。如果你调用 `max`，你就违反了严格全序的语义要求，因为排序无法区分这两个人，但他们并不相等。

这其实没问题。只是我们对函数的领域（domain）过度指定了。我们不想要严格全序，我们只需要一个**严格弱序（Strict Weak Order）**。

这是对严格全序的一种放宽。严格弱序有四个属性：
1.  **非自反性 (Irreflexivity)**：仍然保持。
2.  **传递性 (Transitivity)**：仍然保持。
3.  **非对称性 (Asymmetry)**：如果 `a < b`，那么 `b < a` 必不成立。
4.  **不可比较性的传递性 (Transitivity of Incomparability)**：我们可以定义 `a` 和 `b` 是**等价的（equivalent）**，如果 `a < b` 和 `b < a` 都不成立。那么必须满足：如果 `a` 等价于 `b`，且 `b` 等价于 `c`，则 `a` 必须等价于 `c`。

用更正式的术语来说，S 上的严格弱序定义了在等价关系 `~` 下的等价类上的一个严格全序。这不重要。本质上，这意味着在排序规则下的“相等”可以比对象本身的实际相等性更弱，这是没问题的。

所以，如果它只需要一个严格弱序（标准库的 `std::max` 也是如此），那么上面的代码就完全没问题。唯一的问题是，结果应该是 `p1` 还是 `p2`？我们的排序规则无法区分 `p1` 和 `p2`，因为它只比较名字。但我们可以在结果中区分出是哪个人。那么最大值应该是哪个？

在我们当前的实现中：

```cpp
/* 生成代码，仔细甄别 */

// 版本 1
return a < b ? b : a;
```

如果 `a` 和 `b` “相等”（在我们的排序规则下是等价的），那么 `a < b` 为 false，我们返回 `a`。我们也可以这样实现：

```cpp
/* 生成代码，仔细甄别 */

// 版本 2
return b < a ? a : b;
```

现在这种情况下，如果我们得到两个等价的选项，我们可能会返回 `b`。有一个很有说服力的论点认为我们应该实现第二种版本，因为在某种意义上，第二个参数按定义就比第一个参数“大”。所以如果参数等价，我们返回第二个而不是第一个。然后 `min` 做相反的事情，这样我们就得到了很好的对称性。

但我还是会坚持使用第一个版本，因为这是标准库的做法。Walter Brown 曾就这个问题做过一整个演讲。是的，我正要提到他。因为我去年在 C++ on Sea 讲这个话题时，Walter Brown 就在观众席。他坐在他最后一排的代步车里。讲到这张幻灯片时，他离开了。因为是代步车，我只看到他在背景里慢慢地滑走了。所以，是的，可以说第二个版本更正确，但我所有的幻灯片都做好了，所以……你知道的。对我们现在来说，这会是我们最小的烦恼。


### **4. 处理混合类型比较：`std::common_type` 的陷阱**

让我们尝试支持混合类型比较。因为现在，我们无法获取一个 `std::string` 和一个 `std::string_view` 的最大值。这仅仅是因为我们只有一个模板参数 `T`。编译器试图为 `T` 推导一个单一的类型，要么是 `string`，要么是 `string_view`，所以它无法推导。

然而，这很容易修复：只要给它第二个模板参数。

```cpp
/* 生成代码，仔细甄别 */

template<typename T, typename U>
auto max(const T& a, const U& b) {
    // T 和 U 必须共同提供一个 operator<，其语义上实现了一个严格弱序
    return a < b ? b : a;
}
```
现在我们有了 `typename T` 和 `typename U`，并且我们修改了要求：它们两者之间需要一个 `operator<`，并且在语义上实现严格弱序。所以即使它们是不同的类型，它们也应该代表同样的东西，以便我们可以合理地比较它们。

现在的返回类型是 `auto`。因为，返回类型应该是什么？如果我们不想要 `auto`，我们可以使用一个类型萃取（trait）：`std::common_type<T, U>`。它是 `T` 和 `U` 之间的共同类型。如果你深入思考，这是一个非常奇怪的类型萃取。它本质上是这样的：

```cpp
/* 生成代码，仔细甄别 */

// std::common_type<T, U> 约等于
std::decay_t<decltype(true ? std::declval<T>() : std::declval<U>())>
```

它本质上是三元运算符的 `decltype`，但我们在里面加了一些 `decay`。因为我们不想要任何引用，并且由于某些原因，我们需要在两层都进行 `decay`。还有一堆例外情况，如果你去看标准措辞，会发现“如果 T 是这个，U 是那个，那么共同类型就是这个”。还有一堆涉及数组之类的例外，我不想知道。但基本上，它就是经过充分 `decay` 的三元运算符的 `decltype`，外加一些关于数组的奇怪处理。

但这还没完，因为我们可以自定义它。如果我们有自定义类型，我们可以说：

```cpp
/* 生成代码，仔细甄别 */

namespace std {
    template<>
    struct common_type<MyType, MyOtherType> {
        using type = SomeType;
    };
}
```
这很棒，但它**完全不影响三元运算符的行为**。对吧？仅仅因为你自定义了它，三元运算符仍然使用语言本身的定义。所以，即使你声明了存在一个共同类型，三元运算符也可能看不到它，于是编译不过。所以，这真“有用”，我猜。

*(观众提问：定义一个到另一个类型的转换运算符会有帮助吗？)*

是的，如果你定义一个转换运算符，三元运算符会采纳它。但那样你可能也就不需要……我不知道，可能有一些奇怪的边缘情况。我不想知道。

它还是可变参数的（variadic）。所以你可以一次性获取多个类型的共同类型。但它不是结合的（associative）。这意味着我们可以定义类型 A、B 和 C，使得 `common_type<A, B, C>` 与 `common_type<B, C, A>` 的结果不同。

这些类型就是这样的：

```cpp
/* 生成代码，仔细甄别 */

struct A {};
struct B : A {};
struct C : A {};
```

我们有基类 A 和两个派生自 A 的类 B 和 C。那么，`common_type<common_type<A, B>::type, C>` 的结果是 `A`，因为 `common_type<A, B>` 是 `A`，而 `common_type<A, C>` 是 `A`。但如果我们换个顺序，先计算 `common_type<B, C>`，这个共同类型不存在。因为 `common_type` 的规则意味着结果要么是其中一个类型，而不是某个可以通过转换序列达到的不相关的第三种类型。所以，这很有趣，我猜。

无论如何，我们现在的定义可以工作了。我们可以比较一个 `string` 和一个 `string_view`，得到 "world"。我们也可以比较一个 `int` 和一个 `unsigned int`，用 -1 和 +1，我们得到什么？

*(观众回答：一个 unsigned int)*

是的，我们得到了大约 40 亿。很明显。我的意思是，公平地说，40 亿是比 -1 和 +1 都大。但它不完全是我们想要的。

这里有两个问题：

**第一个问题：有符号/无符号比较**。如果你比较一个 `int` 和一个 `unsigned int`，可以有三种实现方式：
1.  **做正确的事**：比较它们所代表的数学值。这意味着负数小于正数。
2.  **都转为 `int`**：然后比较两个 `int`。这意味着负数小于正数，但如果正数太大，它又会变成负数。
3.  **做 C++ 做的事**：把两个都转成 `unsigned`，然后比较。这样，负数突然就比正数大了。

即使 C++ 定义了做正确的事（顺便说一下，标准库里有个函数 `std::cmp_less` 可以做到），那也解决不了问题。因为**第二个问题是返回类型的转换**。

`int` 和 `unsigned int` 的共同类型是什么？
-   它可以是下一个更大的、能同时容纳两种类型值的有符号整数类型。这是正确的答案。
-   它可以是 `int`，但如果数字太大就会有问题，我们会绕回负数。
-   **C++ 说，它是 `unsigned int`。** 这意味着如果你有一个负值，它会变成一个正值。所以 -1 变成了 `UINT_MAX`。

做正确的事的问题在于，我们最终会用完比特位。对吧？如果你有一个 `unsigned long long` 和一个 `long long`，没有一个内置类型能同时容纳它们的所有值。可能有扩展类型，但即使你用扩展类型，最终还是会用完比特位。

所以，在 think-cell，我们认为这应该是**无效的**。`int` 和 `unsigned int` 之间不应该存在共同类型，因为在泛型情况下，有符号和无符号整数之间不存在共同类型。所以我们实际上有这样一个萃取，叫做 `safely_convertible`。我们说，如果源类型可以转换到目标类型，并且这种转换是**安全的**，那么它就是安全可转换的。

这里的“安全”不是指内存安全，而是指像“派生类到基类的切片（slicing）是不安全的”或“`int` 到 `unsigned` 的转换是不安全的”。它只是禁止了那些我们不希望发生的转换。

于是我们有了 `tc_common_type`，它和 `std::common_type` 一样，但它要求所有类型都能安全地转换到最终的共同类型，否则它就没有定义。

```cpp
/* 生成代码，仔细甄别 */

template<typename T, typename U>
typename tc_common_type<T, U>::type max(const T& a, const U& b) {
    return a < b ? b : a;
}

// ...
max(-1, 1u); // 编译错误！
```

如果我们把返回类型指定为 `tc_common_type`，当我们用 `int` 和 `unsigned int` 调用它时，就会得到一个编译错误。因为 `int` 和 `unsigned int` 之间没有 `tc_common_type`，因为它会涉及一个“不安全”的转换。这样，我们就正确地处理了混合类型比较。


### **5. 完美转发与引用问题：`std::common_reference` 的引入**

好的，现在我们来处理完美转发。目前，我们通过 `const` 引用接收所有参数。所以当我们用两个 `string` 调用它时，结果会是一个 `std::string`，这是一个不必要的拷贝。对吧？在我们处理混合比较之前，返回类型只是 `const T&`，那样它只会返回一个 `const` 引用，没有不必要的拷贝。

所以我们不想要这个拷贝。我们可以直接说，OK，我们返回共同类型，但如果它们是相同的类型，就只返回引用。

```cpp
/* 生成代码，仔细甄别 */

template<typename T, typename U>
std::conditional_t<std::is_same_v<T, U>, const T&, std::common_type_t<T, U>>
max(const T& a, const U& b);
```
这解决了之前的问题。因为现在如果你给它两个相同的类型，你会得到一个引用。但如果你给它两个不同的类型，你会得到一个经过隐式转换的共同类型的值。因为通常情况下，如果你有两个不同的类型，你不能返回一个引用，因为其中一个类型必须被转换成某种东西，所以你不能返回对它的引用，你必须返回一个纯右值（PRvalue）。

这在某种程度上是可行的。当我们用两个 `string` 左值调用它时，结果没有拷贝。但是，如果我们用一个 `const char*` 和一个 `std::string` 值调用它，我们就有两个不同的类型，但它们有一个共同类型 `std::string`。我们返回这个 `std::string` 作为返回类型，这都很好。问题是，我们是通过拷贝 "world" 来实现的，而它本可以被移动（move）。我们不想要一个拷贝操作，我们想要一个移动操作到返回类型中。

返回类型是正确的，只是我们得到它的方式不对。这很容易解决，用**转发**就好了。

```cpp
/* 生成代码，仔细甄别 */

template<typename T, typename U>
decltype(auto) max(T&& a, U&& b) {
    return a < b ? std::forward<U>(b) : std::forward<T>(a);
}
```

不要用 `const T&`，用转发引用 `T&&`，然后在内部转发它。现在我们只需要共同类型存在，但我们实际返回的是任何类型，包括引用。我们用 `decltype(auto)` 返回它。

现在，这也许能行。这里到底发生了什么？如果我们给它一个 `string` 左值引用和一个 `string` 右值引用，这个函数的返回类型是什么？三元运算符会做什么？它遵循这张表：

| `a` \ `b` | `T&` | `const T&` | `T&&` | `const T&&` |
| :--- | :--- | :--- | :--- | :--- |
| **`T&`** | `T&` | `const T&` | `T` | `const T` |
| **`const T&`** | `const T&` | `const T&` | `const T` | `const T` |
| **`T&&`** | `T` | `const T` | `T&&` | `const T&&` |
| **`const T&&`** | `const T` | `const T` | `const T&&` | `const T&&` |

这张表展示了当两个类型仅在 CV 和引用限定符上不同时，三元运算符的行为。
-   左上角：两者都是左值引用。结果总是左值引用，并且如果两者中至少有一个是 `const`，结果就是 `const`。
-   右下角：两者都是右值引用。结果总是右值引用，并且如果两者中至少有一个是 `const`，结果就是 `const`。
-   **混合区域**：如果你混合一个左值引用和一个右值引用，你只会得到一个 `T` 类型的**纯右值（PRvalue）**。

这意味着，在我们的实现中，当我们用 `"hello"` 和 `std::string("world")` 调用时，结果会被正确地移动。但如果我们用一个 `string` 左值和一个 `string` 右值调用，这又会**创建一个不必要的拷贝**，因为三元运算符的结果是一个 PRvalue。尽管在这种情况下，返回一个引用（比如右值引用）是完全没问题的，生命周期也检查通过。这在某种程度上是一个不必要的拷贝。

幸运的是，有一种方法可以解决这个问题。因为还有一个 `std::common_reference`。`std::common_reference` 有点像 `std::common_type` 的引用等价版本。
-   如果两个类型只是在 CV 和引用限定符上不同，它会找出具有正确限定符的引用类型。
-   否则，它会回退到 `std::common_type`。
-   关键是，它**不是**三元运算符的 `decltype`。因为三元运算符会给你一个 PRvalue，而 `common_reference` 会尝试给你一个引用。

`common_reference` 的行为表是这样的：

| `a` \ `b` | `T&` | `const T&` | `T&&` | `const T&&` |
| :--- | :--- | :--- | :--- | :--- |
| **`T&`** | `T&` | `const T&` | **`const T&`** | **`const T&`** |
| **`const T&`** | `const T&` | `const T&` | **`const T&`** | **`const T&`** |
| **`T&&`** | **`const T&`** | **`const T&`** | `T&&` | `const T&&` |
| **`const T&&`** | **`const T&`** | **`const T&`** | `const T&&` | `const T&&` |

它在蓝色和绿色区域与三元运算符相同，但在混合左值和右值引用时，结果是 `const T&`。所以如果我们用它，就能避免 PRvalue。

但为什么它返回 `const T&`？因为它被认为是“通用接收者”（universal receiver），是所有其他引用类型都可以隐式转换成的类型。

| 引用类型 | 绑定到临时对象? | 允许 `const`? |
| :--- | :---: | :---: |
| `T&` | No | No |
| `const T&` | **Yes** | **Yes** |
| `T&&` | Yes | No |
| `const T&&`| **Yes** | **Yes** |

`const T&` 可以绑定到临时对象，也允许绑定到 `const` 对象，所以它是所有引用类型的共同归宿。但这是理想的设计吗？如果我们有时间机器，可以破坏代码，我们会这样做吗？

我认为不会。因为 `const T&` 和 `const T&&` 在这个表里是重复的（都是 Yes, Yes）。我们缺少了“不允许绑定临时对象但允许 `const`”的这一列。

我们 think-cell 认为，理想的世界应该是这样的：

| 引用类型 | 绑定到临时对象? | 允许 `const`? |
| :--- | :---: | :---: |
| `T&` | No | No |
| `const T&` | **No** | **Yes** |  *(<-- 改变在这里)*
| `T&&` | Yes | No |
| `const T&&`| **Yes** | **Yes** |

在这个理想世界里，“通用接收者”会是 `const T&&`。因为它通过 `const` 表明我们不会修改它，通过 `&&` 表明我们接受临时对象。我们认为这是一个更好的世界。唯一需要改变的就是，**阻止 `const T&` 绑定到临时对象**。

这在 C++ 里是不可能的，因为在 `const T&` 被添加时，我们还没有右值引用。所以我们有时会假装我们生活在这个理想世界里。我们有 `tc_common_reference`，它在混合左值和右值时行为不同：`std::common_reference` 给出 `const T&`，而我们给出 `const T&&`。

```cpp
/* 生成代码，仔细甄别 */

template<typename T, typename U>
typename tc_common_reference<T, U>::type max(T&& a, U&& b) {
    return a < b ? std::forward<U>(b) : std::forward<T>(a);
}
```

我们用它来实现 `max`。唯一的麻烦是……这段代码会**崩溃**。

*(观众提问：你不需要对三元运算符的结果做 `static_cast` 吗？)*

你比我快了两张幻灯片。首先，这段代码会崩溃。

因为它会返回一个对**悬垂引用**。三元运算符仍然给你一个 PRvalue。即使你用 `std::common_reference` 作为返回类型，你也会从三元运算符得到一个 PRvalue，而不是一个引用。所以你会得到一个对在 `return` 语句中创建的 PRvalue 的引用，这个引用会立刻悬垂。

要修复它，你得写一个 `if/else`，因为它不会产生 PRvalue。

```cpp
/* 生成代码，仔细甄别 */

template<typename T, typename U>
typename tc_common_reference<T, U>::type max(T&& a, U&& b) {
    if (a < b) {
        return std::forward<U>(b);
    } else {
        return std::forward<T>(a);
    }
}
```

其次，是的，我们需要 `static_cast`。因为我们假装存在一个隐式转换，而实际上没有。`T&` 并不能隐式转换为 `const T&&`。所以你必须加上一个 `static_cast`。这有点丑陋。

所以我们用解决大多数 C++ 问题的方式来解决它：我们有一个**宏**。

```cpp
/* 生成代码，仔细甄别 */

#define TC_CONDITIONAL_RVALUE_AS_REF(cond, a, b) \
    (cond \
        ? static_cast<tc_common_reference_t<decltype((a)), decltype((b))>>(a) \
        : static_cast<tc_common_reference_t<decltype((a)), decltype((b))>>(b) \
    )

template<typename T, typename U>
decltype(auto) max(T&& a, U&& b) {
    return TC_CONDITIONAL_RVALUE_AS_REF(
        a < b,
        std::forward<U>(b),
        std::forward<T>(a)
    );
}
```

这个宏模拟了三元运算符，但把它转换成了你想要的类型。这个宏的一个好处是，现在如果你特化了 `tc_common_reference`，它实际上会被“三元运算符”采纳，因为它反正都会做 `static_cast`。我们有一些代码用它来处理类继承体系，如果你指定一个基类作为成员，我们有一些元编程来找出所有类的共同祖先，并给你想要的引用。

我没看到观众的反应。这真的很有用！当我引入它时，我简化了大量带有额外 `cast` 的代码。

*(观众反应：这已经不泛型了！)*

它还是泛型的。你只需要……好吧，它不是对所有类继承体系都泛型，但对于我们代码库里那个继承了特定东西的继承体系是泛型的。而且用反射你可以让它泛型。而且，我们还有 `common_type` 在 `T` 和 `nullptr_t` 之间的特化，它会给你一个 `optional<T>`。这真的很烦人，三元运算符里竟然没有这个。所以这真的很有用，只是需要一个宏。

但如果你对这个宏反应这么强烈，你不会喜欢接下来的演讲内容的。

无论如何，现在我们的代码可以工作了。`string` 左值和 `string` 右值可以工作，它会给你一个 `const string&&`。


### **6. 组合函数与悬垂引用：问题的核心**

让我们开始组合它。这是 `max`，这是 `min`。这是 `clamp`。

```cpp
/* 生成代码，仔细甄别 */

template<typename T, typename U, typename V>
decltype(auto) clamp(T&& val, U&& lower, V&& upper) {
    return min(
        max(std::forward<T>(val), std::forward<U>(lower)),
        std::forward<V>(upper)
    );
}
```
`clamp` 接受三个参数，我们想要 `max(val, lower_bound)` 和 `upper_bound` 之间的 `min`。我们可以用三个 `string` 调用它，一切正常。但如果我们把边界变成 `string_view`，代码就**崩溃了**。

让我们一步步分析：
1.  `val` 是一个 `string&` 左值引用。
2.  `lower` 是一个 `string_view&` 左值引用。
3.  我们首先调用 `max(string&, string_view&)`。这是两个不相关的类型，所以结果是一个 **PRvalue `string_view`**，因为这是 `string` 和 `string_view` 之间的共同类型。
4.  然后我们把这个 PRvalue `string_view` 和一个 `string_view&` 左值引用一起传递给 `min`。
5.  PRvalue 会被当成一个右值引用传入 `min`。
6.  `min` 的结果是 `tc_common_reference<string_view&&, string_view&>`，也就是 `const std::string_view&&`。

这里发生的是：我们返回了一个指向在函数内部创建的 `string_view` **临时对象**的右值引用。这导致了崩溃。

这很不幸。但有趣的问题是，**这是谁的错？**

我来引入一些术语。我们有一个**投影（Projection）**：一个返回引用的函数，其生命周期与其中一个参数绑定。像 `max`、`min` 和 `clamp`。`clamp` 是一个**组合投影**，因为它是由多个投影组合而成的。

我们遇到的问题是：如果一个投影返回了一个指向 PRvalue 参数的右值引用，组合它们可能导致返回悬垂引用。

如何修复它？
**方法一：投影从不返回右值引用。**
我们可以说，投影永远不返回右值引用。那么问题就解决了。

```cpp
/* 生成代码，仔细甄别 */

template<typename T>
struct decay_rvalue { using type = T; };

template<typename T>
struct decay_rvalue<T&&> { using type = std::remove_reference_t<T>; };

// ... 在 max 内部，如果结果是右值引用，就 decay 它
```

这回避了问题。现在我们不会返回对潜在 PRvalue 的右值引用，而是返回一个 PRvalue 本身。这是一个可行的解决方案，但技术上说，它**太激进了**。我们在一些完全没问题的情况下也 `decay` 了它，比如当 PRvalue 的生命周期被延长，并且足够长的时候。

**方法二：投影从不返回指向 PRvalue 参数的右值引用。**

```cpp
/* 生成代码，仔细甄别 */

// 伪代码
template<typename T, typename U>
decay_if_either_is_prvalue<
    tc_common_reference_t<T, U>,
    T, U
>
max(T&& a, U&& b);
```
如果任何一个参数是 PRvalue，就 `decay` 返回类型。这是个完美的解决方案，只是有一个小问题：**我们实现不了它**。

因为转发引用的工作方式，当你进入函数体时，你无法区分传入的是一个 PRvalue（纯右值）还是一个 Xvalue（将亡值，如 `std::move` 的结果）。它们都被转换成了同样的东西（右值引用）。

这很不幸，因为它本可以很容易地区分。只要稍微调整一下规则，说如果你传入一个 Xvalue，`T` 就被推导为右值引用类型，那么通过检查 `T` 是否是引用，你就能区分 Xvalue 和 PRvalue 了。但这并不是我们最终得到的设计。

即使我们能实现它，它也可能不够精细。

```cpp
/* 生成代码，仔细甄别 */

auto dangling = clamp("B"s, "A"sv, "C"sv); // 有问题
const auto& fine = clamp("B"s, "A"sv, "C"sv); // 没问题
```

在 `clamp` 的例子里，这是悬垂的。但如果你把整个表达式放到另一个上下文中，它就完全没问题，因为生命周期延长会将所有东西的生命周期延长到分号处。问题只在我们跨越函数边界时才出现。

所以，实际上是**组合投影的使用者**有责任防止悬垂引用。

**正确的解决方案**：一个组合投影永远不应该返回对**中间** PRvalue 的引用。
这意味着 `clamp` 应该这样实现：

```cpp
/* 生成代码，仔细甄别 */

// 伪代码
template<typename T, typename U, typename V>
decltype(auto) clamp(T&& val, U&& lower, V&& upper) {
    auto temp_max = max(std::forward<T>(val), std::forward<U>(lower));
    // 如果 temp_max 是一个对 max 内部创建的 PRvalue 的右值引用，就 decay 它
    if (is_rvalue_ref_to_intermediate_prvalue(temp_max)) {
        return min(decay(temp_max), std::forward<V>(upper));
    } else {
        return min(temp_max, std::forward<V>(upper));
    }
}
```
只有当 `max` 的结果是一个 PRvalue 时，我们才必须 `decay` 它，不能返回对它的右值引用。否则，代码可以正常工作。这样我们就能用最少的 `decay` 来保证正确性。

但这很容易出错，而且如果我们进行泛型组合，它也行不通。

```cpp
/* 生成代码，仔细甄别 */

// 一个组合子
auto fgh = compose(f, g, h); // f(g(a), h(b))
```
在这个组合子中，它有责任去 `decay`。我们可能会说，如果 `g` 或 `h` 返回 PRvalue，就 `decay`。但如果 `f` 总是返回数字 5 呢？（比如一个对全局对象的右值引用），那我们就不需要 `decay`。

真正需要的是：**如果 `f` 返回一个指向由 `g` 或 `h` 创建的 PRvalue 的右值引用，就 `decay`**。问题是，在泛型代码中我们不知道这一点。我们不知道 `f`、`g` 和 `h` 的生命周期契约。


### **7. 解决方案：用类型系统追踪生命周期**

在这一点上，我可以说出我最喜欢的一句话：C++ 不是一门特别好的语言，但 C++ 中的所有问题都可以用**更多的 C++** 来解决。

具体来说，我们想追踪生命周期。所以让我们引入一个新的引用类型，一个特殊的标记类型，来表示“这是一个对临时对象的引用”。我们称之为 `tc_temporary`。

```cpp
/* 生成代码，仔细甄别 */

template<typename T>
class tc_temporary {
    T&& m_ref;
public:
    // ... 构造函数 ...
    operator T&&() const { return std::move(m_ref); }
};
```
它本质上是一个花哨的右值引用。它的想法是，我们用它作为标记类型，来表明“嘿，你是一个指向**中间 PRvalue** 的右值引用”，而不仅仅是一个普通的右值引用。

然后我们有一个宏来创建这个东西：

```cpp
/* 生成代码，仔细甄别 */

#define PRVALUE_AS_TEMPORARY(expr) \
    /* ... 魔法 ... */

PRVALUE_AS_TEMPORARY(obj);         // 左值 -> T&
PRVALUE_AS_TEMPORARY(std::move(obj)); // Xvalue -> T&&
PRVALUE_AS_TEMPORARY(T{});         // PRvalue -> tc_temporary<T>
```
它必须是一个宏，因为只有宏有 `decltype` 的能力来实际检测出 PRvalue。整个事情在底层就是一个 `static_cast`，只有在输入是 PRvalue 时，我们才创建一个 `tc_temporary` 对象来包装它。

基本规则是：**一个 `tc_temporary` 永远不应该被返回**。所以我们有一个萃取，如果它是 `tc_temporary` 就 `decay` 它。我们不写 `return`，而是写 `TC_RETURN_TEMPORARY`，它会在必要时进行 `decay`。

```cpp
/* 生成代码，仔细甄别 */

#define TC_RETURN_TEMPORARY(expr) \
    /* ... 魔法 ... */

// ...
TC_RETURN_TEMPORARY(tc_temporary<int>{...}); // decay 成 int
TC_RETURN_TEMPORARY(42);                      // 保持 int
```
除非我们有一个 `tc_temporary`，否则这个宏由于拷贝省略和 `static_cast`，就是一个空操作（no-op）。

现在，我们的泛型组合可以这样写：

```cpp
/* 生成代码，仔细甄别 */

template<typename F, typename G, typename H>
auto compose(F f, G g, H h) {
    return [=](auto&&... args) {
        auto g_res = PRVALUE_AS_TEMPORARY(g(args...));
        auto h_res = PRVALUE_AS_TEMPORARY(h(args...));
        auto f_res = f(g_res, h_res);
        return TC_RETURN_TEMPORARY(f_res);
    };
}
```

现在它能工作了！因为我们在类型系统中获得了信息，知道了 `f` 是否返回了一个派生自其参数之一的引用。

当然，这还是有点啰嗦。但我们可以做得更好，因为我们可能不会直接调用函数，我们会用 `std::invoke`。所以我们可以把这个逻辑教给我们的 `invoke` 函数。我们只需要把它变成一个宏 `TC_INVOKE`，它会自动用 `tc_temporary` 包装参数。然后我们只需要记得在返回时 `decay` 它。


### **8. 实现细节与优化：`tc_temporary` 的威力**

当然，这只在 `f`、`g` 和 `h` 本身能处理 `tc_temporary` 时才有效。

-   像 `max` 这样的函数，由于隐式转换，不需要做任何事情，代码就能正常工作。如果它的任何一个参数是 `tc_temporary`，它就会自动返回一个 `tc_temporary`。
-   但像 `foo.member` 这样的代码就需要调整，因为 `tc_temporary` 没有 `member` 成员。

我们需要**临时解包**它。

```cpp
/* 生成代码，仔细甄别 */

// 伪代码
auto f(auto&& t) {
    auto&& unwrapped = TC_UNWRAP_TEMPORARY(t);
    auto&& result = unwrapped.foo;
    return TC_REWRAP_IF_NECESSARY(result, t);
}
```
我们解包它，访问成员，然后如果原始输入是 `tc_temporary`，我们就**重新包装**结果。重新包装是一个启发式规则，它假设如果任何输入是 `tc_temporary`，我们也需要重新包装输出。

所以，只要 `f` 被更新以处理 `tc_temporary`，这就是我们进行泛型组合所需的正确代码。

当然还有一个复杂情况：如果 `t` 或 `u` 已经是 `tc_temporary` 了呢？因为我们可能在进一步组合这个组合投影。那么我们的逻辑就失效了，因为我们有一个来自外部的 `tc_temporary`，我们不应该 `decay` 它。

所以我们实际的 `tc_temporary` 定义有一个**生命周期计数器**。
-   如果生命周期是 0，它是一个真正的临时对象，适用之前的逻辑。
-   如果生命周期大于 0，它只是某个父作用域中的临时对象。

关键操作是**增加/减少生命周期**。当我们用 `tc_temporary` 调用一个函数时，我们增加它的生命周期，这样它在函数内部就不会被当作生命周期为 0 的临时对象处理，也就不会被 `decay`。函数返回后，我们再把它减回来。幸运的是，这整个逻辑都可以隐藏在 `invoke` 里。

有了这个，我们就得到了一种可行的方法。组合投影使用 `TC_INVOKE` 和 `TC_RETURN_TEMPORARY`，就永远不会返回悬垂引用，因为我们成功地让 C++ 为我们追踪了生命周期。

然而，问题是，所有模板化的投影现在都需要知道 `tc_temporary` 的存在，这很烦人。但这实际上不完全正确。因为 `tc_temporary` **只与可能返回右值引用的投影相关**。如果一个投影从不返回右值引用，它就永远不会返回对悬垂 PRvalue 的右值引用。所以我们不需要这套机制。

这意味着我们可以这样实现 `invoke`：

```cpp
/* 生成代码，仔细甄别 */

// 伪代码
if constexpr (is_rvalue_ref<invoke(f, decay_all_temporaries(args...))>) {
    // f 可能返回右值引用，我们需要追踪！
    return invoke(f, wrap_prvalues_as_temporaries(args...));
} else {
    // f 不会返回右值引用，不需要追踪。
    return invoke(f, decay_all_temporaries(args...));
}
```

我们首先在移除所有 `tc_temporary` 的情况下调用函数，检查结果是否是右值引用。如果不是，我们就不需要用 `tc_temporary` 来调用函数。只有当它返回右值引用时，我们才需要知道这个右值引用是从哪里来的，这时我们才需要 `tc_temporary` 来追踪信息。

这大大简化了问题。大部分用户代码中的投影几乎从不返回右值引用，所以它们根本不需要进入 `tc_temporary` 的世界。最常见的投影就是访问成员，我们通过一个宏创建的 lambda 来泛型地实现了它，所以用户代码不需要知道 `tc_temporary` 的存在。


### **9. 对 C++ 语言设计的反思：真正的问题所在**

我们到底在做什么？我们正在做一些 C++ 显然不擅长做的事情。

让我们退后一步，看看什么样的语言设计能解决这个问题。
-   我们的目标是：不要不必要的拷贝/移动，组合时不要返回对中间临时对象的引用。
-   根本问题是：我们如何追踪结果引用是否与某个参数绑定？

**Rust** 有生命周期。我们可以在函数签名中表达这个关系：

```
// 伪 C++
template<'l>
auto max(const T&:'l a, const U&:'l b) -> common_reference_t<...>&:'l;
```
现在我们在函数签名中看到了，嘿，我们返回的引用，其生命周期 `'l` 与输入参数的生命周期绑定。那我们就不需要发明 `tc_temporary` 了。

但为什么 Rust 需要在签名中明确标注生命周期？为什么编译器不能自己从函数体中推断出来？因为这是一个**契约**。如果你改变了它，就是一个破坏性变更。

但在投影这个特定情况下，生命周期是从行为中得出的。`max` 总是会返回一个与某个参数生命周期绑定的引用。

另一个问题是，为什么 C++ 和 Rust 需要显式选择按引用调用？因为它对生命周期有影响。但对于投影来说，有显而易见的选择：我们不想要拷贝。

所以一个更好的范式可能是，我们只说：嘿，这个函数是一个**投影**。

```cpp
/* 生成代码，仔细甄别 */

// 幻想中的语言
projection max(a: T, b: U) { ... }
```
然后让编译器去做正确的事：用最理想的方式传递参数，返回最理想的返回类型，并且在组合时，**不要蠢到返回一个对悬垂临时对象的引用**。

我认为，**头等（first-class）引用是 C++ 有史以来添加的最糟糕的特性**。
-   它在函数参数中带来了巨大的复杂性：`T&` vs `const T&` vs `T&&` vs 转发引用。
-   临时对象生命周期延长，谁不喜欢呢？
-   悬垂引用。如果你没有引用，你就不会有悬垂引用。
-   头等引用主要是为了运算符重载（比如 `operator[]`）而添加的，但这本应该用不同的方式解决。

**二等（second-class）引用**或参数传递模式会好得多。只要指定“这是一个输入参数”，然后让编译器找出如何实现它。这会是一个更好的解决方案，减少了大量的偶然复杂性。

这就是为什么我对 **Val 语言**感到兴奋。在 Val 中，引用不是一个东西。你只用值语义写代码，然后它就能工作。因为编译器知道如何正确地传递东西。Val 有“下标”（subscripts），也就是我所说的投影，它会自动做正确的事，进行正确的生命周期追踪。语义上都是拷贝，但生成的代码不会拷贝。这干净多了。


### **10. 结论与问答环节**

**主要观点：** 这一切真的有必要吗？
-   如果你绝对想要避免不必要的移动，**是的**，你需要像 `tc_temporary` 这样的东西。否则你无法编写能组合的泛型代码而不在某些情况下崩溃。
-   如果你能接受不必要的移动以换取巨大的简单性，那么，是的，只要 `decay` 掉右值引用就好了。这是一个简单得多的解决方案。
-   但实际上，我们想要的是**不同的语言设计**。

我们还在招聘。所以如果你出于某种原因喜欢 `tc_temporary` 这种东西，我们正在招聘。如果你不喜欢，正如我所说，用户代码实际上不关心它。谢谢。

---
**(问答环节)**

**问：** 你有没有试过用显式模板参数来传递值类别（value category）信息，而不是用 `tc_temporary`？
**答：** 那可能也行。问题是，如果函数参数是 `auto` 而不是模板参数，我不认为你能传递显式模板参数。……哦，可以吗？好吧，我不知道。那也许有帮助，但它对 lambda 不起作用。因为我们 99% 的投影都是用宏生成的 lambda。

**问：** 我不太理解 `tc_temporary` 如何解决生命周期问题，因为你把 `u` 按值接收，然后赋给一个引用，这会产生一个本地值的引用。
**答：** 啊，那是幻灯片代码，我简化得太多了。应该把它理解为一个概念。想法是，我们有一个构造函数接收左值引用，另一个接收右值引用。抱歉，我简化过头了。它不是延长生命周期，它把值作为右值引用持有，整个机制依赖于函数参数中的临时对象生命周期延长，并且它只设计用于在子表达式内部存活。

**问：** 你说 Rust 的生命周期注解对你来说可以接受，但它们似乎做的是不同的事情。Rust 会阻止你编译。
**答：** 是的。Rust 没有右值引用，所以它没有从函数返回右值引用的概念。它本质上总是移动。我所说的是一个假设的、结合了 Rust 生命周期注解和 C++ 右值引用的语言，它会由编译器来防止返回对临时对象的右值引用。Rust 的 `max` 函数总是返回“左值引用”，它们是通过总是返回 `const T&` 类型的代码来解决这个问题的，如果要做混合比较，它们会按值返回，然后进行一次移动。

**问：** 这整个的目标是为了节省 `decay` 的性能开销吗？这个开销明显吗？
**答：** 不是。不明显。第二个问题是，如果我想在用户代码里写我自己的 `max`，我需要做什么？只有当你想要返回右值引用时才需要。我们把整个系统设计成你必须显式选择加入（opt-in）返回右值引用。因为我们不用 `decltype(auto)`，而是用一个宏，如果它最终变成一个右值引用，宏会编译错误。所以你必须刻意去选择返回右值引用。因为那很危险。只有在做这件事的代码里，你才需要了解这个机制。

**问：** 几乎感觉……如果想学点有用的，我应该去看那个“实用 CMake”的演讲。
**答：** 是的，那个演讲和我这个可以说是截然相反的。

**问：** 演讲的很大一部分让我想起你老板（Arno Schödl）的演讲《C++ 生命周期灾难》。
**答：** 是的，同样的想法。

**问：** `tc_temporary` 是需要用户自己去包装的东西吗？
**答：** 不，这完全是隐藏的。`TC_INVOKE` 创建临时对象，然后返回宏隐式地处理它。它完全被隐藏起来了。只有当你选择返回右值引用时，它才会暴露出来。

**问：** 那么，C++26 不是已经把返回对本地变量的引用定为错误了吗？
**答：** 是的，但你可以把它隐藏得足够深，以至于它不再是那个错误。比如，你返回 `f(x)` 而不是 `x`，如果 `f` 是一个恒等函数，编译器就不知道了。因为它不在签名中追踪生命周期。所以你需要一种在签名中追踪生命周期的方法，你知道的……或者，干脆别用引用。

好了，我希望我把你们烦得够呛了。谢谢大家。
