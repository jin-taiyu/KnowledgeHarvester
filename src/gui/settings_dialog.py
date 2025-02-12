from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QCheckBox, QSpinBox, QLineEdit, QPushButton,
    QLabel, QFileDialog, QGroupBox, QTabWidget,
    QWidget
)
from PyQt6.QtCore import Qt

from ..crawler.base import CrawlerConfig
from ..storage.local_storage import StorageConfig

class SettingsDialog(QDialog):
    """Dialog for configuring crawler and storage settings."""
    
    def __init__(self, crawler_config: CrawlerConfig, storage_config: StorageConfig, parent=None):
        super().__init__(parent)
        self.crawler_config = crawler_config
        self.storage_config = storage_config
        
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Crawler settings tab
        crawler_tab = QWidget()
        crawler_layout = QVBoxLayout(crawler_tab)
        
        # Recursion group
        recursion_group = QGroupBox("Recursion Settings")
        recursion_layout = QVBoxLayout()
        
        self.enable_recursion = QCheckBox("Enable Recursive Crawling")
        self.enable_recursion.setChecked(self.crawler_config.enable_recursion)
        recursion_layout.addWidget(self.enable_recursion)
        
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("Maximum Depth:"))
        self.max_depth = QSpinBox()
        self.max_depth.setRange(1, 10)
        self.max_depth.setValue(self.crawler_config.max_depth)
        depth_layout.addWidget(self.max_depth)
        recursion_layout.addLayout(depth_layout)
        
        pages_layout = QHBoxLayout()
        pages_layout.addWidget(QLabel("Maximum Pages:"))
        self.max_pages = QSpinBox()
        self.max_pages.setRange(1, 1000)
        self.max_pages.setValue(self.crawler_config.max_pages)
        pages_layout.addWidget(self.max_pages)
        recursion_layout.addLayout(pages_layout)
        
        domains_layout = QHBoxLayout()
        domains_layout.addWidget(QLabel("Allowed Domains:"))
        self.allowed_domains = QLineEdit()
        if self.crawler_config.allowed_domains:
            self.allowed_domains.setText(",".join(self.crawler_config.allowed_domains))
        self.allowed_domains.setPlaceholderText("domain1.com,domain2.com")
        domains_layout.addWidget(self.allowed_domains)
        recursion_layout.addLayout(domains_layout)
        
        recursion_group.setLayout(recursion_layout)
        crawler_layout.addWidget(recursion_group)
        
        # JavaScript group
        js_group = QGroupBox("JavaScript Settings")
        js_layout = QVBoxLayout()
        
        self.enable_js = QCheckBox("Enable JavaScript")
        self.enable_js.setChecked(self.crawler_config.enable_javascript)
        js_layout.addWidget(self.enable_js)
        
        wait_layout = QHBoxLayout()
        wait_layout.addWidget(QLabel("Wait time (seconds):"))
        self.wait_time = QSpinBox()
        self.wait_time.setRange(1, 60)
        self.wait_time.setValue(self.crawler_config.wait_time)
        wait_layout.addWidget(self.wait_time)
        js_layout.addLayout(wait_layout)
        
        js_group.setLayout(js_layout)
        crawler_layout.addWidget(js_group)
        
        # Network group
        network_group = QGroupBox("Network Settings")
        network_layout = QFormLayout()
        
        self.proxy = QLineEdit()
        if self.crawler_config.proxy:
            self.proxy.setText(self.crawler_config.proxy)
        self.proxy.setPlaceholderText("e.g., http://proxy:8080")
        network_layout.addRow("Proxy:", self.proxy)
        
        self.headers = QLineEdit()
        if self.crawler_config.headers:
            self.headers.setText(str(self.crawler_config.headers))
        self.headers.setPlaceholderText("e.g., {'User-Agent': 'Custom'}")
        network_layout.addRow("Headers:", self.headers)
        
        network_group.setLayout(network_layout)
        crawler_layout.addWidget(network_group)
        
        # Add crawler tab
        tab_widget.addTab(crawler_tab, "Crawler")
        
        # Storage settings tab
        storage_tab = QWidget()
        storage_layout = QVBoxLayout(storage_tab)
        
        # Path settings
        path_group = QGroupBox("Storage Path")
        path_layout = QHBoxLayout()
        
        self.base_path = QLineEdit()
        self.base_path.setText(str(self.storage_config.base_path))
        path_layout.addWidget(self.base_path)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_path)
        path_layout.addWidget(browse_button)
        
        path_group.setLayout(path_layout)
        storage_layout.addWidget(path_group)
        
        # Organization settings
        org_group = QGroupBox("Organization")
        org_layout = QVBoxLayout()
        
        self.create_domain_dirs = QCheckBox("Create domain directories")
        self.create_domain_dirs.setChecked(self.storage_config.create_domain_dirs)
        org_layout.addWidget(self.create_domain_dirs)
        
        self.create_date_dirs = QCheckBox("Create date directories")
        self.create_date_dirs.setChecked(self.storage_config.create_date_dirs)
        org_layout.addWidget(self.create_date_dirs)
        
        # File naming
        name_layout = QFormLayout()
        
        self.file_prefix = QLineEdit()
        self.file_prefix.setText(self.storage_config.file_prefix)
        name_layout.addRow("File prefix:", self.file_prefix)
        
        self.file_suffix = QLineEdit()
        self.file_suffix.setText(self.storage_config.file_suffix)
        name_layout.addRow("File suffix:", self.file_suffix)
        
        org_layout.addLayout(name_layout)
        org_group.setLayout(org_layout)
        storage_layout.addWidget(org_group)
        
        # Add storage tab
        tab_widget.addTab(storage_tab, "Storage")
        
        layout.addWidget(tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def browse_path(self):
        """Open file dialog to select base storage path."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Storage Directory",
            str(self.storage_config.base_path)
        )
        if path:
            self.base_path.setText(path)
    
    def save_settings(self):
        """Save the settings and close dialog."""
        # Update crawler config
        self.crawler_config.enable_javascript = self.enable_js.isChecked()
        self.crawler_config.wait_time = self.wait_time.value()
        
        # Update recursion settings
        self.crawler_config.enable_recursion = self.enable_recursion.isChecked()
        self.crawler_config.max_depth = self.max_depth.value()
        self.crawler_config.max_pages = self.max_pages.value()
        
        # Parse allowed domains
        domains_text = self.allowed_domains.text().strip()
        if domains_text:
            self.crawler_config.allowed_domains = [
                domain.strip() for domain in domains_text.split(",")
                if domain.strip()
            ]
        else:
            self.crawler_config.allowed_domains = []
        
        # Update network settings
        proxy = self.proxy.text().strip()
        self.crawler_config.proxy = proxy if proxy else None
        
        headers_text = self.headers.text().strip()
        try:
            self.crawler_config.headers = eval(headers_text) if headers_text else None
        except:
            self.crawler_config.headers = None
        
        # Update storage config
        self.storage_config.base_path = Path(self.base_path.text())
        self.storage_config.create_domain_dirs = self.create_domain_dirs.isChecked()
        self.storage_config.create_date_dirs = self.create_date_dirs.isChecked()
        self.storage_config.file_prefix = self.file_prefix.text()
        self.storage_config.file_suffix = self.file_suffix.text()
        
        self.accept()
