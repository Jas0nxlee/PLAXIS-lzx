"""
Widget for managing Soil Stratigraphy, including defining multiple soil layers.
PRD Ref: Task 6.2 (Soil Stratigraphy & Properties Input Section)
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, QAbstractItemView,
    QHeaderView, QLabel, QGroupBox, QDoubleSpinBox, QFormLayout, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QAbstractTableModel, QModelIndex, QObject
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from typing import List, Dict, Any, Optional

from ...backend.models import SoilLayer, MaterialProperties # For data structure
from .delegates import SoilModelDelegate, MaterialParametersDelegate
from .soil_stratigraphy_schematic_widget import SoilStratigraphySchematicWidget # Import schematic

logger = logging.getLogger(__name__)

# Placeholder for actual data model from backend
class SoilLayerData: # This class is used internally by the TableModel
    def __init__(self, name: str, thickness: float, material_model: str,
                 parameters: Optional[Dict[str, Any]] = None,
                 original_material: Optional[MaterialProperties] = None):
        self.name = name
        self.thickness = thickness
        self.material_model = material_model
        self.parameters = parameters if parameters is not None else {}
        self.original_material = original_material

class SoilStratigraphyTableModel(QAbstractTableModel):
    # ... (TableModel implementation remains largely the same) ...
    def __init__(self, layers: Optional[List[SoilLayerData]] = None, parent: Optional[QObject] = None): # type: ignore
        super().__init__(parent)
        self._headers = ["Layer Name", "Thickness (m)", "Material Model", "Parameters", "Material ID (Backend)"]
        self._layers: List[SoilLayerData] = layers if layers is not None else []
        self._available_soil_models = ["Mohr-Coulomb", "HardeningSoil", "SoftSoil", "Custom"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._layers)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._layers)):
            return None

        layer = self._layers[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0: return layer.name
            elif column == 1: return f"{layer.thickness:.2f}"
            elif column == 2: return layer.material_model
            elif column == 3:
                return f"Edit {layer.material_model}..." if layer.material_model else "N/A"
            elif column == 4:
                return layer.original_material.Identification if layer.original_material and layer.original_material.Identification else "N/A"

        elif role == Qt.ItemDataRole.EditRole:
            if column == 0: return layer.name
            elif column == 1: return layer.thickness
            elif column == 2: return layer.material_model
            elif column == 3:
                return layer

        elif role == Qt.ItemDataRole.UserRole:
            if column == 2:
                return self._available_soil_models
            if column == 3:
                return layer
        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row = index.row()
        col = index.column()
        layer = self._layers[row]
        changed = False

        if col == 0:
            if layer.name != value:
                layer.name = str(value)
                changed = True
        elif col == 1:
            try:
                val = float(value)
                if layer.thickness != val and val > 0 :
                    layer.thickness = val
                    changed = True
            except ValueError: pass
        elif col == 2:
            if layer.material_model != value:
                layer.material_model = str(value)
                logger.info(f"Layer {row+1} material model changed to: {value}. Parameters might need update.")
                if layer.original_material:
                    layer.original_material.model_name = str(value)
                else:
                    layer.original_material = MaterialProperties(model_name=str(value))
                changed = True
                self.dataChanged.emit(self.index(row, 3), self.index(row, 3), [Qt.ItemDataRole.DisplayRole])
        if changed:
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        if index.column() in [0, 1, 2]:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def add_layer(self, name: str = "New Layer", thickness: float = 1.0,
                  material_model: str = "Mohr-Coulomb",
                  material_properties: Optional[MaterialProperties] = None):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        if material_properties is None:
            material_properties = MaterialProperties(model_name=material_model, Identification=f"{name}_Mat_{self.rowCount()}")

        new_layer = SoilLayerData(name, thickness, material_model, original_material=material_properties)
        self._layers.append(new_layer)
        self.endInsertRows()
        return True

    def remove_layer(self, row: int):
        if 0 <= row < self.rowCount():
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._layers[row]
            self.endRemoveRows()
            return True
        return False

    def get_layer_data(self) -> List[SoilLayerData]:
        return self._layers

    def load_layers_data(self, layers_data: List[SoilLayer]):
        self.beginResetModel()
        self._layers = []
        for backend_layer in layers_data:
            frontend_layer = SoilLayerData(
                name=backend_layer.name,
                thickness=backend_layer.thickness or 1.0,
                material_model=backend_layer.material.model_name or "Mohr-Coulomb",
                original_material=backend_layer.material
            )
            self._layers.append(frontend_layer)
        self.endResetModel()


class SoilStratigraphyWidget(QWidget):
    data_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)

        # GroupBox for better visual structure
        strat_group_box = QGroupBox("Soil Stratigraphy")
        group_layout = QVBoxLayout(strat_group_box)

        self.layers_tableview = QTableView()
        self.table_model = SoilStratigraphyTableModel()
        self.layers_tableview.setModel(self.table_model)
        self.layers_tableview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch) # type: ignore
        self.layers_tableview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # type: ignore

        self.layers_tableview.setItemDelegateForColumn(2, SoilModelDelegate(self.table_model._available_soil_models, self))
        self.layers_tableview.setItemDelegateForColumn(3, MaterialParametersDelegate(self))

        group_layout.addWidget(QLabel("Soil Layers:"))
        group_layout.addWidget(self.layers_tableview)

        layer_buttons_layout = QHBoxLayout()
        self.add_layer_button = QPushButton("Add Layer")
        self.remove_layer_button = QPushButton("Remove Selected Layer")
        layer_buttons_layout.addWidget(self.add_layer_button)
        layer_buttons_layout.addWidget(self.remove_layer_button)
        layer_buttons_layout.addStretch()
        group_layout.addLayout(layer_buttons_layout)

        water_table_layout = QFormLayout()
        self.water_table_spinbox = QDoubleSpinBox()
        self.water_table_spinbox.setSuffix(" m")
        self.water_table_spinbox.setDecimals(2)
        self.water_table_spinbox.setRange(-1000.0, 1000.0)
        self.water_table_spinbox.setValue(2.0)
        water_table_layout.addRow(QLabel("Water Table Depth (m below surface):"), self.water_table_spinbox)
        group_layout.addLayout(water_table_layout)

        self.main_layout.addWidget(strat_group_box)

        # Add Schematic Widget
        self.schematic_widget = SoilStratigraphySchematicWidget(self)
        self.schematic_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Add the schematic inside its own groupbox for better layout management
        schematic_group_box = QGroupBox("Stratigraphy Visual")
        schematic_group_layout = QVBoxLayout(schematic_group_box)
        schematic_group_layout.addWidget(self.schematic_widget)
        self.main_layout.addWidget(schematic_group_box, 1) # Add with stretch factor for schematic

        self.add_layer_button.clicked.connect(self.on_add_layer)
        self.remove_layer_button.clicked.connect(self.on_remove_layer)
        self.table_model.dataChanged.connect(self._emit_data_changed_and_update_schematic)
        self.table_model.rowsInserted.connect(self._emit_data_changed_and_update_schematic)
        self.table_model.rowsRemoved.connect(self._emit_data_changed_and_update_schematic)
        self.water_table_spinbox.valueChanged.connect(self._emit_data_changed_and_update_schematic)

        delete_shortcut = QShortcut(QKeySequence.StandardKey.Delete, self.layers_tableview)
        delete_shortcut.activated.connect(self.on_remove_layer)

        self._update_schematic_display() # Initial draw
        logger.info("SoilStratigraphyWidget initialized with schematic.")

    @Slot()
    def _emit_data_changed_and_update_schematic(self):
        self._update_schematic_display()
        self.data_changed.emit()
        logger.debug("SoilStratigraphyWidget: Data changed signal emitted and schematic updated.")

    def _update_schematic_display(self):
        """Updates the soil stratigraphy schematic widget."""
        if not hasattr(self, 'schematic_widget') or self.schematic_widget is None:
            return

        layers_for_schematic = []
        for layer_data in self.table_model.get_layer_data():
            layers_for_schematic.append({
                "name": layer_data.name,
                "thickness": layer_data.thickness,
                "material_display_name": layer_data.material_model,
                "original_material_id": layer_data.original_material.Identification if layer_data.original_material else None
            })

        current_wt_depth = self.water_table_spinbox.value()
        self.schematic_widget.update_data(layers_for_schematic, current_wt_depth)
        logger.debug(f"Soil schematic display updated with {len(layers_for_schematic)} layers and WT depth {current_wt_depth}")


    @Slot()
    def on_add_layer(self):
        default_mat_props = MaterialProperties(model_name="Mohr-Coulomb", Identification=f"NewLayerMat_{self.table_model.rowCount()+1}")
        self.table_model.add_layer(material_properties=default_mat_props)

    @Slot()
    def on_remove_layer(self):
        selected_indexes = self.layers_tableview.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.information(self, "Remove Layer", "Please select a layer to remove.") # type: ignore
            return

        for index in sorted(selected_indexes, key=lambda idx: idx.row(), reverse=True):
            self.table_model.remove_layer(index.row())

    def load_data(self, soil_profile_data: Optional[Any]):
        logger.info(f"SoilStratigraphyWidget: Loading data - {type(soil_profile_data)}")

        self.table_model.blockSignals(True)
        self.water_table_spinbox.blockSignals(True)

        if soil_profile_data and hasattr(soil_profile_data, 'layers') and hasattr(soil_profile_data, 'water_table_depth'):
            self.table_model.load_layers_data(soil_profile_data.layers)
            self.water_table_spinbox.setValue(soil_profile_data.water_table_depth if soil_profile_data.water_table_depth is not None else 2.0)
            logger.debug("SoilStratigraphyWidget: Data loaded into table and water table spinbox.")
        else:
            self.table_model.load_layers_data([])
            self.water_table_spinbox.setValue(2.0)
            logger.debug("SoilStratigraphyWidget: No valid data provided or data structure mismatch, reset to defaults.")

        self.table_model.blockSignals(False)
        self.water_table_spinbox.blockSignals(False)

        self._emit_data_changed_and_update_schematic()

    def gather_data(self) -> Dict[str, Any]:
        frontend_layers_data = self.table_model.get_layer_data()
        backend_soil_layers: List[SoilLayer] = []
        for fled in frontend_layers_data:
            mat_props: MaterialProperties
            if isinstance(fled.original_material, MaterialProperties):
                mat_props = fled.original_material
                mat_props.model_name = fled.material_model
            else:
                mat_props = MaterialProperties(model_name=fled.material_model, Identification=f"{fled.name}_MatGathered")

            backend_layer = SoilLayer(
                name=fled.name,
                thickness=fled.thickness,
                material=mat_props
            )
            backend_soil_layers.append(backend_layer)

        gathered_data = {
            "layers": backend_soil_layers,
            "water_table_depth": self.water_table_spinbox.value(),
        }
        logger.debug(f"SoilStratigraphyWidget: Gathered data - {len(backend_soil_layers)} layers, WT: {gathered_data['water_table_depth']}")
        return gathered_data


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QMessageBox

    class MockMaterialProperties: # Simplified for testing
        def __init__(self, model_name="Mohr-Coulomb", Identification=None, **kwargs):
            self.model_name = model_name
            self.Identification = Identification if Identification else f"{model_name}_Mat"
            # Store other_params for realism, though not fully used in this mock
            self.other_params = kwargs
            for k,v in kwargs.items(): setattr(self, k, v)
        def __str__(self): return f"MockMat(ID: {self.Identification}, Model: {self.model_name})"

    class MockSoilLayer: # Simplified for testing
        def __init__(self, name, thickness, material: MockMaterialProperties):
            self.name = name; self.thickness = thickness; self.material = material
        def __str__(self): return f"MockLayer(N: {self.name}, T:{self.thickness}, M:{self.material})"

    class MockSoilProfileData:
        def __init__(self, layers: List[MockSoilLayer], water_table_depth: Optional[float]):
            self.layers = layers; self.water_table_depth = water_table_depth


    app = QApplication(sys.argv)
    widget = SoilStratigraphyWidget()

    mat1 = MockMaterialProperties(model_name="Mohr-Coulomb", Identification="MC_Clay", Eref=5000, cRef=10)
    layer_a = MockSoilLayer(name="Top Clay", thickness=2.5, material=mat1)
    mat2 = MockMaterialProperties(model_name="HardeningSoil", Identification="HS_Sand", E50ref=30000, m=0.5)
    layer_b = MockSoilLayer(name="Dense Sand", thickness=7.0, material=mat2)

    test_profile_data = MockSoilProfileData(layers=[layer_a, layer_b], water_table_depth=1.5)

    logger.info("\n--- Testing load_data with MockSoilProfileData ---")
    widget.load_data(test_profile_data)

    gathered_after_load = widget.gather_data()
    logger.info(f"Data gathered after load: {gathered_after_load}")
    assert len(gathered_after_load["layers"]) == 2
    assert gathered_after_load["layers"][0].name == "Top Clay"
    assert gathered_after_load["layers"][0].material.Identification == "MC_Clay"
    assert gathered_after_load["water_table_depth"] == 1.5

    logger.info("\n--- Testing Add Layer Button ---")
    widget.add_layer_button.click()
    gathered_after_add = widget.gather_data()
    logger.info(f"Data gathered after add: {gathered_after_add}")
    assert len(gathered_after_add["layers"]) == 3
    assert gathered_after_add["layers"][2].name == "New Layer"

    widget.setWindowTitle("Soil Stratigraphy Widget Test with Schematic")
    widget.resize(700, 550) # Wider to accommodate schematic and text
    widget.show()

    sys.exit(app.exec())
