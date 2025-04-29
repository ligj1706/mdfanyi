# 匠翻译

一个保持Markdown格式的英文到中文，长文本翻译工具。

## 功能特点

- 保持原始Markdown格式
- 支持代码块、表格、列表等格式元素
- 支持自定义API密钥
- 支持选择不同的OpenAI模型
- 支持调整翻译创造性

## 技术细节

### 1. 长文本分段与并行翻译

- 本项目支持最大 5 万字符（可调整）的长文本输入。为保证翻译质量和接口稳定性，后端会自动将长文本**智能分段**，每段约 1800~2500 字符，优先按段落、句子和章节标题切分，尽量保持语义完整，避免断句断段。
- 分段后，采用**多线程并行**调用 OpenAI API 进行翻译，大幅提升处理效率。每个分段翻译结果会自动按原顺序合并，保证上下文连贯。
- 具体实现见 `split_text_into_chunks` 函数，支持段落优先、句子兜底的分块策略，并在每块前加上章节标记，便于上下文理解。

### 2. Markdown 格式保护与还原

- 为确保翻译后文档格式与原文一致，项目实现了**Markdown元素保护机制**。在翻译前，自动识别并保护如下元素：
  - 代码块（```）、行内代码（`...`）、表格、图片、链接、LaTeX公式、HTML标签等
- 对于链接和图片，仅翻译描述文本，URL 保持不变；代码块和行内代码内容完全保护不翻译；表格结构完整保留。
- 保护方式为将这些元素替换为唯一占位符，翻译后再**逐一还原**，确保格式和内容不丢失、不错位。
- 相关实现见 `MarkdownElementHandler` 类及其 `protect_elements`、`restore_elements` 方法。

### 3. 格式一致性与翻译指令

- 每次调用 OpenAI API 时，都会附加**详细的系统指令**，要求模型严格保持 Markdown 格式，明确哪些内容可翻译、哪些必须保留。
- 指令示例见 `get_translation_instruction` 函数，涵盖标题、列表、表格、链接、图片、代码、LaTeX等格式的处理要求。

### 4. 错误处理与缓存

- 支持分块重试、指数退避，提升大文本翻译的稳定性。
- 翻译结果自动缓存，避免重复请求，提升响应速度。

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

交流加V：a52947593

## 推荐工具：网页转 Markdown

如果你需要将网页内容快速转为 Markdown，可以参考以下工具：

1. **WebInk 智能网页转 Markdown 工具（Chrome 插件）**  
   支持一键将网页内容智能转换为 Markdown，支持实时预览、复制、下载、Notion 集成等功能。  
   [Chrome 应用商店地址](https://chromewebstore.google.com/detail/webink-%E6%99%BA%E8%83%BD%E7%BD%91%E9%A1%B5%E8%BD%ACmarkdown%E5%B7%A5%E5%85%B7/lhifbnmampdmdadbhpeeoikkljhiaohn)

2. **MarkDownload - 网页转 Markdown**  
   一款开源的浏览器扩展，支持一键将当前网页保存为 Markdown 文件。  
   [Chrome 应用商店地址](https://chrome.google.com/webstore/detail/markdownload-markdown-web/pcmpcfapbekmbjjkdalcgopdkipoggdi)

## 许可证

MIT License