.DEFAULT_GOAL := help
.PHONY: transcript help

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

# 空格也是没问题的，比如：make transcript Linux 是如何使用我的 RAM 的？
# 也可以使用双引号：make transcript "Linux 是如何使用我的 RAM 的？"
help:
	@echo "usage: make transcript <title>"

# Did nothing wrong!
%:
	@:

INPUT := $(wordlist 2, $(words $(MAKECMDGOALS)), $(MAKECMDGOALS))
TITLE := $(INPUT)
FILE_PATH := archives/$(TITLE).md
