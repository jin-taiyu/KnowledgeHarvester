import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from .gui.main_window import MainWindow

def setup_logging():
    """Configure logging for the application."""
    log_dir = Path.home() / "Documents" / "KnowledgeHarvester" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "knowledge_harvester.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Application entry point."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting KnowledgeHarvester")
    
    try:
        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("KnowledgeHarvester")
        app.setApplicationVersion("0.1.0")
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Start event loop
        sys.exit(app.exec())
        
    except Exception as e:
        logger.exception("Unhandled exception occurred")
        sys.exit(1)

if __name__ == '__main__':
    main()
