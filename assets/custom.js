// DataMindVV - Plataforma Analítica Integrada
// JavaScript Customizado para Interatividade Avançada

// ===== CONFIGURAÇÕES GLOBAIS =====
const CONFIG = {
    animations: {
        duration: 300,
        easing: 'ease-out'
    },
    chat: {
        maxMessages: 100,
        typingSpeed: 50
    },
    theme: {
        autoDetect: true,
        storageKey: 'datamindvv-theme'
    }
};

// ===== UTILITÁRIOS =====
class Utils {
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    static throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    static fadeIn(element, duration = CONFIG.animations.duration) {
        element.style.opacity = 0;
        element.style.display = 'block';
        
        const start = performance.now();
        
        function animate(currentTime) {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            
            element.style.opacity = progress;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        }
        
        requestAnimationFrame(animate);
    }

    static fadeOut(element, duration = CONFIG.animations.duration) {
        const start = performance.now();
        const startOpacity = parseFloat(getComputedStyle(element).opacity);
        
        function animate(currentTime) {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            
            element.style.opacity = startOpacity * (1 - progress);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                element.style.display = 'none';
            }
        }
        
        requestAnimationFrame(animate);
    }

    static slideDown(element, duration = CONFIG.animations.duration) {
        element.style.height = '0px';
        element.style.overflow = 'hidden';
        element.style.display = 'block';
        
        const targetHeight = element.scrollHeight;
        const start = performance.now();
        
        function animate(currentTime) {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            
            element.style.height = (targetHeight * progress) + 'px';
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                element.style.height = 'auto';
                element.style.overflow = 'visible';
            }
        }
        
        requestAnimationFrame(animate);
    }

    static slideUp(element, duration = CONFIG.animations.duration) {
        const startHeight = element.offsetHeight;
        const start = performance.now();
        
        element.style.overflow = 'hidden';
        
        function animate(currentTime) {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            
            element.style.height = (startHeight * (1 - progress)) + 'px';
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                element.style.display = 'none';
                element.style.height = 'auto';
                element.style.overflow = 'visible';
            }
        }
        
        requestAnimationFrame(animate);
    }
}

// ===== GERENCIADOR DE TEMA =====
class ThemeManager {
    constructor() {
        this.currentTheme = this.getStoredTheme() || this.getPreferredTheme();
        this.init();
    }

    init() {
        this.setTheme(this.currentTheme);
        this.setupThemeToggle();
        this.watchSystemTheme();
    }

    getStoredTheme() {
        return localStorage.getItem(CONFIG.theme.storageKey);
    }

