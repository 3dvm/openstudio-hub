# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_blend_builder.py
# Rol Arquitectónico: UI Component / Batch Entity Genesis Tool
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0
# =========================================================================================

import gazu
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QWidget, QAbstractItemView,
                               QComboBox, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal

from core.production_manager import ProductionManager

class FetchProjectsWorker(QThread):
    data_ready = Signal(list)
    error_occurred = Signal(str)

    def run(self):
        try:
            self.data_ready.emit(gazu.project.all_open_projects())
        except Exception as e:
            self.error_occurred.emit(str(e))

class FetchEntitiesWorker(QThread):
    data_ready = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, pm_core, project_id):
        super().__init__()
        self.pm_core = pm_core
        self.project_id = project_id

    def run(self):
        try:
            self.data_ready.emit(self.pm_core.get_pending_entities(self.project_id))
        except Exception as e:
            self.error_occurred.emit(str(e))

class BatchCreationWorker(QThread):
    finished_batch = Signal(bool, str)

    def __init__(self, pm_core, p_name, entities, template, task_types, status_cb):
        super().__init__()
        self.pm_core = pm_core
        self.p_name = p_name
        self.entities = entities
        self.template = template
        self.task_types = task_types
        self.status_cb = status_cb

    def run(self):
        try:
            succ, msg = self.pm_core.batch_create_entity_files(
                self.p_name, self.entities, self.template, self.task_types, self.status_cb)
            self.finished_batch.emit(succ, msg)
        except Exception as e:
            self.finished_batch.emit(False, str(e))


