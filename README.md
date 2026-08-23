# AoiStudio

基于 Python + Pygame + PySide6 的 AVG / GalGame 制作引擎

- Pygame：游戏运行时核心引擎
- PySide6：可视化编辑器
- .json 文件：文本演出文件
- .cfg 文件：演出脚本文件

License：MIT

面向学生、小白创作者。目标：尽量少手写脚本，依靠可视化编辑器制作视觉小说，摆脱 Unity 的厚重，也不用编写大量 Ren'Py 脚本。

⚠️ 重要提示
.cfg 文件是演出脚本文件
.cfg 文件是演出脚本文件
.cfg 文件是演出脚本文件

## 普通用户使用（推荐，无需 Python 环境）

如果你只是想做 AVG/GalGame，不需要下载源码、不需要配置 Python 开发环境。

前往 Releases 页面下载预编译发行包：
- editor：可视化编辑器，编辑剧情与演出，自动生成 .cfg 演出脚本与 .json 文本演出文件
- engine：游戏播放器，预览、运行你的 AVG 项目

工作流程：
使用编辑器可视化编辑项目 -> 编辑器输出 .json 文本演出文件 & .cfg 演出脚本文件 -> 使用引擎播放器运行预览游戏。

Releases 链接：https://github.com/你的用户名/你的仓库名/releases

## 开发者：源码运行 & 编译

仅适合修改源码、开发插件的人员。普通使用者请直接下载 Release。

### 安装开发环境

1. 安装 Python 3.8 及以上
官网下载：https://www.python.org/downloads/windows/

运行安装exe，务必勾选 Add Python to PATH，然后点击 Install Now。

2. 下载或者克隆本仓库源码。
Win+R 输入 cmd 打开命令行，进入项目根目录执行：

pip install -r Libs.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

国内下载慢带上后面镜像参数。

### 实操运行源码

1. 运行游戏引擎（播放器）
进入 engine_src 目录，运行 main.py

正常现象：弹出窗口，黑色背景，左上角显示FPS，出现简陋主菜单UI，代表环境成功。
弹出 Engine have problem 窗口：代表依赖缺失或者版本存在bug。

2. 运行编辑器源码版（Lite）
进入 editor 目录，运行 editor_main.py

⚠️ 源码运行是 Lite 版本，部分完整功能需要构建产物。
需要先运行 make_abt.py 和 make_engine.py 生成相关产物。

### 打包编译输出

所有编译输出放在 make_out 目录：
- 编辑器打包：运行 make_editor.py，输出 make_out/editor_output
- 游戏播放器打包：运行 make_engine.py，输出 make_out/engine_output
- abt资源工具打包：运行 make_abt.py，输出 make_out/abt_output

### 提交PR

提交 Pull Request 的时候，可以在 PR_Uploaders_list.txt 留下你的ID，不留也可以ovo

## 作者碎碎念

图标是老子画的ovo
作者比较懒，主干更新比较慢，欢迎催更