    getPreferredTheme() {
        if (CONFIG.theme.autoDetect) {
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        return 'light';
    }

    setTheme(theme) {
        // Aplicar tema ao documento
        document.documentElement.setAttribute('data-theme', theme);
        document.body.setAttribute('data-theme', theme);
        
        // Salvar no localStorage
        localStorage.setItem(CONFIG.theme.storageKey, theme);
        this.currentTheme = theme;
        
        // Atualizar botão de toggle
        this.updateThemeToggle();
        
        // Disparar evento customizado para outros componentes
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
        
        // Atualizar gráficos Plotly se existirem
        this.updatePlotlyTheme(theme);
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }
    
    updatePlotlyTheme(theme) {
        // Atualizar tema dos gráficos Plotly
        const plots = document.querySelectorAll('.js-plotly-plot');
        plots.forEach(plot => {
            if (plot.data && plot.layout) {
                const update = {
                    'paper_bgcolor': theme === 'dark' ? '#2d3748' : '#ffffff',
                    'plot_bgcolor': theme === 'dark' ? '#1a1d23' : '#ffffff',
                    'font.color': theme === 'dark' ? '#ffffff' : '#212529'
                };
                Plotly.relayout(plot, update);
            }
        });
    }

    setupThemeToggle() {
        // Verificar se já existe um botão de tema no dashboard
        const dashboardToggle = document.getElementById('theme-toggle-btn');
        if (dashboardToggle) {
            // Se existe, adicionar listener ao botão do dashboard
            dashboardToggle.addEventListener('click', () => this.toggleTheme());
            return;
        }
        
        // Criar botão de toggle flutuante se não existir
        if (!document.getElementById('theme-toggle')) {
            const themeToggle = document.createElement('button');
            themeToggle.id = 'theme-toggle';
            themeToggle.className = 'btn btn-outline-secondary btn-sm';
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
            themeToggle.title = 'Alternar tema';
            themeToggle.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1050;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            `;
            
            themeToggle.addEventListener('click', () => this.toggleTheme());
            themeToggle.addEventListener('mouseenter', () => {
                themeToggle.style.transform = 'scale(1.1)';
            });
            themeToggle.addEventListener('mouseleave', () => {
                themeToggle.style.transform = 'scale(1)';
            });
            
            document.body.appendChild(themeToggle);
        }
    }

    updateThemeToggle() {
        // Atualizar botão flutuante
        const toggle = document.getElementById('theme-toggle');
        if (toggle) {
            const icon = toggle.querySelector('i');
            if (this.currentTheme === 'dark') {
                icon.className = 'fas fa-sun';
                toggle.title = 'Modo claro';
            } else {
                icon.className = 'fas fa-moon';
                toggle.title = 'Modo escuro';
            }
        }
        
        // Atualizar botão do dashboard
        const dashboardToggle = document.getElementById('theme-toggle-btn');
        if (dashboardToggle) {
            const icon = dashboardToggle.querySelector('i');
            if (icon) {
                if (this.currentTheme === 'dark') {
                    icon.className = 'fas fa-sun';
                    dashboardToggle.title = 'Modo claro';
                } else {
                    icon.className = 'fas fa-moon';
                    dashboardToggle.title = 'Modo escuro';
                }
            }
        }
    }

    watchSystemTheme() {
        if (CONFIG.theme.autoDetect) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (!this.getStoredTheme()) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }
}

// ===== CHAT FLUTUANTE =====
class FloatingChat {
    constructor() {
        this.isOpen = false;
        this.messages = [];
        this.init();
    }

    init() {
        this.createChatElements();
        this.setupEventListeners();
    }

    createChatElements() {
        // Botão flutuante
        const floatingButton = document.createElement('div');
        floatingButton.id = 'floating-chat-btn';
        floatingButton.className = 'floating-chat';
        floatingButton.innerHTML = '<i class="fas fa-robot"></i>';
        floatingButton.title = 'Chat com IA';
        
        // Janela do chat
        const chatWindow = document.createElement('div');
        chatWindow.id = 'floating-chat-window';
        chatWindow.className = 'chat-window';
        chatWindow.innerHTML = `
            <div class="chat-header">
                <div class="d-flex justify-content-between align-items-center">
                    <span><i class="fas fa-robot me-2"></i>Chat com IA</span>
                    <button class="btn btn-sm btn-outline-light" id="close-chat">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="chat-body" id="chat-messages">
                <div class="text-center text-muted p-3">
                    <i class="fas fa-robot fa-2x mb-2"></i>
                    <p>Olá! Sou seu assistente de IA. Como posso ajudar com seus dados?</p>
                </div>
            </div>
            <div class="chat-input">
                <div class="input-group">
                    <input type="text" class="form-control" id="chat-input" placeholder="Digite sua pergunta...">
                    <button class="btn btn-primary" id="send-chat">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(floatingButton);
        document.body.appendChild(chatWindow);
    }

    setupEventListeners() {
        const floatingBtn = document.getElementById('floating-chat-btn');
        const chatWindow = document.getElementById('floating-chat-window');
        const closeBtn = document.getElementById('close-chat');
        const sendBtn = document.getElementById('send-chat');
        const chatInput = document.getElementById('chat-input');

        floatingBtn.addEventListener('click', () => this.toggleChat());
        closeBtn.addEventListener('click', () => this.closeChat());
        sendBtn.addEventListener('click', () => this.sendMessage());
        
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });

        // Fechar chat ao clicar fora
        document.addEventListener('click', (e) => {
            if (this.isOpen && !chatWindow.contains(e.target) && !floatingBtn.contains(e.target)) {
                this.closeChat();
            }
        });
    }

    toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }

    openChat() {
        const chatWindow = document.getElementById('floating-chat-window');
        chatWindow.classList.add('show');
        this.isOpen = true;
        
        // Focar no input
        setTimeout(() => {
            document.getElementById('chat-input').focus();
        }, 300);
    }

    closeChat() {
        const chatWindow = document.getElementById('floating-chat-window');
        chatWindow.classList.remove('show');
        this.isOpen = false;
    }

    sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        
        if (message) {
            this.addMessage(message, 'user');
            input.value = '';
            
            // Simular resposta da IA (integrar com o backend real)
            setTimeout(() => {
                this.addMessage('Esta é uma resposta simulada. Integre com o backend real para funcionalidade completa.', 'ai');
            }, 1000);
        }
    }

    addMessage(text, sender) {
        const messagesContainer = document.getElementById('chat-messages');
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender}-message mb-3`;
        
        const isUser = sender === 'user';
        messageElement.innerHTML = `
            <div class="d-flex ${isUser ? 'justify-content-end' : 'justify-content-start'}">
                <div class="${isUser ? 'bg-primary text-white' : 'bg-light'} p-2 rounded" style="max-width: 80%;">
                    ${isUser ? '' : '<i class="fas fa-robot me-1"></i>'}
                    ${text}
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Animação de entrada
        messageElement.style.opacity = '0';
        messageElement.style.transform = 'translateY(20px)';
        
        requestAnimationFrame(() => {
            messageElement.style.transition = 'all 0.3s ease';
            messageElement.style.opacity = '1';
            messageElement.style.transform = 'translateY(0)';
        });
        
        this.messages.push({ text, sender, timestamp: new Date() });
        
        // Limitar número de mensagens
        if (this.messages.length > CONFIG.chat.maxMessages) {
            this.messages.shift();
            messagesContainer.removeChild(messagesContainer.firstChild);
        }
    }
}

// ===== MELHORIAS DE UX =====
class UXEnhancements {
    constructor() {
        this.init();
    }

    init() {
        this.setupSmoothScrolling();
        this.setupTooltips();
        this.setupLoadingStates();
        this.setupFormValidation();
        this.setupKeyboardShortcuts();
        this.setupProgressIndicators();
    }

    setupSmoothScrolling() {
        // Scroll suave para links âncora
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    setupTooltips() {
        // Inicializar tooltips do Bootstrap se disponível
        if (typeof bootstrap !== 'undefined') {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }

    setupLoadingStates() {
        // Adicionar estados de loading para botões
        document.addEventListener('click', function(e) {
            if (e.target.matches('button[type="submit"], .btn-loading')) {
                const btn = e.target;
                const originalText = btn.innerHTML;
                
                btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Carregando...';
                btn.disabled = true;
                
                // Restaurar após 3 segundos (ajustar conforme necessário)
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }, 3000);
            }
        });
    }

    setupFormValidation() {
        // Validação visual em tempo real
        document.addEventListener('input', function(e) {
            if (e.target.matches('input, select, textarea')) {
                const field = e.target;
                const isValid = field.checkValidity();
                
                field.classList.remove('is-valid', 'is-invalid');
                field.classList.add(isValid ? 'is-valid' : 'is-invalid');
            }
        });
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + K para abrir chat
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const chatBtn = document.getElementById('floating-chat-btn');
                if (chatBtn) chatBtn.click();
            }
            
            // Esc para fechar modais/chat
            if (e.key === 'Escape') {
                const chatWindow = document.getElementById('floating-chat-window');
                if (chatWindow && chatWindow.classList.contains('show')) {
                    document.getElementById('close-chat').click();
                }
            }
        });
    }

    setupProgressIndicators() {
        // Indicador de progresso para uploads
        const fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            input.addEventListener('change', function() {
                if (this.files.length > 0) {
                    const progressBar = document.createElement('div');
                    progressBar.className = 'progress mt-2';
                    progressBar.innerHTML = `
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" style="width: 0%"></div>
                    `;
                    
                    this.parentNode.appendChild(progressBar);
                    
                    // Simular progresso (integrar com upload real)
                    let progress = 0;
                    const interval = setInterval(() => {
                        progress += Math.random() * 30;
                        if (progress >= 100) {
                            progress = 100;
                            clearInterval(interval);
                            setTimeout(() => progressBar.remove(), 1000);
                        }
                        progressBar.querySelector('.progress-bar').style.width = progress + '%';
                    }, 200);
                }
            });
        });
    }
}

// ===== INICIALIZAÇÃO =====
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar componentes
    const themeManager = new ThemeManager();
    const floatingChat = new FloatingChat();
    const uxEnhancements = new UXEnhancements();
    
    // Adicionar classe de carregamento concluído
    document.body.classList.add('loaded');
    
    // Log de inicialização
    console.log('🚀 DataMindVV - Plataforma Analítica Integrada carregada com sucesso!');
    console.log('💡 Atalhos disponíveis:');
    console.log('   - Ctrl/Cmd + K: Abrir chat com IA');
    console.log('   - Esc: Fechar modais/chat');
});

// ===== EXPORTAR PARA USO GLOBAL =====
window.DataMindVV = {
    Utils,
    ThemeManager,
    FloatingChat,
    UXEnhancements,
    CONFIG
};