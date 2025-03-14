import os
import re
import time
import uuid
import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from flask_cors import CORS

# 设置默认API密钥
DEFAULT_API_KEY = os.environ.get('OPENAI_API_KEY', '')
DEFAULT_MODEL = 'gpt-4o-mini'
DEFAULT_TEMPERATURE = 0.1
MAX_WORKERS = 4  # 设置最大工作线程数

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 确保 static 和 cache 目录存在
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
for directory in [static_dir, cache_dir]:
    if not os.path.exists(directory):
        os.makedirs(directory)

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

# 创建SVG文件
create_svg_files()

# 定义一个类来处理Markdown元素的保护和恢复
class MarkdownElementHandler:
    def __init__(self):
        # 保护的元素模式及优先级
        self.protected_patterns = [
            # 元组格式: (名称, 正则表达式模式, 优先级, 是否需要翻译内部文本)
            ('code_block', r'```(?:.+?\n)?[\s\S]*?```', 1, False),
            ('table', r'(?:\|.+?\|[ \t]*\r?\n)+(?:\|[-: ]+?\|[ \t]*\r?\n)(?:\|.+?\|[ \t]*\r?\n)+', 2, True),
            ('image', r'!\[(.*?)\]\((.*?)\)', 3, True),
            ('link', r'\[(.*?)\]\((.*?)\)', 4, True),
            ('inline_code', r'`[^`\n]+?`', 5, False),
            ('latex_block', r'\$\$[\s\S]*?\$\$', 6, False),
            ('latex_inline', r'\$[^$\n]+?\$', 7, False),
            ('html_tag', r'<[^>]+>[\s\S]*?</[^>]+>', 8, False)
        ]
        # 排序模式,确保更长的模式先处理
        self.protected_patterns.sort(key=lambda x: x[2])
    
    def protect_elements(self, text):
        """
        保护Markdown特殊元素,处理需要部分翻译的元素(如链接文本)
        返回: (处理后的文本, 元素映射字典)
        """
        elements_map = {}
        processed_text = text
        
        # 按照优先级处理每种模式
        for name, pattern, _, needs_translation in self.protected_patterns:
            if not needs_translation:
                # 完全保护的元素,不需要翻译
                matches = re.finditer(pattern, processed_text)
                for match in matches:
                    element = match.group(0)
                    element_id = f"MD_{name}_{str(uuid.uuid4())[:8]}"
                    elements_map[element_id] = element
                    processed_text = processed_text.replace(element, element_id, 1)
            else:
                # 需要部分翻译的元素(如链接、图片)
                if name == 'link':
                    # 特殊处理链接
                    processed_text = self.process_links(processed_text, elements_map)
                elif name == 'image':
                    # 特殊处理图片
                    processed_text = self.process_images(processed_text, elements_map)
                elif name == 'table':
                    # 特殊处理表格
                    processed_text = self.process_tables(processed_text, elements_map)
        
        return processed_text, elements_map
    
    def process_links(self, text, elements_map):
        """特殊处理链接,保留URL但允许翻译链接文本"""
        processed_text = text
        link_pattern = r'\[(.*?)\]\((.*?)\)'
        
        matches = list(re.finditer(link_pattern, processed_text))
        # 从后向前替换,避免位置偏移问题
        for match in reversed(matches):
            full_link = match.group(0)
            link_text = match.group(1)
            link_url = match.group(2)
            
            # 为URL创建一个唯一标识符
            url_id = f"MD_url_{str(uuid.uuid4())[:8]}"
            elements_map[url_id] = link_url
            
            # 替换为可翻译的格式,但保护URL
            translated_format = f"[{link_text}]({url_id})"
            
            # 定位替换的准确位置
            start = match.start()
            end = match.end()
            processed_text = processed_text[:start] + translated_format + processed_text[end:]
        
        return processed_text
    
    def process_images(self, text, elements_map):
        """特殊处理图片,保留URL但允许翻译图片描述"""
        processed_text = text
        image_pattern = r'!\[(.*?)\]\((.*?)\)'
        
        matches = list(re.finditer(image_pattern, processed_text))
        # 从后向前替换,避免位置偏移问题
        for match in reversed(matches):
            full_image = match.group(0)
            image_alt = match.group(1)
            image_url = match.group(2)
            
            # 为URL创建一个唯一标识符
            url_id = f"MD_img_{str(uuid.uuid4())[:8]}"
            elements_map[url_id] = image_url
            
            # 替换为可翻译的格式,但保护URL
            translated_format = f"![{image_alt}]({url_id})"
            
            # 定位替换的准确位置
            start = match.start()
            end = match.end()
            processed_text = processed_text[:start] + translated_format + processed_text[end:]
        
        return processed_text
    
    def process_tables(self, text, elements_map):
        """
        特殊处理表格,保留表格结构但允许翻译内容
        这是一个复杂任务,这里提供简化实现
        """
        # 对于复杂的表格,我们选择完整保护
        # 在实际应用中,可以开发更复杂的表格解析和处理逻辑
        table_pattern = r'(?:\|.+?\|[ \t]*\r?\n)+(?:\|[-: ]+?\|[ \t]*\r?\n)(?:\|.+?\|[ \t]*\r?\n)+'
        matches = re.finditer(table_pattern, text)
        
        processed_text = text
        for match in matches:
            table = match.group(0)
            table_id = f"MD_table_{str(uuid.uuid4())[:8]}"
            elements_map[table_id] = table
            processed_text = processed_text.replace(table, table_id, 1)
        
        return processed_text
    
    def restore_elements(self, text, elements_map):
        """
        恢复被保护的Markdown元素,特殊处理部分翻译的元素
        """
        restored_text = text
        
        # 先处理URL占位符
        url_pattern = r'\[([^\]]*?)\]\((MD_url_[0-9a-f]{8})\)'
        url_matches = re.finditer(url_pattern, restored_text)
        
        for match in url_matches:
            full_pattern = match.group(0)
            link_text = match.group(1)
            url_placeholder = match.group(2)
            
            if url_placeholder in elements_map:
                actual_url = elements_map[url_placeholder]
                restored_link = f"[{link_text}]({actual_url})"
                restored_text = restored_text.replace(full_pattern, restored_link, 1)
        
        # 处理图片占位符
        img_pattern = r'!\[([^\]]*?)\]\((MD_img_[0-9a-f]{8})\)'
        img_matches = re.finditer(img_pattern, restored_text)
        
        for match in img_matches:
            full_pattern = match.group(0)
            alt_text = match.group(1)
            img_placeholder = match.group(2)
            
            if img_placeholder in elements_map:
                actual_url = elements_map[img_placeholder]
                restored_img = f"![{alt_text}]({actual_url})"
                restored_text = restored_text.replace(full_pattern, restored_img, 1)
        
        # 处理其他占位符
        placeholder_pattern = r'MD_[a-z_]+_[0-9a-f]{8}'
        placeholders = re.findall(placeholder_pattern, restored_text)
        
        for placeholder in placeholders:
            if placeholder in elements_map:
                restored_text = restored_text.replace(placeholder, elements_map[placeholder], 1)
            else:
                logger.warning(f"找不到占位符: {placeholder}")
        
        return restored_text

