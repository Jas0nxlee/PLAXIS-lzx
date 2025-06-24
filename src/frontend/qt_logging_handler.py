import logging
from PySide6.QtCore import QObject, Signal

class QtLogSignal(QObject):
    """
    Defines a signal that carries log messages.
    The signal payload is the formatted log string.
    """
    log_received = Signal(str)

class QtLoggingHandler(logging.Handler):
    """
    A custom logging handler that emits Qt signals for log messages.
    This allows log messages to be displayed in a Qt widget (e.g., QTextEdit).
    """
    def __init__(self, parent_qobject=None):
        super().__init__()
        self.emitter = QtLogSignal(parent_qobject) # Pass parent if needed for lifetime management

    def emit(self, record: logging.LogRecord):
        """
        Formats the log record and emits it via a Qt signal.
        """
        try:
            msg = self.format(record)
            self.emitter.log_received.emit(msg)
        except Exception:
            self.handleError(record)

    def connect(self, slot_function):
        """
        Convenience method to connect a slot to the log_received signal.
        """
        self.emitter.log_received.connect(slot_function)

    def disconnect(self, slot_function):
        """
        Convenience method to disconnect a slot from the log_received signal.
        """
        try:
            self.emitter.log_received.disconnect(slot_function)
        except (TypeError, RuntimeError) as e: # RuntimeError if signal not connected
            # Log this minor issue or handle as needed
            logging.getLogger(__name__).debug(f"Error disconnecting logger: {e}")


if __name__ == '__main__':
    # Example Usage (requires a QApplication to be running for signals/slots)
    from PySide6.QtWidgets import QApplication, QTextEdit, QVBoxLayout, QWidget
    import sys

    # Basic Qt Application setup
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout(window)
    log_display_widget = QTextEdit()
    log_display_widget.setReadOnly(True)
    layout.addWidget(log_display_widget)
    window.resize(600, 400)
    window.setWindowTitle("Qt Logging Handler Test")
    window.show()

    # Setup basic logging
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create and add our Qt handler
    qt_handler = QtLoggingHandler()
    qt_handler.setFormatter(formatter)
    qt_handler.connect(log_display_widget.append) # Connect to QTextEdit's append slot
    root_logger.addHandler(qt_handler)

    # Test logging
    logging.debug("This is a debug message from the root logger.")
    logging.info("This is an info message from the root logger.")

    test_logger = logging.getLogger("MyModuleTest")
    test_logger.warning("This is a warning from MyModuleTest.")
    test_logger.error("This is an error from MyModuleTest.")

    # Example of disconnecting (optional)
    # qt_handler.disconnect(log_display_widget.append)
    # logging.info("This message should not appear in the QTextEdit if disconnected.")

    sys.exit(app.exec())
