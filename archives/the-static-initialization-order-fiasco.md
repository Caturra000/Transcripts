# 静态初始化顺序难题（SIOF）

标题：The Static Initialization Order Fiasco

日期：2021/02/20

作者：Jonathan Müller

链接：[https://www.youtube.com/watch?v=6EOSRKMYCTc](https://www.youtube.com/watch?v=6EOSRKMYCTc)

注意：此为 **AI 翻译生成** 的中文转录稿，详细说明请参阅仓库中的 [README](/README.md) 文件。

备注一：人工添加了代码片段，顺便看完了演讲，讲得真不错。

备注二：结论是学会用 C++20 modules，这些问题都不存在。有生之年用不了模块？那继续看演讲吧。

-------

这就是静态初始化顺序问题，或者说如何正确地初始化全局状态。特别说明，本次演讲不会讨论你是否应该使用全局变量。本次演讲的前提是我们已经决定要使用全局变量，现在我们想知道如何正确地初始化它们，因为正如我们所见，这有点棘手。在整个演讲中，我们将尝试编写一个日志记录器（logger）。这个日志记录器应该能够同时将消息记录到 `std::cout` 和某个文本文件，并且它应该在程序执行的任何时刻都可用。如果你了解我，我有点“库依赖症”。所以在整个演讲过程中，我写了越来越多有用的代码片段，最终把它们放到了一个小型库中，叫做 Atum 库。你可以在那个 URL 找到它，更多信息也在最后。但我们基本上会在这次演讲中编写它的大部分内容。

```cpp
// logger.hpp
class Logger
{
    std::ofstream file_out_;

public:
    Logger() : file_out_("log.txt") {}
    void log(std::string_view msg);
};

extern Logger logger; // declaration


// logger.cpp
Logger logger; // definition
```

那么，这是对我们日志记录器的第一个有点天真的尝试。它是一个类。它包含一个文件流成员。它有一个默认构造函数用于打开文件，然后是一个 `log` 方法，该方法将消息记录到 `zout` 和文件中。我们声明一个全局变量，然后在相应的翻译单元中定义它。

```cpp
// main.cpp
class Application
{
public:
    Application() { logger.log("Application startup."); }
    void run() { /* ... */ }
};

Application app; // definition
```

为了测试我们的代码，我们还添加了一个应用程序类。它的默认构造函数会记录“应用程序启动”，然后我们提供另一个全局变量。

```cpp
$ clang++ -std=c++17 logger.cpp main.cpp
$ ./a.out
Application startup.

$ clang++ -std=c++17 main.cpp logger.cpp
$ ./a.out
fish: "./a.out" terminated by signal SIGSEGV (Address boundary error)
```

我们继续编译代码，执行它，一切运行良好。然后有一天，我们决定以稍微不同的方式编译它，简单地**交换文件参数的顺序**，再次执行，然后我们的程序**崩溃**了。我们打开调试器，会看到我们在应用程序的构造函数中尝试使用一个尚未构造的日志记录器进行记录。

应用程序和日志记录器都有非平凡的构造函数，需要在某个时刻运行以初始化对象。那么这将在什么时候发生呢？特别是，以什么顺序发生？因为看起来仅仅通过交换文件顺序，初始化顺序就改变了。那么让我们看看标准关于全局变量初始化规则是怎么说的。为了理解这点，我们首先需要看两个重要的概念。

第一个概念是**存储期（storage duration）**。存储期控制对象存储**何时被分配**。C++ 中的每个对象都必须存在于某个内存中，存储期控制该内存何时分配和释放。C++ 中有四种存储期。

```
+--------------------------------+   +---------------------------------+
| 1 Automatic Storage Duration:  |   | 3 Thread Storage Duration:      |
| { // begin                     |   | thread_local int thr;           |
|     ...                        |   |                                 |
|     int automatic = 42;        |   | std::thread thr(...); // begin  |
|     ...                        |   | ...                             |
| } // end                       |   | thr.join(); // end              |
+--------------------------------+   +---------------------------------+
| 2 Dynamic Storage Duration:    |   | 4 Static Storage Duration:      |
| ...                            |   | extern int global;              |
| int* ptr = new int; // begin   |   | // begin                        |
| ...                            |   | int main() {}                   |
| delete ptr; // end             |   | // end                          |
+--------------------------------+   +---------------------------------+
```

第一种是**自动存储期（automatic storage duration）**。这是函数内部局部变量使用的存储期。存储在你进入作用域时分配（在左花括号处），在退出作用域时释放（在右花括号处）。然后我们有**动态存储期（dynamic storage duration）**。这是你拥有完全控制的存储期，存储在你调用 `new` 时分配，在调用 `delete` 时释放。**线程局部变量** 具有**线程存储期（thread storage duration）**。它们的内存在你启动一个新线程时分配。这包括主线程，即程序启动时。在线程结束时（被 join 后）销毁时释放。最后，我们有**静态存储期（static storage duration）**。静态存储期是贯穿整个程序生命周期的存储。它在程序启动时分配，在程序结束时释放。

```cpp
int global_scope;

struct foo
{
    static int static_member;
};

void f()
{
    static int function_local_static;
}
```

这是本次演讲最重要的存储期，也是我们将要重点关注的。具有静态存储期的对象包括：全局作用域或命名空间作用域中的所有内容；静态成员变量（如示例中的 `foo` 的静态成员，因为它们在所有对象之间共享）；以及静态函数变量（函数内部的 `static`）。总的来说，我将把它们称为**全局（global）**。静态成员变量和局部静态变量（函数内部的 `static`）并不完全是全局的，但它们仍然遵循相似的规则。所以我们一并讨论它们。

```cpp
{
    ...
    int automatic = 42; // automatic: lifetime starts
    ...
} // automatic: lifetime ends
```

来自 C++ 标准的第二个概念是**生存期（lifetime）**。生存期控制对象的**构造函数和析构函数何时被调用**。这里我们有一个具有自动存储期的变量，它的生存期从控制流首次到达其定义点时开始。生存期在右花括号处析构函数运行时结束。

如我们所见，生存期与存储期并不相同。我们自动变量的存储是在左花括号处分配的，但生存期只有在我们到达定义点才开始。例如，相同的存储可以用于多个对象。当你手动调用析构函数时就会发生这种情况。然后你结束了一个对象的生存期，之后可以在同一存储中构造另一个对象。

既然我们知道了生存期和存储期，我们就可以更精确地表述我们的问题了。我们想知道的是：具有静态存储期的变量的生存期何时开始？标准对此有何规定？嗯，在非常高的层面上，我们有两个阶段。每个初始化都发生在两个阶段。

第一阶段是**静态初始化阶段（static initialization phase）**。在此阶段，所有全局变量的内存被置零。

一旦完成，第二阶段开始：**动态初始化阶段（dynamic initialization phase）**。在此阶段，初始化表达式被执行。

```cpp
std::string str = "abcdefghijklmnopqrstuvwxyz";
std::size_t length = str.size();
```

这里我们有两个全局变量，一个 `string` 和一个 `size_t`。在静态初始化阶段之后，`string` 将包含一些空指针（大概），而 `size_t` 将是零。然后我们进行动态初始化，这将为 `string` 分配内存，复制内容并相应地设置指针。对于 `size_t`，它将询问 `string` 的大小是多少。

现在，动态初始化的顺序是怎样的？因为这段代码只有在 `string` 在 `size_t` 之前初始化才能工作。

不幸的是，标准并没有真正指定顺序。它说动态初始化的顺序是未指定的（unspecified），除了在同一个翻译单元内，变量是从上到下初始化的。

```cpp
std::ifstream file("config");
Config config(file);
```

```cpp
extern Config config; // declaration

std::string key = "verbose";
bool is_verbose = config[key];
```

这里我们有两个翻译单元（它们只是预处理后的源文件，所有头文件都已粘贴进去）。`Config.cpp` 有一个全局的 `ifStream` 对象和一个全局的 `config` 对象，它们存在依赖关系，`config` 对象使用了全局的 `file`。`User.cpp` 有一个全局的 `string` 对象和一个访问 `string` 和 `config` 的布尔值 `isVerbose`。

我们知道在同一个翻译单元内，变量是从上到下初始化的。所以我们知道 `file` 将在 `config` 之前初始化，`key` 将在 `isVerbose` 之前初始化。我们不知道的是 `isVerbose` 和 `config` 之间的顺序会发生什么。由于它们定义在不同的翻译单元中，它们的顺序是未指定的。所以 `isVerbose` 可能在 `config` 之后初始化（这种情况下我们的程序可以工作），也可能在 `config` 之前初始化（这种情况下我们的程序将无法工作）。

这是动态初始化的一般规则，但有两个重要的特殊情况我们需要讨论。

```cpp
constexpr int f(int i) { return 2 * i; }

int favorite_number = 11;    // literal
int the_answer       = f(21); // constant expression
```

第一种是**常量初始化（constant initialization）**。当你有一个全局变量，其初始化器是某个常量表达式（基本上是 `constexpr` 表达式）时，它们在静态初始化阶段就完全初始化了，不需要进行任何动态初始化。所以，是的，我们的全局变量 `favorite_number` 将被初始化为 11，因为这是一个编译时常量，所以它将在静态初始化阶段完成。`answer` 是通过调用函数 `f()` 来初始化的。`f` 是 `constexpr` 的，所以当你调用它时，这也可以在编译时完成。因此它也发生在静态初始化阶段，不需要任何动态初始化。这是一个保证。这不是编译器可以做的优化，这是一个保证。如果你有一个常量初始化器，该变量就不会参与动态初始化阶段。正如我们将看到的，这真的非常有用。

```cpp
void compute(bool trivial)
{
    if (!trivial)
    {
        static int input = 7;           // constant!
        static int result = 5 * input;  // dynamic
    }
}

...
compute(true);
...
compute(false); // initialization of result
```

第二种特殊情况是**函数局部静态变量（function local statics）**。函数局部静态变量的动态初始化被推迟到控制流首次到达其定义点时。所以这里我们有一个 `compute` 函数，它定义了两个函数局部静态变量。`input` 有一个常量初始化器，所以它无论如何都会在静态初始化阶段完成初始化（但在此上下文中，它是在函数首次被调用时才定义）。但 `result` 有一个动态初始化器，因为它读取另一个全局变量 `global_value` 的值。根据定义，除非 `global_value` 是 `constexpr`，否则这就是动态初始化。`result` 的初始化被推迟到我们实际到达其定义点。所以当我们调用 `compute(false)`（在最底部）时。调用 `compute(false)` 没有进入 `if (b)` 分支，因此它不会初始化 `result`。只有当我们调用 `compute(true)` 时，编译器才会初始化它。特别是，如果我们从不调用 `compute(false)`，我们的函数局部静态变量就永远不会被初始化。函数局部静态变量是按需在首次访问时惰性初始化的。

有了这些知识，我们可以创建一个初始化时间线：

1. 执行常量初始化和零初始化。
2. 完成后，执行所有尚未被正确初始化的对象的动态初始化。
3. 然后开始执行 `main` 函数。
4. 然后根据需要初始化函数局部静态变量。

```cpp
// Note: it is impossible to read uninitialized global memory.
extern int other;
int global = other; // guaranteed to read 0 or final value of other
```

作为这些规则的结果，读取未初始化的全局内存是不可能的。这里我们有一个翻译单元包含 `global` 的定义，它读取 `other`，而 `other` 定义在某个其他翻译单元中。如果编译器选择在 `global` 之前初始化 `other`，一切正常，我们读取的是最终值。如果它没有（即先初始化 `global`），我们将会得到零，因为在动态初始化开始之前，所有内容都已被静态初始化（置零）。所以虽然这段代码在所有情况下都不会达到我们想要的效果，但它至少会读取某个定义良好的值（零）。

现在，这些是基本规则，而在 C++ 中，总有一些边界情况需要覆盖。所以这里是该规则的所有边界情况。

```cpp
// header.h
inline int global = compute();
inline int h = global; // ok?

// a.cpp
#include "header.h"
int a = global; // ok?

// b.cpp
#include "header.h"
int b = global; // ok?
```

第一种是**内联变量（inline variables）**。它们是 C++17 的补充，就像内联函数一样，它们允许我们在头文件中完全定义一个变量。这将创建多个定义，但链接器会处理它们并只保留一个。这里我们有一个头文件，其中有两个内联全局变量 `global` 和 `h`。`h` 会读取 `global`。这样行得通吗？嗯，直观上我们期望它能工作，因为 `global` 总是定义在 `h` 之前。所以它应该在那之前初始化。但是当我们开始在其他翻译单元中包含这个头文件时呢？`a` 也在读取 `global`，`b` 也是。这些读取操作可以吗？嗯，仅遵循基本规则，`global` 和 `h` 都定义在与 `a` 或 `b` 相同的翻译单元中（分别地）。所以它们会从上到下初始化。但在最终程序中只有一个 `global` 副本，它不可能同时在两个翻译单元中定义。所以有特殊规则。这里真正意译标准的话：内联变量的初始化行为就像它们是在一个任意的翻译单元中定义的一样。所以 `h` 对 `global` 的读取总是没问题的，因为无论它们最终在哪个翻译单元中，`global` 都定义在 `h` 之前，所以 `global` 会先初始化。但 `a` 和 `b` 都不能保证工作。只有当编译器选择在定义它们的那个翻译单元中初始化它们时才有效。

```cpp
template <typename T>
int type_id = get_id<T>();

template <typename T>
struct templ
{
    static int type_id = get_id<T>();
};
```

第二个边界情况是**模板化变量（templated variables）**。这里特别之处在于，模板化变量在实例化之前并不真正存在。因此初始化不仅取决于它们定义的翻译单元，还取决于它们首次实例化的翻译单元。所以标准并没有真正给我们任何保证。它只是说它们会在 `main` 之前的某个时刻初始化，但我们不知道具体是什么时候。这使得它们使用起来非常棘手，正如我们将看到的。

```cpp
int f(int i) { return 2 * i; } // not constexpr
int the_answer = f(21); // might happen at compile-time
```

编译器允许在编译时执行动态初始化。这里我们再次看到 `answer`。我们仍然在调用 `f()`，但 `f` 不再是 `constexpr`。它仍然可以在编译时执行。我们仍然可以将其标记为 `constexpr`。所以编译器可以自由地在编译时初始化它。但这不再是保证。这是一种优化。如果我们用 `constexpr` 标记 `f`，这就是一个保证。编译器必须在编译时初始化它。没有 `constexpr`，就不再是这样了。

```cpp
const auto startup_time = std::chrono::system_clock::now();

int main()
{
    ...
    auto t = startup_time; // might be initialized at this point
    ...
}

// In particular: an unused global variable might not be initialized at all.
```

编译器也被允许做相反的事情：将动态初始化推迟到 `main` 开始执行之后的某个时间点。这里我们有一个包含启动时间的全局变量。但编译器可以自由地将初始化推迟到我们实际第一次读取该全局变量的时候。特别是，如果你从不使用一个全局变量，它可能根本不会被初始化。编译器不一定会这样做，因为这开销更大，但这条规则的存在是为了允许库的延迟动态链接。如果在运行时的某个时刻，我们加载另一个包含全局变量的库，这些库只能在加载它们时初始化，而不是在 `main` 开始执行之前。所以编译器可以自由地推迟动态初始化。

这些是关于初始化的大量规则，但主要的要点是：不同翻译单元中全局变量的动态初始化顺序**未被标准指定**。

这种动态初始化顺序的缺失被称为**静态初始化顺序问题（static initialization order fiasco）**，因为命名很难。这不是标准为了刁难你才这样做的。标准无法指定它是因为 C++ 的编译模型。编译器将完全独立地编译每个翻译单元，没有任何通信。因此翻译单元无法协调出一个全局的初始化顺序以使一切顺利进行。只有在一个翻译单元内部，我们才能对初始化做出任何保证。

```cpp
// logger.cpp
Logger logger; // definition

// main.cpp
class Application
{
public:
    Application() { logger.log("Application startup."); }
    void run() { /* ... */ }
};

Application app; // definition
```

现在我们理解了这些规则，就能理解为什么我们最初的程序失败了。`logger` 定义在 `logger.cpp` 中，`application` 定义在 `main.cpp` 中。这些是不同的翻译单元。因此我们不能依赖它们之间的任何特定定义顺序。看起来当我们用 Clang 编译时，Clang 选择了命令行上文件的顺序来决定初始化顺序。所以当我们把 `logger` 放在前面时，`logger` 先初始化；当我们把 `main` 放在前面时，`main` 先初始化。

```cpp
class Application
{
public:
    Application()
    {
        std::cout << "Hello";   // OK?
        std::puts(" World");    // OK?
        int* ptr = new int(42); // OK?
    }
};

Application app;
```

问题甚至比这更严重。还有或多或少**隐藏的全局状态**。例如，我们能否安全地在应用程序构造函数中使用 `cout` 打印东西？`cout` 是一个全局变量，那么它会被初始化吗？使用 `puts` 呢？嗯，那只是一个函数。在内部，它必须有一些全局状态，比如输出缓冲区等等。这些会被初始化吗？使用 `new` 呢？堆肯定有一些内部控制结构需要在被使用之前设置好。那么这样做可以吗？我刚刚在聊天中看到一个关于 Meyer 单例（Meyer Singleton）的问题。我们稍后会回到这个问题。

因此，从所有这些规则中得出的主要要点再次是：**除非其文档另有说明，否则你不应该在另一个全局对象的构造函数中访问全局状态。** 它不被要求能正常工作。

那么我们如何才能真正确保我们的全局对象可以安全使用呢？我们如何编写一个可以在应用程序构造函数中安全使用的日志记录器呢？让我们看看各种解决方案。

```cpp
constexpr float pi = 3.1415...;      // always OK
constexpr std::size_t threshold = 8; // always OK
```

第一个是使用**常量初始化（constant initialization）**。根据常量初始化的规则，由某个常量表达式初始化的全局变量在静态初始化阶段初始化，不需要进行任何动态初始化。特别地，常量表达式不能访问动态初始化的全局变量。这使得它不可能依赖另一个全局变量的值，但其他全局变量可以安全地依赖我们。因此，只要可能，你应该将全局变量设为 `constexpr`。这总是安全的。它们将在静态初始化阶段初始化。因此当动态初始化开始时，它们已经可以安全使用了。而且它们本身不能访问其他非 `constexpr` 的全局变量。所以一切都能顺利进行。当然，这有一个很大的缺点：现在我们的全局变量是不可变的（immutable）。这并不总是我们想要的。所以仍然是一个较弱的指导原则：**尽可能使用常量初始化**。因此，不是让变量本身是 `constexpr`，而是让初始化表达式是 `constexpr` 的。

```cpp
class mutex
{
public:
    constexpr mutex();
};

std::mutex mutex; // always OK
```

有一些令人惊讶的常量初始化例子。例如，你知道 `std::mutex` 有一个 `constexpr` 默认构造函数吗？`std::mutex` 根本不是设计用于编译时的。它是线程间的同步原语，而这尚未在编译时发生。但它仍然有一个 `constexpr` 默认构造函数。这正是为了利用常量初始化。当我们有一个全局的 `std::mutex` 时，它总是可以安全使用，因为它使用了常量初始化。当然，仅仅通过看到定义并不明显就能知道它是安全的。而且它可能变得更加脆弱。

```cpp
constexpr int compute(bool use_default)
{
    if (use_default)
        return 42;
    else
        return std::getchar();
}

int the_answer   = compute(true);  // constant initialization
int the_response = compute(false); // dynamic initialization
```

例如，这里我们有 `answer`，它被初始化为 `compute(true)`。`compute` 是一个 `constexpr` 函数。如果我们调用 `compute(true)`，它只会返回 42。所以这是常量初始化。但 `response` 是使用 `compute(false)` 初始化的。如果我们调用 `compute(false)`，这将走不同的分支并实际调用 `getchar()`。这在编译时还不可能完成。所以这使用了动态初始化。而 `compute` 是一个完全没问题的 `constexpr` 函数，因为存在一组参数组合（`true`）使得它能在编译时工作。这对编译器来说就足够了。所以，不仅初始化表达式只使用 `constexpr` 函数是不够的，`constexpr` 函数内部的分支也需要完全是 `constexpr` 的。这真的非常脆弱。


我们想要的是有人要求编译器仔细检查：“嘿，我打算在这里使用常量初始化。请检查一下。” 这正是 C++20 所增加的：一个新的关键字 `constinit`。`constinit` 就像是 `constexpr` 减去 `const`。该变量将使用常量初始化，否则你会得到一个编译时错误。但变量本身不是 `const`，可以在运行时使用和修改。

```cpp
constinit std::mutex mutex; // always OK (else compile-time error)

constinit int the_answer   = compute(true);  // always OK
constinit int the_response = compute(false); // error
```

所以使用 `constinit`，我们可以创建一个全局互斥锁作为 `constinit std::mutex;`。这总是安全的，否则我们会得到编译时错误。`answer` 可以被标记为 `constinit`，因为它是常量初始化。而 `response`，如果你尝试将其标记为 `constinit`，这将是一个错误。

因此，使用 `constinit`，我们可以要求编译器检查我们的全局变量是否在编译时初始化。你应该将全局变量声明为 `constinit` 来检查初始化问题。如果它作为 `constinit` 编译通过，你就没有任何问题。否则，你需要在这里寻找不同的解决方案。

需要指出的是，`constinit` **并不改变初始化时间**。即使你不放 `constinit` 在那里，它仍然会使用常量表达式，所以它仍然会在编译时初始化。`constinit` 只是为你双重检查了这一点。所以你今天就可以开始使用 `constinit`。你只需要用宏包装它。这个宏在你不支持 `constinit` 时扩展为空，否则一切正常。这是我添加到 Atum 库的第一样东西：一个你今天就可以开始使用的 `constinit` 宏。

所以有人问现在编译器是否实现了全局互斥锁的 `constinit`。我会在演讲结束时回答这个问题。

好的。为了使 `constinit` 正常工作，它需要一个 `constexpr` 构造函数。所以你应该尝试为你想要作为 `constinit` 全局变量的类型添加 `constexpr` 构造函数。在很多情况下构造函数都可以做到这一点。例如，容器的默认构造函数可以做成 `constexpr`。它不需要分配任何东西。它只是将一些大小设为零，一些指针设为 null 等等。这可以在编译时完成。如果你有一个作为资源句柄（resource handle）的类（如文件、套接字等），它可能有一个空的“被移动状态”（moved-from state）。所以你可以给它一个 `constexpr` 构造函数，将其初始化为该状态（空状态）。这允许你安全地将它们用作全局变量，因为它们在静态初始化阶段就被初始化了。

```cpp
// logger.hpp:

class Logger
{
    std::optional<std::ofstream> file_out_;

public:
    constexpr Logger() = default;

    void log(std::string_view msg);
};

extern constinit Logger logger; // declaration
```

我们的日志记录器不是这些类型之一。它的默认构造函数打开了一个文件，这不是 `constexpr`。因此我们改变策略，将 `file` 放入一个 `optional` 中。然后默认构造函数将构造一个空的 `optional`，这可以被 `constexpr` 地完成。所以我们可以将其标记为 `constexpr`（实际上是指整个类的默认构造函数是 `constexpr`），并可以为我们的日志记录器使用 `constinit`。

```cpp
// logger.cpp:

constinit Logger logger; // definition

void Logger::log(std::string_view msg)
{
    if (!file_out_)
        file_out_.emplace("log.txt");
    *file_out_ << msg << '\n';
    std::cout << msg << '\n';
}
```

当然，我们还需要改变定义。当我们第一次调用 `log` 时，我们需要打开文件。这完全解决了静态初始化顺序问题，因为现在我们本质上是在做惰性初始化（lazy initialization）。

缺点是我们的惰性初始化不是线程安全的（thread-safe）。所以如果你随后需要进行惰性初始化，就不应该使用 `constinit`。有一个优越得多的解决方案。那么我们现在就来看看它。

**惰性初始化（Lazy Initialization）**。这里的想法是：如果我们是在访问时初始化它，就不可能访问到一个未初始化的全局变量。我们可以利用惰性初始化的函数局部静态变量来实现这一点。它们将被惰性初始化。所以我们可以用它们来惰性初始化我们的全局变量。而且从 C++11 开始，这完全是线程安全的。编译器在内部处理了它，我们不需要担心。

```cpp
// Before
Global global;
...
global.foo(); // potentially uninitialized

// After
Global& global()
{
    static Global g;
    return g;
}
...
global().foo(); // always initialized
```

以前我们有一个普通的旧全局变量（plain old global）。当我们使用它时，这可能是危险的，因为它可能未被初始化。现在我们改变它。我们把全局对象作为函数局部静态变量放在一个函数内部。当我们想访问它时，我们调用那个函数。它给我们一个引用，然后我们就可以使用它了。现在不可能访问到未初始化的全局变量了。

```cpp
Global& get_global()
{
    static Global g;
    return g;
}
Global& global = get_global();
...
global.foo(); // uh-oh
```

我其实不太喜欢这样，因为现在我们不得不调用一个函数来访问全局变量。我的意思是，这有点道理，因为它可能调用构造函数等等。但我真的不喜欢这个语法。所以我尝试这样做：我简单地将函数调用的结果缓存在一个全局引用中。然后我们就可以使用那个引用了。我们内部的全局对象 `g` 总是会被惰性初始化。但引用本身需要初始化。

```cpp
Global& get_global()
{
    static Global g;
    return g;
}
constinit Global& global = get_global();

...

global.foo(); // uh-oh

// error: variable does not have a constant initializer
// constinit Global& global = get_global();
//                   ^        ~~~~~~~~~~~~
```

当我们遵循之前的指导原则并将其设为 `constinit` 时，我们的代码无法编译。因为它调用了一个非 `constexpr` 函数。这很糟糕。这可能会访问一个尚未初始化的引用（可以说是空引用）。所以**永远不要**将函数局部静态变量的引用缓存在全局变量中，或者甚至将其复制到其他地方。这完全违背了惰性初始化的目的，并且你仍然会遇到之前相同的问题。同样，我们可以使用 `constinit` 来捕获此类错误。

```cpp
template <typename Tag, typename T>
class lazy_init
{
public:
    constexpr lazy_init() = default;

    T& get()
    {
        static T global;
        return global;
    }

    T& operator*() { return get(); }
    T* operator->() { return &get(); }
};
```

所以我们不能直接使用引用。但我们还能以某种方式让访问语法更友好吗？想法是使用一个智能指针。我们称之为 `lazy_init`。它是一个指向惰性初始化类型 `T` 的智能指针。所以我们有一个 `get()` 函数，它包含函数局部静态变量并返回它。我们给它提供类似指针的访问方式以便优雅地使用它。以及一个 `constexpr` 默认构造函数。所以智能指针本身可以被 `constinit` 地初始化。所以现在它就在那里了。

我可能应该指出，当你在成员变量中有一个函数局部静态变量时，它是该类的所有对象之间共享的。所以如果你想要两个 `lazy_init<int>`，这不能直接实现。我们需要创建它们，将它们变成不同的类型。这就是 `Tag` 的用途。所以每次我们定义它时，我们给它一个唯一的类型作为标签（tag）。这个标签区分了不同的 `lazy_init` 对象。因此通过使用标签，我们可以拥有多个相同类型的 `lazy_init`。这也是我添加到 Atum 库中的东西。

```cpp
#include <atum.hpp>

constinit atum::lazy_init<struct global_tag, Global> global;

...

global->foo(); // always initialized
```

所以使用 `lazy_init`，我们可以创建我们的 `constinit atum::lazy_init<Tag, Logger>`。我们给它一个唯一的标签。我选择了命名模式 `variable_name_tag`。我们可以在模板参数中轻松声明它，这有点巧妙。然后我们可以使用类似指针的语法访问它：`logger->log("Hello");`。这同样总是工作正常。`lazy_init` 本身使用常量初始化（因为它只是一个空类型，不包含任何东西）。然后我们可以安全地使用类似指针的语法访问它，因为这最终访问的是函数局部静态变量。

```cpp
// logger.hpp:

class Logger
{
    std::ofstream file_out_;

public:
    Logger() : file_out_("log.txt") {}

    void log(std::string_view msg);
};

extern constinit atum::lazy_init<struct logger_tag, Logger> logger;
```

因此我们可以直接将该技术应用于我们的日志记录器。我们不需要改变类本身，它也不需要为此拥有常量默认构造函数。我们只需要将全局变量的类型改为 `constinit atum::lazy_init<logger_tag, Logger>`，给它一个唯一的标签，并适当地定义它。当然，在访问时，我们必须使用指针语法（`->`）。

当然，由于这是惰性初始化，这意味着每次我们调用它时，都可能是第一次使用它。所以它可能开销较大。第一次调用必须做额外的工作。所以如果你有一个像这个片段中的热循环，最好在那之前调用一次日志记录器。Atum 的 `lazy_init` 甚至有一个 `initialized()` 函数，你可以调用它来显式请求初始化。

```cpp
class Application
{
    ~Application() // dtor!
    {
        logger->log("Application shutdown"); // OK?
    }
};

Application app;
```

对我们惰性初始化的解决方案感到满意后，我们继续记录“应用程序关闭”。我们给应用程序对象添加一个析构函数，它只是使用日志记录器。但这能工作吗？虽然它不可能访问一个尚未初始化的日志记录器，但日志记录器在某个时刻会被销毁。那么会发生什么？我们是否真的会遇到尝试访问一个已经被销毁的日志记录器的情况？

要回答这个问题，我们需要看看**全局变量销毁的规则**。这次标准明确指定了它们：它说全局变量以**逆动态初始化顺序**（reverse dynamic initialization order）被销毁，就像其他所有东西一样。但有一个注意事项：当你有一个具有常量初始化器的全局变量时，它们会按照它们（如果使用动态初始化的话）本应有的动态初始化顺序的逆序被销毁。所以，在某个时刻，如果它们使用了动态初始化，它们就会被动态初始化。销毁遵循那个顺序。

```cpp
A a;
constinit B b;

void function()
{
    static C c;
}

int main()
{
    function();
}

// 1. Initialize b.
// 2. Initialize a.
// 3. Initialize c.
// 4. Destroy c.
// 5. Destroy b.
// 6. Destroy a.
```

为了说明，这里我们有几个全局变量：`a`、`b` 和 `c`。`a` 使用动态初始化，`b` 使用常量初始化，`c` 是函数局部静态。从时间线我们知道 `b` 会最先初始化（因为它是常量初始化），然后是 `a`（动态初始化），最后是 `c`（惰性初始化）。我们现在将在程序结束时以逆动态顺序销毁它们。所以我们首先销毁 `c`（因为它最后创建），然后销毁 `b`（因为如果它使用了动态初始化，它会在 `a` 之后被销毁），最后销毁 `a`。

这些规则有点奇怪，但仔细想想是有道理的。`b` 定义在 `a` 之后。所以在某个时刻，我们可以安全地让 `b` 引用 `a`，然后 `b` 就可以自由地使用它。如果 `a` 在 `b` 之前被销毁，`b` 在其析构函数中可能会访问一个已经被销毁的 `a`。所以 `a` 总是在 `b` 之后被销毁，以遵循从上到下的流程（定义顺序）。

有了这些知识，我们可以完成我们的初始化时间线，创建一个程序时间线：

1. 执行初始化（常量初始化 -> 零初始化 -> 动态初始化）。
2. 开始执行 `main` 函数。
3. 然后惰性初始化函数局部静态变量（按需）。
4. 然后程序完成（`main` 返回）。
5. 此时，我们将销毁我们初始化过的函数局部静态变量（按逆序）。
6. 然后我们以逆序销毁其他所有东西（具有动态初始化的全局变量，然后是常量初始化的全局变量）。

现在，虽然标准确实为销毁指定了确切的顺序（逆初始化顺序），但它首先就没有指定初始化顺序。因此，不同翻译单元中全局变量的销毁顺序也是未指定的。这就是**静态销毁顺序问题（static destruction order fiasco）**。它远不如静态初始化顺序问题那么出名，但它仍然可能导致完全相同的问题，只是发生在程序结束时。

因此我们可以给出相同的指导原则：**除非其文档另有说明，否则不要在另一个全局对象的析构函数中访问全局状态。** 这甚至适用于 `constinit` 的全局变量，因为它们可以有非平凡的析构函数（non-trivial destructors）。

```cpp
class Application
{
    ~Application() // dtor
    {
        logger->log("Application shutdown"); // Not OK!
    }
};

Application app;
```

这对 `application` 对象意味着什么？这**保证**不能工作。日志记录器在我们第一次使用它时（在 `application` 构造函数中）被惰性初始化。因此它将在 `application` 之前被销毁。所以当 `application` 析构函数运行时，它保证会访问一个已经被销毁的日志记录器。

这意味着你**不应该**在域结束（end of domain）后可能被使用的情况下使用函数局部静态变量。或者你可以直接说：**不要使用函数局部静态变量**。它们的销毁**太早了**。

好的。还有一个关于线程顺序的问题，我会在演讲结束时提到。

```cpp
template <typename Tag, typename T>
class lazy_init
{
public:
    constexpr lazy_init() = default;

    T& get()
    {
        static T global;
        return global;
    }
};
```

所以，这个使用函数局部静态的 `lazy_init` 实现，并不是真正的实现，因为它不能可靠地工作。我们想确保它不会被过早销毁。最简单的实现方式是确保它**永远不被销毁**。

```cpp
template <typename Tag, typename T>
class lazy_init
{
public:
    constexpr lazy_init() = default;

    T& get()
    {
        if (!_storage.is_initialized())
            _storage.initialize();
        return _storage.get();
    }

private:
    storage<T> _storage;
};
```

所以我们给 `lazy_init` 一个 `storage` 成员。这包含为 `T` 准备的未初始化存储。然后我们的 `get()` 函数在第一次访问时初始化它。我们仍然有一个 `constexpr` 默认构造函数。一旦我们初始化了它，我们永远不会销毁它。

```cpp
template <typename Tag, typename T>
class lazy_init
{
public:
    constexpr lazy_init() = default;

    T& get()
    {
        static bool dummy = (_storage.initialize(), true);
        return _storage.get();
    }

private:
    storage<T> _storage;
};
```

当然，现在我们不再是线程安全的了。而且让惰性初始化既线程安全又高效真的很难。幸运的是我们不需要自己实现它。我们可以让编译器为我们做这件事。我们简单地引入一个虚拟（dummy）函数局部静态变量。虚拟变量的初始化器调用 `storage.initialize()`，然后（使用逗号运算符）变成 `true`。当我们第一次调用 `get()` 时，编译器将以某种方式线程安全地、惰性地初始化 `dummy`。通过这样做，它必须调用 `storage.initialize()`，这也初始化了我们的 `T`。

所以现在我们有了一个 `lazy_init`，它是安全惰性初始化的，但实际上从不销毁任何东西。

当然，我们可以创建一个 `lazy_init<string>`，它分配内存，但该内存永远不会被释放。这是内存泄漏吗？我们可以问 Clang（`-fsanitize=leak`），它会说不是。这是有道理的。这不是真正的内存泄漏。内存并没有丢失，我们仍然拥有它。我们只是没有费心在程序结束时释放它。程序结束后，操作系统会立即回收它。所以何必麻烦呢？那 `lazy_init<ofstream>` 呢？它大概有一个打开的文件句柄。这是文件句柄泄漏（file leak）吗？算是吧。但就像，操作系统会在程序结束后立即关闭所有打开的文件句柄。所以重点是什么？

当然，如果你有一个全局变量，它的析构函数做实际的工作，比如保存应用程序状态或通过网络通信等等，那么这（不调用析构函数）就不会发生。所以这不会造成实际的泄漏（resource leak beyond OS cleanup）。但如果你有重要的工作要做，**为什么**你要把它放在全局对象的析构函数里呢？它会在某个时刻运行，对吧？你最好在 `main` 中显式地做它，当你可以明确控制它何时以及如何发生的时候。而不是放在一个全局析构函数里，在编译器觉得合适的时候运行（这顺序不可控）。但我能理解如果这对你来说不能令人满意。

那么，有没有办法拥有两个被正确销毁的、合适的全局变量呢？答案是有的。为此我们必须看看**巧妙计数器（Nifty Counters）**。

```cpp
class Global
{
public:
    Global()
    {
        std::cout << "Hello World\n"; // OK?
    }
};

Global global;
```

如果你回想演讲开头，我介绍了我们的全局变量，并问在我们的应用程序构造函数中使用 `cout` 是否安全。标准说可以。具有静态存储期对象的构造函数和析构函数可以访问 `cout`。但标准如何真正保证这一点呢？它只是标准魔法吗？不是。我们可以做同样的技巧。我们利用我们拥有的唯一顺序保证：在**一个翻译单元内**，变量是从上到下初始化的。我们知道两件事：你必须在使用全局变量之前包含声明它的头文件；并且定义在该头文件中的每个全局变量都会在你的全局变量之前初始化，因为它被粘贴在你的代码前面。

```cpp
// header.hpp
static Global global; // definition

// a.cpp
#include "header.hpp"
int a = global.foo();

// b.cpp
#include "header.hpp"
int b = global.foo();

// But this creates multiple globals!
```

因此，通过在头文件中静态定义一个全局变量（例如一个计数器），它将被包含到每个包含该头文件的翻译单元中。这意味着 `A` 和 `B` 都将访问一个已被正确初始化的全局变量（`cout`），因为（包含在头文件里的）那个全局变量（计数器）定义在它们之前。由于我们讨论过的规则，它也将在它们之后被销毁。所以这就能正常工作。

当然，缺点是，这创建了多个全局变量（多个计数器实例），这不是我们想要的。所以我们做和之前惰性初始化类似的事情：我们利用一个静态变量来为我们完成工作。

```cpp
// header.hpp
extern Global global; // declaration
static int dummy 
    = (ensure_global_is_initialized(), 0); // definition!

// a.cpp
#include "header.hpp"
int a = global.foo();

// b.cpp
#include "header.hpp"
int b = global.foo();
```

想法是这样的：我们在头文件中声明我们的全局变量（例如 `cout`），并在某个其他翻译单元中定义它（像往常一样）。然后我们向该头文件添加一个虚拟静态变量（dummy static variable），其初始化器具有初始化我们全局变量的副作用。然后，当我们包含该头文件时，它必然引入这个虚拟变量（计数器）。编译器将在该翻译单元中的所有其他东西之前初始化这个虚拟变量（计数器），这就会初始化我们的全局变量（`cout`）。所以这工作正常。

```cpp
template <typename T>
class nifty_init
{
public:
    constexpr nifty_init() = default;

    void initialize()
    {
        if (!_storage.is_initialized())
            _storage.initialize();
    }

private:
    storage<T> _storage;
};
```

我也在 Atum 库中添加了对它的支持。所以是另一个智能指针类型，它就像一个指向通过巧妙计数器初始化的 `T` 的指针。我们再次使用我们的 `storage`（不构造任何东西），并给它一个 `constexpr` 默认构造函数。然后我们添加一个 `initialize()` 函数，如果还没做就初始化 `storage`。

```cpp
// header.hpp
extern constinit atum::nifty_init<Global> global; // declaration
static int dummy 
    = (global.initialize(), 0); // definition!

// a.cpp
#include "header.hpp"
int a = global->foo();

// b.cpp
#include "header.hpp"
int b = global->foo();
```

然后我们可以创建我们的全局变量作为 `constinit atum::nifty_init<Logger> logger;`（应为 `global`）。因为全局变量本身现在总是可以安全使用（它的构造函数不做任何事）。然后我们定义静态计数器 `static int nifty_counter;`，其初始化器将调用 `logger.initialize()`。

```
If initialization in a.cpp is done before b.cpp:
  1 Initialize dummy in a.cpp: initializes global
  2 Initialize a in a.cpp: OK
  3 Initialize dummy in b.cpp: no effect
  4 Initialize b in b.cpp: OK

If initialization in b.cpp is done before a.cpp:
  1 Initialize dummy in b.cpp: initializes global
  2 Initialize b in b.cpp: OK
  3 Initialize dummy in a.cpp: no effect
  4 Initialize a in a.cpp: OK
```

让我们梳理一下：

- 如果编译器选择在 `b.cpp` 之前初始化 `a.cpp` 的所有内容，它会从上到下进行。所以它会先初始化 `a.cpp` 中的 `dummy`（计数器）。这样做时，它将调用 `logger` 的 `initialize()`，这会初始化我们的全局 `logger`。然后当它初始化 `a` 时，`logger` 已经被构造了，所以可以安全使用。然后编译器将初始化 `b.cpp` 的内容，从上到下。所以先初始化 `b.cpp` 中的 `dummy`（计数器）。这不再做任何事（因为 `logger` 已经初始化了）。`b` 仍然是安全的。
- 如果它以另一种方式做（先初始化 `b.cpp` 再初始化 `a.cpp`），`b.cpp` 中的 `dummy`（计数器）将完成实际工作。`b` 就可以自由使用它。`a.cpp` 中的 `dummy`（计数器）不再有效果。
- 即使编译器选择交错初始化顺序或其他情况，这总能正常工作，基于我们拥有的顺序保证。

```cpp
template <typename T>
class nifty_init
{
public:
    void initialize()
    {
        if (_counter++ == 0) _storage.initialize();
    }
    void destroy()
    {
        if (--_counter == 0) _storage.get().~T();
    }

private:
    int _counter = 0;
};
```

这个惯用法被称为**巧妙计数器惯用法（nifty counter idiom）**。我们也可以确保销毁。我们知道应该在什么时候销毁东西：应该在初始化它们的那个计数器被销毁时销毁它们。所以我们给 `nifty_init` 类一个计数器和一个 `destroy()` 函数。`initialize()` 增加计数器，并在第一次调用时（计数器从 0 到 1）真正调用初始化（构造对象）。`destroy()` 减少计数器，当计数器再次达到零时销毁对象（析构对象）。然后我们不能再使用一个 `int` 作为计数器，因为我们需要一个析构函数。

```cpp
template <typename NiftyInitT>
struct nifty_counter_for
{
    NiftyInitT& _nifty_init;

    nifty_counter_for(NiftyInitT& nifty_init)
        : _nifty_init(nifty_init)
    {
        _nifty_init.initialize();
    }

    ~nifty_counter_for()
    {
        _nifty_init.destroy();
    }
};
```

所以我们把它变成一个 `nifty_counter_for` 类（或结构体）。它的构造函数调用 `initialize()`（增加计数器并可能初始化对象），它的析构函数调用 `destroy()`（减少计数器并在最后一次时销毁对象）。碰巧的是，那个第一次在构造函数中调用 `initialize()` 的 nifty 对象，也将会是最后一个被销毁的。所以它在最后一次（计数器归零时）调用 `destroy()`。因此销毁也能工作。


```cpp
template <typename NiftyInitT, NiftyInitT& NiftyInit>
struct nifty_counter_for
{
    nifty_counter_for()
    {
        NiftyInit.initialize();
    }
    ~nifty_counter_for()
    {
        NiftyInit.destroy();
    }
};
```

这个实现（在头文件中定义静态计数器）的代价是每个翻译单元都有一个全局计数器实例。但我们可以通过将计数器的引用作为非类型模板参数（non-type template parameter）来消除它。一个全局引用在编译时是某种程度已知的。

```cpp
template <auto& NiftyInit>
struct nifty_counter_for
{
    nifty_counter_for()
    {
        NiftyInit.initialize();
    }
    ~nifty_counter_for()
    {
        NiftyInit.destroy();
    }
};
```

在 C++17 中，你甚至可以使用 `auto` 来省略类型（在模板参数中）。

```cpp
// header.hpp
extern constinit atum::nifty_init<Global> global;  // declaration
static atum::nifty_counter_for<global> dummy;     // definition

// a.cpp
#include "header.hpp"
int a = global->foo();

// b.cpp
#include "header.hpp"
int b = global->foo();
```

所以这样，我们的全局变量看起来像这样。

```cpp
template <typename T>
class nifty_init
{
public:
    constexpr nifty_init() = default;

    constexpr T& reference() { return _storage.get(); }

private:
    storage<T> _storage;
};
```

当然，我们仍然使用类似指针的语法（`logger->log(...)`）访问全局变量。但我们甚至可以修复这一点。我们需要做的就是在 `nifty_init` 中添加一个 `reference()` 方法，它是 `constexpr` 的，并返回对存储位置的引用（该位置稍后将包含对象）。形成对尚未包含对象的存储位置的引用是完全没问题的（在 C++ 对象模型中允许），我们只是不能在编译时访问它（否则编译失败）。

```cpp
// header.hpp
extern constinit atum::nifty_init<Global> global_init; // declaration
static atum::nifty_counter_for<global_init> dummy; // definition
inline constinit Global& global = global_init.reference();

// a.cpp
#include "header.hpp"
int a = global.foo();

// b.cpp
#include "header.hpp"
int b = global.foo();
```

所以这样，我们向头文件添加另一个全局引用。

```cpp
// header.hpp
extern constinit atum::nifty_init<Global> global_init; // declaration
static atum::nifty_counter_for<global_init> dummy; // definition
inline constinit Global& global = global_init.reference();

constinit Global copy = global; // compile error
```

这个引用只是常量初始化地绑定到我们稍后将包含全局对象的位置。然后我们可以自由地使用这个引用 `logger_ref.log(...);` 来访问它。不可能在 `logger_ref` 被绑定到正确位置之前访问它（全局对象）。如果我们尝试这样做，例如通过 `constinit auto global_copy = logger_ref;`，这将是一个编译错误，因为它不是 `constinit`（尝试在编译时访问尚未构造的对象）。如果我们以其他方式做任何事情，我们无法做到（在静态初始化阶段访问未初始化的引用会被编译器诊断为未定义行为（UB））。

```cpp
// logger.hpp

class Logger
{
    std::ofstream file_out_;

public:
    Logger() : file_out_("log.txt") {}
    void log(std::string_view msg);
};

extern constinit atum::nifty_init<Logger> logger_init;
static atum::nifty_counter_for<logger_init> logger_counter;
extern constinit Logger& logger;
```

因此，将其应用到我们的日志记录器：我们再次保留原始类。然后我们只需添加 `constinit Atum::nifty_init<Logger> logger;` 来存储未初始化的存储（`storage`）。我们在每个翻译单元中添加一个静态的 `logger_nifty_counter`（或者通过模板/外部定义优化）和一个 `constinit` 引用 `logger_ref`。

```cpp
// logger.cpp

constinit atum::nifty_init<Logger> logger_init;
constinit Logger& logger = logger_init.reference();
```

然后我们在翻译单元中定义它们。这样我们就完全解决了静态初始化顺序问题，而不需要改变任何访问语法或其他东西。我们的日志记录器将被正确销毁，一切正常。

```cpp
class std::ios_base::Init {
public:
    Init();
    Init(const Init&) = default;
    ~Init();
    Init& operator=(const Init&) = default;
private:
    static int init_cnt; // exposition only
};

// 后面的代码自己看幻灯片，不贴了
```

这种技术正是标准为 `cout` 所做的。有一个叫 `__iosinit` 的类（在标准库实现中常见，如 `std::__ioinit`）。它的名字以大写字母开头（实际实现常以下划线开头），我不知道为什么。这是一个空的计数器。它甚至在那里有初始化计数器。标准规定，当你包含 `<iostream>` 时，其效果应如同你获得了一个具有静态存储期的 `__iosinit` 对象（或类似机制）。所以它使用了巧妙计数器。

当然，如果你足够努力，我们可以破坏它。例如，我们可以在头文件中定义我们的类 `Global`。然后它的默认构造函数想要使用 `cout`。为了整洁，我们只在源文件（.cpp）中包含 `<iostream>`，而不在头文件中。这意味着源文件（.cpp）最终会有巧妙计数器对象。然而，当我们在不同的翻译单元中定义 `global` 时，仅仅包含头文件并不会给我们带来巧妙计数器对象。所以在 `global` 初始化时（调用默认构造函数），我们必须也在那个翻译单元中包含 `<iostream>` 来获得巧妙计数器对象在那里。当使用一个依赖巧妙计数器的全局变量时，我们需要确保包含必要的头文件以引入计数器对象。

那个方法（只在 .cpp 包含）对于模板化对象不起作用。这就是标准暴露 `__iosinit` 的原因。思路是你会手动构造它（通过包含 `<iostream>`），然后就可以安全使用了。

有人问我们是否可以为巧妙计数器对象使用内联静态变量（inline static），以便只有一个巧妙计数器。现在我们**不能**这样做，因为我们需要在每个翻译单元中有一个巧妙计数器对象（`nifty_counter` 实例），否则它不会参与翻译单元内的排序保证（guarantees）。一个声明为 `inline static` 的巧妙计数器对象**不参与**排序保证。哦，等等，如果它被定义为 `inline static`，我不确定（具体规则）。但如果是定义为 `inline`，它就不参与（翻译单元内从上到下的初始化顺序）。巧妙计数器对象是一个空类型（empty type），所以它最多占一个字节，或者根本不占空间（空基类优化）。它只是用来让初始化表达式（调用 `initialize()`）被包含进去。实际上只有一个（逻辑上的）巧妙计数器（管理实际全局对象），但每个翻译单元都需要自己的计数器实例（`nifty_counter` 对象）来触发初始化。这些计数器对象本身不包含任何状态（除了计数功能，但计数状态通常由实际管理对象生命周期的单例机制维护）。

回顾我们目前看到的解决方案：

- `constinit` 并不总是适用。
- 惰性初始化（使用函数局部静态）必然会导致泄漏（不调用析构函数）。
- 巧妙计数器（nifty counters）是黑魔法（black magic）。

所以还有一个简单的解决方案：**在 `main` 之前或之后什么也不做**。在 `main` 的第一件事中初始化它们，在 `main` 的最后一件事中销毁它们。这样你就有了完全的控制权。手动完成它。

那么，让我们看看**手动初始化（Manual Initialization）**。我在 Atum 库中添加了另一个类似智能指针的类型：`manual_init`。我们再次使用 `storage`，并显式地可以通过 `initialize()` 和 `destroy()` 来初始化和销毁它。然后我们提供一个简单的 `scoped_initializer`。它接受一个（或多个）`init` 类（如 `manual_init`），在构造时调用 `initialize()`，在析构时调用 `destroy()`。

当我们想要一个全局变量时，我们将其设为 `manual_init`。智能指针本身（`manual_init` 实例）可以再次被设为 `constinit`（它的构造函数是平凡的）。然后，在 `main` 的第一件事中，我们创建一个 `scoped_initializer`，这将初始化我们的全局状态。然后我们就可以自由使用它们了。如果我们有多个全局变量，我们扩展 `scoped_initializer`，它可以一次接受多个引用。构造函数将初始化它们全部，析构函数将按逆序销毁它们全部。然后我们只需要确保我们以正确的顺序提供它们（以满足依赖关系）。

将其应用于我们的日志记录器：不需要再次更改类。只需更改类型：`constinit atum::manual_init<Logger> logger;`。使我们的 `application` 也必须是 `constinit`（否则它在 `main` 开始前初始化，可能早于手动初始化）。然后在 `main` 中创建一个 `scoped_initializer`：`scoped_initializer init(logger, app);`。它首先初始化 `logger`，然后是 `app`。一切正常。
当然，你应该在你的项目中为**所有**全局变量使用手动初始化，或者**一个都不用**。而且你必须记住初始化它们所有。你有完全的控制权，但这也是最容易出错（error prone）的方法。Atum 库有一个调试模式（debug mode），它将在每次访问全局变量时检查它是否已被初始化。这可以帮助你捕获错误，但仍然可能出错。

这些是针对静态初始化顺序问题的四个主要解决方案。
顺便说一下，**Atum**（埃及神 Atum）是左边那个家伙（演讲中可能展示了图片）。他是埃及的“存在之前和存在之后”之神（god of pre-existence and post-existence）。我发现这对于一个处理 `main` 之前或之后对象的初始化和销毁的库来说，是一个完美的名字。我也真的很喜欢 Atum 的双关联系。它是一个 C++17 单头文件库（single header library）。它对标准库的依赖最小（minimal standard library dependencies）。并且有我提到的调试模式。你可以在那个 URL 找到它。我基本上已经展示了它提供的一切，除了策略（policies）。

所以，对于每个智能指针类，你可以通过指定使用其中一种策略来指定它如何被初始化。例如，这里我们有一个全局的 `manual_init<string>`，它使用花括号初始化（braced initialization）将其初始化为 `"abc"`。这些是我可用的策略。作为参考，这是你如何在提供的内存上调用放置 `new`（placement new）的方法。

有人已经问过关于**单例（singletons）** 的问题。
单例本质上是一种类型，但你只能构造一个全局可用的对象。我所谈论的一切也都适用于单例。当你像通常那样定义它们时：

```
T& instance() {
    static T inst;
    return inst;
}
```

使用一个静态实例对象，它给你一个对函数局部静态的引用。这具有我在惰性初始化部分讨论过的所有相同的缺点。你必须非常小心销毁顺序。所以我不推荐这样做。相反，你应该使用像 `atum::lazy_init` 这样的东西。然后你只需要在内部使用 `lazy_init`，并确保只有一个对象等等。但单例部分并不是真正有趣的，全局部分才是——相同的规则适用。

这些规则也适用于**线程局部（thread local）** 全局变量。它们也有静态初始化阶段（当线程启动时）。我们同样没有动态初始化的顺序保证（除了静态初始化（零初始化）在动态初始化之前发生），主线程的动态初始化是分开的。

有人问当对象在不同线程中创建时会发生什么。这不会发生（对于全局变量的静态/动态初始化）。静态初始化阶段完全在一个线程上执行。保证此时没有其他线程可以启动。当我们进行线程局部初始化时，它也会发生（在线程启动时）。函数局部静态的惰性初始化是线程安全的（C++11 起）。所以你不会遇到线程安全问题。这显然是一个单线程问题（指全局初始化顺序）。

关于销毁：线程局部全局变量以逆序销毁（在它们所属的线程结束时）。

**结论（Conclusion）**：每个全局变量都应该不存在（non-existent）或者是 `constinit` 的（这意味着它是可变的（mutable））。这样你就避开了（bypass）静态初始化顺序问题。所以你必须小心 `constinit`。但如果你能的话，对于我的应用程序中的大多数情况，`constinit` 就是我需要的全部。

然后我准备提交一个 90 分钟的演讲。这个会议被取消了。所以我做了一些研究，看看有没有其他 C++20 特性改变了初始化规则。**模块（Modules）** 怎么样？

如前所述，翻译单元之间的动态初始化顺序未被指定，这是由于 C++ 的编译方式：每个翻译单元被完全独立地处理，它们之间没有通信。但是有了模块，这就不再成立了。编译器必须在不同模块之间协调编译。特别是，它必须等到所有被导入的模块都已编译完成后才编译该模块。这意味着标准终于能够给我们额外的保证了。

当你有一个来自导入模块（imported module）的全局变量时，它将会被**首先初始化**。这意味着当我们有一个库模块（library module），其中有两个全局变量 `A` 和 `B`，然后有两个翻译单元导入该库并定义其他全局变量 `C` 和 `D`。我们现在知道 `A` 将在 `B` 之前初始化（像往常一样在模块内部），但也会在 `C` 和 `D` 之前初始化，因为 `C` 和 `D` 都导入了 `library` 模块。我们仍然不知道 `C` 和 `D` 之间的顺序（因为它们之间没有关系），但我们对导入的库有了保证。

这意味着当你使用模块时，你可以直接编写我们的日志记录器，把它放在一个模块中，导出一个定义（就是一个普通的旧日志记录器，不需要其他技巧），然后在应用程序中导入它，它就能正常工作。编译器将首先初始化日志记录器，因为模块被导入了。所以它就工作了。

因此，我演讲的真正结论是：**直接去使用模块（modules）吧。它们解决了一切问题。**

像往常一样，你可以在资源 URL 找到幻灯片和其他链接。如果你在 Twitter 上关注我，我也会把它发出来。如果你真的喜欢我正在做的事情，请考虑支持我。我有一些非常酷的东西在筹备中。敬请期待。非常感谢聆听。
