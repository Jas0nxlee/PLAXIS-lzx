"""
Custom delegates for QTableView in the PLAXIS Spudcan Automation Tool.
PRD Ref: Task 6.2.3, 6.2.4 (related to material parameter editing)
"""
import logging
from PySide6.QtWidgets import QStyledItemDelegate, QComboBox, QWidget, QPushButton, QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PySide6.QtCore import Qt, QModelIndex, Slot
from PySide6.QtGui import QPainter # For custom painting if needed later

logger = logging.getLogger(__name__)

class SoilModelDelegate(QStyledItemDelegate):
    """
    A delegate for editing soil model types using a QComboBox.
    """
    def __init__(self, available_models: list[str], parent=None):
        super().__init__(parent)
        self.available_models = available_models if available_models else ["Mohr-Coulomb"] # Default if empty

    def createEditor(self, parent: QWidget, option: 'QStyleOptionViewItem', index: QModelIndex) -> QWidget: # type: ignore
        editor = QComboBox(parent)
        model_list = index.model().data(index, Qt.ItemDataRole.UserRole) # Get list from model
        if model_list and isinstance(model_list, list):
            editor.addItems(model_list)
        else: # Fallback if model doesn't provide the list via UserRole as expected
            editor.addItems(self.available_models)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        if not isinstance(editor, QComboBox):
            return
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        editor.setCurrentText(str(value))

    def setModelData(self, editor: QWidget, model: 'QAbstractItemModel', index: QModelIndex) -> None: # type: ignore
        if not isinstance(editor, QComboBox):
            return
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor: QWidget, option: 'QStyleOptionViewItem', index: QModelIndex) -> None: # type: ignore
        editor.setGeometry(option.rect)


