"""
Matplotlib Widget for PySide6 Integration.
Provides a QWidget that can embed a Matplotlib figure.
"""
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt # For theme context

logger = logging.getLogger(__name__)

class MplWidget(QWidget):
    """
    A QWidget that embeds a Matplotlib Figure.
    """
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        super().__init__(parent)

        # Use a context manager for potentially better theme integration if available
        # and to ensure styles are applied correctly.
        try:
            with plt.style.context('seaborn-v0_8-darkgrid'): # Example style
                self.figure = Figure(figsize=(width, height), dpi=dpi)
                self.canvas = FigureCanvas(self.figure)
        except Exception: # Fallback if style context fails or style not found
            logger.warning("Failed to apply 'seaborn-v0_8-darkgrid' style. Using default Matplotlib style.")
            self.figure = Figure(figsize=(width, height), dpi=dpi)
            self.canvas = FigureCanvas(self.figure)

        self.axes = self.figure.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        logger.debug("MplWidget initialized with a new Figure and Canvas.")

    def plot_data(self, x_data, y_data, title="Plot", x_label="X-axis", y_label="Y-axis", clear_previous=True):
        """
        Plots given x and y data on the canvas.
        Args:
            x_data (list or array-like): Data for the x-axis.
            y_data (list or array-like): Data for the y-axis.
            title (str): Title of the plot.
            x_label (str): Label for the x-axis.
            y_label (str): Label for the y-axis.
            clear_previous (bool): Whether to clear previous plots on the axes.
        """
        if not x_data or not y_data or len(x_data) != len(y_data):
            logger.warning("Invalid or mismatched data provided for plotting. No plot generated.")
            self.axes.clear() # Clear even if data is bad, to show an empty plot
            self.axes.set_title(title)
            self.axes.set_xlabel(x_label)
            self.axes.set_ylabel(y_label)
            self.canvas.draw()
            return

        if clear_previous:
            self.axes.clear()

        self.axes.plot(x_data, y_data)
        self.axes.set_title(title)
        self.axes.set_xlabel(x_label)
        self.axes.set_ylabel(y_label)
        self.axes.grid(True) # Ensure grid is on

        self.figure.tight_layout() # Adjust layout to prevent labels from being cut off
        self.canvas.draw()
        logger.info(f"Plotted data for '{title}'. X points: {len(x_data)}, Y points: {len(y_data)}")

    def clear_plot(self):
        """Clears the plot."""
        self.axes.clear()
        self.canvas.draw()
        logger.info("Plot cleared.")

if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    import sys

    logging.basicConfig(level=logging.DEBUG)
    app = QApplication(sys.argv)
    main_widget = QWidget()
    layout = QVBoxLayout(main_widget)

    mpl_chart = MplWidget(main_widget, width=6, height=5, dpi=100)
    layout.addWidget(mpl_chart)

    # Example data
    x_sample = [i * 0.1 for i in range(100)]
    y_sample = [val**2 for val in x_sample] # x_sample_data

    mpl_chart.plot_data(x_sample, y_sample, title="Sample Parabola", x_label="X Value", y_label="Y Value (X^2)")

    main_widget.setWindowTitle("Matplotlib Widget Test")
    main_widget.resize(800, 600)
    main_widget.show()
    sys.exit(app.exec())
