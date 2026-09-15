import sys
import re
import os
import urllib.parse
import time
import socket
from PyQt6.QtCore import QUrl, Qt, QPoint, QEvent, QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QVBoxLayout, 
    QWidget, QHBoxLayout, QPushButton, QDialog, QTextEdit, QTabWidget, QLabel
)
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView

# Get the exact directory where this script is saved
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Built-in custom Aim start page HTML
AIM_START_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Aim Start Page</title>
    <style>
        body {
            background-color: #292a2d;
            margin: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        }
        .sign-in-btn {
            position: absolute;
            top: 20px;
            left: 20px;
            background-color: #8ab4f8;
            color: #202124;
            padding: 8px 24px;
            text-decoration: none;
            border-radius: 4px;
            font-weight: 500;
            font-size: 14px;
            transition: background-color 0.2s;
        }
        .sign-in-btn:hover {
            background-color: #aecbfa;
        }
        h1 {
            color: #e8eaed; 
            font-size: 80px;
            font-weight: 500;
            margin-bottom: 30px;
            letter-spacing: -2px;
            user-select: none;
        }
        .search-container {
            width: 100%;
            max-width: 584px;
        }
        form {
            display: flex;
            background-color: #ffffff;
            border-radius: 24px;
            padding: 0 20px;
            height: 46px;
            align-items: center;
            box-shadow: 0 1px 6px rgba(0, 0, 0, 0.2);
        }
        input[type="text"] {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            font-size: 16px;
            color: #202124;
        }
    </style>
</head>
<body>
    <a class="sign-in-btn" href="https://accounts.google.com/v3/signin/identifier?continue=https://www.youtube.com/signin?action_handle_signin%3Dtrue%26app%3Ddesktop%26hl%3Den%26next%3Dhttps%253A%252F%252Fwww.youtube.com%252F%253FthemeRefresh%253D1&ec=65620&hl=en&passive=true&service=youtube&uilel=3&flowName=GlifWebSignIn&flowEntry=ServiceLogin&dsh=S454513712:1789253135142594">Sign in</a>
    
    <h1>Aim</h1>
    <div class="search-container">
        <form onsubmit="search(event)">
            <input type="text" id="query" placeholder="Search the web or type a URL (!w, !yt, !g)" autofocus autocomplete="off">
        </form>
    </div>

    <script>
        function search(event) {
            event.preventDefault();
            let q = document.getElementById("query").value.trim();
            if (q) {
                if (q.startsWith("http://") || q.startsWith("https://")) {
                    window.location.href = q;
                    return;
                }
                
                let engine = "google";
                let query = q;
                
                if (q.endsWith(" !w")) {
                    engine = "wikipedia";
                    query = q.substring(0, q.length - 3).trim();
                } else if (q.endsWith(" !yt")) {
                    engine = "youtube";
                    query = q.substring(0, q.length - 4).trim();
                } else if (q.endsWith(" !g")) {
                    engine = "google";
                    query = q.substring(0, q.length - 3).trim();
                } else if (q.includes(".") && !q.includes(" ")) {
                    window.location.href = "https://" + q;
                    return;
                }
                
                let encoded = encodeURIComponent(query);
                if (engine === "wikipedia") {
                    window.location.href = "https://en.wikipedia.org/wiki/Special:Search?search=" + encoded;
                } else if (engine === "youtube") {
                    window.location.href = "https://www.youtube.com/results?search_query=" + encoded;
                } else {
                    window.location.href = "https://www.google.com/search?q=" + encoded;
                }
            }
        }
    </script>
