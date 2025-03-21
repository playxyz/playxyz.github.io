clean:
	git pull
	git tag backup && git push origin backup -f && rm -rf .git
	git config --global init.defaultBranch main
	git init .
	git remote add origin git@github.com:playxyz/playxyz.github.io.git
	git add .
	git commit -am "clean"
	git push origin -f
	git branch --set-upstream-to=origin/main

setup:
	git branch --set-upstream-to=origin/main

# 测试相关命令
test:
	@echo "运行 util 目录下的所有测试..."
	python -m unittest discover -s news/scripts/util -p "*_test.py"

.PHONY: clean setup test