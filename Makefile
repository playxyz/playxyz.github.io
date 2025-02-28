clean:
	rm -rf .git
	git config --global init.defaultBranch main
	git init .
	git remote add origin git@github.com:playxyz/playxyz.github.io.git
	git add .
	git commit -am "clean"

setup:
	git branch --set-upstream-to=origin/main