class MaterialParametersDelegate(QStyledItemDelegate):
    """
    A delegate for editing material parameters.
    This will likely open a dialog for complex parameter input.
    Placeholder for now. Task 6.2.4
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent: QWidget, option: 'QStyleOptionViewItem', index: QModelIndex) -> QWidget: # type: ignore
        # For now, we don't create an inline editor.
        # We'll handle the click event to open a dialog.
        # So, return a simple QPushButton that will trigger a dialog.
        # However, a more robust way is to handle the click/double-click in the view
        # and not make the cell itself directly editable in the traditional sense if it always opens a dialog.

        # Alternative: Open dialog on edit trigger (e.g., double-click)
        # This is a common pattern for complex data.
        # The editor itself is the dialog.

        # For this iteration, let's make it simple: clicking the cell will be handled by a custom slot in the view
        # or by overriding editorEvent. For now, let's assume the view handles the click.
        # If we were to make it a button that opens a dialog:
        # button = QPushButton("Edit...", parent)
        # button.clicked.connect(lambda: self.open_parameters_dialog(index.model().data(index, Qt.ItemDataRole.UserRole))) # UserRole has SoilLayerData
        # return button
        # However, QStyledItemDelegate expects the editor to be the primary input widget.
        # A button that opens a dialog is better handled by not making the cell itself "editable"
        # and using a custom click handler on the table view.

        # For task 6.2.3, this delegate is for the "Parameters" column which might just show "Edit..."
        # and the actual editing is done through a dialog.
        # The editor for "Parameters" column might not be directly invoked if a dialog is preferred.
        # Let's make it non-editable for now, and clicking it will be handled by the view/widget.
        # So, this createEditor might not be used if the cell is made read-only and click is handled.
        # If it IS made editable and this is called, we show a simple label.
        label = QLabel("Click to Edit (Not Implemented)", parent)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label


    def open_parameters_dialog(self, layer_data_item): # layer_data_item is SoilLayerData
        if not layer_data_item:
            logger.warning("MaterialParametersDelegate: No layer data provided to open_parameters_dialog.")
            return

        dialog = QDialog() # self.parent() if we pass parent to delegate
        dialog.setWindowTitle(f"Edit Parameters for {layer_data_item.material_model}")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Editing parameters for: {layer_data_item.name} ({layer_data_item.material_model})"))
        # Add parameter fields here based on layer_data_item.material_model
        # For now, a placeholder:
        layout.addWidget(QLabel("Parameter editing UI will be here."))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.exec()
        # If accepted, update the model data.
        if dialog.result() == QDialog.DialogCode.Accepted:
            new_params = dialog.get_parameters()
            # Update the original_material object directly.
            # This assumes layer_data_item.original_material is the actual MaterialProperties object from the model's list.
            for key, value in new_params.items():
                if hasattr(layer_data_item.original_material, key):
                    setattr(layer_data_item.original_material, key, value)
                else:
                    layer_data_item.original_material.other_params[key] = value

            # Notify the model that data for this specific item has changed.
            # We need the QModelIndex of the item whose parameters were edited.
            # This delegate instance doesn't inherently know its index when open_parameters_dialog is called from editorEvent.
            # This is a limitation. A better way is for the dialog to be created by createEditor,
            # or for the view to handle the dialog and then call model.setData().

            # For now, we assume the model needs to be refreshed for that row or the specific cell.
            # The editorEvent that calls this doesn't easily give us a way to emit commitData for the model.
            # The model itself should emit dataChanged for the "Parameters" cell display if it changes.
            # This part needs to be connected to the model's update mechanism.
            # A simple (but not ideal) way is to rely on the calling context to refresh.
            # A more direct way if this delegate was a persistent editor: self.commitData.emit(editor_widget_that_is_the_dialog)
            logger.info(f"Parameters updated for {layer_data_item.name}.")
            # We need to find the index for which this dialog was opened to tell the model to update.
            # This is tricky because editorEvent doesn't keep the delegate "open".
            # Let's assume the view will handle refreshing the display of this cell if needed,
            # or the model's setData for material_model change already refreshes the param display.

        logger.info(f"Material parameters dialog for {layer_data_item.name} was closed with result {dialog.result()}.")


    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        # This is called when an editor created by createEditor is shown.
        # Since our "editor" (the dialog) is created on the fly in editorEvent,
        # this method might not be directly used in the same way.
        pass

    def setModelData(self, editor: QWidget, model: 'QAbstractItemModel', index: QModelIndex) -> None: # type: ignore
        # This is called to commit data from an editor created by createEditor.
        # If the dialog is our editor, it would call this.
        # However, with editorEvent, the flow is different.
        # The dialog's accept() should ideally trigger model.setData().
        pass

    # We might need to override paint() if we want to make it look like a button or clickable text
    def paint(self, painter: QPainter, option: 'QStyleOptionViewItem', index: QModelIndex) -> None: # type: ignore
        super().paint(painter, option, index)


    # editorEvent is used to intercept clicks and open the dialog.
    def editorEvent(self, event, model, option, index):
        # Ensure we are handling the correct column (e.g., "Parameters" column, typically index 3)
        if index.column() == 3: # Make sure this column index is correct for "Parameters"
            if event.type() == event.MouseButtonDblClick or \
               (event.type() == event.KeyPress and event.key() in (Qt.Key_Enter, Qt.Key_Return)):
                # Open dialog on double-click or Enter/Return press
                layer_data_item = model.data(index, Qt.ItemDataRole.UserRole) # UserRole should give SoilLayerData
                if layer_data_item and hasattr(layer_data_item, 'original_material'):
                    # Create and open the dialog
                    dialog = ParameterEditDialog(layer_data_item.original_material, parent=option.widget) # option.widget is the view
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        new_params = dialog.get_parameters()
                        current_material = layer_data_item.original_material
                        changed = False
                        for key, value in new_params.items():
                            old_value = getattr(current_material, key, current_material.other_params.get(key))
                            if old_value != value:
                                changed = True
                            if hasattr(current_material, key):
                                setattr(current_material, key, value)
                            else:
                                current_material.other_params[key] = value

                        if changed:
                            # Important: Notify the model that data has changed for this index.
                            # This will make the view update (e.g., if display text for params changes).
                            model.setData(index, current_material, Qt.ItemDataRole.EditRole) # Or a custom role
                            logger.info(f"Parameters updated for {layer_data_item.name} via delegate.")
                    return True # Event handled
        return super().editorEvent(event, model, option, index)


# --- Helper Dialog for Parameter Editing ---
SOIL_MODEL_PARAMETERS = {
    "Mohr-Coulomb": [
        # (param_name, display_name, type, default_value)
        ("gammaUnsat", "γ_unsat (kN/m³)", float, 18.0),
        ("gammaSat", "γ_sat (kN/m³)", float, 20.0),
        ("eInit", "e_init", float, 0.8),
        ("Eref", "E'_ref (kN/m²)", float, 10000.0),
        ("nu", "ν' (Poisson's ratio)", float, 0.3),
        ("cRef", "c'_ref (kN/m²)", float, 5.0),
        ("phi", "φ' (friction angle °)", float, 30.0),
        ("psi", "ψ (dilatancy angle °)", float, 0.0),
    ],
    "HardeningSoil": [
        ("gammaUnsat", "γ_unsat (kN/m³)", float, 18.0),
        ("gammaSat", "γ_sat (kN/m³)", float, 20.0),
        ("eInit", "e_init", float, 0.7),
        ("E50ref", "E50_ref (kN/m²)", float, 30000.0),
        ("Eoedref", "Eoed_ref (kN/m²)", float, 30000.0),
        ("Eurref", "Eur_ref (kN/m²)", float, 90000.0),
        ("m", "m (power for stress-level dependency)", float, 0.5),
        ("nu", "ν'_ur (Poisson's ratio unload/reload)", float, 0.2),
        ("cRef", "c'_ref (kN/m²)", float, 1.0),
        ("phi", "φ' (friction angle °)", float, 35.0),
        ("psi", "ψ (dilatancy angle °)", float, 5.0),
        ("pRef", "p_ref (kN/m²)", float, 100.0),
        ("K0NC", "K0_NC (normally consolidated)", float, 0.5),
        ("Rf", "Rf (failure ratio)", float, 0.9),
        # G0ref and gamma07 are for HSsmall, add if HSsmall is a distinct model or option
    ],
    "SoftSoil": [
        ("gammaUnsat", "γ_unsat (kN/m³)", float, 16.0),
        ("gammaSat", "γ_sat (kN/m³)", float, 18.0),
        ("eInit", "e_init", float, 1.2),
        ("lambda_star", "λ* (modified compression index)", float, 0.1),
        ("kappa_star", "κ* (modified swelling index)", float, 0.02),
        ("nu", "ν'_ur (Poisson's ratio unload/reload)", float, 0.15),
        ("cRef", "c'_ref (kN/m²)", float, 2.0),
        ("phi", "φ' (friction angle °)", float, 25.0),
        ("psi", "ψ (dilatancy angle °)", float, 0.0),
        # M, K0NC etc.
    ],
    "Custom": [] # Allows manual key-value pairs in other_params
    # Add other models like SoftSoilCreep, HoekBrown, NGI-ADP, etc. as needed
}


from PySide6.QtWidgets import QFormLayout, QLineEdit, QDoubleSpinBox # Add missing imports

class ParameterEditDialog(QDialog):
    def __init__(self, material_props, parent=None):
        super().__init__(parent)
        self.material_props = material_props
        self.model_name = material_props.model_name or "Mohr-Coulomb" # Default if None
        self.setWindowTitle(f"Edit '{self.model_name}' Parameters")
        self.setMinimumWidth(400)

        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.parameter_widgets = {}

        param_definitions = SOIL_MODEL_PARAMETERS.get(self.model_name, [])
        if not param_definitions and self.model_name != "Custom":
            self.layout.addWidget(QLabel(f"No predefined parameters for model: {self.model_name}. Using custom fields."))
            param_definitions = [] # Fallback to custom if model unknown but not "Custom"

        if self.model_name == "Custom" or not param_definitions:
            # For "Custom" or unknown models, edit other_params directly
            # This is a simplified editor for "Custom"
            self.layout.addWidget(QLabel("Edit custom parameters (key: value). Add new ones as needed."))
            all_params = {**{k: getattr(self.material_props, k, None) for k, _, _, _ in SOIL_MODEL_PARAMETERS.get("Mohr-Coulomb", []) if hasattr(self.material_props, k)},
                          **self.material_props.other_params}

            for key, value in all_params.items():
                val_str = str(value) if value is not None else ""
                editor = QLineEdit(val_str)
                self.form_layout.addRow(key, editor)
                self.parameter_widgets[key] = editor
            # Allow adding new custom parameters (simplified)
            self.new_param_key_edit = QLineEdit()
            self.new_param_val_edit = QLineEdit()
            self.form_layout.addRow("New Param Key:", self.new_param_key_edit)
            self.form_layout.addRow("New Param Value:", self.new_param_val_edit)

        else:
            for param_name, display_name, param_type, default_val in param_definitions:
                # Prioritize direct attribute, then other_params, then default
                current_value = None
                if hasattr(self.material_props, param_name):
                    current_value = getattr(self.material_props, param_name)

                if current_value is None: # If direct attribute is None or not present, check other_params
                    current_value = self.material_props.other_params.get(param_name)

                if current_value is None: # If still None, use default_val
                    current_value = default_val

                if param_type == float:
                    editor = QDoubleSpinBox()
                    editor.setRange(-1e9, 1e9) # Generic large range
                    editor.setDecimals(3) # Reasonable precision
                    editor.setValue(float(current_value) if current_value is not None else float(default_val))
                elif param_type == int: # Example if int params were needed
                    editor = QSpinBox()
                    editor.setRange(-1000000, 1000000)
                    editor.setValue(int(current_value) if current_value is not None else int(default_val))
                else: # Default to QLineEdit for string or other types
                    editor = QLineEdit(str(current_value) if current_value is not None else str(default_val))

                self.form_layout.addRow(display_name, editor)
                self.parameter_widgets[param_name] = editor

        self.layout.addLayout(self.form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_parameters(self) -> dict:
        params = {}
        if self.model_name == "Custom" or not SOIL_MODEL_PARAMETERS.get(self.model_name):
            for key, editor in self.parameter_widgets.items():
                try: # Try to convert to float if possible, else string
                    params[key] = float(editor.text())
                except ValueError:
                    params[key] = editor.text()

            new_key = self.new_param_key_edit.text().strip()
            new_val_str = self.new_param_val_edit.text().strip()
            if new_key and new_val_str:
                try: params[new_key] = float(new_val_str)
                except ValueError: params[new_key] = new_val_str
        else:
            param_definitions = SOIL_MODEL_PARAMETERS.get(self.model_name, [])
            for param_name, _, param_type, _ in param_definitions:
                editor = self.parameter_widgets[param_name]
                if param_type == float:
                    params[param_name] = editor.value()
                elif param_type == int:
                    params[param_name] = editor.value()
                else:
                    params[param_name] = editor.text()
        return params

```
