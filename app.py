import os
import re
import time
from flask import Flask, request, jsonify, render_template, send_from_directory
from openai import OpenAI
from flask_cors import CORS
from collections import Counter

# 设置默认API密钥
DEFAULT_API_KEY = os.environ.get('OPENAI_API_KEY', '')
DEFAULT_MODEL = 'gpt-4o-mini'
DEFAULT_TEMPERATURE = 0.1

app = Flask(__name__)
CORS(app)

# 确保 static 目录存在
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# 创建SVG logo和favicon
def create_svg_files():
    # 创建logo.svg
    logo_svg = '''<svg width="120" height="120" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
  <!-- 背景圆形 -->
  <circle cx="60" cy="60" r="55" fill="#0071e3"/>
  
  <!-- 匠字 - 简化版 -->
  <path d="M40,35 h40 M40,55 h40 M60,35 v50 M45,85 h30" stroke="white" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  
  <!-- 翻译图标元素 -->
  <path d="M30,70 L35,60 L40,70" stroke="white" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M80,70 L85,60 L90,70" stroke="white" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''
    
    # 创建favicon.svg
    favicon_svg = '''<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <!-- 背景圆形 -->
  <circle cx="32" cy="32" r="30" fill="#0071e3"/>
  
  <!-- 匠字 - 简化版 -->
  <path d="M20,20 h24 M20,32 h24 M32,20 v28 M24,48 h16" stroke="white" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
