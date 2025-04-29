# 匠翻译

一个保持Markdown格式的英文到中文翻译工具，使用OpenAI API。

## 功能特点

- 保持原始Markdown格式
- 支持代码块、表格、列表等格式元素
- 支持自定义API密钥
- 支持选择不同的OpenAI模型
- 支持调整翻译创造性

## 部署

本项目使用Zeabur部署。

## 本地运行

1. 克隆仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 配置环境变量：
   - 复制 `.env.example` 文件并重命名为 `.env`
   - 在 `.env` 文件中填入你的 OpenAI API 密钥
4. 运行应用：`python app.py`

## 环境变量配置

项目使用 `.env` 文件管理环境变量，主要配置项包括：

- `OPENAI_API_KEY`: OpenAI API密钥（必需）
- `FLASK_ENV`: 运行环境（development/production）
- `FLASK_APP`: 应用入口文件

注意：请确保不要将包含实际API密钥的 `.env` 文件提交到版本控制系统中。

## 使用方法

1. 在左侧文本框中粘贴需要翻译的英文Markdown文本
2. 点击"翻译"按钮
3. 翻译结果将显示在右侧文本框中 

转md的对话参考：https://grok.com/share/bGVnYWN5_f728ebee-56e1-4428-807f-5eebd9121f81

## 常用命令

cd /Users/john/Documents/aitian/mynewenv
source bin/activate
cd /Users/john/Documents/aitian/jiangfanyi

===

git add .

git commit -m "更新介绍"

git push origin main -f