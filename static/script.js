document.addEventListener('DOMContentLoaded', function() {
    // DOM元素
    const sourceText = document.getElementById('source-text');
    const resultText = document.getElementById('result-text');
    const translateBtn = document.getElementById('translate-btn');
    const clearSourceBtn = document.getElementById('clear-source');
    const copyResultBtn = document.getElementById('copy-result');
    const downloadResultBtn = document.getElementById('download-result');
    const sourceCount = document.getElementById('source-count');
    const progressContainer = document.getElementById('progress-container');
    const statusBar = document.getElementById('status-bar');
    const formatInfo = document.getElementById('format-info');
    const translationInfo = document.getElementById('translation-info');
    const modelSelect = document.getElementById('model-select');
    const temperatureSlider = document.getElementById('temperature');
    const temperatureValue = document.getElementById('temperature-value');
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const settingsBtn = document.getElementById('settings-btn');
    const settingsModal = document.getElementById('settings-modal');
    const closeSettingsBtn = document.getElementById('close-settings');

    // 计数器
    sourceText.addEventListener('input', function() {
        const length = sourceText.value.length;
        sourceCount.textContent = `${length}/50000`;
        
        // 超出限制时显示警告
        if (length > 50000) {
            sourceCount.style.color = 'var(--error-color)';
        } else {
            sourceCount.style.color = '';
        }
    });

    // 翻译按钮
    translateBtn.addEventListener('click', function() {
        const text = sourceText.value.trim();
        if (!text) {
            showNotification('请输入需要翻译的文本', 'error');
            return;
        }
        
        translateText(text);
    });

    // 翻译函数
    async function translateText(text) {
        translateBtn.disabled = true;
        progressContainer.style.display = 'flex';
        resultText.value = '';
        statusBar.classList.add('hidden');
        
        try {
            const response = await fetch('/translate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    model: modelSelect.value,
                    temperature: parseFloat(temperatureSlider.value)
                }),
            });
            
            const result = await response.json();
            
            if (response.ok) {
                resultText.value = result.translated_text;
                displayStatus(result);
                showNotification('翻译完成', 'success');
            } else {
                showNotification(result.error || '翻译失败，请重试', 'error');
            }
        } catch (error) {
            showNotification('发生错误: ' + error.message, 'error');
        } finally {
            translateBtn.disabled = false;
            progressContainer.style.display = 'none';
        }
    }

    // 显示翻译状态
    function displayStatus(result) {
        if (result.format_elements) {
            const elements = result.format_elements;
            formatInfo.innerHTML = `
                保留了 ${elements.code_blocks || 0} 个代码块,
                ${elements.headers || 0} 个标题,
                ${elements.tables || 0} 个表格,
                ${elements.links || 0} 个链接
            `;
        }
        
        if (result.chunks) {
            translationInfo.textContent = `分成 ${result.chunks} 个块处理`;
        }
        
        statusBar.classList.remove('hidden');
    }

    // 显示通知
    function showNotification(message, type = 'info') {
        // 如果存在先前的通知，移除它
        const existingNotification = document.querySelector('.notification');
        if (existingNotification) {
            existingNotification.remove();
        }
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // 3秒后自动消失
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }

    // 清空源文本
    clearSourceBtn.addEventListener('click', function() {
        sourceText.value = '';
        sourceCount.textContent = '0/50000';
    });

    // 复制结果
    copyResultBtn.addEventListener('click', function() {
        if (!resultText.value) {
            showNotification('没有可复制的内容', 'error');
            return;
        }
        
        resultText.select();
        document.execCommand('copy');
        showNotification('已复制到剪贴板', 'success');
    });

    // 下载结果
    downloadResultBtn.addEventListener('click', function() {
        if (!resultText.value) {
            showNotification('没有可下载的内容', 'error');
            return;
        }
        
        const blob = new Blob([resultText.value], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'translated_markdown.md';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showNotification('文件已下载', 'success');
    });

    // 更新温度值显示
    temperatureSlider.addEventListener('input', function() {
        temperatureValue.textContent = temperatureSlider.value;
    });

    // 主题切换
    themeToggleBtn.addEventListener('click', function() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        
        // 更新图标
        const icon = themeToggleBtn.querySelector('i');
        if (newTheme === 'dark') {
            icon.className = 'fas fa-sun';
        } else {
            icon.className = 'fas fa-moon';
        }
        
        // 保存主题偏好到本地存储
        localStorage.setItem('theme', newTheme);
    });

    // 显示设置面板
    function showSettings() {
        settingsModal.classList.remove('hidden');
        setTimeout(() => {
            settingsModal.classList.add('visible');
        }, 10);
    }

    // 隐藏设置面板
    function hideSettings() {
        settingsModal.classList.remove('visible');
        setTimeout(() => {
            settingsModal.classList.add('hidden');
        }, 300);
    }

    // 设置按钮点击
    settingsBtn.addEventListener('click', showSettings);
    
    // 关闭设置按钮点击
    closeSettingsBtn.addEventListener('click', hideSettings);
    
    // 点击模态框外部关闭
    settingsModal.addEventListener('click', function(e) {
        if (e.target === settingsModal) {
            hideSettings();
        }
    });

    // 从本地存储加载设置
    function loadSettings() {
        // 加载主题
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
            const icon = themeToggleBtn.querySelector('i');
            icon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
        
        // 加载其他设置
        const savedModel = localStorage.getItem('model');
        if (savedModel) {
            modelSelect.value = savedModel;
        }
        
        const savedTemperature = localStorage.getItem('temperature');
        if (savedTemperature) {
            temperatureSlider.value = savedTemperature;
            temperatureValue.textContent = savedTemperature;
        }
    }

    // 保存设置
    function saveSettings() {
        localStorage.setItem('model', modelSelect.value);
        localStorage.setItem('temperature', temperatureSlider.value);
    }

    // 监听设置变化
    modelSelect.addEventListener('change', saveSettings);
    temperatureSlider.addEventListener('change', saveSettings);

    // 页面加载时加载设置
    loadSettings();
    
    // 添加键盘快捷键
    document.addEventListener('keydown', function(e) {
        // Esc键关闭设置面板
        if (e.key === 'Escape' && !settingsModal.classList.contains('hidden')) {
            hideSettings();
        }
        
        // Cmd/Ctrl + Enter 执行翻译
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            if (document.activeElement === sourceText && !translateBtn.disabled) {
                translateBtn.click();
            }
        }
    });
});