def split_text_into_chunks(text, max_chunk_size=2500):
    """
    将文本分割成较小的块,同时保持句子和段落的完整性
    """
    # 提取章节标题信息
    section_match = re.search(r'^#+\s+(.+?)$', text, re.MULTILINE)
    current_section = section_match.group(1) if section_match else "无标题章节"
    
    # 按段落分割
    paragraphs = re.split(r'(\n\s*\n)', text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for i in range(0, len(paragraphs), 2):
        paragraph = paragraphs[i] if i < len(paragraphs) else ""
        separator = paragraphs[i+1] if i+1 < len(paragraphs) else ""
        
        # 检查段落是否为新章节标题
        header_match = re.search(r'^(#+)\s+(.+?)$', paragraph.strip(), re.MULTILINE)
        if header_match:
            level, title = header_match.groups()
            current_section = title
        
        para_size = len(paragraph) + len(separator)
        
        # 如果当前段落会使块超过大小限制,则开始新块
        if current_size + para_size > max_chunk_size and current_chunk:
            chunk_text = ''.join(current_chunk)
            chunk_text = f"[SECTION:{current_section}]\n\n{chunk_text}"
            chunks.append(chunk_text)
            current_chunk = []
            current_size = 0
        
        # 处理特别长的段落
        if para_size > max_chunk_size:
            # 如果有当前内容,先保存
            if current_chunk:
                chunk_text = ''.join(current_chunk)
                chunk_text = f"[SECTION:{current_section}]\n\n{chunk_text}"
                chunks.append(chunk_text)
                current_chunk = []
                current_size = 0
            
            # 然后处理长段落(尝试按句子分割)
            sentences = re.split(r'([.!?。！？]\s+)', paragraph)
            
            sentence_chunk = []
            sentence_size = 0
            
            for j in range(0, len(sentences), 2):
                sentence = sentences[j] if j < len(sentences) else ""
                sent_end = sentences[j+1] if j+1 < len(sentences) else ""
                sent_full = sentence + sent_end
                sent_size = len(sent_full)
                
                if sentence_size + sent_size > max_chunk_size and sentence_chunk:
                    sent_text = ''.join(sentence_chunk)
                    sent_text = f"[SECTION:{current_section}]\n\n{sent_text}"
                    chunks.append(sent_text)
                    sentence_chunk = []
                    sentence_size = 0
                
                sentence_chunk.append(sent_full)
                sentence_size += sent_size
            
            if sentence_chunk:
                sent_text = ''.join(sentence_chunk) + separator
                sent_text = f"[SECTION:{current_section}]\n\n{sent_text}"
                chunks.append(sent_text)
        else:
            current_chunk.append(paragraph + separator)
            current_size += para_size
    
    if current_chunk:
        chunk_text = ''.join(current_chunk)
        chunk_text = f"[SECTION:{current_section}]\n\n{chunk_text}"
        chunks.append(chunk_text)
    
    return chunks

def get_translation_instruction(current_section=""):
    """
    获取翻译指令
    """
    instruction = """
    你是一位精通AI领域的图书专业翻译,你擅长将英文文档翻译成地道的简体中文。要求:
    
    【翻译要求】
    1) 充分理解原文的背景和语言风格
    2) 翻译时不遗漏任何信息,忠于原文内容
    3) 调整语序,符合汉语规则和中文阅读习惯
    4) 采用意译而非直译,表达流畅自然、地道
    
    【格式要求 - 非常重要】
    1. 严格保持原文的Markdown格式,包括标题、列表、表格等
    2. 链接格式 [链接文本](链接URL) 中:
       - 请翻译链接文本部分
       - 保持链接URL部分不变
       - 例如: "[read more](https://example.com)" 应翻译为 "[阅读更多](https://example.com)"
    3. 图片格式 ![描述文本](图片URL) 中:
       - 请翻译描述文本部分
       - 保持图片URL部分不变
    4. 代码块内的代码不翻译,注释可以翻译
    5. 行内代码不翻译
    6. 保留所有LaTeX公式和数学表达式
    7. 对于以"MD_"开头的占位符,必须完全保留,不要更改或翻译
    
    请直接提供翻译结果,不要加入解释或额外信息。
    """
    
    # 添加章节信息
    if current_section:
        instruction += f"\n\n当前翻译的内容属于「{current_section}」章节。"
    
    return instruction

def create_cache_key(text, model, temperature):
    """
    为文本创建唯一的缓存键
    """
    # 结合文本、模型和温度生成缓存键
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    return f"{text_hash}_{model}_{temperature}"

def load_from_cache(cache_key):
    """
    从缓存加载翻译
    """
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 检查缓存是否过期(30天)
                if time.time() - data.get('timestamp', 0) < 30 * 24 * 60 * 60:
                    return data
                logger.info(f"缓存已过期: {cache_key}")
        except Exception as e:
            logger.error(f"读取缓存失败: {e}")
    return None

def save_to_cache(cache_key, data):
    """
    保存翻译到缓存
    """
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    try:
        # 添加时间戳
        data['timestamp'] = time.time()
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存缓存失败: {e}")
        return False

def translate_text(text, api_key, model="gpt-4o-mini", temperature=0):
    """
    使用OpenAI API翻译文本
    """
    client = OpenAI(api_key=api_key)
    
    # 提取章节信息
    section_info = re.match(r'\[SECTION:(.+?)\]', text)
    current_section = ""
    
    if section_info:
        current_section = section_info.group(1)
        # 移除章节标记
        text = re.sub(r'\[SECTION:.+?\]\n\n', '', text)
    
    # 获取翻译指令
    instruction = get_translation_instruction(current_section)
    
    try:
        logger.info(f"开始翻译,文本长度: {len(text)}字符")
        
        # API调用
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": f"以下是需要翻译的文章:\n\n{text}"}
            ],
            temperature=temperature,
            timeout=60
        )
        
        translated = response.choices[0].message.content
        return translated
            
    except Exception as e:
        logger.error(f"翻译错误: {str(e)}")
        return f"[翻译错误: {str(e)}]"

