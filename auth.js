/**
 * Web UI認証機能
 * JWT認証を使用したログイン・ログアウト・トークン管理
 */

class AuthManager {
    constructor() {
        this.token = localStorage.getItem('jwt_token');
        this.user = JSON.parse(localStorage.getItem('user_info') || 'null');
        this.apiBase = '';
    }

    /**
     * ログイン処理
     */
    async login(username, password) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'ログインに失敗しました');
            }

            const data = await response.json();
            this.setAuthData(data.access_token, data.user);
            return { success: true, user: data.user };
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * ログアウト処理
     */
    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('jwt_token');
        localStorage.removeItem('user_info');
        this.updateUI();
    }

    /**
     * 認証データの設定
     */
    setAuthData(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem('jwt_token', token);
        localStorage.setItem('user_info', JSON.stringify(user));
        this.updateUI();
    }

    /**
     * ログイン状態の確認
     */
    isLoggedIn() {
        return !!this.token && !!this.user;
    }

    /**
     * 現在のユーザー情報を取得
     */
    getCurrentUser() {
        return this.user;
    }

    /**
     * 認証ヘッダーを取得
     */
    getAuthHeaders() {
        if (!this.token) {
            return {};
        }
        return {
            'Authorization': `Bearer ${this.token}`
        };
    }

    /**
     * 認証付きAPIリクエスト
     */
    async apiRequest(url, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...this.getAuthHeaders(),
            ...(options.headers || {})
        };

        const response = await fetch(url, {
            ...options,
            headers: headers
        });

        if (response.status === 401) {
            // 認証エラーの場合はログアウト
            this.logout();
            this.showLoginModal();
            throw new Error('認証が必要です');
        }

        return response;
    }

    /**
     * UIの更新
     */
    updateUI() {
        const loginSection = document.getElementById('login-section');
        const userSection = document.getElementById('user-section');
        const loginBtn = document.getElementById('login-btn');
        const userInfo = document.getElementById('user-info');
        const logoutBtn = document.getElementById('logout-btn');

        if (this.isLoggedIn()) {
            if (loginSection) loginSection.style.display = 'none';
            if (userSection) userSection.style.display = 'block';
            if (userInfo) userInfo.textContent = this.user.username;
            if (loginBtn) loginBtn.style.display = 'none';
        } else {
            if (loginSection) loginSection.style.display = 'block';
            if (userSection) userSection.style.display = 'none';
            if (loginBtn) loginBtn.style.display = 'block';
        }
    }

    /**
     * ログインモーダルを表示
     */
    showLoginModal() {
        const modalElement = document.getElementById('loginModal');
        if (modalElement) {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        }
    }

    /**
     * ページ読み込み時の初期化
     */
    initialize() {
        this.updateUI();
        this.addLoginModal();
        this.addEventListeners();
    }

    /**
     * ログインモーダルをページに追加
     */
    addLoginModal() {
        const modalHTML = `
        <div class="modal fade" id="loginModal" tabindex="-1" aria-labelledby="loginModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="loginModalLabel">
                            <i class="bi bi-person-lock"></i> ログイン
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="loginForm">
                            <div class="mb-3">
                                <label for="username" class="form-label">ユーザー名</label>
                                <input type="text" class="form-control" id="username" required>
                            </div>
                            <div class="mb-3">
                                <label for="password" class="form-label">パスワード</label>
                                <input type="password" class="form-control" id="password" required>
                            </div>
                            <div id="loginError" class="alert alert-danger d-none"></div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
                        <button type="button" class="btn btn-primary" id="loginSubmit">
                            <span id="loginSpinner" class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                            ログイン
                        </button>
                    </div>
                </div>
            </div>
        </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    /**
     * イベントリスナーの追加
     */
    addEventListeners() {
        // ログインフォームの送信
        document.addEventListener('click', (e) => {
            if (e.target.id === 'loginSubmit') {
                this.handleLogin();
            }
            if (e.target.id === 'logout-btn') {
                this.logout();
            }
            if (e.target.id === 'login-btn') {
                this.showLoginModal();
            }
        });

        // Enterキーでログイン
        document.addEventListener('keypress', (e) => {
            if (e.target.closest('#loginModal') && e.key === 'Enter') {
                this.handleLogin();
            }
        });
    }

    /**
     * ログイン処理の実行
     */
    async handleLogin() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorDiv = document.getElementById('loginError');
        const spinner = document.getElementById('loginSpinner');
        const submitBtn = document.getElementById('loginSubmit');

        if (!username || !password) {
            this.showError('ユーザー名とパスワードを入力してください');
            return;
        }

        // ローディング表示
        spinner.classList.remove('d-none');
        submitBtn.disabled = true;
        errorDiv.classList.add('d-none');

        try {
            const result = await this.login(username, password);
            
            if (result.success) {
                // ログイン成功
                const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
                modal.hide();
                
                // フォームをリセット
                document.getElementById('loginForm').reset();
                
                // 成功メッセージ
                this.showSuccess(`ようこそ、${result.user.username}さん！`);
                
                // ページをリロード（必要に応じて）
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
                
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('ログインエラーが発生しました');
        } finally {
            spinner.classList.add('d-none');
            submitBtn.disabled = false;
        }
    }

    /**
     * エラーメッセージの表示
     */
    showError(message) {
        const errorDiv = document.getElementById('loginError');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.classList.remove('d-none');
        }
    }

    /**
     * 成功メッセージの表示
     */
    showSuccess(message) {
        // Bootstrap toastまたはアラートで成功メッセージを表示
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-success border-0 position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-check-circle me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        document.body.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // 3秒後に削除
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    /**
     * ナビゲーションバーに認証情報を追加
     */
    addAuthToNavbar() {
        console.log('addAuthToNavbar called');
        const navbar = document.querySelector('.navbar .navbar-nav');
        console.log('navbar element:', navbar);
        if (!navbar) {
            console.log('navbar element not found');
            return;
        }

        // 既存の認証要素を削除
        const existingLogin = document.getElementById('login-section');
        const existingUser = document.getElementById('user-section');
        if (existingLogin) existingLogin.remove();
        if (existingUser) existingUser.remove();

        const authHTML = `
            <div id="login-section" class="nav-item">
                <button id="login-btn" class="btn btn-outline-light btn-sm">
                    <i class="bi bi-person-lock"></i> ログイン
                </button>
            </div>
            <div id="user-section" class="nav-item dropdown" style="display: none;">
                <a class="nav-link dropdown-toggle text-white" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                    <i class="bi bi-person-circle"></i> <span id="user-info"></span>
                </a>
                <ul class="dropdown-menu">
                    <li><button id="logout-btn" class="dropdown-item">
                        <i class="bi bi-box-arrow-right"></i> ログアウト
                    </button></li>
                </ul>
            </div>
        `;
        
        navbar.insertAdjacentHTML('beforeend', authHTML);
        console.log('auth elements added to navbar');
    }
}

// グローバルインスタンス
const authManager = new AuthManager();

// ページ読み込み完了時に初期化
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing auth manager');
    authManager.initialize();
    authManager.addAuthToNavbar();
});

// バックアップ初期化（windowがロードされた後）
window.addEventListener('load', () => {
    console.log('Window loaded, checking auth navbar');
    const loginBtn = document.getElementById('login-btn');
    if (!loginBtn) {
        console.log('Login button not found, re-adding navbar');
        authManager.addAuthToNavbar();
    }
});

// エクスポート（他のスクリプトで使用する場合）
window.authManager = authManager; 