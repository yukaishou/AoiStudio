"""
AoiStudio UI 编辑器
支持可视化编辑 UI 元素属性、预览、层级树等功能
"""

import os
import sys
import json
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QFrame, QScrollArea,
    QFileDialog, QMessageBox, QGroupBox, QFormLayout,
    QColorDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor


class UIElementPropertiesPanel(QWidget):
    """UI 元素属性编辑面板"""
    
    property_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_element = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 基础属性组
        base_group = QGroupBox("基础属性")
        base_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("元素名称")
        self.name_edit.textChanged.connect(self.on_property_change)
        base_layout.addRow("名称:", self.name_edit)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Button", "Image", "Text", "Rect"])
        self.type_combo.currentTextChanged.connect(self.on_property_change)
        base_layout.addRow("类型:", self.type_combo)
        
        base_group.setLayout(base_layout)
        layout.addWidget(base_group)
        
        # 位置属性组
        pos_group = QGroupBox("位置")
        pos_layout = QFormLayout()
        
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-9999, 9999)
        self.x_spin.setSuffix(" px")
        self.x_spin.valueChanged.connect(self.on_property_change)
        pos_layout.addRow("X:", self.x_spin)
        
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-9999, 9999)
        self.y_spin.setSuffix(" px")
        self.y_spin.valueChanged.connect(self.on_property_change)
        pos_layout.addRow("Y:", self.y_spin)
        
        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)
        
        # 尺寸属性组
        size_group = QGroupBox("尺寸")
        size_layout = QFormLayout()
        
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0, 9999)
        self.width_spin.setSuffix(" px")
        self.width_spin.valueChanged.connect(self.on_property_change)
        size_layout.addRow("宽度:", self.width_spin)
        
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0, 9999)
        self.height_spin.setSuffix(" px")
        self.height_spin.valueChanged.connect(self.on_property_change)
        size_layout.addRow("高度:", self.height_spin)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # 锚点属性组
        anchor_group = QGroupBox("锚点")
        anchor_layout = QFormLayout()
        
        self.anchor_combo = QComboBox()
        self.anchor_combo.addItems(["topleft", "center", "topright", "bottomleft", "bottomright"])
        self.anchor_combo.currentTextChanged.connect(self.on_property_change)
        anchor_layout.addRow("锚点:", self.anchor_combo)
        
        anchor_group.setLayout(anchor_layout)
        layout.addWidget(anchor_group)
        
        # 颜色属性组
        color_group = QGroupBox("颜色")
        color_layout = QFormLayout()
        
        self.color_button = QPushButton("选择颜色")
        self.color_button.clicked.connect(self.choose_color)
        self.current_color = QColor(100, 100, 100)
        self.update_color_button()
        color_layout.addRow("", self.color_button)
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        layout.addStretch()
    
    def update_color_button(self):
        self.color_button.setStyleSheet(
            f"background-color: {self.current_color.name()};"
        )
    
    def choose_color(self):
        color = QColorDialog.getColor(self.current_color, self, "选择颜色")
        if color.isValid():
            self.current_color = color
            self.update_color_button()
            self.on_property_change()
    
    def load_element(self, element_data: dict):
        """加载元素数据到面板"""
        self.current_element = element_data
        
        # 阻止信号触发
        self.name_edit.blockSignals(True)
        self.x_spin.blockSignals(True)
        self.y_spin.blockSignals(True)
        self.width_spin.blockSignals(True)
        self.height_spin.blockSignals(True)
        
        # 填充数据
        self.name_edit.setText(element_data.get("name", ""))
        self.type_combo.setCurrentText(element_data.get("type", "Button"))
        self.x_spin.setValue(element_data.get("x", 0))
        self.y_spin.setValue(element_data.get("y", 0))
        self.width_spin.setValue(element_data.get("width", 100))
        self.height_spin.setValue(element_data.get("height", 50))
        self.anchor_combo.setCurrentText(element_data.get("anchor", "center"))
        
        if "color" in element_data:
            color = element_data["color"]
            if isinstance(color, (list, tuple)) and len(color) >= 3:
                self.current_color = QColor(color[0], color[1], color[2])
                self.update_color_button()
        
        # 恢复信号
        self.name_edit.blockSignals(False)
        self.x_spin.blockSignals(False)
        self.y_spin.blockSignals(False)
        self.width_spin.blockSignals(False)
        self.height_spin.blockSignals(False)
    
    def on_property_change(self):
        """属性变化时发出信号"""
        if self.current_element is None:
            return
        
        properties = {
            "name": self.name_edit.text(),
            "type": self.type_combo.currentText(),
            "x": self.x_spin.value(),
            "y": self.y_spin.value(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "anchor": self.anchor_combo.currentText(),
            "color": [self.current_color.red(), self.current_color.green(), self.current_color.blue()]
        }
        
        self.property_changed.emit(properties)


class UIHierarchyTree(QTreeWidget):
    """UI 层级树形视图"""
    
    element_selected = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["UI 元素"])
        self.setExpandsOnDoubleClick(False)
        self.itemSelectionChanged.connect(self.on_selection_changed)
        self.elements_map = {}  # item -> element_data
    
    def load_elements(self, elements: list):
        """加载 UI 元素列表"""
        self.clear()
        self.elements_map.clear()
        
        for element in elements:
            item = QTreeWidgetItem([element.get("name", "Unnamed")])
            item.setData(0, Qt.UserRole, element)
            self.addTopLevelItem(item)
            self.elements_map[item] = element
    
    def on_selection_changed(self):
        items = self.selectedItems()
        if items:
            item = items[0]
            element_data = item.data(0, Qt.UserRole)
            if element_data:
                self.element_selected.emit(element_data)


