import os
import json
import time
import webbrowser
import urllib.parse
from typing import Optional, Dict
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Event
import requests
from PyQt6.QtWidgets import QMessageBox, QWidget, QLabel
from PyQt6.QtCore import QTimer

class CookieHandler(BaseHTTPRequestHandler):
    """Handler for capturing cookies from the browser."""
    def do_GET(self):
        """Handle GET request from browser."""
        if self.path == "/":
            # Initial page that redirects to ArkhamDB
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            port = self.server.server_address[1]
            html = f"""
            <html><body>
            <h2>TTSDeckSlicer Authorization</h2>
            <p id="message">Starting authentication process...</p>
            <div id="instructions" style="margin-top: 20px; padding: 10px; background: #f0f0f0; border-radius: 5px;">
                <strong>Quick Steps:</strong>
                <ol>
                    <li>ArkhamDB login will open in a new tab</li>
                    <li>Log in with your ArkhamDB credentials</li>
                    <li>While on ArkhamDB (still logged in), click this bookmarklet: <br>
                        <a href="javascript:(()=>{{try{{fetch('http://localhost:{port}/callback?cookies='+encodeURIComponent(document.cookie),{{mode:'no-cors'}}).then(()=>alert('Cookies sent to TTSDeckSlicer. You can return to the app.')).catch(()=>alert('Sent. You can return to the app.'));}}catch(e){{alert('Could not send automatically. As a fallback, copy this into TTSDeckSlicer: '+document.cookie);}}}})()" style="display:inline-block;padding:8px 12px;background:#1976d2;color:#fff;border-radius:4px;text-decoration:none;">Send ArkhamDB Cookies</a>
                    </li>
                    <li>Or click the button below to Check Login Status</li>
                </ol>
                <small>If the bookmarklet is blocked, open your browser bookmarks bar and drag the link onto it. Then click it from the ArkhamDB tab after logging in.</small>
                <hr style=\"margin:16px 0\"/>
                <div>
                    <strong>Manual paste (always works):</strong>
                    <p>From Chrome DevTools → Application → Cookies → https://arkhamdb.com, copy the value of <code>laravel_session</code> (and optionally <code>remember_web</code>) and paste below. You can paste either the single value or a full cookie string like <code>laravel_session=...; remember_web=...</code></p>
                    <form method=\"POST\" action=\"/callback\" onsubmit=\"setTimeout(()=>{{document.getElementById('message').innerText='Sent. You can return to TTSDeckSlicer.';}}, 100);\"> 
                        <textarea name=\"cookies\" rows=\"3\" style=\"width:100%;box-sizing:border-box;\" placeholder=\"laravel_session=...; remember_web=...\"></textarea>
                        <div style=\"margin-top:8px;\">
                            <button type=\"submit\" style=\"padding:8px 12px;\">Send Manually</button>
                        </div>
                    </form>
                </div>
            </div>
            <script>
                setTimeout(() => {{
                    document.getElementById('message').innerHTML = 'Redirecting to ArkhamDB in 3 seconds...';
                }}, 1000);
                
                setTimeout(() => {{
                    document.getElementById('message').innerHTML = 'Redirecting to ArkhamDB in 2 seconds...';
                }}, 2000);
                
                setTimeout(() => {{
                    document.getElementById('message').innerHTML = 'Redirecting to ArkhamDB in 1 second...';
                }}, 3000);
                
                setTimeout(() => {{
                    // Open ArkhamDB in a new tab so user can easily return
                    window.open('https://arkhamdb.com/login', '_blank');
                    document.getElementById('message').innerHTML = 
                        'ArkhamDB opened in new tab. After logging in there, click the "Send ArkhamDB Cookies" link (bookmarklet) while on ArkhamDB, or use the Check Login Status button below:';
                    document.getElementById('instructions').innerHTML = 
                        '<button onclick="window.location.href=\\'/check\\'" style="padding: 15px 30px; font-size: 16px; background: #1976d2; color: white; border: none; border-radius: 5px;">Check Login Status</button>';
                }}, 4000);
            </script>
            </body></html>
            """
            self.wfile.write(html.encode())
            
        elif self.path.startswith('/check'):
            # New endpoint for checking login status
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
            <html><head>
                <title>TTSDeckSlicer - Check Login</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
                    .status { padding: 15px; margin: 10px 0; border-radius: 5px; }
                    .info { background: #e3f2fd; border: 1px solid #1976d2; color: #1976d2; }
                    .success { background: #e8f5e8; border: 1px solid #4caf50; color: #2e7d32; }
                    .error { background: #ffebee; border: 1px solid #f44336; color: #c62828; }
                    button { padding: 10px 20px; margin: 5px; font-size: 14px; cursor: pointer; }
                    .big-button { padding: 15px 30px; font-size: 16px; background: #1976d2; color: white; border: none; border-radius: 5px; }
                </style>
            </head><body>
            <h2>TTSDeckSlicer - Check ArkhamDB Login</h2>
            <div id="status" class="status info">Checking for ArkhamDB cookies...</div>
            <div id="actions"></div>
            
            <script>
                function getAllCookies() {
                    try {
                        const cookies = {};
                        if (document.cookie && document.cookie.trim() !== '') {
                            document.cookie.split(';').forEach(cookie => {
                                try {
                                    const parts = cookie.trim().split('=');
                                    if (parts.length >= 2) {
                                        const name = parts[0].trim();
                                        const value = parts.slice(1).join('=').trim();
                                        if (name && value && value !== 'deleted') {
                                            cookies[name] = value;
                                        }
                                    }
                                } catch (e) {
                                    console.error('Error parsing cookie:', e);
                                }
                            });
                        }
                        return cookies;
                    } catch (e) {
                        console.error('Error getting cookies:', e);
                        return {};
                    }
                }
                
                function checkArkhamDBCookies(cookies) {
                    // Look for any ArkhamDB-related cookies
                    const arkhamCookies = ['PHPSESSID', 'remember_web', 'laravel_session', 'arkhamdb_session', 'XSRF-TOKEN'];
                    const found = arkhamCookies.filter(name => cookies.hasOwnProperty(name));
                    console.log('Found ArkhamDB cookies:', found);
                    return found.length > 0;
                }
                
                function sendCookies(cookies) {
                    const cookieData = JSON.stringify(cookies);
                    console.log('Sending cookies to TTSDeckSlicer:', Object.keys(cookies));
                    
                    return fetch('/callback?cookies=' + encodeURIComponent(cookieData), {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json',
                        }
                    })
                    .then(response => {
                        console.log('Callback response status:', response.status);
                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                        }
                        return response.json().catch(() => ({status: 'success'}));
                    });
                }
                
                function updateStatus(message, type = 'info') {
                    const statusDiv = document.getElementById('status');
                    statusDiv.className = `status ${type}`;
                    statusDiv.innerHTML = message;
                }
                
                function setActions(html) {
                    document.getElementById('actions').innerHTML = html;
                }
                
                function checkLoginStatus() {
                    console.log('Checking for ArkhamDB cookies...');
                    
                    const cookies = getAllCookies();
                    console.log('All cookies:', Object.keys(cookies));
                    
                    if (checkArkhamDBCookies(cookies)) {
                        updateStatus('✅ ArkhamDB login detected! Connecting to TTSDeckSlicer...', 'success');
                        setActions('<div>Please wait while we complete the connection...</div>');
                        
                        sendCookies(cookies)
                            .then(data => {
                                console.log('Authentication successful:', data);
                                updateStatus('🎉 Success! TTSDeckSlicer is now connected to ArkhamDB.<br>You can close this window.', 'success');
                                setActions('<button onclick="window.close()">Close Window</button>');
                                
                                // Try to close automatically after a delay
                                setTimeout(() => {
                                    try { window.close(); } catch(e) { console.log('Could not auto-close window'); }
                                }, 3000);
                            })
                            .catch(err => {
                                console.error('Callback error:', err);
                                updateStatus('❌ Error connecting to TTSDeckSlicer: ' + err.message, 'error');
                                setActions('<button onclick="checkLoginStatus()" class="big-button">Retry Connection</button>');
                            });
                    } else {
                        updateStatus('❌ No ArkhamDB login detected.', 'error');
                        setActions(`
                            <button onclick="openArkhamDB()" class="big-button">Open ArkhamDB Login</button>
                            <button onclick="checkLoginStatus()">Check Again</button>
                            <p><strong>Instructions:</strong></p>
                            <ol>
                                <li>Click "Open ArkhamDB Login" above</li>
                                <li>Log in with your ArkhamDB credentials</li>
                                <li>Return here and click "Check Again"</li>
                            </ol>
                            <p><small>Make sure cookies are enabled and you're using the same browser.</small></p>
                        `);
                    }
                }
                
                function openArkhamDB() {
                    window.open('https://arkhamdb.com/login', '_blank');
                    updateStatus('ArkhamDB login opened in new tab. After logging in, return here and click "Check Again".', 'info');
                }
                
                // Start checking immediately
                setTimeout(checkLoginStatus, 500);
            </script>
            </body></html>
            """
            self.wfile.write(html.encode())
            
        elif self.path.startswith('/callback'):
            # Store the cookies and signal completion
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            cookies = query.get('cookies', [''])[0]
            
            if hasattr(self.server, 'auth_instance'):
                self.server.auth_instance.cookies = self._parse_cookies(cookies)
                if hasattr(self.server, 'done_event'):
                    self.server.done_event.set()
            
            # Send proper response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "success"}')

    def do_POST(self):
        """Allow posting cookies via a form (manual paste fallback)."""
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except Exception:
            length = 0
        body = self.rfile.read(length) if length > 0 else b''
        # Default encoding utf-8
        try:
            body_text = body.decode('utf-8', errors='ignore')
        except Exception:
            body_text = ''

        cookies_str = ''
        ctype = self.headers.get('Content-Type', '')
        if 'application/x-www-form-urlencoded' in ctype:
            params = urllib.parse.parse_qs(body_text)
            cookies_str = params.get('cookies', [''])[0]
        else:
            cookies_str = body_text.strip()

        if hasattr(self.server, 'auth_instance'):
            self.server.auth_instance.cookies = self._parse_cookies(cookies_str)
            if hasattr(self.server, 'done_event'):
                self.server.done_event.set()

        # Respond with an HTML page that informs success and tries to close
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = """
        <html><body>
        <h3>Cookie received</h3>
        <p>You can return to TTSDeckSlicer. This window may close automatically.</p>
        <script>setTimeout(()=>{ try { window.close(); } catch(e) {} }, 1000);</script>
        </body></html>
        """
        self.wfile.write(html.encode('utf-8'))
    
    def _parse_cookies(self, cookie_str):
        """Parse cookie string into a dictionary."""
        if not cookie_str:
            return {}
        # First try JSON format: {"name":"value", ...}
        try:
            data = json.loads(cookie_str)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        # Fallback: raw cookie header string: "a=1; b=2; c=3"
        result: Dict[str, str] = {}
        try:
            parts = [p.strip() for p in cookie_str.split(';') if p.strip()]
            for part in parts:
                if '=' in part:
                    name, value = part.split('=', 1)
                    name = name.strip()
                    value = value.strip()
                    if name and value and value.lower() != 'deleted':
                        result[name] = value
        except Exception:
            return {}
        return result

    def log_message(self, format, *args):
        """Suppress logging."""
        pass

class BrowserAuth:
    """Handle browser-based authentication with ArkhamDB."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        self.parent = parent
        self.cookies = {}
        self._load_cookies()
    
    def _get_cookie_path(self) -> str:
        """Get path to cookie storage file."""
        return os.path.join(os.path.expanduser("~"), ".ttsdeck_cookies.json")
    
    def _load_cookies(self):
        """Load saved cookies."""
        try:
            with open(self._get_cookie_path(), 'r') as f:
                self.cookies = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.cookies = {}
    
    def _save_cookies(self):
        """Save cookies to file."""
        try:
            with open(self._get_cookie_path(), 'w') as f:
                json.dump(self.cookies, f)
        except Exception as e:
            print(f"Failed to save cookies: {e}")
    
    def apply_to_session(self, session: requests.Session):
        """Apply saved cookies to a requests session."""
        # If we have a web profile from embedded login, try to extract its cookies
        if hasattr(self, '_web_profile') and self._web_profile:
            try:
                # Force load all cookies from the profile
                store = self._web_profile.cookieStore()
                
                def capture_profile_cookie(cookie):
                    try:
                        domain = cookie.domain()
                        name = str(cookie.name())
                        value = str(cookie.value())
                        if 'arkhamdb' in domain.lower():
                            self.cookies[name] = value
                    except Exception:
                        pass
                
                # Connect temporarily to capture cookies
                store.cookieAdded.connect(capture_profile_cookie)
                store.loadAllCookies()
                
                # Wait a moment for cookies to be loaded
                import time
                time.sleep(0.5)
                
            except Exception:
                pass
        
        if not self.cookies:
            return

        # Clear any existing cookies first to avoid duplicates
        session.cookies.clear()
        
        # Apply cookies - use simple assignment for reliability
        for name, value in self.cookies.items():
            if not value:
                continue
            try:
                # Simple assignment - let requests handle domain matching
                session.cookies[name] = value
            except Exception:
                pass
    
    def authenticate(self) -> bool:
        """Start browser authentication process."""
        server = None
        thread = None
        done_event = Event()
        
        try:
            # Start local server to capture cookies
            server = HTTPServer(('localhost', 0), CookieHandler)
            port = server.server_address[1]
            
            # Store references in server
            server.auth_instance = self
            server.done_event = done_event
            
            # Start server in background thread
            thread = Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()
            
            # Clear any existing cookies
            self.cookies = {}
            
            # Try an embedded browser-based login (captures HttpOnly cookies) if available
            embedded_shown = False
            try:
                embedded_shown = self._try_embedded_web_login(done_event)
            except Exception:
                embedded_shown = False

            if not embedded_shown:
                # Open the root helper page in the browser
                # This page contains clear instructions and a bookmarklet to send cookies back
                auth_url = f'http://localhost:{port}/'
                try:
                    # Prefer opening in a new tab to keep the helper page visible
                    webbrowser.open_new_tab(auth_url)
                except Exception:
                    # Fallback
                    webbrowser.open(auth_url)
            
            # Show instructions dialog with better messaging
            if self.parent:
                if embedded_shown:
                    # For embedded login, the dialog handles everything internally
                    # Use a non-blocking wait with event processing
                    import time
                    from PyQt6.QtWidgets import QApplication
                    
                    timeout = 120
                    start_time = time.time()
                    
                    while not done_event.is_set() and (time.time() - start_time) < timeout:
                        QApplication.processEvents()  # Keep UI responsive
                        time.sleep(0.1)  # Small delay to prevent busy waiting
                    
                else:
                    # For browser-based login, use modal dialog as before
                    msg = QMessageBox(self.parent)
                    msg.setWindowTitle("ArkhamDB Login")
                    msg.setText("Connecting to ArkhamDB...")
                    msg.setInformativeText(
                        "1. A helper page has opened in your browser\n"
                        "2. Click 'Open ArkhamDB Login' and sign in\n"
                        "3. While on ArkhamDB, click the 'Send ArkhamDB Cookies' bookmarklet\n"
                        "4. Return to TTSDeckSlicer – this dialog will close automatically when done\n\n"
                        "Tip: If the bookmarklet can't be clicked, drag it to your bookmarks bar first."
                    )
                    msg.setIcon(QMessageBox.Icon.Information)
                    msg.setStandardButtons(QMessageBox.StandardButton.Cancel)
                    msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
                    
                    # Create a timer to update the message text and check for completion
                    remaining = 120  # Increased timeout to 2 minutes
                    
                    def update_timer():
                        nonlocal remaining
                        if done_event.is_set():
                            # Success! Close the dialog
                            msg.accept()
                            return
                        elif remaining > 0 and msg.isVisible():
                            msg.setText(f"Connecting to ArkhamDB...\n\nWaiting for login... ({remaining}s)")
                            remaining -= 1
                            QTimer.singleShot(1000, update_timer)
                        elif remaining <= 0 and msg.isVisible():
                            msg.reject()
                    
                    msg.setText("Connecting to ArkhamDB...\n\nWaiting for login... (120s)")
                    QTimer.singleShot(1000, update_timer)
                    
                    # Show the dialog - this will block until user cancels or authentication completes
                    result = msg.exec()
                    
                    # If user cancelled and we haven't succeeded yet
                    if result == QMessageBox.StandardButton.Cancel and not done_event.is_set():
                        return False
            else:
                # If no parent, just wait for completion
                done_event.wait(timeout=120)
            
            # Check final result
            if done_event.is_set() and self.cookies:
                if self.parent:
                    QMessageBox.information(self.parent, "Login Successful",
                        "Successfully connected to ArkhamDB!")
                return True
            else:
                # Manual fallback: allow user to paste cookie value from browser if helper flow failed
                try:
                    from PyQt6.QtWidgets import QInputDialog
                    text, ok = QInputDialog.getMultiLineText(
                        self.parent or QWidget(),
                        "Paste ArkhamDB Cookie",
                        (
                            "If the browser flow didn't finish, you can paste your ArkhamDB cookie here.\n\n"
                            "How to get it (Chrome):\n"
                            "1) Open ArkhamDB, press Option+Cmd+I (DevTools)\n"
                            "2) Go to Application → Storage → Cookies → https://arkhamdb.com\n"
                            "3) Copy the value of 'laravel_session' (and optionally 'remember_web')\n"
                            "4) Paste here either the single value, or the whole 'name=value; name2=value2' string."
                        ),
                        ""
                    )
                    if ok and text.strip():
                        parsed = self._parse_cookies(text.strip())
                        if not parsed:
                            # Assume it's just the laravel_session value
                            parsed = {"laravel_session": text.strip()}
                        self.cookies = parsed
                        if self.parent:
                            QMessageBox.information(self.parent, "Cookie Saved",
                                "Cookie captured. TTSDeckSlicer will now use your ArkhamDB session.")
                        return True
                except Exception:
                    pass
                if self.parent:
                    QMessageBox.warning(self.parent, "Login Failed",
                        "Failed to complete ArkhamDB login. Please try again.")
                return False
            
        except Exception as e:
            if self.parent:
                QMessageBox.warning(self.parent, "Login Error",
                    f"Failed to authenticate: {str(e)}")
            return False
            
        finally:
            # Clean up resources
            if server:
                try:
                    server.shutdown()
                    server.server_close()
                except:
                    pass
                    
            if thread:
                try:
                    thread.join(timeout=2.0)  # Increased join timeout
                except:
                    pass
                    
            if self.cookies:
                self._save_cookies()

    def _try_embedded_web_login(self, done_event: Event) -> bool:
        """Open an embedded browser to allow login and capture cookies via cookie store.
        Returns True if an embedded window was shown; False if not available.
        """
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            from PyQt6.QtWebEngineCore import QWebEngineProfile
            from PyQt6.QtCore import QUrl, QTimer as QtTimer, Qt
        except Exception:
            return False

        # Create a simple window with QWebEngineView
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel as QtLabel, QPushButton, QHBoxLayout

        dlg = QDialog(self.parent)
        dlg.setWindowTitle("ArkhamDB Login")
        dlg.resize(1000, 750)
        # Make it non-modal so the UI stays responsive
        dlg.setModal(False)
        layout = QVBoxLayout(dlg)

        # Status bar at top
        status_layout = QHBoxLayout()
        status_label = QtLabel("Log in with your ArkhamDB username/password below. This dialog will close automatically when login completes.")
        status_layout.addWidget(status_label)
        
        # Test button to verify WebEngine works
        test_btn = QPushButton("Test (Load Google)")
        test_btn.clicked.connect(lambda: view.setUrl(QUrl("https://www.google.com")))
        status_layout.addWidget(test_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(lambda: (done_event.set(), dlg.reject()))
        status_layout.addWidget(cancel_btn)
        
        layout.addLayout(status_layout)

        # Embedded browser
        view = QWebEngineView(dlg)
        layout.addWidget(view)

        # Use a dedicated persistent profile to ensure cookies are stored and signals fire reliably
        profile = QWebEngineProfile("TTSDeckSlicerProfile", dlg)
        try:
            home = os.path.expanduser("~")
            storage_path = os.path.join(home, ".ttsdeck_webprofile")
            os.makedirs(storage_path, exist_ok=True)
            profile.setPersistentStoragePath(storage_path)
            profile.setCachePath(os.path.join(storage_path, "cache"))
            
            # Set a user agent to avoid blocking
            profile.setHttpUserAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            try:
                # Force persistence where supported
                profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)  # type: ignore[attr-defined]
            except Exception:
                pass
        except Exception:
            pass

        # Create a page with the profile
        from PyQt6.QtWebEngineCore import QWebEnginePage
        page = QWebEnginePage(profile, view)
        view.setPage(page)
        
        store = profile.cookieStore()

        # Capture cookies as they are added - focus on actual login cookies, not just session cookies
        login_cookies = {"laravel_session", "remember_web", "arkhamdb_session", "REMEMBERME", "PHPSESSID"}  # Auth cookies
        session_cookies = {"XSRF-TOKEN", "sessionid", "csrftoken"}  # Session management

        def on_cookie_added(cookie):
            try:
                domain = cookie.domain()
                # PyQt6 returns QByteArray for name/value; convert robustly
                try:
                    name = bytes(cookie.name()).decode('utf-8', 'ignore')
                except Exception:
                    name = str(cookie.name())
                try:
                    value = bytes(cookie.value()).decode('utf-8', 'ignore')
                except Exception:
                    value = str(cookie.value())
                
                if 'arkhamdb' in domain.lower():
                    self.cookies[name] = value
                    # Consider success when authentication cookie is present
                    if name in login_cookies and value and value.lower() != 'deleted':
                        done_event.set()
                        dlg.accept()
            except Exception:
                pass

        store.cookieAdded.connect(on_cookie_added)
        
        # Also connect to cookieRemoved for cleanup
        def on_cookie_removed(cookie):
            try:
                domain = cookie.domain()
                name = str(cookie.name())
                if 'arkhamdb' in domain.lower() and name in self.cookies:
                    del self.cookies[name]
            except Exception:
                pass
        
        store.cookieRemoved.connect(on_cookie_removed)

        # Periodically sweep all cookies in case the signal was missed
        def sweep_cookies():
            try:
                # loadAllCookies will emit cookieAdded for each cookie
                store.loadAllCookies()
            except Exception:
                pass
            if not done_event.is_set() and dlg.isVisible():
                QtTimer.singleShot(5000, sweep_cookies)

        QtTimer.singleShot(1000, sweep_cookies)

        # Also sweep on navigation changes and check for login success
        def on_url_changed(url):
            url_str = url.toString()
            
            # If we navigated away from /login, we might be logged in
            if 'arkhamdb.com' in url_str and '/login' not in url_str:
                # Trigger cookie sweep
                sweep_cookies()
                
                # Also check if we can access a protected resource
                QtTimer.singleShot(2000, lambda: check_login_success())
        
        def check_login_success():
            """Check if login was successful by running JS to detect user info"""
            try:
                js_code = """
                // Check for common login indicators
                var loggedIn = false;
                var userInfo = '';
                
                // Look for user menu, logout button, or username
                var userMenu = document.querySelector('.navbar .dropdown-toggle, .user-menu, [href*="logout"], .username');
                if (userMenu) {
                    loggedIn = true;
                    userInfo = userMenu.textContent || userMenu.innerText || 'User found';
                }
                
                // Check for absence of login button
                var loginBtn = document.querySelector('a[href*="login"], .login-button');
                if (!loginBtn) {
                    loggedIn = true;
                }
                
                JSON.stringify({loggedIn: loggedIn, userInfo: userInfo, cookies: document.cookie});
                """
                
                def handle_login_check(result):
                    try:
                        if result and 'loggedIn":true' in result:
                            # Force cookie capture
                            store.loadAllCookies()
                            
                            # Check if we have actual login cookies
                            found_login_cookies = [k for k in self.cookies.keys() if k in login_cookies]
                            if found_login_cookies:
                                done_event.set()
                                dlg.accept()
                            else:
                                # Since login was successful, let's complete anyway and 
                                # rely on the WebEngine profile having the HttpOnly cookies
                                done_event.set()
                                dlg.accept()
                    except Exception:
                        pass
                
                view.page().runJavaScript(js_code, handle_login_check)
            except Exception:
                pass
        
        try:
            view.urlChanged.connect(on_url_changed)
        except Exception:
            pass

        # Connect to page load signals for debugging
        def on_load_started():
            status_label.setText("Loading ArkhamDB login page...")
        
        def on_load_finished(success):
            if success:
                status_label.setText("✅ ArkhamDB loaded. Please enter your username/password below and click 'Log in'")
            else:
                status_label.setText("❌ Failed to load ArkhamDB. Check your internet connection.")
        
        def on_load_progress(progress):
            status_label.setText(f"Loading ArkhamDB... {progress}%")
        
        view.loadStarted.connect(on_load_started)
        view.loadFinished.connect(on_load_finished)
        view.loadProgress.connect(on_load_progress)
        
        view.setUrl(QUrl("https://arkhamdb.com/login"))

        # Store the profile for later cookie extraction
        self._web_profile = profile
        
        # Timer to auto-close on success and update status
        remaining = 180  # Longer timeout for manual login
        def update_status():
            nonlocal remaining
            if done_event.is_set():
                status_label.setText("✅ Login successful! You have access to spoiler cards. Closing...")
                QTimer.singleShot(2000, dlg.accept)
                return
            elif remaining > 0:
                # Check if we have any login cookies to show progress
                login_cookie_count = len([k for k in self.cookies.keys() if k in login_cookies])
                if login_cookie_count > 0:
                    status_label.setText(f"✅ Login detected! Verifying access... ({remaining}s)")
                else:
                    status_label.setText(f"⏳ Please log in with your ArkhamDB credentials below ({remaining}s)")
                remaining -= 1
                QTimer.singleShot(1000, update_status)
            else:
                status_label.setText("⏰ Timeout - you can still continue logging in or click Cancel")
                # Don't auto-close, let user continue or cancel manually
        
        QTimer.singleShot(1000, update_status)
        
        # Show as non-modal dialog to keep UI responsive
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        
        # Process events to ensure dialog appears
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        return True