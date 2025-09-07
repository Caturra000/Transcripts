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
help:
	@echo "make server"
	@echo "make html"
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

.PHONY: help Makefile server

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
