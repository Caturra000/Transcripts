# 手把手教你移植 U-BOOT 到 ARM 板卡

标题：Porting U-Boot and Linux on New ARM Boards: A Step-by-Step Guide

日期：2017/10/28

作者：Quentin Schulz

链接：[https://www.youtube.com/watch?v=5E0sdYkvq-Q](https://www.youtube.com/watch?v=5E0sdYkvq-Q)

注意：此为 **AI 翻译生成** 的中文转录稿，详细说明请参阅仓库中的 [README](/README.md) 文件。

-------

我想我们现在可以开始了。大家早上好。我是 Quentin，今天我演讲的主题是 U-Boot 和 Linux 在 ARM 平台上的移植入门。这基本上是一个分步指南。不会涉及大量代码，不需要处理驱动程序编写或任何真正涉及代码的内容。

先简单介绍一下我自己。我是 Quentin Schulz。我在 Free Electrons 担任嵌入式 Linux 和内核工程师大约一年了。我一年前开始在内核上写代码。我之所以做这个演讲，是因为我一直在为一个定制的 i.MX6 板卡添加 U-Boot 和 Linux 支持。所以这将是我让 U-Boot 和 Linux 在这个特定板卡上工作的历程反馈。这是一块基于 i.MX6 的板卡。这是一个得到良好支持的 SoC，并且有很多已经得到良好支持的 IP（知识产权模块）。这就是为什么我选择使用这块板卡作为示例，这样就不需要涉及太多编码技能。

正如我在标题中所说，内容分为 U-Boot 和 Linux 两部分。当然，如果解释如何将 Linux 移植到一块板卡上真的那么容易，就不会有嵌入式 Linux 会议（ELCE）了。所以演讲重点在 U-Boot，也会有一小部分关于 Linux。

当你想要为一块板卡添加支持时，有几条黄金法则：

1. 你首先真的、真的希望拥有你的 BSP（板级支持包）的源代码。如果你有它们，你希望在你的平台上编译并运行 BSP 代码。这样，你可以验证 IP 是否真的能用某些代码工作，即使这些代码很丑陋、不易维护或其他问题。
2. 拥有一个参考代码，这样你就可以使用 BSP 中的那些寄存器、工作流程、探测过程等一切内容。并且拥有一个可以用来调试的代码。这真的、真的、真的非常重要。这将极大地帮助你为你的板卡添加支持。
3. 然后，你只想专注于 RAM 初始化和 UART（串口）。只做这些。一旦你有了 UART，你就可以开始调试并添加新的 IP 和功能等等。所以到此为止。只做 RAM、UART，提交（commit）。没问题。然后你可以一次添加一个 IP，然后再提交。因为有时当你为一个新 IP 添加支持时，可能会破坏另一个 IP，这时你就可以用 Git（版本控制）回溯（sack with Git，此处应为 sack，指用 Git 回退）。这些就是黄金法则。

简单介绍一下我使用的、并在上面移植了 U-Boot 和 Linux 的定制板卡。它是一块 i.MX6 Solo 或 Quad。我们有两块板卡：一个核心模块带一个扩展板。在这个产品上，你有以太网支持、I2C、SPI、NAND、eMMC、SD 卡读卡器、USB 设备、I2C 上的 EEPROM、GPIO、UART、I2S 上的音频、HDMI、LVDS、PCIe、USB 主机、RTC 和 PMIC（电源管理 IC）。我认为其中一些在 Linux 中受支持，一些在 U-Boot 中受支持。客户并不需要所有功能。我将介绍我是如何添加支持的以及它有多简单。

第一部分，U-Boot 移植，这是本次演讲的主要部分。
首先，你必须知道 U-Boot 在两个方面正处于过渡阶段。

- 第一个方面是，U-Boot 过去只使用板卡头文件（board header files）。你必须在板卡头文件中定义常量和宏（`#define`），来声明我想探测这个设备，我想这样或那样配置它，以及寄存器基地址等等。还有一些功能，比如你想在 U-Boot 中使用哪些命令，例如 NAND 或 UBI 命令或 FIT 镜像命令等等。现在它正在缓慢地向仅使用 Kconfig 选项迁移。这样你就可以通过 menuconfig 访问它们，这真的非常有帮助。
- 第二个迁移是从模块驱动探测（module driver probing）到驱动模型（driver model）。现在驱动程序在类（class）中注册，我认为基本上更好，但这仍在进行中。所以仍然有一些代码大量使用板卡头文件而不是 Kconfig，驱动模型方面也一样。因此，当你从其他板卡获取灵感时，要小心，因为它们的方式可能已经过时（obsolete）了。

简单介绍一下 U-Boot 架构：

- 首先，你有 `arch` 目录，包含所有与架构（Arch）或平台相关的内容：DTS（设备树源）、设备资源文件、CPU 初始化序列、引脚复用控制器（pinmux controller）、DRAM 控制器、时钟等等。
- 然后你有 `board` 目录。这是板卡特定的代码。就是你板卡的初始化序列（init sequence）。例如，在我们的案例中，我们必须在给定的时序中，在初始化序列里将一组 GPIO 先拉高再拉低，这样板卡才能启动。这就是你放置这个初始化序列的地方。你也有引脚复用配置（pinmux configuration）。
- 一些 Kconfig 文件，用来声明在哪里找到板卡头文件、在哪里找到板卡文件、Makefile 等等。我将解释它们中的每一个。
- 然后你有 `configs` 目录，里面有所有的配置（configs），即 defconfig 文件。
- 然后你有 `drivers`（驱动）。
- 在 `include` 中你有所有的头文件，特别是在 `include/configs` 中，你有所有板卡的头文件。这就是你为你的板卡定义所需常量和宏的地方。
  当然，还有很多，但在这个演讲中不是特别有帮助。

接下来，你需要一个工作流程，这样你就不会迷失方向，并且每次你想为一块新板卡添加支持时都能轻松地做同样的事情。

1. 首先，你想创建板卡文件（board file）。板卡文件是你声明“我的板卡需要这个引脚复用配置”、“它需要这个初始化序列”等内容的文件。
2. 然后你创建板卡配置（Kconfig）文件，用来声明你希望在哪里找到 Makefile、板卡头文件、板卡文件等等。
3. 然后你有 Makefile、该板卡的 defconfig 文件、头文件。
4. 最后两个，你必须在架构的配置（architecture's config）中引入（source）你的板卡配置，以便它能被找到，并在其 CPU 的 Kconfig 中定义目标配置选项（target config option）。我将解释所有这些。

但你必须小心。这个演讲是关于我在 i.MX 6 上的经验，而像 Allwinner 这样的一些平台共享通用文件。所以你不必，例如，做前三点和第五点。你不需要做它们。基本上，对于 Allwinner 板卡，你只需要创建一个 defconfig。

1. 首先，你必须创建板卡文件（board file）。你在 `board/<my_vendor>/` 下创建一个 `<my_board>` 目录，并在里面放置你的板卡文件（例如 `<my_board>.c`）。
   - 你必须创建一个新的数据指针（`gd_t`）。
   - 在这个文件中，你有所有需要的包含（`#include`），以及这个奇怪的 `DECLARE_GLOBAL_DATA_PTR` 声明，它可以在 RAM 初始化之前使用。这是一个你可以使用的寄存器（稍后解释）。
   - 你初始化你的 RAM。基本上，你只需声明 RAM 大小等于某个值（对于 i.MX6，它是 i.MX6 相关的）。
   - 然后你有强制的板卡初始化函数（`board_init`），这基本上是你想要放置所有引脚复用配置代码和启动所需的一切的地方。
   - 关于这个 `DECLARE_GLOBAL_DATA_PTR`：它可以通过 `gd` 全局变量使用，就像你在上一张幻灯片中看到的。在 ARM 上，对于 ARM32 它等于 R9 寄存器，对于 ARM64 等于 X18 寄存器。所以它是一个通用寄存器。U-Boot 在 RAM 初始化之前使用它来设置很多标志。这样它们就知道如何做，例如，RAM 的大小。你也可以在那里禁用控制台（console）等等。很多事情。就像我说的，它存储的信息在启动过程中非常、非常、非常早期（在 RAM 初始化之前）就可用。
   - 是的，基本上你拥有所有信息，包含 `<asm/global_data.h>` 以查找存储了哪些类型的信息。有很多变量。
2. 接下来，我们想创建 Kconfig 文件。这个非常重要的 Kconfig 文件位于同一个目录下：`board/<my_vendor>/<my_board>/`。
   - 首先是 `if TARGET_<MY_BOARD>`。所有的 Kconfig 都在你的架构 Kconfig 中被引入（sourced）。这意味着所有选项都会被处理。你当然只希望你的 `SYS_BOARD`、`SYS_VENDOR` 和 `SYS_CONFIG_NAME` 针对这块特定的板卡。所以你必须在 Kconfig 文件中为你的板卡选项使用 `if` 语句。
   - 然后你设置 `SYS_BOARD` 为默认值 `<my_board>`，`SYS_VENDOR` 为 `<my_vendor>`，`SYS_CONFIG_NAME` 为 `<my_config>`。它们是什么？它们做什么？
     - `SYS_VENDOR` 和 `SYS_BOARD` 用于标识板卡文件的位置。U-Boot 不知道它在哪里。它需要这些 Kconfig 选项。所以：
       - 如果两者都存在，板卡文件将在 `board/$(SYS_VENDOR)/$(SYS_BOARD)/` 下。
       - 如果省略了 `SYS_VENDOR`，它在 `board/$(SYS_BOARD)/` 下。
       - 如果省略了 `SYS_BOARD`，它在 `board/$(SYS_BOARD)/$(SYS_VENDOR)_common/` 下。
     - `SYS_CONFIG_NAME` 用于标识板卡头文件（board header file）。例如，在这里你有 `include/configs/$(SYS_CONFIG_NAME).h`。
   - 所以从前面的幻灯片中，你现在知道你在哪里了... 抱歉。是的，它不是用来找板卡文件的。它是用来找 Make 编译时使用的文件的。从那里，你基本上会有 `board/<my_vendor>/<my_board>/Makefile`。有了 `SYS_CONFIG_NAME`，你就会有 `include/configs/<my_board>.h`。
3. 创建板卡 Makefile。它在 `board/<my_vendor>/<my_board>/Makefile`。然后你只需说，我需要编译 `my_board.o`，这是我的板卡文件的名字（例如 `obj-y += my_board.o`）。
4. 第四步，你需要创建板卡的 defconfig。这里我们有架构（`ARCH=arm`），平台类型（`PLATFORM=imx6`），你想要 `TARGET_<MY_BOARD>`（还记得 Kconfig 文件顶部的那个吗？）。所以这里，在 `CONFIG_` 前缀后面是一样的。当然，我们需要 UART 驱动（`CONFIG_DM_SERIAL=y`）。否则，我们就不会有任何 UART。就是这样。这基本上是你启动一个 i.MX6 空间板卡（space board? 应为 i.MX6 based board）所需的第一件事。
   - 是的，基本上在这个 defconfig 文件中，你放入所有你能找到的、并且可以在 menuconfig 中选择的东西。所以基本上是驱动、功能或命令，像 RSA 或任何其他你可以在 menuconfig 中选择的东西。
5. 这是板卡头文件（board header file）的最小示例。所以第五步，创建你的板卡头文件（`include/configs/<my_board>.h`）。
   - 很多不同的选项。
   - 你在这里看到最重要的一个：`#include <asm/arch/mx6_common.h>`，这基本上是 SoC 的头文件（SOC header file）。你想在所有基于 i.MX6 的板卡中包含它。当然，对于不同的 SoC 或架构，会有不同的文件。
   - 首先，我们想确保我们没有双重包含它（`#ifndef ... #define ... #endif`）。
   - 然后你想定义... 所以这些都是 i.MX6 特定的。你只需说明你的 UART 驱动的基础地址在哪里（`CONFIG_MXC_UART_BASE`）。
   - 还有很多其他的定义常量（`#define`）和如何计算的东西。就是这样。这就是 i.MX6 从一开始让 UART 工作所需的全部。
6. 然后，在你的架构中引入（source）你的板卡 Kconfig 文件。我不太确定。我在 U-Boot 里看了一下。有两种不同的方式来引入你的板卡 Kconfig 文件：要么直接在你的架构（如 ARM）的 Kconfig 中引入，要么在你的平台 Kconfig 文件中引入。就像我在这里展示的，你在 `arch/arm/Kconfig` 中直接引入 `source "board/my_vendor/my_board/Kconfig"`，或者在你的平台 Kconfig 文件中引入。目前，对于 i.MX6，是后一种。但对于所有平台，这取决于情况。所以看看 U-Boot 源代码，找出你应该使用哪一种。
7. 我认为最后一步是将你在 Kconfig 文件中使用的 `TARGET_<MY_BOARD>` Kconfig 选项添加到你的 CPU 的 Kconfig 中（例如 `arch/arm/cpu/armv7/mx6/Kconfig`）。
   - 你只需说，是的，这是我的超棒板卡（`config TARGET_MY_BOARD`），它在 i.MX6 Solo 上（`bool "My awesome board"`）。
   - 在这里，你选择（`select`）所有在 Kconfig 中无法选择的选项。它们在 menuconfig 中可见，但你不能选择它们。对于 `IMX6S` 就是这种情况（`select CPU_V7`, `select SUPPORT_SPL`, `select MX6S`）。
   - 就是这样。

现在你需要知道什么来添加 IP、设置你的板卡等等？有一个非常特定的 U-Boot 初始化序列（init sequence）。

- 首先，你需要知道有两组函数列表会被调用：一组在代码重定位（relocation）到 RAM 之前调用，一组在之后调用。
- 第一组称为 `init_sequence_f`，它在 `common/board_f.c` 中。包含初始化 RAM 所需的一切。基本上，这是非常、非常底层的代码。
- 然后你有 `init_sequence_r`（在 `common/board_r.c` 中），当然是在 `init_sequence_f` 之后执行。然后你可以在里面使用 RAM，时钟等其他东西也初始化了。
- 你必须知道，有些函数只有在定义了某个常量时才会运行。例如，在 `init_sequence_f` 中，有一个名为 `board_early_init_f` 的函数，它只有在你的板卡头文件中定义了 `CONFIG_BOARD_EARLY_INIT_F` 时才会被编译和运行。
- 这两组列表中任何返回非零值的函数都会导致 U-Boot 失败。它会停止，然后你可能停在 UART 输出的中间。所以你知道 U-Boot 开始了，它打印了所有东西... 例如 NAND，我有这么多 GB... 它可能停在中间，只是为了... 所以你知道。
- 为了调试这个，因为它真的很烦人，你可以定义 `DEBUG`。这会添加更多代码。但在这个 `init_sequence_f` 循环中，你会看到哪个函数失败了。
- 你还必须知道，并非所有功能在所有函数中都可用。例如，我们遇到了一个问题，`udelay` 不能在 `board_early_init_f` 中使用。这花了我们大约两天时间才发现。

然后，你当然想启用你的 IP 的驱动。你可能想从具有相同 IP 的板卡中获取灵感。例如，我从 Sabre SD（Sabrelite）板卡中获取灵感，它基本上使用相同的 SoC。所以如果你在寻找正确的驱动和配置选项时遇到麻烦，这是一个好的起点。

1. 你想检查驱动以确保它确实是你想要的。所以进入相应的子系统，例如对于 NAND，你想进入 `drivers/mtd/nand/`。你到那里，打开第一个看起来有点像你想要的或者以你的 IP 命名的文件。
2. 首先关注行为（behavior），看看它是否能匹配。
3. 然后是寄存器（registers）、位偏移（bit offsets）等。
4. 检查未定义的宏（undefined macros）。

所以第一点和第二点是为了选择你想使用的驱动。第三点是为了找出你需要定义哪些宏和常量来让这个驱动工作甚至编译。第四点是你要小心。在 U-Boot 中有很多 `#ifdef` 块。这些也是你想在你的板卡头文件中定义的常量。

然后你想在子系统的 Makefile 中查找这个驱动的目标文件（object file）。例如，对于 NAND，我们会去 `drivers/mtd/nand/Makefile`。我想我稍后会展示它。然后你有你的驱动的基本名称（base name）。例如 `nand_mxs.o`。你知道你需要启用这个驱动。

要启用驱动，你必须设置这个定义（`#define`），可以在你板卡的 Kconfig（即 defconfig）中设置，或者在你的板卡头文件中设置。最好的方法是知道把它放在哪里，就是抓住这个配置选项（`CONFIG_...`）：

- 如果它在某个 Kconfig 文件中是一个可见符号（visible symbol），也就是说如果在 menuconfig 中可见，你就把它添加到板卡的 defconfig 中。
- 如果它在 menuconfig 中不可见（即你在 menuconfig 中能看到它但无法选择它），或者如果它是在其他板卡头文件中定义的，你就把它放在你的板卡头文件中。

确保你的驱动被编译了。这在我身上发生过很多次。所以你想查找 `my_driver.o` 文件。这是一个好的迹象。

一个使用 NAND 驱动的小例子，如何命名它。我为我们的板卡启用了它。

- 驱动 `drivers/mtd/nand/nand_mxs.c` 是我们想用于这块板卡的驱动。我是用前面幻灯片解释的相同方法找到它的。
- 你必须设置三个不同的定义：
  - 第一个是 `CONFIG_NAND_MXS`，你需要它来编译驱动。所以在子系统的 Makefile 中，它是 `obj-$(CONFIG_NAND_MXS) += nand_mxs.o`。你需要在你的 defconfig 中包含它 (`CONFIG_NAND_MXS=y`)。
  - 然后你有 `CONFIG_SYS_MAX_NAND_DEVICE` 和 `CONFIG_SYS_NAND_BASE`，它们是配置你的设备的常量。
- 在你的板卡 defconfig 中，你添加 `CONFIG_NAND_MXS=y` 并说，是的，我想要它。
- 然后你转到下一个，也就是板卡头文件。你定义需要的内容。所以 `CONFIG_SYS_MAX_NAND_DEVICE` 是一个，我们只想要一个设备。它的基地址是这个（`CONFIG_SYS_NAND_BASE=...`）。
- 当然，它是一个 IP。你很可能需要设置引脚复用（pinmux）。所以你到你的板卡文件（`<my_board>.c`）中的 `board_init` 函数里，使用这个 i.MX6 函数（`imx_iomux_v3_setup_multiple_pads(...)`），但你可以直接写寄存器来设置正确的引脚复用配置。
- 就是这样。你现在为 U-Boot 添加了你的驱动，你的 NAND 驱动支持。

关于设备树（device trees）的一点说明。我知道现在 U-Boot 中有设备树。它进展缓慢... 嗯，它始于 2012 年。代码正在缓慢地迁移，驱动一个接一个，子系统一个接一个地迁移以支持设备树。这仍然是一项正在进行的工作。你需要驱动模型（driver model）支持才能使设备树工作。这个驱动模型是通过 `CONFIG_DM` 启用的。大多数子系统和驱动都有很多大的 `#ifdef` 块。所以你不能真正选择你想对哪些驱动使用 DM（驱动模型），哪些不想用。所以这有点像全有或全无（all or nothing）。对我们来说，是无（nothing），因为 NAND 框架现在还没有迁移到 DM 模型。我们必须支持它。所以我不会深入探讨这个。我的意思是，这就是我能说的全部。但你要知道，U-Boot 中有设备树支持。这仍然是一项正在进行的工作。所以如果可以，请帮忙（贡献代码）。

为我的板卡添加 U-Boot 支持所需的工作量基本上是：现在所有工作的东西是以太网、I2C 上的 EEPROM、NAND、eMMC、SD 卡读卡器、USB 设备、UPI（？应为 GPIO）、UART、音频和 PMIC。我需要写的只有 510 行代码，基本上只有一半，因为这里的 160 行仅用于 RAM 配置，是由 BSP 或供应商提供的。所以我必须在架构的 Kconfig 文件中添加一行（`source "board/my_vendor/my_board/Kconfig"`）来引入我的板卡 Kconfig。这个 Kconfig 文件有 15 行长。在 `arch/arm/cpu/armv7/mx6/Kconfig` 中添加了四行代码来定义 `TARGET_MY_BOARD`。实际上只有 100 行代码，只在板卡文件（`<my_board>.c`）的 `board_init` 配置中设置了引脚复用（pinmux）。除此之外，没有修改 U-Boot 源代码。所以这真的很重要。对于 i.MX6 来说真的很简单。

当然，我们遇到了一些错误。我们遇到了一个非常、非常奇怪的错误。对于这个客户，我们必须使用签名的 FIT 镜像（signed FIT image）。U-Boot 实际上在启动前会检查 FIT 镜像。它基于 RSA 库（RSA lib），它就在检查过程中崩溃了。我不得不稍微看一下库代码里面，但找不到任何真正相关的东西。所以运气不好，我就想，为什么不更新 U-Boot 呢，对吧？从 3 月份的 2017 年版本，我升级到了 7 月份的版本。这相当容易。我只需要拿走板卡头文件、板卡文件，基本上就是我之前说的所有东西，并确保在板卡头文件中定义的选项现在不是 Kconfig 选项了。就这样。然后我编译它，运行它，它就工作了。所以我花了大约半个小时就升级好了。所以你知道，一旦你的板卡在上游（upstream）得到支持，更新就真的很简单，你不必因为不理解为什么它不工作而用头撞桌子（bang your head on your table）。你先更新，如果不行，你再去看代码。我认为这是一个相当不错的技术。

还有其他遇到的问题。就像我说的，我们遇到了 `udelay` 的问题。我们的板卡初始化序列基本上是以给定的时序切换（toggling）几个 GPIO。所有信号，这非常重要，所有信号，甚至 UART，都经过它的 FPGA。所以基本上如果 FPGA 没上电，就没有 UART。初始化序列失败，没有 FPGA，没有 UART，头上一根头发都没了（no hair on the head anymore）。所以花了我们，就像我说的，差不多两天才发现你不能在 `board_early_init_f` 中使用 `udelay`。我们的解决方法是使用一个忙等待循环（`for` loop）加 `cpu_relax()`。然后它工作了。所以我认为我们必须给邮件列表发邮件，询问为什么或者在早期启动序列中处理延迟的正确方法是什么。抱歉？（听众插话）好的，谢谢。答案是使用 `timer_init()`，然后你就可以使用 `udelay` 了。好的。所以一旦它初始化了，你就可以直接使用它。谢谢。是的，忘记这张幻灯片吧。

U-Boot 部分就到这里。现在轮到 Linux 内核了，它会非常、非常快，也必须快。你的工作流程：

1. 创建你板卡的设备树（device tree），并将你的设备树二进制文件（DTB）添加到 Makefile 中。
2. 然后为你创建一个 defconfig。
   就是这样。

- 设备树（DTS）是一个特殊格式的文件。设备树源（DTS）纯粹描述你板卡的硬件，或者至少应该是。它通过兼容字符串（compatible strings）将 IP 与驱动匹配起来。
- 你可以在 `Documentation/devicetree/bindings/` 中找到这些设备树节点的文档。
- 当然，我不会在这里介绍设备树本身，因为这是一个非常长的主题。你可以在这里找到一个非常有趣的演讲，由我的同事 Thomas Pettazzoni 四年前做的关于设备树的演讲。

1. 创建一个板卡设备树（`arch/arm/boot/dts/<my_board>.dts`）。
   - 你真的想写一个你的 IP 关系图（map），以了解哪个依赖于哪个。这可以很好地理解你的平台如何工作，你的板卡如何工作。
   - 首先你想找到 SoC 的 DTSI 文件（`.dtsi`）。所有在 SoC 内部的 IP 都已经定义好了。所以你只需要找到 SoC 的 DTSI。对于我们的板卡，是 i.MX6，我想它是 `imx6dl.dtsi`。
   - 然后在正确的子系统中查找 IP 驱动。就像我们在 U-Boot 中做的那样，你进入正确的子系统，然后你可以尝试获取你的 IP 的代号（code name）。这通常是一个好的开始。或者你可以找到与你的 IP 非常接近的 IP。例如，我不得不在另一个主题上，但对于 PMIC，它的代号并不完全相同，但它与一个非常接近的东西一起工作。所以你的兼容字符串（compatible string）不必完全匹配你的 IP 的名称，当然。
   - 一旦找到，在你的驱动中查找兼容字符串（`compatible = "..."`），并在设备树绑定文档（DT binding documentation）中找到它。这样你就知道需要向你的设备树添加哪些属性（properties）。
   - 你遵循文档，编写正确的绑定（binding）。有些绑定是框架级别的（framework-wide）。所以你还需要去框架的设备树绑定文档。这样你就能确保设备树中的所有属性都设置正确了。
   - 是的，基本上对于 i.MX6，这真的很容易，因为 SoC 的 IP 都在 SoC 的 DTSI 中定义好了。我只需要添加它们（到我的板卡 DTS 中）。
2. 这里是我的超棒板卡（`my_awesome_board.dts`）的例子。
   - 我们有 `imx6s`。所以这是一块 i.MX6 Solo 板卡。
   - `.dts` 文件包含（`#include`）正确的 `.dtsi`。它是 `imx6dl.dtsi`，因为它是 Dual Lite 或 Solo 或... 我的意思是，Freescale 真的... 抱歉我的语言，但搞得很混乱（fucked up）。因为你有 i.MX6 Quad (`imx6q.dtsi`)，但它几乎和 DL（Dual Lite）一样。但是是的，Solo 也可以工作。我不知道。
   - 对于 PCIe，我只需要添加复位（reset）GPIO。所以你只需设置 PCIe 的复位 GPIO 是这里（`gpios = <&gpio1 0 GPIO_ACTIVE_LOW>`）。它是低电平有效（active low）。端口电源（`port-supply`）是这个稳压器（`regulator`）。我想启用它（`status = "okay"`）。
   - 就是这样。
3. 然后你想用正确的平台编译你的设备树。当你选择正确的平台时。例如，就像我说的，Freescale 的是 `imx6q`。没有针对 DL 或 S 的选项。所以你把所有属于 i.MX6Q、DL、S 的东西都放在代码的这一部分（`dtb-$(CONFIG_SOC_IMX6Q) += ... my_awesome_board.dtb`）。
4. 当你有一个选择了 `CONFIG_SOC_IMX6Q` 的 defconfig 时，你的 DTS 将被编译成 DTB。
5. 为你的板卡创建一个 defconfig（例如 `arch/arm/configs/my_awesome_board_defconfig`）。
   - 你从你的 SoC 的 defconfig 开始。在我的例子中，它是 `imx_v6_v7_defconfig`。
   - 如果你不像我这么幸运（指 SoC 有专门的 defconfig），你必须从 `multi_v7_defconfig` 开始，它启用了所有 st（？应为 ARMv7）系列和所有驱动。启用了大多数驱动。所以这真的是第二种选择。
   - 你必须做的第二步是剥离（strip）你不需要的所有东西。与你的板卡无关的驱动。功能。基本上所有无用的东西。SoC 家族（`CONFIG_SOC_...`），你不想构建任何东西... Atmail（？）相关的... 嗯，你有一个 i.MX6 SoC。在那里（指在 `multi_v7_defconfig` 基础上）。
   - 然后添加你想构建的驱动的配置（`CONFIG_...=y`）。我说过你像在 U-Boot 中那样获取驱动的基本名称（`.o`）。它在哪里？它在哪里？（指在源码树中的位置）。所以你有 `.o`（目标文件）。你只需取这个名字（指配置符号，通常是 `CONFIG_<SUBSYSTEM>_<DRIVER>`）并把它添加到你的 defconfig 中。当然不是 U-Boot 的那个。是的，开始吧。
   - 你必须知道，大多数驱动当然也依赖于子系统。所以如果你想启用驱动，比如 NAND 驱动，你也必须启用 NAND 子系统。我的意思是，这是合乎逻辑的。

遇到的问题：

- PCI 驱动在探测（probing），但没有枚举（enumerating）任何设备。基本上它在 BSP 中是工作的，所以我知道是我的错，或者是主流（mainline）代码、上游（upstream）缺少了某些东西。事实就是如此。我缺少了一个稳压器支持（regulator support）。是的。我写了一个补丁，发送到上游，就是这样。它工作了。
- 对于驱动（指某个具体驱动），它缺少一个复位后的延迟（post reset delay）。所以它没有初始化。同样。写了一个 20 行的补丁，发送到上游，就是这样。

支持 Linux 所需的工作量。我的意思是，这里列出的所有东西现在都支持了，用了 1000 行代码。是的。大部分是 DTS。所以你得到了设备树绑定文档的帮助。defconfig 只需选择正确的子系统和驱动。所以是在 Makefile 中添加一行（`dtb-$(CONFIG_SOC_IMX6Q) += my_awesome_board.dtb`），在 Makefile 中再添加一行（？指添加 DTB 到编译列表），20 行用于稳压器支持等等。除此之外，没有修改 Linux 源代码。这要归功于得到良好支持的 i.MX6。所以你能够做 DTS 和我们在扩展板上的 IP。

当然我们遇到了一些问题。我们在双显示（dual display）上遇到了一些奇怪的错误。当我们同时启用 HDMI 和 LVDS 的 DTS 节点时，即使输出没有同时连接，这个显示驱动也会崩溃，完全崩溃。我们在邮件列表上收到了一些关于奇怪错误的报告。然后决定，嗯，最好升级到 4.13 版本。他们真的复制了 DTB（指从旧内核复制 DTB 到新内核目录？），确保绑定（bindings）没有变化。是的，它工作了。所以花了半个小时的工作，就解决了我的问题。

基本上我只是想说，一旦你的 SoC 得到了很好的支持，为你的板卡（ball? 应为 board）添加支持就真的很容易，非常、非常容易，而且不耗时。

对我来说就这些了。你们有什么问题吗？我想我们最多还有两三分钟。是的。好的。是的。

（听众1）：关于 i.MX6，我有几点意见。这是一个有点过时（legacy）的设计。这就是为什么它在 U-Boot 中看起来是那样的。它不是超级... 关于引脚复用控制器（pinmux controller）、DRAM 时钟，它们现在实际上进入了驱动（drivers）。好的。因为 i.MX6 是一个过时的设计，它仍然在 `arch/` 里，但在更新的移植中，它进入了 `drivers/`。实际上，如果你在做一个新的移植，你应该总是使用驱动模型（driver model）。所以避免遗留的东西（legacy stuff）。是的。如果可能的话，使用设备树（device tree）。是的。这样它可以与 Linux 共享。同样，由于 i.MX6 有点过时（legacy-ish），它还没到那一步（指完全使用驱动模型和设备树）。是的。我们遇到了一些驱动的问题，当用 DM（驱动模型）编译时，它们根本不能工作。所以... 嗯，修补它（patch it），欢迎（贡献）。是的，修补它。是的，当然。但，嗯，客户真的想要一个立即的解决方案。所以我没有（用 DM）... 否则 i.MX6 的移植显然非常好。是的。顺便说一下，在幻灯片 34 上，你的设备树里有个拼写错误（typo）。好的。谢谢。你想指出来吗？是的，根节点（root node）应该是 `/`（forward slash）。谢谢。哦，好的。谢谢。还有其他人吗？否则就非常好，再见。

（听众2）：好的。抱歉。什么？是的，是的，我会把它放在网上。是的，在网站上。演讲之后马上。不，没关系。

（听众3）：嗨。顺便说一句，幻灯片很棒。但你怎么知道它完成了？我的意思是，你怎么知道你应该完成移植？你的测试套件（test case suit）是什么？你是从客户那里得到的，还是你有一套标准的客户测试集？

（Quentin）：基本上，是的。我使用客户的用例（use case）。所以，你在 U-Boot 中有一组命令（commands）。例如，测试 NAND，你擦除 NAND，写入 NAND，启动现在在 NAND 中的任何东西，或者把它加载到 RAM 中，然后测试它和你从其他方式下载的文件是否相同。所以，基本上，是的，你必须设置你自己的测试。我不知道是否有测试套件，但我不知道，对此一无所知，所以。

（听众3）：好的。

（另一位听众插话）：等等。是的，等等。抱歉？

（听众3）：是的。

（插话者）：好的。所以有一个名为 `mtd-tests` 的包，你可以在 U-Boot 中使用。

（Quentin）：谢谢。是的，但如果你想... 哦，我想问题是在 U-Boot 和 Linux 两方面，对吧？

（听众3）：嗯。

（Quentin）：在 Linux 方面，是 `mtd-tests`。在 U-Boot 方面，是 `nand` 命令。好的。所以在 U-Boot 中，没有真正定义好的东西。你必须自己使用 `nand` 命令。在 Linux 中，是 `mtd-tests`。这回答了问题吗？

（听众3）：是的，好的。谢谢。

（Quentin）：我想，是的。谢谢。

. . . . . . . . . . (转录结束)
