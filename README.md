<div align="center">

# 🧹 YT-PDFCleaner

**PDF 水印探测与清除工具 — 单文件处理 / 批量处理 / PDF 输出 / Markdown 转换**

![Python](https://img.shields.io/badge/Python-3.13-blue)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.23%2B-green)
![ttkbootstrap](https://img.shields.io/badge/ttkbootstrap-1.10%2B-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)
![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-lightgrey)

---

**YT 出品 · 匠心质检 · 安全可控**

</div>

---

## 📋 目录

- [简介](#-简介)
- [功能特性](#-功能特性)
- [快速开始](#-快速开始)
  - [安装 Python](#1-安装-python-313)
  - [下载与安装](#2-下载与安装)
  - [运行程序](#3-运行程序)
- [使用方法](#-使用方法)
  - [图形界面 (GUI)](#图形界面-gui)
  - [命令行模式 (CLI)](#命令行模式-cli)
- [界面预览](#-界面预览)
- [打包为独立程序](#-打包为独立程序)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [常见问题](#-常见问题)
- [许可证](#-许可证)

---

## 📖 简介

**YT-PDFCleaner** 是一款专为 PDF 文档设计的**水印探测与清除工具**。它能够智能检测 PDF 文件中的跟踪水印（如 SGCC 国网公司文档中常见的隐蔽水印），并将其彻底清除，输出干净的 PDF 或 Markdown 文件。

> 🎯 **适用场景**
> - 处理企业内部带水印的 PDF 文档
> - 批量清理 PDF 文件夹中的所有文件
> - 将 PDF 转换为干净的 Markdown 文本
> - 对敏感文档进行脱敏处理

---

## ✨ 功能特性

| 特性 | 说明 |
|------|------|
| 🔍 **智能水印检测** | 自动识别 PDF 中的跟踪水印，支持多种水印模式匹配 |
| 🧹 **精确水印清除** | 移除水印的同时保留原始文档排版和内容，不影响可读性 |
| 📄 **PDF 输出** | 清除水印后输出干净的 PDF 文件 |
| 📝 **Markdown 转换** | 将 PDF 内容转换为 Markdown 格式，方便分享和编辑 |
| 📂 **批量处理** | 支持整个文件夹的批量扫描和处理 |
| 🎨 **现代化 GUI** | 基于 ttkbootstrap 构建的图形界面，支持多款精美主题 |
| 🖥️ **CLI 模式** | 支持命令行模式，方便集成到自动化流程中 |
| 🛡️ **安全可靠** | 所有处理均在本地完成，不联网、不上传，保障文档安全 |

---

## 🚀 快速开始

### 1. 安装 Python 3.13

> **Windows 用户**: 从 [python.org](https://www.python.org/downloads/) 下载 Python 3.13，安装时请勾选 **"Add Python to PATH"**。

验证安装：

```bash
python --version
# 输出: Python 3.13.x
```

### 2. 下载与安装

**方式一：解压即用（推荐）**

从 [Releases](https://github.com/titanks-lab/yt-pdf-cleaner/releases) 页面下载最新版 `YT-PDFCleaner.zip`，解压后双击运行 `YT-PDFCleaner.exe` 即可。

**方式二：源码运行**

```bash
# 克隆仓库
git clone https://github.com/titanks-lab/yt-pdf-cleaner.git
cd yt-pdf-cleaner

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

### 3. 运行程序

```bash
# GUI 模式（默认）
python main.py

# CLI 模式 — 处理单个文件
python main.py --cli input.pdf --mode pdf

# CLI 模式 — 批量处理文件夹
python main.py --cli --dir ./my_pdfs --mode markdown

# CLI 模式 — 指定输出目录
python main.py --cli input.pdf --output ./output

# 指定 GUI 主题
python main.py --theme superhero
python main.py --theme darkly
python main.py --theme cyborg
```

---

## 🎯 使用方法

### 图形界面 (GUI)

1. **启动程序**：双击 `YT-PDFCleaner.exe` 或运行 `python main.py`
2. **选择文件**：点击 **"选择文件"** 按钮添加单个 PDF，或点击 **"选择文件夹"** 批量添加
3. **选择模式**：
   - **PDF 模式**：清除水印后输出 PDF
   - **Markdown 模式**：清除水印并转换为 Markdown
4. **开始处理**：点击 **"开始处理"** 按钮
5. **查看结果**：处理完成的文件会显示状态，输出目录为原文件所在文件夹下的 `YT_output/`

### 命令行模式 (CLI)

适合自动化脚本和批量处理场景：

```bash
# 扫描整个文件夹，清除水印后输出 PDF
python main.py --cli --dir ./documents --mode pdf

# 处理单个文件，转换为 Markdown
python main.py --cli report.pdf --mode markdown

# 处理文件并指定输出位置
python main.py --cli input.pdf --output ./cleaned --mode pdf
```

---

## 🖥️ 界面预览

```
 ┌──────────────────────────────────────────────────┐
 │  YT-PDFCleaner — PDF 水印清除工具          — □ X │
 ├──────────────────────────────────────────────────┤
 │  📂 [选择文件]  📁 [选择文件夹]  [🧹 开始处理]     │
 │  ──────────────────────────────────────────────── │
 │  文件列表:                                        │
 │  ┌──────────────────────────────────────────────┐│
 │  │ ✅ report_2024.pdf     [PDF]  [已清除]       ││
 │  │ ✅ meeting_notes.pdf   [MD]   [已转换]       ││
 │  │ ❌ protected.pdf              [加密文件跳过]  ││
 │  └──────────────────────────────────────────────┘│
 │                                                   │
 │  模式: ◉ PDF 输出  ○ Markdown 输出                │
 │  进度: ████████████░░░░░░ 75%                     │
 │  状态: 处理完成: 2 成功, 1 跳过                   │
 ├──────────────────────────────────────────────────┤
 │  YT-PDFCleaner v1.0.0    Made with ❤️ by YT      │
 └──────────────────────────────────────────────────┘
```

---

## 📦 打包为独立程序

如果希望在无 Python 环境的 Windows 电脑上运行，可以使用 PyInstaller 打包：

```bash
# 1. 安装打包工具
pip install pyinstaller

# 2. 运行打包脚本
python build/build.py

# 或直接使用 PyInstaller
pyinstaller --name "YT-PDFCleaner" --onedir --console --clean --noconfirm ^
    --exclude-module tkinter --exclude-module test --exclude-module unittest ^
    --hidden-import ttkbootstrap --hidden-import ttkbootstrap.constants ^
    --hidden-import ttkbootstrap.dialogs --hidden-import ttkbootstrap.toast ^
    main.py

# 3. 打包产物位于 dist/YT-PDFCleaner/
#    将该文件夹压缩后即可分发给其他用户
```

**Windows 一键打包**：双击 `build/build.bat` 即可自动完成打包。

打包后的文件结构：

```
dist/YT-PDFCleaner/
├── YT-PDFCleaner.exe       # 主程序（双击运行）
├── _internal/              # 依赖库和资源
│   ├── *.pyd               # Python 扩展模块
│   ├── *.dll               # 动态链接库
│   └── ...                 # 其他资源文件
└── ...
```

> 💡 **提示**：打包后的程序为 **解压即用** 的便携版，无需安装，可在 U 盘中随身携带。

---

## 🛠 技术栈

| 技术 | 用途 |
|------|------|
| **[Python 3.13](https://www.python.org/)** | 编程语言 |
| **[PyMuPDF (fitz)](https://pymupdf.readthedocs.io/)** | PDF 解析与处理核心引擎 |
| **[ttkbootstrap](https://ttkbootstrap.readthedocs.io/)** | 现代化 GUI 界面库（多主题支持） |
| **[PyInstaller](https://pyinstaller.org/)** | Windows 便携版打包 |
| **[pytest](https://pytest.org/)** | 单元测试与集成测试 |

---

## 📁 项目结构

```
yt-pdf-cleaner/
├── core/                   # 核心功能模块
│   ├── engine.py           #   水印检测 / 清除 / Markdown 转换引擎
│   ├── scanner.py          #   文件扫描与批量处理
│   └── utils.py            #   工具函数（路径、日志等）
├── gui/                    # 图形界面模块
│   ├── app.py              #   主窗口
│   ├── file_list.py        #   文件列表组件
│   └── processor.py        #   后台处理线程
├── tests/                  # 测试套件
│   ├── conftest.py         #   pytest 配置与 fixture
│   ├── test_engine.py      #   引擎单元测试
│   ├── test_scanner.py     #   扫描器单元测试
│   ├── test_utils.py       #   工具函数测试
│   └── test_integration.py #   集成测试
├── build/                  # 打包脚本
│   ├── build.py            #   PyInstaller 打包脚本（跨平台）
│   └── build.bat           #   Windows 一键打包批处理
├── main.py                 # 程序入口（GUI / CLI）
├── requirements.txt        # Python 依赖
├── pytest.ini              # pytest 配置
└── README.md               # 本文件
```

---

## ❓ 常见问题

<details>
<summary><b>Q: 为什么程序报错 "无法导入 ttkbootstrap"？</b></summary>

请确保已安装所有依赖：
```bash
pip install -r requirements.txt
```
</details>

<details>
<summary><b>Q: 打包后的程序报毒怎么办？</b></summary>

PyInstaller 打包的程序可能被部分杀毒软件误报。这是 PyInstaller 打包程序的常见情况，并非程序本身有问题。您可以：
- 将程序目录添加到杀毒软件的白名单
- 使用源码运行（`python main.py`）
</details>

<details>
<summary><b>Q: 支持批量处理多少个文件？</b></summary>

没有数量限制。程序会逐个处理文件，处理大量文件时建议使用 CLI 模式。
</details>

<details>
<summary><b>Q: 支持 macOS 或 Linux 吗？</b></summary>

程序本身是跨平台的，但 PyInstaller 打包目前仅针对 Windows。macOS/Linux 用户可以直接使用源码运行。
</details>

<details>
<summary><b>Q: 处理后的文件保存在哪里？</b></summary>

默认输出目录为输入文件所在文件夹下的 <code>YT_output/</code>。您也可以在 CLI 模式下通过 <code>--output</code> 参数指定。
</details>

---

## 📄 许可证

本项目基于 **MIT License** 开源。

```
MIT License

Copyright (c) 2026 YT (titanks-lab)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions...
```

---

<div align="center">

**Made with ❤️ by YT** · [GitHub](https://github.com/titanks-lab/yt-pdf-cleaner)

</div>
