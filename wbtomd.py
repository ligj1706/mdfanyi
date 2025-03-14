#!/usr/bin/env python3
"""
WebInk: Intelligent Web to Markdown Converter
将网页内容转换为标准Markdown格式
"""

import argparse
import re
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import unicodedata
import string

class WebInkConverter:
    def __init__(self):
        self.base_url = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def fetch_url(self, url):
        """获取网页内容"""
        self.base_url = url
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"获取网页内容失败: {e}")
    
    def extract_main_content(self, html):
        """使用BeautifulSoup提取主要内容"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 获取页面标题
        title = soup.title.string if soup.title else "无标题"
        
        # 移除不需要的元素
        for tag in soup.select('script, style, iframe, nav, footer, header, aside, [class*="sidebar"], [class*="banner"], [class*="ad-"], [class*="advertisement"], [id*="ad-"]'):
            tag.decompose()
            
        # 查找主要内容区域
        main_content = None
        for selector in ['main', 'article', '[role="main"]', '.main-content', '.post-content', '.entry-content', '.content', '#content']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # 如果没有找到明确的主要内容，使用body
        if not main_content:
            main_content = soup.body
            
        return title, main_content
    
    def convert_to_markdown(self, url, html=None):
        """将网页转换为Markdown"""
        if html is None:
            html = self.fetch_url(url)
        
        title, main_content = self.extract_main_content(html)
        
        # 开始转换
        markdown = f"# {title}\n\n"
        markdown += self.process_element(main_content)
        
        # 清理多余空行
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        return title, markdown
    
    def process_element(self, element):
        """递归处理HTML元素"""
        if element is None:
            return ""
        
        result = ""
        
        # 处理标题
        if element.name and re.match(r'h[1-6]', element.name):
            level = int(element.name[1])
            result += f"\n{'#' * level} {element.get_text().strip()}\n\n"
            return result
        
        # 处理段落
        elif element.name == 'p':
            text = element.get_text().strip()
            if text:
                result += f"{text}\n\n"
            return result
        
        # 处理链接
        elif element.name == 'a':
            href = element.get('href', '')
            if href:
                href = urljoin(self.base_url, href)
                text = element.get_text().strip() or href
                result += f"[{text}]({href})"
            else:
                result += element.get_text().strip()
            return result
        
        # 处理图片
        elif element.name == 'img':
            src = element.get('src', '')
            if src:
                src = urljoin(self.base_url, src)
                alt = element.get('alt', '') or "图片"
                title = element.get('title', '')
                title_attr = f' "{title}"' if title else ''
                result += f"![{alt}]({src}{title_attr})\n\n"
            return result
        
        # 处理列表
        elif element.name in ['ul', 'ol']:
            result += "\n"
            for i, li in enumerate(element.find_all('li', recursive=False)):
                marker = "- " if element.name == 'ul' else f"{i+1}. "
                li_text = self.process_element(li).strip()
                result += f"{marker}{li_text}\n"
            result += "\n"
            return result
        
        # 处理列表项
        elif element.name == 'li':
            for child in element.children:
                if hasattr(child, 'name'):
                    result += self.process_element(child)
                elif child.string and child.string.strip():
                    result += child.string.strip() + " "
            return result
        
        # 处理引用
        elif element.name == 'blockquote':
            inner_content = self.process_element(element).strip()
            result += "\n" + "\n".join(f"> {line}" for line in inner_content.split("\n")) + "\n\n"
            return result
        
        # 处理代码块
        elif element.name == 'pre':
            code = element.get_text().strip()
            code_language = ""
            if element.find('code') and element.find('code').get('class'):
                classes = element.find('code').get('class')
                lang_class = [c for c in classes if c.startswith('language-')]
                if lang_class:
                    code_language = lang_class[0][9:]
            result += f"\n```{code_language}\n{code}\n```\n\n"
            return result
        
        # 处理行内代码
        elif element.name == 'code' and element.parent.name != 'pre':
            result += f"`{element.get_text().strip()}`"
            return result
        
        # 处理强调
        elif element.name in ['strong', 'b']:
            result += f"**{element.get_text().strip()}**"
            return result
        
        # 处理斜体
        elif element.name in ['em', 'i']:
            result += f"*{element.get_text().strip()}*"
            return result
        
        # 处理表格
        elif element.name == 'table':
            # 获取表头
            header_row = element.find('thead').find('tr') if element.find('thead') else None
            if not header_row:
                header_row = element.find('tr')
            
            if header_row:
                headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
                result += "| " + " | ".join(headers) + " |\n"
                result += "| " + " | ".join(['---'] * len(headers)) + " |\n"
                
                # 获取表格内容
                rows = element.find('tbody').find_all('tr') if element.find('tbody') else element.find_all('tr')
                if element.find('thead') and rows and rows[0] == header_row:
                    rows = rows[1:]
                
                for row in rows:
                    cells = [td.get_text().strip() for td in row.find_all(['td', 'th'])]
                    result += "| " + " | ".join(cells) + " |\n"
                
                result += "\n"
            return result
        
        # 处理水平线
        elif element.name == 'hr':
            result += "\n---\n\n"
            return result
        
        # 处理换行
        elif element.name == 'br':
            result += "\n"
            return result
        
        # 处理文本节点
        elif element.name is None and element.string:
            text = element.string.strip()
            if text:
                result += text + " "
            return result
        
        # 递归处理子元素
        for child in element.children:
            if hasattr(child, 'name') or (hasattr(child, 'string') and child.string and child.string.strip()):
                result += self.process_element(child)
        
        return result

def slugify(text):
    """
    将文本转换为slug格式（小写，连字符分隔）
    """
    # 转换为ASCII，忽略无法转换的字符
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    # 移除非字母数字字符
    text = re.sub(r'[^\w\s-]', '', text.lower())
    # 将空格、下划线替换为连字符
    text = re.sub(r'[-\s]+', '-', text).strip('-_')
    return text

def get_filename_from_url(url, title):
    """
    从URL和标题生成文件名
    """
    # 尝试从标题生成
    if title and title.strip() != "无标题":
        return slugify(title)
    
    # 如果没有合适的标题，从URL生成
    parsed_url = urlparse(url)
    path = parsed_url.path.rstrip('/')
    if path:
        # 使用URL的最后一部分
        last_part = path.split('/')[-1]
        if last_part:
            # 移除文件扩展名（如果有）
            filename = os.path.splitext(last_part)[0]
            return slugify(filename)
    
    # 如果URL不包含有用信息，使用主机名
    return slugify(parsed_url.netloc)

def main():
    parser = argparse.ArgumentParser(description='WebInk: 将网页转换为Markdown格式')
    parser.add_argument('url', help='要转换的网页URL')
    parser.add_argument('-o', '--output', help='输出文件路径（默认根据标题自动生成）')
    parser.add_argument('-d', '--dir', help='输出目录（默认为当前目录）', default='.')
    
    args = parser.parse_args()
    
    converter = WebInkConverter()
    try:
        title, markdown = converter.convert_to_markdown(args.url)
        
        if args.output:
            # 使用指定的输出文件名
            output_file = args.output
            if not output_file.endswith('.md'):
                output_file += '.md'
        else:
            # 根据标题生成输出文件名
            filename = get_filename_from_url(args.url, title)
            output_file = f"{filename}.md"
        
        # 确保输出目录存在
        os.makedirs(args.dir, exist_ok=True)
        
        # 构建完整的输出路径
        output_path = os.path.join(args.dir, output_file)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"已保存到 {output_path}")
        
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()