import sys
from pathlib import Path
from typing import Optional, List
import asyncio
import threading
from queue import Queue
import uuid
import json

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QProgressBar, QComboBox,
    QTextEdit, QLabel, QFileDialog, QMessageBox,
    QApplication, QListWidget, QListWidgetItem, QGroupBox,
    QMenu, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QPoint, QTimer

from ..crawler.base import BaseCrawler, CrawlerConfig, CrawlResult
from ..crawler.filters import PruningContentFilter, BM25ContentFilter, FilterPipeline
from ..crawler.formatters import MarkdownFormatter, JsonFormatter, FormattedContent
from ..storage.local_storage import LocalStorage, StorageConfig

class CrawlerWorker(QObject):
    """Worker for running crawler in a separate thread."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    
    def __init__(self, url: str, config: CrawlerConfig):
        super().__init__()
        self.url = url
        self.config = config
        self.crawler = BaseCrawler(config)
        self._should_stop = False
    
    def stop(self):
        """Stop the crawler."""
        self._should_stop = True
    
    async def run(self):
        """Run the crawler."""
        try:
            # Initial progress
            self.progress.emit(10)
            self.status.emit("Starting crawler...")
            
            # Process in chunks to keep UI responsive
            results = []
            async for result in self.crawler.crawl(self.url):
                if self._should_stop:
                    break
                    
                results.append(result)
                self.status.emit(f"Crawled {len(results)} pages...")
                self.progress.emit(min(90, int(10 + 80 * len(results) / max(1, self.config.max_pages))))
                
                # Let the event loop process UI events
                await asyncio.sleep(0)
            
            if self._should_stop:
                self.status.emit("Crawling stopped")
                self.progress.emit(0)
            else:
                self.status.emit("Crawling completed")
                self.progress.emit(100)
            
            self.finished.emit(results)
            
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    """Main window of the application."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KnowledgeHarvester")
        self.setMinimumSize(800, 600)
        
        # Initialize components
        self.crawler_config = CrawlerConfig()
        self.storage = LocalStorage(StorageConfig(
            base_path=Path.home() / "Documents" / "KnowledgeHarvester" / "data"
        ))
        
        self.init_ui()
        
        # Initialize filters and formatters
        self.pruning_filter = PruningContentFilter()
        self.bm25_filter = BM25ContentFilter()
        self.filter_pipeline = FilterPipeline([
            self.pruning_filter,
            self.bm25_filter
        ])
        
        self.markdown_formatter = MarkdownFormatter()
        self.json_formatter = JsonFormatter()
        
        # Initialize worker
        self.worker = None
        self.thread = None
    
    def init_ui(self):
        """Initialize the user interface."""
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # URL input area
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL to crawl...")
        url_layout.addWidget(self.url_input)
        
        self.crawl_button = QPushButton("Crawl")
        self.crawl_button.clicked.connect(self.start_crawl)
        url_layout.addWidget(self.crawl_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_crawl)
        self.stop_button.setEnabled(False)
        url_layout.addWidget(self.stop_button)
        
        layout.addLayout(url_layout)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Output Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Markdown", "JSON"])
        format_layout.addWidget(self.format_combo)
        
        # Add settings button
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.show_settings)
        format_layout.addWidget(self.settings_button)
        
        layout.addLayout(format_layout)
        
        # Progress area
        progress_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar, stretch=1)
        
        self.status_label = QLabel()
        progress_layout.addWidget(self.status_label)
        
        layout.addLayout(progress_layout)
        
        # Results area
        results_layout = QHBoxLayout()
        
        # Pages list
        pages_group = QGroupBox("Crawled Pages")
        pages_layout = QVBoxLayout()
        
        # Add pages list toolbar
        pages_toolbar = QHBoxLayout()
        
        self.add_page_button = QPushButton("+")
        self.add_page_button.setToolTip("Add new page")
        self.add_page_button.clicked.connect(self.add_new_page)
        pages_toolbar.addWidget(self.add_page_button)
        
        self.remove_page_button = QPushButton("-")
        self.remove_page_button.setToolTip("Remove selected pages")
        self.remove_page_button.clicked.connect(self.remove_selected_pages)
        pages_toolbar.addWidget(self.remove_page_button)
        
        self.move_up_button = QPushButton("↑")
        self.move_up_button.setToolTip("Move pages up")
        self.move_up_button.clicked.connect(lambda: self.move_pages(-1))
        pages_toolbar.addWidget(self.move_up_button)
        
        self.move_down_button = QPushButton("↓")
        self.move_down_button.setToolTip("Move pages down")
        self.move_down_button.clicked.connect(lambda: self.move_pages(1))
        pages_toolbar.addWidget(self.move_down_button)
        
        pages_layout.addLayout(pages_toolbar)
        
        self.pages_list = QListWidget()
        self.pages_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.pages_list.itemSelectionChanged.connect(self.on_page_selection_changed)
        self.pages_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pages_list.customContextMenuRequested.connect(self.show_pages_context_menu)
        pages_layout.addWidget(self.pages_list)
        
        # Page info
        self.page_info = QLabel("Total pages: 0")
        pages_layout.addWidget(self.page_info)
        
        pages_group.setLayout(pages_layout)
        pages_group.setMaximumWidth(300)
        results_layout.addWidget(pages_group)
        
        # Preview area
        preview_group = QGroupBox("Content Preview")
        preview_layout = QVBoxLayout()
        
        # Preview toolbar
        preview_toolbar = QHBoxLayout()
        
        self.edit_mode_button = QPushButton("Edit Mode")
        self.edit_mode_button.setCheckable(True)
        self.edit_mode_button.clicked.connect(self.toggle_edit_mode)
        preview_toolbar.addWidget(self.edit_mode_button)
        
        preview_layout.addLayout(preview_toolbar)
        
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.textChanged.connect(self.on_preview_changed)
        preview_layout.addWidget(self.preview)
        
        preview_group.setLayout(preview_layout)
        results_layout.addWidget(preview_group)
        
        layout.addLayout(results_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.save_all_button = QPushButton("Save All")
        self.save_all_button.clicked.connect(self.save_all_content)
        self.save_all_button.setEnabled(False)
        button_layout.addWidget(self.save_all_button)
        
        self.save_selected_button = QPushButton("Save Selected")
        self.save_selected_button.clicked.connect(self.save_selected_content)
        self.save_selected_button.setEnabled(False)
        button_layout.addWidget(self.save_selected_button)
        
        self.save_merged_button = QPushButton("Save Merged")
        self.save_merged_button.clicked.connect(self.save_merged_content)
        self.save_merged_button.setEnabled(False)
        button_layout.addWidget(self.save_merged_button)
        
        layout.addLayout(button_layout)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def show_settings(self):
        """Show settings dialog."""
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.crawler_config, self.storage.config, self)
        if dialog.exec():
            # Settings were saved, update storage instance with new config
            self.storage = LocalStorage(self.storage.config)
    
    def start_crawl(self):
        """Start crawling the specified URL."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(
                self,
                "Error",
                "Please enter a URL to crawl."
            )
            return
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting...")
        
        # Create and start worker thread
        self.thread = QThread()
        self.worker = CrawlerWorker(url, self.crawler_config)
        self.worker.moveToThread(self.thread)
        
        # Connect signals
        self.thread.started.connect(lambda: asyncio.run(self.worker.run()))
        self.worker.finished.connect(self.handle_crawl_result)
        self.worker.error.connect(self.handle_crawl_error)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        
        # Update UI
        self.crawl_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.statusBar().showMessage("Crawling...")
        
        # Start crawling
        self.thread.start()
    
    def stop_crawl(self):
        """Stop the current crawl operation."""
        if self.worker:
            self.worker.stop()
            self.stop_button.setEnabled(False)
            self.statusBar().showMessage("Stopping crawler...")
    
    def handle_crawl_result(self, results: List[CrawlResult]):
        """Handle successful crawl results."""
        self.crawl_results = []  # Store all results
        self.pages_list.clear()
        
        for result in results:
            # Apply filters
            filtered_content = self.filter_pipeline.process(result.content)
            
            # Format content
            formatter = (
                self.markdown_formatter 
                if self.format_combo.currentText() == "Markdown"
                else self.json_formatter
            )
            formatted = formatter.format(filtered_content, result.metadata)
            
            # Store formatted result
            self.crawl_results.append((result, formatted))
            
            # Add to list widget with unique ID
            item = QListWidgetItem(result.url)
            item.setData(Qt.ItemDataRole.UserRole, str(uuid.uuid4()))
            item.setToolTip(f"Crawled at: {result.crawl_time}\nChild URLs: {len(result.child_urls)}")
            self.pages_list.addItem(item)
        
        # Update UI
        self.page_info.setText(f"Total pages: {len(self.crawl_results)}")
        self.save_all_button.setEnabled(bool(self.crawl_results))
        self.save_merged_button.setEnabled(bool(self.crawl_results))
        
        # Select first item if available
        if self.pages_list.count() > 0:
            self.pages_list.setCurrentRow(0)
        
        # Cleanup
        self.cleanup_worker()
        self.statusBar().showMessage(f"Crawl completed - {len(self.crawl_results)} pages")
    
    def cleanup_worker(self):
        """Clean up worker thread."""
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        self.worker = None
        self.thread = None
        self.crawl_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.clear()
    
    def on_page_selection_changed(self):
        """Handle page selection changes."""
        selected_items = self.pages_list.selectedItems()
        
        # Update preview if single selection
        if len(selected_items) == 1:
            item = selected_items[0]
            index = self.pages_list.row(item)
            if 0 <= index < len(self.crawl_results):
                _, formatted = self.crawl_results[index]
                self.preview.setText(formatted.content)
        else:
            self.preview.clear()
        
        # Update buttons
        self.save_selected_button.setEnabled(bool(selected_items))
    
    def save_selected_content(self):
        """Save selected pages."""
        selected_items = self.pages_list.selectedItems()
        if not selected_items:
            return
        
        success_count = 0
        error_count = 0
        error_messages = []
        
        for item in selected_items:
            index = self.pages_list.row(item)
            if 0 <= index < len(self.crawl_results):
                result, formatted = self.crawl_results[index]
                try:
                    # Generate unique filename using UUID
                    filename = f"{str(uuid.uuid4())[:8]}_{result.url}"
                    saved_path = self.storage.save(formatted, filename)
                    if saved_path:
                        success_count += 1
                    else:
                        error_count += 1
                        error_messages.append(f"Failed to save {result.url}")
                except Exception as e:
                    error_count += 1
                    error_messages.append(f"Error saving {result.url}: {str(e)}")
        
        # Show summary
        message = f"Successfully saved {success_count} pages."
        if error_count > 0:
            message += f"\nFailed to save {error_count} pages:"
            message += "\n" + "\n".join(error_messages)
        
        if error_count > 0:
            QMessageBox.warning(self, "Save Results", message)
        else:
            QMessageBox.information(self, "Save Results", message)
        
        self.statusBar().showMessage(f"Saved {success_count} pages")
    
    def save_all_content(self):
        """Save all crawled pages."""
        if not self.crawl_results:
            return
        
        # Select all pages and use save_selected_content
        self.pages_list.selectAll()
        self.save_selected_content()
    
    def handle_crawl_error(self, error_msg: str):
        """Handle crawl error."""
        QMessageBox.critical(
            self,
            "Error",
            f"Failed to crawl URL: {error_msg}"
        )
        
        # Cleanup
        self.cleanup_worker()
        self.statusBar().showMessage("Crawl failed")
    
    def toggle_edit_mode(self):
        """Toggle edit mode for preview."""
        is_edit_mode = self.edit_mode_button.isChecked()
        self.preview.setReadOnly(not is_edit_mode)
        self.edit_mode_button.setText("Exit Edit Mode" if is_edit_mode else "Edit Mode")
    
    def on_preview_changed(self):
        """Handle preview content changes."""
        if not self.edit_mode_button.isChecked():
            return
        
        # Update stored content for selected page
        selected_items = self.pages_list.selectedItems()
        if len(selected_items) != 1:
            return
        
        index = self.pages_list.row(selected_items[0])
        if 0 <= index < len(self.crawl_results):
            result, formatted = self.crawl_results[index]
            formatted.content = self.preview.toPlainText()
    
    def add_new_page(self):
        """Add a new empty page."""
        url, ok = QInputDialog.getText(self, "Add Page", "Enter page URL:")
        if ok and url:
            # Create empty result
            result = CrawlResult(
                url=url,
                content="",
                metadata={},
                child_urls=set()
            )
            formatted = FormattedContent(
                content="",
                metadata={},
                format_type='markdown' if self.format_combo.currentText() == "Markdown" else 'json'
            )
            
            # Add to list with unique ID
            self.crawl_results.append((result, formatted))
            item = QListWidgetItem(url)
            item.setData(Qt.ItemDataRole.UserRole, str(uuid.uuid4()))
            self.pages_list.addItem(item)
            self.pages_list.setCurrentItem(item)
            
            # Update UI
            self.page_info.setText(f"Total pages: {len(self.crawl_results)}")
            self.save_all_button.setEnabled(True)
            self.save_merged_button.setEnabled(True)
    
    def remove_selected_pages(self):
        """Remove selected pages."""
        selected_items = self.pages_list.selectedItems()
        if not selected_items:
            return
        
        # Remove items in reverse order to maintain indices
        for item in reversed(selected_items):
            index = self.pages_list.row(item)
            self.pages_list.takeItem(index)
            self.crawl_results.pop(index)
        
        # Update UI
        self.page_info.setText(f"Total pages: {len(self.crawl_results)}")
        if not self.crawl_results:
            self.save_all_button.setEnabled(False)
            self.save_merged_button.setEnabled(False)
            self.preview.clear()
    
    def move_pages(self, direction: int):
        """Move selected pages up or down."""
        selected_items = self.pages_list.selectedItems()
        if not selected_items:
            return
        
        # Sort items by row number
        items_with_rows = [(self.pages_list.row(item), item) for item in selected_items]
        items_with_rows.sort(reverse=(direction > 0))
        
        for current_row, item in items_with_rows:
            new_row = current_row + direction
            if 0 <= new_row < self.pages_list.count():
                # Move in list widget
                self.pages_list.takeItem(current_row)
                self.pages_list.insertItem(new_row, item)
                item.setSelected(True)
                
                # Move in results list
                result = self.crawl_results.pop(current_row)
                self.crawl_results.insert(new_row, result)
    
    def show_pages_context_menu(self, position):
        """Show context menu for pages list."""
        selected_items = self.pages_list.selectedItems()
        if not selected_items:
            return
        
        menu = QMenu()
        
        if len(selected_items) == 1:
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self.rename_page(selected_items[0]))
        
        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(self.remove_selected_pages)
        
        menu.exec(self.pages_list.mapToGlobal(position))
    
    def rename_page(self, item: QListWidgetItem):
        """Rename a page."""
        new_name, ok = QInputDialog.getText(
            self, "Rename Page", 
            "Enter new name:",
            text=item.text()
        )
        
        if ok and new_name:
            index = self.pages_list.row(item)
            if 0 <= index < len(self.crawl_results):
                item.setText(new_name)
                result, formatted = self.crawl_results[index]
                result.url = new_name
    
    def save_merged_content(self):
        """Save all pages as a single merged file."""
        if not self.crawl_results:
            return
        
        # Get save path
        file_type = "Markdown (*.md)" if self.format_combo.currentText() == "Markdown" else "JSON (*.json)"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Merged Content",
            str(self.storage.config.base_path),
            file_type
        )
        
        if not path:
            return
            
        try:
            merged_content = []
            
            if self.format_combo.currentText() == "Markdown":
                # Merge Markdown content
                for result, formatted in self.crawl_results:
                    merged_content.append(f"# {result.url}\n\n{formatted.content}\n\n---\n\n")
                final_content = "".join(merged_content)
            else:
                # Merge JSON content
                merged_data = {
                    "pages": [
                        {
                            "url": result.url,
                            "content": formatted.content,
                            "metadata": formatted.metadata
                        }
                        for result, formatted in self.crawl_results
                    ]
                }
                final_content = json.dumps(merged_data, indent=2, ensure_ascii=False)
            
            # Save merged content
            with open(path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            self.statusBar().showMessage(f"Saved merged content to: {path}")
            QMessageBox.information(
                self,
                "Success",
                f"Merged content saved to:\n{path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save merged content: {str(e)}"
            )

def main():
    """Run the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