class UIPreviewWidget(QWidget):
    """UI 预览窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: #f0f0f0;")
        self.elements = []
    
    def load_elements(self, elements: list):
        """加载 UI 元素进行预览"""
        self.elements = elements
        self.update()
    
    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QBrush, QPen
        from PyQt5.QtCore import QRectF
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor(240, 240, 240))
        
        # 绘制所有 UI 元素
        for element in self.elements:
            x = element.get("x", 0)
            y = element.get("y", 0)
            width = element.get("width", 100)
            height = element.get("height", 50)
            color = element.get("color", [100, 100, 100])
            
            rect = QRectF(x, y, width, height)
            painter.setBrush(QBrush(QColor(*color)))
            painter.setPen(QPen(Qt.black, 1))
            painter.drawRect(rect)
            
            # 绘制元素名称
            painter.setPen(QPen(Qt.white if sum(color) < 384 else Qt.black, 1))
            painter.drawText(rect, Qt.AlignCenter, element.get("name", ""))


class UIEditorWindow(QMainWindow):
    """UI 编辑器主窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AoiStudio UI 编辑器")
        self.resize(1200, 800)
        self.current_file_path = None
        self.ui_elements = []
        
        self.init_ui()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        self.btn_new = QPushButton("新建")
        self.btn_new.clicked.connect(self.new_ui)
        self.btn_open = QPushButton("打开")
        self.btn_open.clicked.connect(self.open_ui)
        self.btn_save = QPushButton("保存")
        self.btn_save.clicked.connect(self.save_ui)
        self.btn_save_as = QPushButton("另存为")
        self.btn_save_as.clicked.connect(self.save_ui_as)
        self.btn_add_element = QPushButton("添加元素")
        self.btn_add_element.clicked.connect(self.add_element)
        
        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_open)
        toolbar.addWidget(self.btn_save)
        toolbar.addWidget(self.btn_save_as)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_add_element)
        
        main_layout.addLayout(toolbar)
        
        # 主分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：层级树
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.hierarchy_tree = UIHierarchyTree()
        self.hierarchy_tree.element_selected.connect(self.on_element_selected)
        left_layout.addWidget(self.hierarchy_tree)
        
        splitter.addWidget(left_widget)
        
        # 中间：预览区
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_widget = UIPreviewWidget()
        self.preview_scroll.setWidget(self.preview_widget)
        splitter.addWidget(self.preview_scroll)
        
        # 右侧：属性面板
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.properties_panel = UIElementPropertiesPanel()
        self.properties_panel.property_changed.connect(self.on_property_changed)
        right_layout.addWidget(self.properties_panel)
        
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setSizes([250, 600, 350])
        
        main_layout.addWidget(splitter)
    
    def new_ui(self):
        """新建 UI"""
        self.ui_elements = []
        self.current_file_path = None
        self.hierarchy_tree.load_elements([])
        self.preview_widget.load_elements([])
        self.setWindowTitle("AoiStudio UI 编辑器 - 未命名")
    
    def open_ui(self):
        """打开 UI 文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开 UI 文件", "", "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.ui_elements = json.load(f)
                
                self.current_file_path = file_path
                self.hierarchy_tree.load_elements(self.ui_elements)
                self.preview_widget.load_elements(self.ui_elements)
                self.setWindowTitle(f"AoiStudio UI 编辑器 - {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开文件失败：{str(e)}")
    
    def save_ui(self):
        """保存 UI 文件"""
        if self.current_file_path:
            self.save_ui_to_path(self.current_file_path)
        else:
            self.save_ui_as()
    
    def save_ui_as(self):
        """另存为 UI 文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存 UI 文件", "", "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        
        if file_path:
            self.save_ui_to_path(file_path)
    
    def save_ui_to_path(self, file_path: str):
        """保存到指定路径"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.ui_elements, f, indent=2, ensure_ascii=False)
            
            self.current_file_path = file_path
            self.setWindowTitle(f"AoiStudio UI 编辑器 - {os.path.basename(file_path)}")
            QMessageBox.information(self, "成功", "UI 文件保存成功")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件失败：{str(e)}")
    
    def add_element(self):
        """添加新元素"""
        new_element = {
            "name": f"Element_{len(self.ui_elements) + 1}",
            "type": "Button",
            "x": 100,
            "y": 100,
            "width": 120,
            "height": 40,
            "anchor": "center",
            "color": [100, 100, 100]
        }
        
        self.ui_elements.append(new_element)
        self.hierarchy_tree.load_elements(self.ui_elements)
        self.preview_widget.load_elements(self.ui_elements)
    
    def on_element_selected(self, element_data: dict):
        """选择元素时"""
        self.properties_panel.load_element(element_data)
    
    def on_property_changed(self, properties: dict):
        """属性变化时"""
        # TODO: 更新选中的元素属性
        pass


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    win = UIEditorWindow()
    win.show()
    sys.exit(app.exec_())