def translate_chunk(chunk, api_key, model, temperature):
    """
    翻译单个文本块
    """
    # 创建缓存键
    chunk_key = create_cache_key(chunk, model, temperature)
    chunk_cache = load_from_cache(chunk_key)
    
    if chunk_cache and 'translated' in chunk_cache:
        # 从缓存返回结果
        logger.info(f"从缓存加载翻译结果,大小: {len(chunk_cache['translated'])}字符")
        return chunk_cache['translated']
    
    # 翻译当前块
    max_retries = 2
    for attempt in range(max_retries):
        try:
            translated = translate_text(chunk, api_key, model, temperature)
            
            if translated and not translated.startswith("[翻译错误"):
                # 保存到缓存
                save_to_cache(chunk_key, {'translated': translated})
                return translated
            
            # 出错时,添加重试间隔
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避策略
                
        except Exception as e:
            logger.error(f"翻译尝试 {attempt+1} 失败: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    return f"[翻译失败: 已尝试 {max_retries} 次]"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate():
    try:
        data = request.json
        text = data.get('text', '')
        temperature = float(data.get('temperature', DEFAULT_TEMPERATURE))
        model = data.get('model', DEFAULT_MODEL)
        
        # 使用服务器端API密钥
        api_key = DEFAULT_API_KEY
        
        # 检查文本长度
        if len(text) > 50000:
            return jsonify({'error': '文本长度超过限制（最大50000字符）'}), 400
        
        if not text.strip():
            return jsonify({'error': '请提供要翻译的文本'}), 400
        
        # 创建Markdown元素处理器
        md_handler = MarkdownElementHandler()
        
        # 1. 保护Markdown特殊元素
        protected_text, elements_map = md_handler.protect_elements(text)
        logger.info(f"保护了 {len(elements_map)} 个特殊元素")
        
        # 2. 分割文本为可管理的块
        chunks = split_text_into_chunks(protected_text, max_chunk_size=1800)
        logger.info(f"文本被分割为 {len(chunks)} 个块")
        
        # 3. 使用线程池并行翻译chunks
        translated_chunks = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 提交翻译任务
            future_to_chunk = {
                executor.submit(
                    translate_chunk, chunk, api_key, model, temperature
                ): i for i, chunk in enumerate(chunks)
            }
            
            # 收集结果(按原始顺序)
            results = [None] * len(chunks)
            for future in future_to_chunk:
                chunk_index = future_to_chunk[future]
                try:
                    results[chunk_index] = future.result()
                except Exception as exc:
                    logger.error(f"翻译线程 {chunk_index} 生成异常: {exc}")
                    results[chunk_index] = f"[翻译异常: {str(exc)}]"
            
            translated_chunks = results
        
        # 4. 合并翻译后的块
        translated_content = '\n'.join(translated_chunks)
        
        # 5. 恢复所有特殊Markdown元素
        final_translated = md_handler.restore_elements(translated_content, elements_map)
        
        # 获取翻译统计信息
        translation_errors = sum(1 for chunk in translated_chunks if '[翻译' in chunk)
        success_rate = (len(chunks) - translation_errors) / len(chunks) * 100 if chunks else 0
        
        return jsonify({
            'translated_text': final_translated,
            'chunks': len(chunks),
            'success_rate': success_rate,
            'protected_elements': len(elements_map)
        })
    
    except Exception as e:
        logger.exception("翻译过程中发生错误")
        return jsonify({'error': f'翻译处理失败: {str(e)}'}), 500

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.svg')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)