# 匠翻译

一个保持Markdown格式的英文到中文翻译工具，使用OpenAI API。

## 功能特点

- 保持原始Markdown格式
- 支持代码块、表格、列表等格式元素
- 支持自定义API密钥
- 支持选择不同的OpenAI模型
- 支持调整翻译创造性

## 快速开始

1. 克隆仓库
```bash
git clone https://github.com/ligj1706/mdfanyi.git
cd mdfanyi
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 OpenAI API 密钥
```

4. 运行应用
```bash
python app.py
```

## 环境变量配置

项目使用 `.env` 文件管理环境变量，主要配置项包括：

- `OPENAI_API_KEY`: OpenAI API密钥（必需）
- `FLASK_ENV`: 运行环境（development/production）
- `FLASK_APP`: 应用入口文件

## 使用方法

1. 在左侧文本框中粘贴需要翻译的英文Markdown文本
2. 点击"翻译"按钮
3. 翻译结果将显示在右侧文本框中

## 部署

本项目支持多种部署方式：

- 本地部署：按照快速开始步骤操作
- 云平台部署：支持部署到 Zeabur 等云平台

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License