import sys
import os
import re
import json
import threading
import queue
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yt_dlp
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class CompactVideoDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Platform settings
        self.platform_settings = {
            'youtube': {'formats': ['mp4', 'mkv', 'webm'], 'max_resolution': '2160p'},
            'tiktok': {'formats': ['mp4'], 'watermark_removal': True},
            'instagram': {'formats': ['mp4'], 'supports_stories': True},
            'twitter': {'formats': ['mp4']},
            'facebook': {'formats': ['mp4'], 'requires_login': False},
            'vimeo': {'formats': ['mp4', 'webm']},
            'dailymotion': {'formats': ['mp4']},
            'twitch': {'formats': ['mp4', 'm3u8']},
            'reddit': {'formats': ['mp4']},
            'bilibili': {'formats': ['mp4', 'flv']}
        }
        
        # Variables
        self.downloading = False
        self.cancel_flag = threading.Event()
        self.message_queue = queue.Queue()
        
        # Config files
        self.config_file = Path.home() / ".video_downloader_config.json"
        self.history_file = Path.home() / ".video_downloader_history.json"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler('video_downloader.log')]
        )
        self.logger = logging.getLogger(__name__)
        
        self.load_config()
        self.initUI()
        
        # Start queue processor
        QTimer.singleShot(100, self.process_queue)
    
    def process_queue(self):
        """Process messages from the queue for thread-safe GUI updates"""
        try:
            while True:
                func, args = self.message_queue.get_nowait()
                func(*args)
        except queue.Empty:
            pass
        finally:
            QTimer.singleShot(100, self.process_queue)
    
    def queue_gui_update(self, func, *args):
        """Queue a GUI update for thread-safe execution"""
        self.message_queue.put((func, args))
    
    def load_config(self):
        """Load saved configuration"""
        self.config = {
            'output_path': os.path.expanduser('~/Downloads'),
            'quality': 'best',
            'format': 'mp4',
            'subtitle': False,
            'thumbnail': True,
            'metadata': True
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
    
    def save_config(self):
        """Save current configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def detect_platform(self, url: str) -> Optional[str]:
        """Detect which platform the URL belongs to"""
        patterns = {
            'youtube': [r'youtube\.com/watch', r'youtu\.be/', r'youtube\.com/shorts/'],
            'tiktok': [r'tiktok\.com/', r'vm\.tiktok\.com/', r'vt\.tiktok\.com/'],
            'instagram': [r'instagram\.com/', r'instagr\.am/'],
            'twitter': [r'twitter\.com/', r'x\.com/'],
            'facebook': [r'facebook\.com/', r'fb\.watch/'],
            'vimeo': [r'vimeo\.com/'],
            'dailymotion': [r'dailymotion\.com/'],
            'twitch': [r'twitch\.tv/', r'twitch\.tv/videos/'],
            'reddit': [r'reddit\.com/', r'redd\.it/'],
            'bilibili': [r'bilibili\.com/', r'b23\.tv/']
        }
        
        for platform, platform_patterns in patterns.items():
            for pattern in platform_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return platform
        
        return None
    
    def initUI(self):
        # Main window settings - Compact size
        self.setWindowTitle('hex Downloader')
        self.setGeometry(80, 80, 400, 600)  # Smaller window size
        
        # Simple dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #24292e;
            }
            QLabel {
                color: #ffffff;
                font-size: 11px;
            }
            QLineEdit {
                background-color: #24292e;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #24292e;
            }
            QPushButton {
                background-color: #24292e;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
            QTextEdit {
                background-color: #24292e;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px;
                font-family: 'Consolas', 'Monaco';
                font-size: 10px;
            }
            QProgressBar {
                background-color: #24292e;
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
                color: white;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #24292e;
                border-radius: 2px;
            }
            QComboBox {
                background-color: #24292e;
                color: white;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 4px;
                font-size: 11px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #24292e;
                color: white;
                selection-background-color: #24292e;
            }
            QCheckBox {
                color: white;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
            QCheckBox::indicator:checked {
                background-color: #24292e;
                border: 1px solid #24292e;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #24292e;
            }
            QTabBar::tab {
                background-color: #333;
                color: #ccc;
                padding: 6px 10px;
                margin-right: 1px;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background-color: #24292e;
                color: white;
                border-bottom: 2px solid #24292e;
            }
            QGroupBox {
                color: #ccc;
                border: 1px solid #444;
                border-radius: 3px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
            QStatusBar {
                background-color: #24292e;
                color: #ccc;
                border-top: 1px solid #444;
                font-size: 10px;
            }
        """)
        
        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title bar
        title_layout = QHBoxLayout()
        title_label = QLabel('🎬 Video Downloader')
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            padding: 5px;
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Simple platform indicator
        self.platform_label = QLabel('Platform: Auto')
        self.platform_label.setStyleSheet("color: #888; font-size: 10px;")
        title_layout.addWidget(self.platform_label)
        
        main_layout.addLayout(title_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setMaximumHeight(450)  # Limit height
        
        # Create tabs
        self.download_tab = QWidget()
        self.settings_tab = QWidget()
        
        self.tab_widget.addTab(self.download_tab, "Download")
        self.tab_widget.addTab(self.settings_tab, "Settings")
        
        main_layout.addWidget(self.tab_widget)
        
        # Setup each tab
        self.setup_download_tab()
        self.setup_settings_tab()
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('Ready')
        
        # Set main layout
        central_widget.setLayout(main_layout)
    
    def setup_download_tab(self):
        layout = QVBoxLayout(self.download_tab)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # URL section
        url_group = QGroupBox("Video URL")
        url_layout = QVBoxLayout()
        url_layout.setSpacing(5)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('Paste video URL here (YouTube, TikTok, Instagram, etc.)')
        self.url_input.textChanged.connect(self.auto_detect_platform)
        
        url_buttons = QHBoxLayout()
        paste_btn = QPushButton('📋 Paste')
        paste_btn.clicked.connect(lambda: self.url_input.setText(QApplication.clipboard().text()))
        paste_btn.setMaximumWidth(80)
        
        clear_btn = QPushButton('Clear')
        clear_btn.clicked.connect(lambda: self.url_input.clear())
        clear_btn.setMaximumWidth(80)
        
        url_buttons.addWidget(paste_btn)
        url_buttons.addWidget(clear_btn)
        url_buttons.addStretch()
        
        url_layout.addWidget(self.url_input)
        url_layout.addLayout(url_buttons)
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)
        
        # Download options in a grid
        options_group = QGroupBox("Download Options")
        options_layout = QGridLayout()
        options_layout.setSpacing(10)
        
        # Row 1: Quality and Format
        quality_label = QLabel('Quality:')
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(['best', '1080p', '720p', '480p', '360p', 'worst'])
        self.quality_combo.setCurrentText(self.config['quality'])
        self.quality_combo.setMaximumWidth(120)
        
        format_label = QLabel('Format:')
        self.format_combo = QComboBox()
        self.format_combo.addItems(['mp4', 'mkv', 'webm', 'mp3'])
        self.format_combo.setCurrentText(self.config['format'])
        self.format_combo.setMaximumWidth(100)
        
        options_layout.addWidget(quality_label, 0, 0)
        options_layout.addWidget(self.quality_combo, 0, 1)
        options_layout.addWidget(format_label, 0, 2)
        options_layout.addWidget(self.format_combo, 0, 3)
        
        # Row 2: Checkboxes
        self.subtitle_cb = QCheckBox('Subtitles')
        self.subtitle_cb.setChecked(self.config['subtitle'])
        self.thumbnail_cb = QCheckBox('Thumbnail')
        self.thumbnail_cb.setChecked(self.config['thumbnail'])
        self.metadata_cb = QCheckBox('Metadata')
        self.metadata_cb.setChecked(self.config['metadata'])
        
        options_layout.addWidget(self.subtitle_cb, 1, 0)
        options_layout.addWidget(self.thumbnail_cb, 1, 1)
        options_layout.addWidget(self.metadata_cb, 1, 2, 1, 2)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Output directory
        output_layout = QHBoxLayout()
        output_label = QLabel('Save to:')
        self.output_path = QLineEdit()
        self.output_path.setText(self.config['output_path'])
        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(self.browse_folder)
        browse_btn.setMaximumWidth(80)
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(browse_btn)
        layout.addLayout(output_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.info_btn = QPushButton('Get Info')
        self.info_btn.clicked.connect(self.get_video_info)
        self.info_btn.setMaximumWidth(100)
        
        self.download_btn = QPushButton('⬇ Download')
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setMaximumWidth(120)
        
        self.cancel_btn = QPushButton('Cancel')
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setMaximumWidth(100)
        
        button_layout.addWidget(self.info_btn)
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Compact log area
        log_label = QLabel('Log:')
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        
        layout.addWidget(log_label)
        layout.addWidget(self.log_text)
        
        layout.addStretch()
    
    def setup_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Advanced options
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QVBoxLayout()
        
        # User agent
        user_agent_layout = QHBoxLayout()
        user_agent_label = QLabel('User Agent:')
        self.user_agent_input = QLineEdit()
        self.user_agent_input.setText("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        user_agent_layout.addWidget(user_agent_label)
        user_agent_layout.addWidget(self.user_agent_input)
        advanced_layout.addLayout(user_agent_layout)
        
        # Proxy
        proxy_layout = QHBoxLayout()
        proxy_label = QLabel('Proxy:')
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText('Optional: http://user:pass@host:port')
        
        proxy_layout.addWidget(proxy_label)
        proxy_layout.addWidget(self.proxy_input)
        advanced_layout.addLayout(proxy_layout)
        
        # Cookies
        cookies_layout = QHBoxLayout()
        cookies_label = QLabel('Cookies File:')
        self.cookies_input = QLineEdit()
        self.cookies_input.setPlaceholderText('Optional: For private content')
        
        cookies_layout.addWidget(cookies_label)
        cookies_layout.addWidget(self.cookies_input)
        advanced_layout.addLayout(cookies_layout)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # FFmpeg check
        ffmpeg_group = QGroupBox("System")
        ffmpeg_layout = QVBoxLayout()
        
        check_btn = QPushButton('Check FFmpeg')
        check_btn.clicked.connect(self.check_ffmpeg)
        check_btn.setMaximumWidth(120)
        
        self.ffmpeg_label = QLabel('FFmpeg: Not checked')
        self.ffmpeg_label.setStyleSheet("color: #888;")
        
        ffmpeg_layout.addWidget(check_btn)
        ffmpeg_layout.addWidget(self.ffmpeg_label)
        ffmpeg_group.setLayout(ffmpeg_layout)
        layout.addWidget(ffmpeg_group)
        
        # Save button
        save_btn = QPushButton('Save Settings')
        save_btn.clicked.connect(self.save_current_config)
        save_btn.setMaximumWidth(120)
        layout.addWidget(save_btn, alignment=Qt.AlignCenter)
        
        layout.addStretch()
    
    def auto_detect_platform(self):
        url = self.url_input.text().strip()
        if not url:
            self.platform_label.setText('Platform: Auto')
            return
        
        platform = self.detect_platform(url)
        if platform:
            self.platform_label.setText(f'Platform: {platform.capitalize()}')
        else:
            self.platform_label.setText('Platform: Unknown')
    
    def log(self, message):
        """Add message to log"""
        timestamp = QTime.currentTime().toString('hh:mm:ss')
        self.log_text.append(f'[{timestamp}] {message}')
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Download Folder', 
                                                 self.output_path.text())
        if folder:
            self.output_path.setText(folder)
            self.log(f'Download folder: {folder}')
    
    def check_ffmpeg(self):
        def check():
            try:
                import subprocess
                result = subprocess.run(['ffmpeg', '-version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    version = result.stdout.split('\n')[0].split('version ')[1].split(' ')[0]
                    self.queue_gui_update(self.ffmpeg_label.setText, f'FFmpeg: ✓ {version}')
                    self.queue_gui_update(self.ffmpeg_label.setStyleSheet, "color: #4CAF50;")
                else:
                    self.queue_gui_update(self.ffmpeg_label.setText, 'FFmpeg: ✗ Not working')
                    self.queue_gui_update(self.ffmpeg_label.setStyleSheet, "color: #f44336;")
            except FileNotFoundError:
                self.queue_gui_update(self.ffmpeg_label.setText, 'FFmpeg: ✗ Not installed')
                self.queue_gui_update(self.ffmpeg_label.setStyleSheet, "color: #f44336;")
                self.queue_gui_update(
                    lambda: QMessageBox.information(self, "FFmpeg Required",
                    "FFmpeg is recommended for audio conversion.\n\n"
                    "Download from: https://ffmpeg.org/download.html")
                )
            except Exception as e:
                self.queue_gui_update(self.ffmpeg_label.setText, f'FFmpeg: ✗ Error')
                self.queue_gui_update(self.ffmpeg_label.setStyleSheet, "color: #f44336;")
        
        threading.Thread(target=check, daemon=True).start()
    
    def get_video_info(self):
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, 'Missing URL', 'Please enter a video URL')
            return
        
        self.log(f'Fetching info for: {url[:50]}...')
        
        def fetch_info():
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'socket_timeout': 30,
                    'user_agent': self.user_agent_input.text(),
                }
                
                # Add proxy if provided
                if self.proxy_input.text():
                    ydl_opts['proxy'] = self.proxy_input.text()
                
                # Add cookies if provided
                if self.cookies_input.text() and os.path.exists(self.cookies_input.text()):
                    ydl_opts['cookiefile'] = self.cookies_input.text()
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    if info:
                        title = info.get('title', 'Unknown')
                        duration = info.get('duration', 0)
                        uploader = info.get('uploader', 'Unknown')
                        
                        info_text = f"Title: {title}\n"
                        if duration:
                            mins, secs = divmod(duration, 60)
                            hours, mins = divmod(mins, 60)
                            if hours > 0:
                                info_text += f"Duration: {hours}:{mins:02d}:{secs:02d}\n"
                            else:
                                info_text += f"Duration: {mins}:{secs:02d}\n"
                        info_text += f"Uploader: {uploader}"
                        
                        self.queue_gui_update(self.log, f'✓ Info fetched successfully')
                        self.queue_gui_update(
                            lambda: QMessageBox.information(self, "Video Information", info_text)
                        )
                    else:
                        self.queue_gui_update(self.log, '✗ Could not fetch video information')
                        
            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e)
                if "Private video" in error_msg or "Sign in" in error_msg:
                    self.queue_gui_update(self.log, '✗ Private/age-restricted video (use cookies)')
                elif "not available" in error_msg.lower():
                    self.queue_gui_update(self.log, '✗ Geo-restricted content (use proxy)')
                else:
                    self.queue_gui_update(self.log, f'✗ Error: {error_msg[:100]}')
                    
            except Exception as e:
                self.queue_gui_update(self.log, f'✗ Error: {str(e)[:100]}')
        
        threading.Thread(target=fetch_info, daemon=True).start()
    
    def progress_hook(self, d):
        """yt-dlp progress callback"""
        if self.cancel_flag.is_set():
            raise yt_dlp.utils.DownloadError("Download cancelled by user")
        
        if d['status'] == 'downloading':
            if 'total_bytes' in d or 'total_bytes_estimate' in d:
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                
                if total > 0:
                    percent = (downloaded / total) * 100
                    speed = d.get('speed', 0)
                    
                    speed_str = ""
                    if speed:
                        if speed > 1024*1024:
                            speed_str = f"{speed/1024/1024:.1f} MB/s"
                        elif speed > 1024:
                            speed_str = f"{speed/1024:.1f} KB/s"
                        else:
                            speed_str = f"{speed:.0f} B/s"
                    
                    status = f"Downloading: {percent:.0f}%"
                    if speed_str:
                        status += f" ({speed_str})"
                    
                    self.queue_gui_update(lambda s=status: self.status_bar.showMessage(s))
                    self.queue_gui_update(lambda p=percent: self.progress_bar.setValue(int(p)))
                    
        elif d['status'] == 'finished':
            self.queue_gui_update(lambda: self.status_bar.showMessage("Processing..."))
    
    def get_ydl_options(self):
        """Get yt-dlp options based on current settings"""
        ydl_opts = {
            'outtmpl': os.path.join(self.output_path.text(), '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'no_warnings': True,
            'overwrites': True,
            'socket_timeout': 30,
            'user_agent': self.user_agent_input.text(),
        }
        
        # Add proxy if provided
        if self.proxy_input.text():
            ydl_opts['proxy'] = self.proxy_input.text()
        
        # Add cookies if provided
        if self.cookies_input.text() and os.path.exists(self.cookies_input.text()):
            ydl_opts['cookiefile'] = self.cookies_input.text()
        
        # Format selection
        download_type = self.format_combo.currentText()
        quality = self.quality_combo.currentText()
        
        if download_type == 'mp3':
            # Audio download
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            
            if self.metadata_cb.isChecked():
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                })
                
            if self.thumbnail_cb.isChecked():
                ydl_opts['postprocessors'].append({
                    'key': 'EmbedThumbnail',
                })
                
        else:
            # Video download
            if quality == 'best':
                ydl_opts['format'] = 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b'
            elif quality == 'worst':
                ydl_opts['format'] = 'wv*+wa/w'
            else:
                res = quality.replace('p', '')
                ydl_opts['format'] = f'bv*[height<={res}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b'
            
            ydl_opts['merge_output_format'] = download_type
            
            # Add subtitles
            if self.subtitle_cb.isChecked():
                ydl_opts['writesubtitles'] = True
                ydl_opts['embedsubtitles'] = True
            
            # Add thumbnail
            if self.thumbnail_cb.isChecked():
                ydl_opts['writethumbnail'] = True
                ydl_opts['embedthumbnail'] = True
            
            # Add metadata
            if self.metadata_cb.isChecked():
                ydl_opts['addmetadata'] = True
        
        return ydl_opts
    
    def download_worker(self, url):
        """Worker thread for downloading"""
        try:
            self.cancel_flag.clear()
            self.queue_gui_update(lambda: self.progress_bar.setValue(0))
            self.queue_gui_update(lambda: self.log(f'Starting download...'))
            
            ydl_opts = self.get_ydl_options()
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if info:
                    title = info.get('title', 'Unknown')
                    self.queue_gui_update(lambda: self.progress_bar.setValue(100))
                    self.queue_gui_update(lambda: self.log(f'✓ Download complete: {title}'))
                    self.queue_gui_update(lambda: self.status_bar.showMessage('Download complete', 3000))
                    
                    # Show success message
                    self.queue_gui_update(
                        lambda: QMessageBox.information(self, "Success", 
                                                      f"Downloaded successfully!\n\n{title}")
                    )
                    
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "cancelled" in error_msg.lower():
                self.queue_gui_update(lambda: self.log('✗ Download cancelled'))
                self.queue_gui_update(lambda: self.status_bar.showMessage('Cancelled', 3000))
            else:
                self.queue_gui_update(lambda: self.log(f'✗ Download failed: {error_msg[:100]}'))
                self.queue_gui_update(
                    lambda: QMessageBox.critical(self, "Error", 
                                               f"Download failed:\n\n{error_msg[:200]}")
                )
                
        except Exception as e:
            self.queue_gui_update(lambda: self.log(f'✗ Error: {str(e)[:100]}'))
            self.queue_gui_update(
                lambda: QMessageBox.critical(self, "Error", 
                                           f"An error occurred:\n\n{str(e)[:200]}")
            )
            
        finally:
            self.downloading = False
            self.queue_gui_update(lambda: self.download_btn.setEnabled(True))
            self.queue_gui_update(lambda: self.cancel_btn.setEnabled(False))
    
    def start_download(self):
        """Validate input and start download"""
        if self.downloading:
            return
        
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a video URL")
            return
        
        if not re.match(r'https?://', url):
            QMessageBox.warning(self, "Invalid URL", 
                              "Please enter a valid URL starting with http:// or https://")
            return
        
        # Validate output directory
        output_path = self.output_path.text()
        if not os.path.exists(output_path):
            try:
                os.makedirs(output_path, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot create directory:\n{e}")
                return
        
        # Disable/enable buttons
        self.downloading = True
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # Save current settings
        self.save_current_config()
        
        # Start download in background thread
        thread = threading.Thread(
            target=self.download_worker,
            args=(url,),
            daemon=True
        )
        thread.start()
    
    def cancel_download(self):
        """Cancel ongoing download"""
        if self.downloading:
            self.cancel_flag.set()
            self.status_bar.showMessage('Cancelling...')
            self.log('Cancelling download...')
            self.downloading = False
    
    def save_current_config(self):
        """Save current configuration from UI"""
        self.config.update({
            'output_path': self.output_path.text(),
            'quality': self.quality_combo.currentText(),
            'format': self.format_combo.currentText(),
            'subtitle': self.subtitle_cb.isChecked(),
            'thumbnail': self.thumbnail_cb.isChecked(),
            'metadata': self.metadata_cb.isChecked()
        })
        self.save_config()
        self.log('Settings saved')
        self.status_bar.showMessage('Settings saved', 3000)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application name
    app.setApplicationName("Video Downloader")
    app.setApplicationDisplayName("Video Downloader")
    
    window = CompactVideoDownloader()
    window.show()
    sys.exit(app.exec_())

