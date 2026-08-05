这是一个AVG游戏引擎，用的Python+pygame+pyqt5做的。其中pygame用作引擎核心，pyqt5用做编辑器

如何开始？
先安装python：https://www.python.org/downloads/windows/
打开链接后找3.8以上的Download Windows Installer
根据系统选择指令集
下载完后打开exe，把下面的两个勾打上，然后点击Install Now
安装完后打开命令行（Win+r 输入cmd）,然后输入pip install -r 把项目中的Libs.txt拖到这，然后再按回车，等待一会就安装好了，如果太慢的话可以加上-i https://pypi.tuna.tsinghua.edu.cn/simple
等待一会环境就安装好啦
打开核心：
    打开engine_src，在里面找到main.py，打开它
    此时你可以看到一个几乎全黑的窗口，左上角有FPS显示，和一个有点简陋的主菜单UI界面
    这就说明你的python环境搭建成功了
    如果出现Engine have problem窗口，说明环境没搭好或者你下到的版本有bug
打开编辑器：
    打开ediotr，里面找到editor_main.py，打开它
    如果没有报ModuleNotFoundError错或者任何关于模块导入的错误，那说明你环境搭好了
    但注意，编辑器的源码版本质上是LiteRelease版，你需要运行make_abt.py和make_engine.py这两个来获取aoi文件安装
打包/编译：
    编辑器：运行make_editor.py，生成在make_out/editor_output
    播放器：运行make_engine.py，生成在make_out/engine_output
    abt：运行make_abt.py，生成在make_out/abt_output
上传PR的时候记得在PR_Uploaders_list.txt留下名字，不留也可以ovo
图标是老子画的ovo
还有，作者比较懒，主干更新比较慢，欢迎催更