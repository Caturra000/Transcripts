# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
#
# make server
# 启动一个简单的 http 服务器，指向 4000 端口
#
# make html
# 转发给 sphinx-build 构建 html 文件
#
# make transcript <title>
# 创建演讲稿模板，估计只有我自己愿意用了
help:
	@echo "make server"
	@echo "make html"
	@echo "make transcript <title>"
	@echo "=======sphinx======="
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# make server 为调试模式，影响 conf.py 对文件后缀的处理
# 需要 sphinx-autobuild 依赖
server:
	@make clean
	@export CATURRA_SPHINX_DEBUG=1 \
		&& sphinx-autobuild . _build/html --host 127.0.0.1 --port 4000 -j auto

# 与 make server 类似，但是不需要 sphinx-autobuild 依赖
# 缺陷是不支持实时更新
native_server:
	@make clean
	@export CATURRA_SPHINX_DEBUG=1 && make html
	python3 -m http.server 4000 -d _build/html/

# 空格也是没问题的，比如：make transcript Linux 是如何使用我的 RAM 的？
# 也可以使用双引号：make transcript "Linux 是如何使用我的 RAM 的？"
transcript:
	@touch "${FILE_PATH}"
	@echo "# ${TITLE}"  >> "${FILE_PATH}"
	@echo               >> "${FILE_PATH}"
	@echo 标题：         >> "${FILE_PATH}"
	@echo               >> "${FILE_PATH}"
	@echo 日期：         >> "${FILE_PATH}"
	@echo               >> "${FILE_PATH}"
	@echo 作者：         >> "${FILE_PATH}"
	@echo               >> "${FILE_PATH}"
	@echo 链接：         >> "${FILE_PATH}"
	@echo               >> "${FILE_PATH}"
	@echo "注意：此为 **AI 翻译生成** 的中文转录稿，详细说明请参阅仓库中的 [README](/README.md) 文件。" >> "${FILE_PATH}"
	@echo               >> "${FILE_PATH}"
	@echo "-------"     >> "${FILE_PATH}"
	@echo               >> "${FILE_PATH}"
	@echo done.

.PHONY: help Makefile server native_server transcript

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
#
# 当调用 transcript 时，catch-all 改为静默忽略，
# 用于吞掉 "make transcript <title>" 中的多余参数。
ifneq ($(filter transcript,$(MAKECMDGOALS)),)
  INPUT     := $(wordlist 2, $(words $(MAKECMDGOALS)), $(MAKECMDGOALS))
  TITLE     := $(INPUT)
  FILE_PATH := archives/$(TITLE).md

  # Did nothing wrong!
  %:
	@:
else
  %: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
endif
