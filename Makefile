.DEFAULT_GOAL := help
.PHONY: transcript help

transcript:
	@touch "${FILENAME}"
	@echo "# ${TITLE}"  >> "${FILENAME}"
	@echo               >> "${FILENAME}"
	@echo 标题：         >> "${FILENAME}"
	@echo               >> "${FILENAME}"
	@echo 日期：         >> "${FILENAME}"
	@echo               >> "${FILENAME}"
	@echo 作者：         >> "${FILENAME}"
	@echo               >> "${FILENAME}"
	@echo 链接：         >> "${FILENAME}"
	@echo               >> "${FILENAME}"
	@echo "注意：此为 **AI 翻译生成** 的中文转录稿，详细说明请参阅仓库中的 [README](/README.md) 文件。" >> "${FILENAME}"
	@echo               >> "${FILENAME}"
	@echo "-------"     >> "${FILENAME}"
	@echo               >> "${FILENAME}"
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
FILENAME := $(TITLE).md