class WidgetBlendBuilder(QFrame):
    def __init__(self, parent, auth_manager, config_factory, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.auth = auth_manager
        self.config_factory = config_factory
        self.status_callback = status_callback
        
        self.pm_core = ProductionManager(self.auth, self.config_factory)
        self.current_project_id = None
        self.project_map = {}

        self.setObjectName("TransparentGridContainer")
        self._build_ui()
        
        self._load_projects_from_kitsu()
        self._load_templates_from_vault()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # Header Interno
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        lbl_title = QLabel(self.tr("Batch Entity Creation"))
        lbl_title.setObjectName("PageTitle")
        header_layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(self.tr("Review approved editorial sequences and assets from Kitsu. Click 'Create .blends' to automatically generate their physical files and VCS directory structures."))
        lbl_desc.setObjectName("PageDescription")
        lbl_desc.setWordWrap(True)
        header_layout.addWidget(lbl_desc)
        main_layout.addLayout(header_layout)

        # Controls & KPI
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)

        self.lbl_kpi_total = self._create_kpi_label(self.tr("Total Entries: 0"))
        self.lbl_kpi_shots = self._create_kpi_label(self.tr("Shots: 0"))
        self.lbl_kpi_assets = self._create_kpi_label(self.tr("Assets: 0"))

        controls_layout.addWidget(self.lbl_kpi_total)
        controls_layout.addWidget(self.lbl_kpi_shots)
        controls_layout.addWidget(self.lbl_kpi_assets)
        controls_layout.addStretch()

        self.combo_projects = QComboBox()
        self.combo_projects.setObjectName("StandardComboBox")
        self.combo_projects.setFixedSize(200, 35)
        self.combo_projects.currentIndexChanged.connect(self._on_project_changed)
        controls_layout.addWidget(self.combo_projects)

        self.combo_templates = QComboBox()
        self.combo_templates.setObjectName("StandardComboBox")
        self.combo_templates.setFixedSize(200, 35)
        controls_layout.addWidget(self.combo_templates)

        self.btn_create_files = QPushButton(self.tr("Create .blends"))
        self.btn_create_files.setObjectName("PrimaryButton")
        self.btn_create_files.setFixedSize(140, 35)
        self.btn_create_files.setCursor(Qt.PointingHandCursor)
        self.btn_create_files.clicked.connect(self._trigger_batch_creation)
        controls_layout.addWidget(self.btn_create_files)
        main_layout.addLayout(controls_layout)

        # Data Grid
        self.table = QTableWidget(0, 6)
        self.table.setObjectName("DataGrid")
        self.table.setHorizontalHeaderLabels(["", self.tr("Entity Name"), self.tr("Type"), self.tr("Parent Sequence"), self.tr("Frame Range"), self.tr("Kitsu Status")])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 40)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        main_layout.addWidget(self.table, stretch=1)

    def _create_kpi_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("KPILabel")
        return lbl

    def _create_pill_label(self, text: str, color_hex: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setObjectName("PillLabel")
        lbl.setStyleSheet(f"background-color: {color_hex};")
        layout.addWidget(lbl)
        return widget

    def _load_projects_from_kitsu(self):
        self.combo_projects.blockSignals(True)
        self.combo_projects.addItem(self.tr("Loading projects..."))
        
        self.worker_projects = FetchProjectsWorker()
        self.worker_projects.data_ready.connect(self._on_projects_loaded)
        self.worker_projects.error_occurred.connect(lambda e: self.status_callback(f"Project fetch error: {e}", "red"))
        self.worker_projects.start()

    def _on_projects_loaded(self, projects: list):
        self.combo_projects.clear()
        self.project_map.clear()
        if not projects:
            self.combo_projects.addItem(self.tr("No open projects found"))
            self.combo_projects.blockSignals(False)
            return

        for p in projects:
            self.project_map[p.get("name", "Unknown")] = p.get("id")
            self.combo_projects.addItem(p.get("name", "Unknown"))
        self.combo_projects.blockSignals(False)
        self._on_project_changed()

    def _load_templates_from_vault(self):
        self.combo_templates.clear()
        try:
            if self.pm_core.vault_templates_dir.exists():
                templates = [d.name for d in self.pm_core.vault_templates_dir.iterdir() if d.is_dir() or d.name.endswith(".blend")]
                if templates: self.combo_templates.addItems(templates)
                else: self.combo_templates.addItem(self.tr("-- No templates --"))
        except Exception:
            self.combo_templates.addItem(self.tr("-- Error reading Vault --"))

    def _on_project_changed(self):
        project_name = self.combo_projects.currentText()
        if project_name in self.project_map:
            self.current_project_id = self.project_map[project_name]
            self.load_entities_from_kitsu()

    def load_entities_from_kitsu(self):
        if not self.current_project_id: return
            
        self.status_callback(self.tr("Fetching pending entities from Kitsu..."), "yellow")
        self.table.setRowCount(0)
        self.btn_create_files.setEnabled(False)
        
        self.worker_entities = FetchEntitiesWorker(self.pm_core, self.current_project_id)
        self.worker_entities.data_ready.connect(self._render_entities)
        self.worker_entities.error_occurred.connect(lambda e: self.status_callback(f"Entity fetch error: {e}", "red"))
        self.worker_entities.start()

    def _render_entities(self, entities: list):
        self.table.setRowCount(len(entities))
        shots_count, assets_count = 0, 0
        
        for row, entity in enumerate(entities):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Unchecked)
            chk_item.setData(Qt.UserRole, entity)
            self.table.setItem(row, 0, chk_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(entity.get("name", "Unknown")))
            
            e_type = entity.get("type", "Shot")
            color = "#F59E0B" if e_type == "Shot" else "#8B5CF6"
            if e_type == "Shot": shots_count += 1 
            else: assets_count += 1
            self.table.setCellWidget(row, 2, self._create_pill_label(e_type, color))
            
            parent_item = QTableWidgetItem(entity.get("parent", "Unknown"))
            self.table.setItem(row, 3, parent_item)
            self.table.setItem(row, 4, QTableWidgetItem(str(entity.get("frame_in", 0))))
            
            status_item = QTableWidgetItem(entity.get("status", "Unknown"))
            self.table.setItem(row, 5, status_item)

        self.lbl_kpi_total.setText(self.tr(f"Total Entries: {len(entities)}"))
        self.lbl_kpi_shots.setText(self.tr(f"Shots: {shots_count}"))
        self.lbl_kpi_assets.setText(self.tr(f"Assets: {assets_count}"))
        
        self.btn_create_files.setEnabled(True)
        self.status_callback(self.tr("✓ Entities loaded. Select the items you want to physicalize."), "green")

    def _trigger_batch_creation(self):
        selected_entities = [self.table.item(r, 0).data(Qt.UserRole) for r in range(self.table.rowCount()) if self.table.item(r, 0).checkState() == Qt.Checked]

        if not selected_entities:
            self.status_callback(self.tr("No entities selected for file creation."), "yellow")
            return
            
        template_name = self.combo_templates.currentText()
        if template_name.startswith("--"):
            QMessageBox.warning(self, self.tr("Missing Template"), self.tr("You must select a valid base .blend template from the Vault."))
            return

        self.btn_create_files.setEnabled(False)
        self.combo_projects.setEnabled(False)
        
        self.status_callback(self.tr("Initializing batch creation for {0} entities...").format(len(selected_entities)), "yellow")
        
        self.worker_batch = BatchCreationWorker(
            pm_core=self.pm_core,
            p_name=self.combo_projects.currentText(),
            entities=selected_entities,
            template=template_name,
            task_types=["Modeling", "Rigging", "Animation", "Lighting", "Compositing"],
            status_cb=self.status_callback
        )
        self.worker_batch.finished_batch.connect(self._on_batch_finished)
        self.worker_batch.start()

    def _on_batch_finished(self, success: bool, message: str):
        self.btn_create_files.setEnabled(True)
        self.combo_projects.setEnabled(True)
        
        if success:
            self.status_callback(self.tr("✓ {0}").format(message), "green")
            self.load_entities_from_kitsu()
        else:
            self.status_callback(self.tr("✗ Batch Error: {0}").format(message), "red")
            QMessageBox.critical(self, self.tr("Batch Creation Failed"), message)
