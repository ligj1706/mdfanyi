document.addEventListener('DOMContentLoaded', function() {
    // 确保进度指示器初始状态为隐藏
    const progressContainer = document.getElementById('progress-container');
    if (progressContainer) {
        progressContainer.style.display = 'none';
    }
    
    // 元素引用
    const apiKeyInput = document.getElementById('api-key');
    const apiKeyContainer = document.getElementById('api-key-container');
    const modelSelect = document.getElementById('model-select');
    const modelSelectContainer = document.getElementById('model-select-container');
    const temperatureSlider = document.getElementById('temperature');
    const temperatureContainer = document.getElementById('temperature-container');
    const temperatureValue = document.getElementById('temperature-value');
    const sourceText = document.getElementById('source-text');
    const resultText = document.getElementById('result-text');
    const translateBtn = document.getElementById('translate-btn');
    const clearSourceBtn = document.getElementById('clear-source');
    const copyResultBtn = document.getElementById('copy-result');
    const downloadResultBtn = document.getElementById('download-result');
    const sourceCount = document.getElementById('source-count');
    const statusBar = document.getElementById('status-bar');
    const formatInfo = document.getElementById('format-info');
    const translationInfo = document.getElementById('translation-info');
    const advancedSettingsBtn = document.getElementById('advanced-settings-btn');
    const advancedSettingsPanel = document.getElementById('advanced-settings-panel');
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    
    // 主题切换
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
    
    themeToggleBtn.addEventListener('click', function() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        updateThemeIcon(newTheme);
    });
    
    function updateThemeIcon(theme) {
        if (theme === 'dark') {
            themeToggleBtn.innerHTML = '<i class="fas fa-sun"></i>';
        } else {
            themeToggleBtn.innerHTML = '<i class="fas fa-moon"></i>';
        }
    }
    
    // 高级设置按钮
    advancedSettingsBtn.addEventListener('click', function() {
        if (advancedSettingsPanel.style.display === 'none') {
            advancedSettingsPanel.style.display = 'block';
            advancedSettingsBtn.innerHTML = '<i class="fas fa-times"></i> 隐藏高级设置';
        } else {
            advancedSettingsPanel.style.display = 'none';
            advancedSettingsBtn.innerHTML = '<i class="fas fa-cog"></i> 高级设置';
        }
    });
    
    // 保存API密钥到本地存储
    if (localStorage.getItem('api_key')) {
        apiKeyInput.value = localStorage.getItem('api_key');
    }
    
    apiKeyInput.addEventListener('change', function() {
        localStorage.setItem('api_key', apiKeyInput.value);
    });
    
    // 温度滑块更新 - 默认值设为0.1
    temperatureValue.textContent = temperatureSlider.value;
    
    temperatureSlider.addEventListener('input', function() {
        temperatureValue.textContent = this.value;
    });
    
    // 字数统计
    sourceText.addEventListener('input', function() {
        const count = this.value.length;
        sourceCount.textContent = `${count}/50000`;
        
        if (count > 50000) {
            sourceCount.style.color = 'red';
        } else {
            sourceCount.style.color = '';
        }
    });
    
    // 清空源文本
    clearSourceBtn.addEventListener('click', function() {
        sourceText.value = '';
        sourceCount.textContent = '0/50000';
    });
    
    // 复制结果
    copyResultBtn.addEventListener('click', function() {
        const text = resultText.value;
        navigator.clipboard.writeText(text).then(function() {
            showToast('已复制到剪贴板');
        }, function() {
            showToast('复制失败，请手动复制', 'error');
        });
    });
    
    // 下载结果
    downloadResultBtn.addEventListener('click', function() {
        const text = resultText.value;
        const blob = new Blob([text], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'translated_' + new Date().toISOString().slice(0, 10) + '.md';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
    
    // 翻译按钮
    translateBtn.addEventListener('click', function() {
        const text = sourceText.value.trim();
        const apiKey = apiKeyInput.value.trim();
        const model = modelSelect.value;
        const temperature = temperatureSlider.value;
        
        if (!text) {
            showToast('请输入需要翻译的文本', 'error');
            return;
        }
        
        if (text.length > 50000) {
            showToast('文本长度超过限制（最大50000字符）', 'error');
            return;
        }
        
        // 显示进度
        translateBtn.disabled = true;
        if (progressContainer) {
            progressContainer.style.display = 'flex';
        }
        resultText.value = '';
        statusBar.classList.add('hidden');
        
        // 发送翻译请求
        fetch('/translate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                api_key: apiKey,
                temperature: temperature,
                model: model
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || '翻译请求失败');
                });
            }
            return response.json();
        })
        .then(data => {
            resultText.value = data.translated_text;
            
            // 显示格式信息
            formatInfo.innerHTML = `
                <strong>文档格式:</strong> 
                代码块: ${data.format_elements.code_blocks}, 
                标题: ${data.format_elements.headers}, 
                列表: ${data.format_elements.lists}, 
                表格: ${data.format_elements.tables}
            `;
            
            translationInfo.innerHTML = `
                <strong>翻译信息:</strong> 
                分块数: ${data.chunks}, 
                模型: ${model}, 
                温度: ${temperature}
            `;
            
            statusBar.classList.remove('hidden');
            showToast('翻译完成！', 'success');
        })
        .catch(error => {
            showToast(error.message, 'error');
            console.error('Error:', error);
        })
        .finally(() => {
            translateBtn.disabled = false;
            if (progressContainer) {
                progressContainer.style.display = 'none';
            }
        });
    });
    
    // 显示提示消息
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }
    
    // 添加Toast样式
    const style = document.createElement('style');
    style.textContent = `
        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background-color: #333;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            opacity: 0;
            transition: all 0.3s ease;
            z-index: 1000;
        }
        
        .toast.show {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }
        
        .toast-success {
            background-color: var(--success-color);
        }
        
        .toast-error {
            background-color: var(--error-color);
        }
        
        .toast-info {
            background-color: var(--primary-color);
        }
    `;
    document.head.appendChild(style);
}); 