// ==UserScript==
// @name         获取网站Cookies
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  获取当前网站的cookies并以JSON格式显示，支持复制
// @author       You
// @match        *://*/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    
    // 创建一个悬浮按钮
    const button = document.createElement('button');
    button.textContent = '获取Cookies';
    button.style.position = 'fixed';
    button.style.top = '10px';
    button.style.right = '10px';
    button.style.zIndex = '9999';
    button.style.padding = '8px 12px';
    button.style.backgroundColor = '#4CAF50';
    button.style.color = 'white';
    button.style.border = 'none';
    button.style.borderRadius = '4px';
    button.style.cursor = 'pointer';
    
    // 添加点击事件
    button.addEventListener('click', function() {
        // 获取所有cookies
        const cookiesString = document.cookie;
        const cookiesList = cookiesString.split(';').map(cookie => cookie.trim());
        
        // 创建cookie对象
        const cookiesObject = {};
        cookiesList.forEach(cookie => {
            const [name, value] = cookie.split('=');
            if (name) {
                cookiesObject[name] = value;
            }
        });
        
        // 创建storage_state格式的对象
        const storageState = {
            cookies: Object.entries(cookiesObject).map(([name, value]) => {
                return {
                    name: name,
                    value: value,
                    domain: window.location.hostname,
                    path: '/',
                    expires: -1,
                    httpOnly: false,
                    secure: window.location.protocol === 'https:',
                    sameSite: 'Lax'
                };
            }),
            origins: []
        };
        
        // 创建自定义对话框
        const cookieData = JSON.stringify(storageState, null, 2);
        showCustomDialog(cookieData);
    });
    
    // 创建自定义对话框
    function showCustomDialog(content) {
        // 创建遮罩层
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        overlay.style.zIndex = '10000';
        
        // 创建对话框
        const dialog = document.createElement('div');
        dialog.style.position = 'fixed';
        dialog.style.top = '50%';
        dialog.style.left = '50%';
        dialog.style.transform = 'translate(-50%, -50%)';
        dialog.style.backgroundColor = 'white';
        dialog.style.padding = '20px';
        dialog.style.borderRadius = '8px';
        dialog.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
        dialog.style.maxWidth = '90%';
        dialog.style.width = '800px';
        dialog.style.maxHeight = '80%';
        dialog.style.overflow = 'auto';
        dialog.style.zIndex = '10001';
        dialog.style.display = 'flex';
        dialog.style.flexDirection = 'column';
        
        // 创建标题
        const title = document.createElement('h2');
        title.textContent = 'Cookies 数据';
        title.style.margin = '0 0 15px 0';
        
        // 创建内容区域
        const textarea = document.createElement('textarea');
        textarea.value = content;
        textarea.style.width = '100%';
        textarea.style.minHeight = '400px';
        textarea.style.marginBottom = '15px';
        textarea.style.padding = '8px';
        textarea.style.border = '1px solid #ccc';
        textarea.style.borderRadius = '4px';
        textarea.style.resize = 'vertical';
        textarea.style.fontFamily = 'monospace';
        textarea.style.fontSize = '14px';
        
        // 创建按钮容器
        const buttonContainer = document.createElement('div');
        buttonContainer.style.display = 'flex';
        buttonContainer.style.justifyContent = 'space-between';
        
        // 创建复制按钮
        const copyButton = document.createElement('button');
        copyButton.textContent = '复制';
        copyButton.style.padding = '8px 16px';
        copyButton.style.backgroundColor = '#4CAF50';
        copyButton.style.color = 'white';
        copyButton.style.border = 'none';
        copyButton.style.borderRadius = '4px';
        copyButton.style.cursor = 'pointer';
        
        copyButton.addEventListener('click', function() {
            textarea.select();
            document.execCommand('copy');
            copyButton.textContent = '已复制!';
            setTimeout(() => {
                copyButton.textContent = '复制';
            }, 2000);
        });
        
        // 创建关闭按钮
        const closeButton = document.createElement('button');
        closeButton.textContent = '关闭';
        closeButton.style.padding = '8px 16px';
        closeButton.style.backgroundColor = '#f44336';
        closeButton.style.color = 'white';
        closeButton.style.border = 'none';
        closeButton.style.borderRadius = '4px';
        closeButton.style.cursor = 'pointer';
        
        closeButton.addEventListener('click', function() {
            document.body.removeChild(overlay);
        });
        
        // 组装对话框
        buttonContainer.appendChild(copyButton);
        buttonContainer.appendChild(closeButton);
        
        dialog.appendChild(title);
        dialog.appendChild(textarea);
        dialog.appendChild(buttonContainer);
        
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
    }
    
    // 将按钮添加到页面
    document.body.appendChild(button);
})(); 