"""
Widget for managing Soil Stratigraphy, including defining multiple soil layers.
PRD Ref: Task 6.2 (Soil Stratigraphy & Properties Input Section)
Specifically Task 6.2.1 (UI for Managing Soil Layers)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, QAbstractItemView,
    QHeaderView, QLabel, QGroupBox
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Signal, Slot, Qt, QModelIndex
from typing import Optional, List

# from ...backend.models import SoilLayer, MaterialProperties # For data interaction later

class SoilStratigraphyWidget(QWidget):
    """
    A widget for users to define and manage soil stratigraphy (multiple layers).
    """
    data_changed = Signal()

    # Define column indices for clarity
    COL_NAME = 0
    COL_THICKNESS = 1
    COL_MATERIAL_MODEL = 2
    # Add more columns as needed (e.g., Unit Weight, Cohesion, Friction Angle directly, or a "Details" button)
    COLUMN_COUNT = 3


    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.main_layout = QVBoxLayout(self)
        # self.main_layout.setContentsMargins(0,0,0,0) # Use parent's margins

        group_box = QGroupBox("Soil Stratigraphy")
        self.main_layout.addWidget(group_box)

        group_layout = QVBoxLayout(group_box)

        # --- Table View for Soil Layers (Task 6.2.1 - Part 1) ---
        self.table_view = QTableView()
        self.table_model = QStandardItemModel(0, self.COLUMN_COUNT) # Rows, Columns
        self.table_view.setModel(self.table_model)
        self._setup_table_headers()

        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # self.table_view.setAlternatingRowColors(True) # Optional styling

        # Connect model's itemChanged signal to emit data_changed
        self.table_model.itemChanged.connect(self.on_table_item_changed)

        group_layout.addWidget(self.table_view)

        # --- Add/Remove Layer Buttons (Task 6.2.1 - Part 2) ---
        buttons_layout = QHBoxLayout()
        self.add_layer_button = QPushButton("Add Layer")
        self.add_layer_button.clicked.connect(self.on_add_layer)
        buttons_layout.addWidget(self.add_layer_button)

        self.remove_layer_button = QPushButton("Remove Selected Layer")
        self.remove_layer_button.clicked.connect(self.on_remove_layer)
        buttons_layout.addWidget(self.remove_layer_button)

        buttons_layout.addStretch() # Push buttons to one side

        # TODO: Add Up/Down buttons for reordering layers later

        group_layout.addLayout(buttons_layout)

        print("SoilStratigraphyWidget initialized.")

    def _setup_table_headers(self):
        headers = ["Layer Name", "Thickness (m)", "Material Model"]
        for col, header in enumerate(headers):
            self.table_model.setHorizontalHeaderItem(col, QStandardItem(header))

    @Slot()
    def on_add_layer(self):
        print("SoilStratigraphyWidget: Add Layer clicked.")
        # Add a new row with default/placeholder values
        row_count = self.table_model.rowCount()

        name_item = QStandardItem(f"Layer {row_count + 1}")
        thickness_item = QStandardItem("1.0") # Default thickness
        material_item = QStandardItem("MohrCoulomb (Placeholder)") # Default material

        # Make items editable
        name_item.setEditable(True)
        thickness_item.setEditable(True)
        # material_item might be a dropdown later, or open a dialog. For now, text.
        material_item.setEditable(True)

        self.table_model.appendRow([name_item, thickness_item, material_item])
        self.data_changed.emit() # Signal that data has changed

    @Slot()
    def on_remove_layer(self):
        print("SoilStratigraphyWidget: Remove Layer clicked.")
        selected_indexes = self.table_view.selectionModel().selectedRows()
        if not selected_indexes:
            print("No layer selected to remove.")
            # Optionally show a QMessageBox to the user
            return

        # Remove rows in reverse order to avoid index shifting issues if multiple were selected (though single selection is set)
        for index in sorted(selected_indexes, key=QModelIndex.row, reverse=True):
            self.table_model.removeRow(index.row())

        self.data_changed.emit()

    @Slot(QStandardItem)
    def on_table_item_changed(self, item: QStandardItem):
        """Slot connected to QStandardItemModel.itemChanged signal."""
        print(f"SoilStratigraphyWidget: Item changed in table - row {item.row()}, col {item.column()}, text '{item.text()}'")
        self.data_changed.emit()


    # --- Data Interaction Stubs (Task 6.2.1 - Step 4 of plan) ---
    def load_data(self, soil_stratigraphy_data: Optional[List] = None) -> None: # List[SoilLayer] later
        """
        Populates the table with soil layer data.
        """
        self.table_model.removeRows(0, self.table_model.rowCount()) # Clear existing rows
        print(f"SoilStratigraphyWidget: Loading data - {soil_stratigraphy_data}")

        if soil_stratigraphy_data:
            for layer_data in soil_stratigraphy_data: # layer_data should be a SoilLayer object
                name = getattr(layer_data, 'name', f"Layer {self.table_model.rowCount() + 1}")
                thickness = str(getattr(layer_data, 'thickness', 1.0))

                material_name = "N/A"
                if hasattr(layer_data, 'material') and layer_data.material:
                    material_name = getattr(layer_data.material, 'model_name', "DefaultModel")

                name_item = QStandardItem(name)
                thickness_item = QStandardItem(thickness)
                material_item = QStandardItem(material_name)

                name_item.setEditable(True)
                thickness_item.setEditable(True)
                material_item.setEditable(True) # Or use a delegate for a combobox later

                self.table_model.appendRow([name_item, thickness_item, material_item])
            print(f"SoilStratigraphyWidget: Loaded {len(soil_stratigraphy_data)} layers into table.")
        else:
            # Optionally add a default layer if list is empty/None
            # self.on_add_layer()
            print("SoilStratigraphyWidget: No soil stratigraphy data provided or data is empty.")

    def gather_data(self) -> List: # List[SoilLayer] later
        """
        Collects data from the table and returns a list of SoilLayer data objects.
        For now, returns a list of dictionaries as a placeholder.
        """
        # from ...backend.models import SoilLayer, MaterialProperties # Import when ready

        gathered_layers = []
        for row in range(self.table_model.rowCount()):
            try:
                name = self.table_model.item(row, self.COL_NAME).text() if self.table_model.item(row, self.COL_NAME) else f"Layer {row+1}"
                thickness_str = self.table_model.item(row, self.COL_THICKNESS).text() if self.table_model.item(row, self.COL_THICKNESS) else "0.0"
                thickness = float(thickness_str) # TODO: Add validation here

                material_model_str = self.table_model.item(row, self.COL_MATERIAL_MODEL).text() if self.table_model.item(row, self.COL_MATERIAL_MODEL) else "MohrCoulomb"

                # Placeholder: create simple dict. Later, create actual SoilLayer and MaterialProperties objects.
                # material_obj = MaterialProperties(model_name=material_model_str) # Example
                # layer_obj = SoilLayer(name=name, thickness=thickness, material=material_obj)
                # gathered_layers.append(layer_obj)

                layer_dict = {
                    "name": name,
                    "thickness": thickness,
                    "material": {"model_name": material_model_str} # Simplified material
                }
                gathered_layers.append(layer_dict)
            except ValueError as e:
                print(f"Error gathering data for row {row}: {e}. Skipping this layer.")
                # Optionally, raise an error or inform the user via UI.
            except Exception as e: # Catch any other unexpected errors for a row
                print(f"Unexpected error gathering data for row {row}: {e}. Skipping this layer.")


        print(f"SoilStratigraphyWidget: Gathered data for {len(gathered_layers)} layers.")
        return gathered_layers


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication
    # For testing with mock backend models:
    # class MockMaterialProperties:
    #     def __init__(self, model_name="TestModel"):
    #         self.model_name = model_name
    # class MockSoilLayer:
    #     def __init__(self, name="TestLayer", thickness=1.0, material=None):
    #         self.name = name
    #         self.thickness = thickness
    #         self.material = material if material else MockMaterialProperties()

    app = QApplication(sys.argv)
    widget = SoilStratigraphyWidget()

    # Test load_data with mock objects
    # test_layers_data = [
    #     MockSoilLayer(name="Clay", thickness=2.5, material=MockMaterialProperties("MohrCoulomb")),
    #     MockSoilLayer(name="Sand", thickness=3.0, material=MockMaterialProperties("HardeningSoil"))
    # ]
    # print("\nTesting load_data:")
    # widget.load_data(test_layers_data)

    # Simulate adding a few layers for testing gather_data if load_data isn't fully tested
    widget.on_add_layer() # Adds "Layer 1"
    widget.on_add_layer() # Adds "Layer 2"
    if widget.table_model.rowCount() > 0:
        widget.table_model.item(0, widget.COL_NAME).setText("Top Clay")
        widget.table_model.item(0, widget.COL_THICKNESS).setText("3.5")
        widget.table_model.item(0, widget.COL_MATERIAL_MODEL).setText("MC_Clay_Custom")


    print("\nTesting gather_data:")
    gathered = widget.gather_data()
    print(f"Gathered layer data from UI: {gathered}")

    widget.setWindowTitle("Soil Stratigraphy Widget Test")
    widget.resize(600, 400)
    widget.show()

    sys.exit(app.exec())