</body>
</html>
"""

class PingWorker(QThread):
    result = pyqtSignal(str)
    
    def __init__(self, url_str):
        super().__init__()
        self.url_str = url_str

    def run(self):
        try:
            host = urllib.parse.urlparse(self.url_str).netloc
            if not host:
                self.result.emit("N/A")
                return
            if ':' in host:
                host = host.split(':')[0]
            
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((host, 443))
            sock.close()
            
            latency = int((time.time() - start_time) * 1000)
            self.result.emit(f"{latency} ms")
        except Exception:
            self.result.emit("Timeout")

class AimConsole(QDialog):
    def __init__(self, browser_window):
        super().__init__(browser_window)
        self.browser_window = browser_window
        self.setWindowTitle("Aim.console")
        self.resize(650, 400)
        self.setStyleSheet("background-color: #202124; color: #e8eaed;")
        
        self.pending_url = None

        layout = QVBoxLayout(self)
        
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet("""
            QTextEdit {
                background-color: #292a2d;
                color: #8ab4f8;
                border: 1px solid #3c4043;
                font-family: Consolas, monospace;
                font-size: 13px;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.output_area)
        
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type Aim.CMD command or JavaScript...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #292a2d;
                color: white;
                border: 1px solid #5f6368;
                padding: 8px;
                font-family: Consolas, monospace;
                font-size: 13px;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #8ab4f8;
            }
        """)
        self.input_field.returnPressed.connect(self.execute_command)
        
        exec_btn = QPushButton("Run")
        exec_btn.setStyleSheet("""
            QPushButton {
                background-color: #8ab4f8;
                color: #202124;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #aecbfa;
            }
        """)
        exec_btn.clicked.connect(self.execute_command)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(exec_btn)
        layout.addLayout(input_layout)
        
        self.output_area.append("Aim.console initialized. Press F12 to toggle or close.\nAvailable Commands:\n- Aim.start/open-file = \"...\" \"...\" Aim.end/open-file\n- Aim.start/dart site = URL '...' Aim.end/dart site\n- Aim.start/Debug = True Aim.end/debug")

    def execute_command(self):
        cmd = self.input_field.text().strip()
        if not cmd:
            return
        
        self.output_area.append(f"> {cmd}")
        self.input_field.clear()

        match_debug = re.search(r"Aim\.start/Debug\s*=\s*(true|false)\s*Aim\.end/debug", cmd, re.IGNORECASE)
        if match_debug:
            state_str = match_debug.group(1).lower()
            state = (state_str == 'true')
            self.browser_window.set_debug_mode(state)
            self.output_area.append(f"[Aim.CMD] Debug mode set to {state}\n")
            return

        pattern1 = re.search(r"Aim\.start/open-file\s*=\s*['\"]([^'\"]+)['\"]\s*['\"]([^'\"]+)['\"]\s*Aim\.end/open-file", cmd, re.IGNORECASE)
        pattern2 = re.search(r"Aim\.start/open-file\s*=\s*['\"]([^'\"]+)['\"]\s*Aim\.end/open-file", cmd, re.IGNORECASE)
        file_path = None
        if pattern1:
            file_path = pattern1.group(2)
        elif pattern2:
            file_path = pattern2.group(1)

        if file_path:
            abs_path = os.path.abspath(file_path)
            if os.path.exists(abs_path):
                current_view = self.browser_window.current_browser()
                if current_view:
                    current_view.setUrl(QUrl.fromLocalFile(abs_path))
                self.output_area.append(f"[Aim.CMD] Opened file: {abs_path}\n")
            else:
                self.output_area.append(f"[Aim.CMD] File not found: {abs_path}\n")
            return

        if self.pending_url:
            ans = cmd.lower()
            if ans == 'y':
                self.browser_window.save_dart(self.pending_url)
                current_view = self.browser_window.current_browser()
                if current_view:
                    current_view.setUrl(QUrl(self.pending_url))
                self.output_area.append(f"[Aim.CMD] Darted and opened {self.pending_url}\n")
            elif ans == 'n':
                current_view = self.browser_window.current_browser()
                if current_view:
                    current_view.setUrl(QUrl(self.pending_url))
                self.output_area.append(f"[Aim.CMD] Opened {self.pending_url} without darting.\n")
            else:
                self.output_area.append("Please respond with 'y' or 'n'.")
                return
            self.pending_url = None
            return
        
        match = re.search(r"Aim\.start/dart\s+site\s*=\s*URL\s*['\"]([^'\"]+)['\"]\s*Aim\.end/dart\s+site", cmd, re.IGNORECASE)
        if match:
            url = match.group(1)
            if self.browser_window.is_url_darted(url):
                current_view = self.browser_window.current_browser()
                if current_view:
                    current_view.setUrl(QUrl(url))
                self.output_area.append(f"[Aim.CMD] Site already darted. Opening {url}\n")
            else:
                self.pending_url = url
                self.output_area.append(f"do you want to dart '{url}' and open? y/n\n")
        else:
            current_view = self.browser_window.current_browser()
            if current_view:
                current_view.page().runJavaScript(cmd, lambda result: self.handle_js_result(result))

    def handle_js_result(self, result):
        if result is not None:
            self.output_area.append(f"Result: {result}\n")
        else:
            self.output_area.append("Executed JS successfully.\n")

class AimBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aim Browser")
        self.resize(1200, 800)
        
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setMouseTracking(True)
        
        QApplication.instance().installEventFilter(self)

        self.resize_dir = None
        self.is_dragging = False
        self.drag_pos = QPoint()
        self.initial_geometry = self.geometry()

        # Persistent Profile Setup stored right next to the script
        storage_path = os.path.join(SCRIPT_DIR, "browser_data")
        os.makedirs(storage_path, exist_ok=True)
        self.profile = QWebEngineProfile("AimPersistentProfile", self)
        self.profile.setPersistentStoragePath(storage_path)
        self.profile.setCachePath(os.path.join(storage_path, "cache"))
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        self.debug_mode = False
        self.current_ping = "Calculating..."
        self.current_fps = 0

        central_widget = QWidget()
        central_widget.setMouseTracking(True)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        toolbar = QWidget()
        toolbar.setFixedHeight(44) 
        toolbar.setStyleSheet("background-color: #292a2d; border-bottom: 1px solid #3c4043;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.setSpacing(8)

        self.back_btn = QPushButton("←")
        self.forward_btn = QPushButton("→")
        self.reload_btn = QPushButton("↻")
        self.new_tab_btn = QPushButton("+")

        for btn in [self.back_btn, self.forward_btn, self.reload_btn, self.new_tab_btn]:
            btn.setFixedSize(30, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #bdc1c6;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3c4043;
                    color: white;
                }
            """)

        self.back_btn.clicked.connect(lambda: self.current_browser().back() if self.current_browser() else None)
        self.forward_btn.clicked.connect(lambda: self.current_browser().forward() if self.current_browser() else None)
        self.reload_btn.clicked.connect(self.reload_page)
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab())

        self.dart_btn = QPushButton("🎯 Dart")
        self.dart_btn.setFixedHeight(30)
        self.dart_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                color: #8ab4f8;
                border: none;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5f6368;
                color: white;
            }
        """)
        self.dart_btn.clicked.connect(self.toggle_dart_current_site)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.setStyleSheet("""
            QLineEdit {
                background-color: #202124;
                color: white;
                padding: 4px 10px;
                font-size: 13px;
                border: 1px solid #5f6368;
                border-radius: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #8ab4f8;
            }
        """)

        self.go_btn = QPushButton("Go")
        self.go_btn.setFixedSize(36, 30)
        self.go_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #bdc1c6; border: none; border-radius: 4px; font-size: 13px; }
            QPushButton:hover { background-color: #3c4043; color: white; }
        """)
        self.go_btn.clicked.connect(self.navigate_to_url)

        self.min_btn = QPushButton("—")
        self.close_btn = QPushButton("✕")
        for btn, hover_color in zip([self.min_btn, self.close_btn], ["#3c4043", "#e81123"]):
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: transparent; color: #bdc1c6; border: none; border-radius: 4px; font-size: 12px; }}
                QPushButton:hover {{ background-color: {hover_color}; color: white; }}
            """)
        self.min_btn.clicked.connect(self.showMinimized)
        self.close_btn.clicked.connect(self.close)

        toolbar_layout.addWidget(self.back_btn)
        toolbar_layout.addWidget(self.forward_btn)
        toolbar_layout.addWidget(self.reload_btn)
        toolbar_layout.addWidget(self.new_tab_btn)
        toolbar_layout.addWidget(self.dart_btn)
        toolbar_layout.addWidget(self.url_bar)
        toolbar_layout.addWidget(self.go_btn)
        toolbar_layout.addWidget(self.min_btn)
        toolbar_layout.addWidget(self.close_btn)

        main_layout.addWidget(toolbar)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #202124;
            }
            QTabBar::tab {
                background-color: #202124;
                color: #bdc1c6;
                padding: 6px 14px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: #292a2d;
                color: #ffffff;
                border-bottom: 2px solid #8ab4f8;
            }
            QTabBar::tab:hover:not(:selected) {
                background-color: #3c4043;
            }
        """)

        main_layout.addWidget(self.tab_widget)

        self.debug_label = QLabel(self)
        self.debug_label.setStyleSheet("""
            background-color: rgba(32, 33, 36, 220); 
            color: #8ab4f8; 
            font-family: Consolas, monospace; 
            font-size: 12px; 
            padding: 8px; 
            border: 1px solid #5f6368; 
            border-radius: 4px;
        """)
        self.debug_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.debug_label.hide()

        self.debug_timer = QTimer(self)
        self.debug_timer.timeout.connect(self.fetch_debug_data)

        self.add_new_tab()
        self.console_dialog = None

    def set_debug_mode(self, enabled):
        self.debug_mode = enabled
        if enabled:
            self.debug_label.show()
            self.debug_timer.start(1000)
            self.fetch_debug_data()
        else:
            self.debug_label.hide()
            self.debug_timer.stop()

    def fetch_debug_data(self):
        if not self.debug_mode: 
            return
            
        url = self.get_current_clean_url()
        
        if not hasattr(self, 'ping_worker') or not self.ping_worker.isRunning():
            self.ping_worker = PingWorker(url)
            self.ping_worker.result.connect(self.on_ping_result)
            self.ping_worker.start()
            
        js_fps_tracker = """
        if (typeof window.aim_fps_running === 'undefined') {
            window.aim_fps_running = true;
            window.aim_current_fps = 0;
            let frames = 0;
            let last = performance.now();
            function loop() {
                frames++;
                let now = performance.now();
                if (now - last >= 1000) {
                    window.aim_current_fps = Math.round((frames * 1000) / (now - last));
                    frames = 0;
                    last = now;
                }
                requestAnimationFrame(loop);
            }
            requestAnimationFrame(loop);
        }
        window.aim_current_fps;
        """
        browser = self.current_browser()
        if browser:
            browser.page().runJavaScript(js_fps_tracker, self.on_fps_result)
        else:
            self.on_fps_result(0)

    def on_ping_result(self, ping_str):
        self.current_ping = ping_str
        self.refresh_debug_ui()

    def on_fps_result(self, fps):
        self.current_fps = fps if fps else 0
        self.refresh_debug_ui()

    def refresh_debug_ui(self):
        if not self.debug_mode:
            return
        
        url = self.get_current_clean_url()
        display_url = url if len(url) < 45 else url[:42] + "..."
        
        text = f"URL : {display_url}\nPing: {self.current_ping}\nFPS : {self.current_fps}"
        self.debug_label.setText(text)
        self.debug_label.adjustSize()
        self.debug_label.move(self.width() - self.debug_label.width() - 20, 55)
        self.debug_label.raise_()

    def resizeEvent(self, event):
        if self.debug_mode and self.debug_label.isVisible():
            self.debug_label.move(self.width() - self.debug_label.width() - 20, 55)
        super().resizeEvent(event)

    def get_resize_direction(self, pos):
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = 6

        left = x < m
        right = x > w - m
        top = y < m
        bottom = y > h - m

        if top and left: return "top-left"
        if top and right: return "top-right"
        if bottom and left: return "bottom-left"
        if bottom and right: return "bottom-right"
        if left: return "left"
        if right: return "right"
        if top: return "top"
        if bottom: return "bottom"
        return None

    def eventFilter(self, obj, event):
        if not self.isVisible() or self.isMinimized() or self.isMaximized():
            return super().eventFilter(obj, event)

        widget = obj if isinstance(obj, QWidget) else None
        if widget and not self.isAncestorOf(widget) and widget != self:
            return super().eventFilter(obj, event)

        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                global_pos = event.globalPosition().toPoint()
                local_pos = self.mapFromGlobal(global_pos)
                self.resize_dir = self.get_resize_direction(local_pos)
                if self.resize_dir:
                    self.initial_geometry = self.geometry()
                    self.drag_pos = global_pos
                    return True
                elif local_pos.y() <= 44 and local_pos.x() < self.width() - 80:
                    self.is_dragging = True
                    self.drag_pos = global_pos
                    return True

        elif event.type() == QEvent.Type.MouseMove:
            global_pos = event.globalPosition().toPoint()
            if self.resize_dir:
                delta = global_pos - self.drag_pos
                geo = self.initial_geometry
                x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
                min_w, min_h = 400, 300

                if "left" in self.resize_dir:
                    new_w = max(min_w, w - delta.x())
                    if new_w > min_w or delta.x() <= 0:
                        x = x + (w - new_w)
                        w = new_w
                if "right" in self.resize_dir:
                    w = max(min_w, w + delta.x())
                if "top" in self.resize_dir:
                    new_h = max(min_h, h - delta.y())
                    if new_h > min_h or delta.y() <= 0:
                        y = y + (h - new_h)
                        h = new_h
                if "bottom" in self.resize_dir:
                    h = max(min_h, h + delta.y())

                self.setGeometry(x, y, w, h)
                return True

            elif self.is_dragging:
                delta = global_pos - self.drag_pos
                self.move(self.pos() + delta)
                self.drag_pos = global_pos
                return True

            else:
                local_pos = self.mapFromGlobal(global_pos)
                dir_hover = self.get_resize_direction(local_pos)
                if dir_hover in ("left", "right"):
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif dir_hover in ("top", "bottom"):
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                elif dir_hover in ("top-left", "bottom-right"):
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif dir_hover in ("top-right", "bottom-left"):
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                else:
                    self.unsetCursor()

        elif event.type() == QEvent.Type.MouseButtonRelease:
            if self.resize_dir or self.is_dragging:
                self.resize_dir = None
                self.is_dragging = False
                self.unsetCursor()
                return True

        return super().eventFilter(obj, event)

    def current_browser(self):
        return self.tab_widget.currentWidget()

    def add_new_tab(self, url=None, label="New Tab"):
        page = QWebEnginePage(self.profile, self)
        browser = QWebEngineView()
        browser.setPage(page)

        index = self.tab_widget.addTab(browser, label)
        self.tab_widget.setCurrentIndex(index)
        
        if url:
            browser.setUrl(QUrl(url))
        else:
            browser.setHtml(AIM_START_PAGE_HTML, QUrl("https://www.google.com"))
            
        browser.urlChanged.connect(lambda qurl, b=browser: self.on_browser_url_changed(b, qurl))
        browser.titleChanged.connect(lambda title, b=browser: self.on_browser_title_changed(b, title))
        return browser

    def close_tab(self, index):
        if self.tab_widget.count() > 1:
            widget = self.tab_widget.widget(index)
            widget.deleteLater()
            self.tab_widget.removeTab(index)
        else:
            browser = self.tab_widget.widget(index)
            if browser:
                browser.setHtml(AIM_START_PAGE_HTML, QUrl("https://www.google.com"))
                self.tab_widget.setTabText(index, "New Tab")

    def on_browser_url_changed(self, browser, qurl):
        if browser == self.current_browser():
            url_string = qurl.toString()
            if url_string == "about:blank" or url_string.startswith("data:"):
                self.url_bar.setText("")
            else:
                self.url_bar.setText(url_string)
            self.update_dart_button_state()

    def on_browser_title_changed(self, browser, title):
        index = self.tab_widget.indexOf(browser)
        if index != -1:
            if title:
                display_title = title if len(title) <= 20 else title[:17] + "..."
                self.tab_widget.setTabText(index, display_title)
            else:
                self.tab_widget.setTabText(index, "New Tab")

    def on_tab_changed(self, index):
        browser = self.current_browser()
        if browser:
            url_string = browser.url().toString()
            if url_string == "about:blank" or url_string.startswith("data:"):
                self.url_bar.setText("")
            else:
                self.url_bar.setText(url_string)
            self.update_dart_button_state()
            
            if self.debug_mode:
                self.fetch_debug_data()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F12:
            if self.console_dialog is None or not self.console_dialog.isVisible():
                self.console_dialog = AimConsole(self)
                self.console_dialog.show()
            else:
                self.console_dialog.close()
        else:
            super().keyPressEvent(event)

    def reload_page(self):
        browser = self.current_browser()
        if browser:
            if not self.url_bar.text():
                browser.setHtml(AIM_START_PAGE_HTML, QUrl("https://www.google.com"))
            else:
                browser.reload()

    def parse_search_input(self, text):
        text = text.strip()
        if not text:
            return "https://www.google.com"

        pattern1 = re.search(r"Aim\.start/open-file\s*=\s*['\"]([^'\"]+)['\"]\s*['\"]([^'\"]+)['\"]\s*Aim\.end/open-file", text, re.IGNORECASE)
        pattern2 = re.search(r"Aim\.start/open-file\s*=\s*['\"]([^'\"]+)['\"]\s*Aim\.end/open-file", text, re.IGNORECASE)
        file_path = None
        if pattern1:
            file_path = pattern1.group(2)
        elif pattern2:
            file_path = pattern2.group(1)

        if file_path:
            abs_path = os.path.abspath(file_path)
            if os.path.exists(abs_path):
                return QUrl.fromLocalFile(abs_path).toString()

        if text.startswith("http://") or text.startswith("https://"):
            return text

        engine = "google"
        query = text

        if text.endswith(" !w"):
            engine = "wikipedia"
            query = text[:-3].strip()
        elif text.endswith(" !yt"):
            engine = "youtube"
            query = text[:-4].strip()
        elif text.endswith(" !g"):
            engine = "google"
            query = text[:-3].strip()
        elif "." in text and " " not in text:
            return "https://" + text

        encoded_query = urllib.parse.quote(query)
        if engine == "wikipedia":
            return f"https://en.wikipedia.org/wiki/Special:Search?search={encoded_query}"
        elif engine == "youtube":
            return f"https://www.youtube.com/results?search_query={encoded_query}"
        else:
            return f"https://www.google.com/search?q={encoded_query}"

    def get_current_clean_url(self):
        browser = self.current_browser()
        if not browser:
            return ""
        url_str = browser.url().toString()
        if not url_str or url_str == "about:blank" or url_str.startswith("data:"):
            url_str = self.url_bar.text().strip()

        if url_str and not url_str.startswith("data:") and url_str != "about:blank":
            return self.parse_search_input(url_str)
        return ""

    def get_darts_file_path(self):
        return os.path.join(SCRIPT_DIR, "darts.txt")

    def is_url_darted(self, url_str):
        darts_path = self.get_darts_file_path()
        if not os.path.exists(darts_path):
            return False
        try:
            with open(darts_path, "r", encoding="utf-8") as f:
                content = f.read()
                return f'"{url_str}"' in content
        except Exception:
            return False

    def update_dart_button_state(self):
        url_str = self.get_current_clean_url()
        if url_str and self.is_url_darted(url_str):
            self.dart_btn.setText("❌ Undart")
        else:
            self.dart_btn.setText("🎯 Dart")

    def save_dart(self, url_str):
        darts_path = self.get_darts_file_path()
        dart_entry = f'Aim.start/Dart-Site = URL \n"{url_str}"\nAim.end/Dart-site\n\n'
        with open(darts_path, "a", encoding="utf-8") as f:
            f.write(dart_entry)
        self.update_dart_button_state()

    def remove_dart(self, url_str):
        darts_path = self.get_darts_file_path()
        if not os.path.exists(darts_path):
            return
        try:
            with open(darts_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            pattern = re.compile(rf'Aim\.start/Dart-Site\s*=\s*URL\s*\n\s*["\']?{re.escape(url_str)}["\']?\s*\n\s*Aim\.end/Dart-site\s*\n*', re.IGNORECASE)
            new_content = pattern.sub('', content)
            
            with open(darts_path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception:
            pass
        self.update_dart_button_state()

    def toggle_dart_current_site(self):
        url_str = self.get_current_clean_url()
        if url_str:
            if self.is_url_darted(url_str):
                self.remove_dart(url_str)
            else:
                self.save_dart(url_str)

    def navigate_to_url(self):
        text = self.url_bar.text().strip()
        browser = self.current_browser()
        if not browser:
            return
        if not text:
            browser.setHtml(AIM_START_PAGE_HTML, QUrl("https://www.google.com"))
            return

        final_url = self.parse_search_input(text)
        browser.setUrl(QUrl(final_url))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AimBrowser()
    window.show()
    sys.exit(app.exec())