</svg>'''
    
    # 保存SVG文件
    with open(os.path.join(static_dir, 'logo.svg'), 'w') as f:
        f.write(logo_svg)
    
    with open(os.path.join(static_dir, 'favicon.svg'), 'w') as f:
        f.write(favicon_svg)
    
    print("SVG files created successfully!")

# 创建SVG文件
create_svg_files()

def split_text_preserving_markdown(text, max_chunk_size=1500):
    """
    将文本分割成较小的块，同时保持Markdown格式的完整性
    """
    # 识别章节标题
    headers = re.findall(r'^(#{1,3}\s+.+)$', text, re.MULTILINE)
    current_section = "开始部分"
    
    # 首先识别并保护代码块
    code_block_pattern = r'(```[\s\S]*?```)'
    parts = re.split(code_block_pattern, text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    chunk_section = current_section
    
    for part in parts:
        # 检查是否为代码块
        if part.startswith('```') and part.endswith('```'):
            # 如果当前块加上代码块会超过大小限制，先保存当前块
            if current_size > 0 and current_size + len(part) > max_chunk_size:
                full_chunk = f"[章节：{chunk_section}]\n\n" + ''.join(current_chunk)
                chunks.append(full_chunk)
                current_chunk = []
                current_size = 0
                chunk_section = current_section
            
            # 将整个代码块作为一个单元添加
            current_chunk.append(part)
            current_size += len(part)
        else:
            # 处理非代码块文本
            paragraphs = re.split(r'(\n\s*\n)', part)
            
            for i in range(0, len(paragraphs), 2):
                para = paragraphs[i]
                # 获取段落分隔符（如果有）
                separator = paragraphs[i+1] if i+1 < len(paragraphs) else ""
                
                # 检查这个段落是否包含章节标题
                header_match = re.search(r'^(#{1,3}\s+.+)$', para, re.MULTILINE)
                if header_match:
                    current_section = header_match.group(1).strip('# ')
                    chunk_section = current_section
                
                # 如果当前段落加上分隔符会使当前块超过最大尺寸，则开始新块
                if current_size + len(para) + len(separator) > max_chunk_size and current_chunk:
                    full_chunk = f"[章节：{chunk_section}]\n\n" + ''.join(current_chunk)
                    chunks.append(full_chunk)
                    current_chunk = []
                    current_size = 0
                    chunk_section = current_section
                
                # 处理特别长的段落
                if len(para) > max_chunk_size:
                    if current_chunk:
                        full_chunk = f"[章节：{chunk_section}]\n\n" + ''.join(current_chunk)
                        chunks.append(full_chunk)
                        current_chunk = []
                        current_size = 0
                    
                    # 长段落按句子分割
                    sentences = re.split(r'([.!?。！？]\s+)', para)
                    temp_chunk = []
                    temp_size = 0
                    
                    for j in range(0, len(sentences), 2):
                        sentence = sentences[j]
                        # 获取句子分隔符（如果有）
                        sent_separator = sentences[j+1] if j+1 < len(sentences) else ""
                        
                        if temp_size + len(sentence) + len(sent_separator) > max_chunk_size and temp_chunk:
                            full_chunk = f"[章节：{chunk_section}]\n\n" + ''.join(temp_chunk) + separator
                            chunks.append(full_chunk)
                            temp_chunk = []
                            temp_size = 0
                        
                        temp_chunk.append(sentence + sent_separator)
                        temp_size += len(sentence) + len(sent_separator)
                    
                    if temp_chunk:
                        full_chunk = f"[章节：{chunk_section}]\n\n" + ''.join(temp_chunk) + separator
                        chunks.append(full_chunk)
                else:
                    current_chunk.append(para + separator)
                    current_size += len(para) + len(separator)
    
    if current_chunk:
        full_chunk = f"[章节：{chunk_section}]\n\n" + ''.join(current_chunk)
        chunks.append(full_chunk)
    
    return chunks

def identify_format_elements(text):
    """
    识别并提取文本中的格式元素（如Markdown语法）
    """
    # 识别代码块
    code_blocks = re.findall(r'```[\s\S]*?```', text)
    
    # 识别标题
    headers = re.findall(r'^#{1,6}\s.*$', text, re.MULTILINE)
    
    # 识别列表
    lists = re.findall(r'^[\s]*[-*+]\s.*(?:\n[\s]*[-*+]\s.*)*', text, re.MULTILINE)
    
    # 识别表格
    tables = re.findall(r'^\|.*\|$[\s\S]*?(?:^\|.*\|$)', text, re.MULTILINE)
    
    format_elements = {
        'code_blocks': len(code_blocks),
        'headers': len(headers),
        'lists': len(lists),
        'tables': len(tables)
    }
    
    return format_elements

def extract_key_terminology(text, max_terms=15):
    """
    提取文本中的关键术语，专注于代码中的变量、类名和重复出现的专业术语
    """
    # 提取所有单词
    words = re.findall(r'\b[A-Za-z][A-Za-z0-9_]+\b', text)
    
    # 提取代码块中的变量和类名
    code_blocks = re.findall(r'```[\s\S]*?```', text)
    code_identifiers = []
    
    for block in code_blocks:
        # 提取可能的变量名、函数名和类名
        identifiers = re.findall(r'\b[A-Za-z][A-Za-z0-9_]+\b', block)
        code_identifiers.extend(identifiers)
    
    # 计数所有单词
    word_counts = Counter(words)
    
    # 给代码标识符更高权重
    for identifier in code_identifiers:
        if identifier in word_counts:
            word_counts[identifier] += 2
    
    # 过滤常见单词和太短的单词
    common_words = {'the', 'and', 'for', 'that', 'this', 'from', 'with', 'not', 'have', 'has'}
    key_terms = [word for word, count in word_counts.most_common(max_terms*2)
                if word.lower() not in common_words and len(word) > 3]
    
    # 返回顶部术语
    return key_terms[:max_terms]

def translate_text(text, api_key, model="gpt-4o-mini", temperature=0, key_terms=None):
    """
    使用OpenAI API翻译文本
    """
    client = OpenAI(api_key=api_key)
    
    # 提取章节信息
    section_info = re.match(r'\[章节：(.+?)\]', text)
    current_section = ""
    
    if section_info:
        current_section = section_info.group(1)
        # 移除章节标记
        text = re.sub(r'\[章节：.+?\]\n\n', '', text)
    
    instruction = """
    你是一位资深的翻译专家，请将以下英文文本翻译成简体中文，达到母语级别。严格保持原有的Markdown格式结构，包括：
    1. 所有标题格式 (#, ##, 等)
    2. 所有列表格式 (-, *, +)
    3. 所有表格结构
    4. 所有链接格式 [text](url)
    5. 所有图片引用 ![alt](url)
    6. 所有加粗、斜体等文本格式 (**bold**, *italic*)
    7. 所有代码块和行内代码 (``` ```与`code`)
    
    特别重要的说明：
    - 代码块中的代码和命令不需要翻译，保持原样
    - 代码块中的注释（以 # 或 // 开头的行）可以翻译，但保持其位置和格式
    - 保持所有LaTeX公式不变
    - 保留所有原始URL不变
    - 保持标点符号与原文风格一致
    """
    
    # 添加章节信息
    if current_section:
        instruction += f"\n\n当前翻译的内容属于文档的「{current_section}」章节。"
    
    # 添加关键术语
    if key_terms and len(key_terms) > 0:
        instruction += "\n\n以下是文档中出现的重要术语，请确保翻译一致："
        for term in key_terms:
            instruction += f"\n- {term}"
    
    instruction += "\n\n这是一个长文档的一部分，请确保翻译的连贯性和术语一致性。"
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": text}
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"翻译时出错: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html', api_key=DEFAULT_API_KEY)

@app.route('/translate', methods=['POST'])
def translate():
    data = request.json
    text = data.get('text', '')
    api_key = data.get('api_key', DEFAULT_API_KEY)
    temperature = float(data.get('temperature', DEFAULT_TEMPERATURE))
    model = data.get('model', DEFAULT_MODEL)
    
    # 如果没有提供API密钥，使用默认密钥
    if not api_key:
        api_key = DEFAULT_API_KEY
    
    # 检查文本长度
    if len(text) > 50000:
        return jsonify({'error': '文本长度超过限制（最大50000字符）'}), 400
    
    # 识别文本格式
    format_elements = identify_format_elements(text)
    
    # 提取关键术语
    key_terms = extract_key_terminology(text)
    
    # 分割文本
    chunks = split_text_preserving_markdown(text, max_chunk_size=1500)
    
    # 翻译每个块
    translated_chunks = []
    progress = 0
    
    for chunk in chunks:
        # 连续尝试直到成功
        max_retries = 3
        for attempt in range(max_retries):
            try:
                translated = translate_text(chunk, api_key, model, temperature, key_terms)
                if translated:
                    translated_chunks.append(translated)
                    break
                else:
                    if attempt == max_retries - 1:
                        translated_chunks.append("[翻译失败]")
            except Exception as e:
                if attempt == max_retries - 1:
                    translated_chunks.append(f"[翻译失败: {str(e)}]")
        
        progress += 1
        
        # 避免API限制
        time.sleep(0.5)
    
    # 合并翻译后的文本
    translated_content = '\n'.join(translated_chunks)
    
    return jsonify({
        'translated_text': translated_content,
        'format_elements': format_elements,
        'chunks': len(chunks),
        'key_terms': key_terms
    })

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.svg')

if __name__ == '__main__':
    app.run(debug=True)