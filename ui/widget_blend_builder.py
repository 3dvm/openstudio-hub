# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_blend_builder.py
# Rol Arquitectónico: UI Component / Batch Entity Genesis Tool
# =========================================================================================

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QWidget, QAbstractItemView,
                               QComboBox, QMessageBox, QStackedWidget, QListWidget, QLineEdit)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from core.production_manager import ProductionManager
from ui.components.pipeline_wizard import PipelineWizardWidget
from ui.workers.spawning_workers import (FetchProjectsWorker, FetchEntitiesWorker, BatchCreationWorker,
                                         MasterSpawningWorker, StoryboardBatchWorker, SpawningProgressDialog)

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

        # --- 1. SELECTOR DE PROYECTO ---
        project_layout = QHBoxLayout()
        lbl_proj = QLabel(self.tr("Active Project:"))
        lbl_proj.setObjectName("InputLabel")
        
        self.combo_projects = QComboBox()
        self.combo_projects.setObjectName("StandardComboBox")
        self.combo_projects.setFixedSize(250, 35)
        self.combo_projects.currentIndexChanged.connect(self._on_project_changed)
        
        project_layout.addWidget(lbl_proj)
        project_layout.addWidget(self.combo_projects)
        project_layout.addStretch()
        main_layout.addLayout(project_layout)

        # --- 2. PIPELINE WIZARD (Top Section) ---
        self.wizard = PipelineWizardWidget(self)
        self.wizard.action_requested.connect(self._ejecutar_fase_pipeline)
        main_layout.addWidget(self.wizard)

        # --- 3. STACKED WIDGET (Panel Dinámico Inferior) ---
        self.stack = QStackedWidget()
        
        # PÁGINA 0: BREAKDOWN MANUAL DE STORYBOARD
        self.page_storyboard = QWidget()
        sb_layout = QVBoxLayout(self.page_storyboard)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_sb_desc = QLabel(self.tr("Enter the sequences (e.g. SQ010) identified during the script breakdown. This will register them in Kitsu and spawn their physical .blend files."))
        lbl_sb_desc.setObjectName("PageDescription")
        lbl_sb_desc.setWordWrap(True)
        sb_layout.addWidget(lbl_sb_desc)

        input_layout = QHBoxLayout()
        self.input_seq = QLineEdit()
        self.input_seq.setObjectName("FormInput")
        self.input_seq.setPlaceholderText(self.tr("Enter Sequence Name (e.g. SQ010) and press Enter"))
        self.input_seq.setFixedSize(300, 35)
        self.input_seq.returnPressed.connect(self._add_sequence_to_list)
        
        self.btn_add_seq = QPushButton(self.tr("Add"))
        self.btn_add_seq.setObjectName("SecondaryButton")
        self.btn_add_seq.setFixedSize(80, 35)
        self.btn_add_seq.clicked.connect(self._add_sequence_to_list)
        
        input_layout.addWidget(self.input_seq)
        input_layout.addWidget(self.btn_add_seq)
        input_layout.addStretch()
        sb_layout.addLayout(input_layout)
        
        self.list_sequences = QListWidget()
        self.list_sequences.setObjectName("FormInput") 
        sb_layout.addWidget(self.list_sequences)
        
        self.btn_clear_seq = QPushButton(self.tr("Clear List"))
        self.btn_clear_seq.setObjectName("LinkButton")
        self.btn_clear_seq.setCursor(Qt.PointingHandCursor)
        self.btn_clear_seq.clicked.connect(self.list_sequences.clear)
        sb_layout.addWidget(self.btn_clear_seq, alignment=Qt.AlignRight)
        
        self.stack.addWidget(self.page_storyboard)

        # PÁGINA 1: TABLA KANBAN (Edición, Assets, Shots)
        self.page_entities = QWidget()
        ent_layout = QVBoxLayout(self.page_entities)
        ent_layout.setContentsMargins(0, 0, 0, 0)
        
        controls_layout = QHBoxLayout()
        self.lbl_kpi_total = self._create_kpi_label(self.tr("Total Entries: 0"))
        self.lbl_kpi_shots = self._create_kpi_label(self.tr("Shots: 0"))
        self.lbl_kpi_assets = self._create_kpi_label(self.tr("Assets: 0"))

        controls_layout.addWidget(self.lbl_kpi_total)
        controls_layout.addWidget(self.lbl_kpi_shots)
        controls_layout.addWidget(self.lbl_kpi_assets)
        controls_layout.addStretch()
        
        self.combo_templates = QComboBox()
        self.combo_templates.setObjectName("StandardComboBox")
        self.combo_templates.setFixedSize(200, 35)
        controls_layout.addWidget(self.combo_templates)
        ent_layout.addLayout(controls_layout)

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

        ent_layout.addWidget(self.table, stretch=1)
        self.stack.addWidget(self.page_entities)
        
        main_layout.addWidget(self.stack, stretch=1)

    # --- UI HELPERS ---
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

    def advance_wizard(self, step_number: int):
        self.wizard.set_step(step_number)
        self.stack.setCurrentIndex(0 if step_number == 1 else 1)

    def _add_sequence_to_list(self):
        seq_name = self.input_seq.text().strip().upper()
        if not seq_name: return
        existing = [self.list_sequences.item(i).text() for i in range(self.list_sequences.count())]
        if seq_name not in existing:
            self.list_sequences.addItem(seq_name)
        self.input_seq.clear()
        self.input_seq.setFocus()

    # --- NETWORK / I/O LOGIC ---
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
            self.advance_wizard(1) # Forzar paso 1 al cambiar de proyecto
            self.load_entities_from_kitsu()

    def load_entities_from_kitsu(self):
        if not self.current_project_id: return
        self.status_callback(self.tr("Fetching pending entities from Kitsu..."), "yellow")
        self.table.setRowCount(0)
        
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
            self.table.setItem(row, 5, QTableWidgetItem(entity.get("status", "Unknown")))

        self.lbl_kpi_total.setText(self.tr(f"Total Entries: {len(entities)}"))
        self.lbl_kpi_shots.setText(self.tr(f"Shots: {shots_count}"))
        self.lbl_kpi_assets.setText(self.tr(f"Assets: {assets_count}"))
        
        self.status_callback(self.tr("✓ Entities loaded."), "green")

    # --- ENRUTADOR PRINCIPAL ---
    def _ejecutar_fase_pipeline(self, step_id: int):
        if not self.current_project_id:
            self.status_callback(self.tr("Please select a project first."), "yellow")
            return

        if step_id == 1:
            if self.input_seq.text().strip():
                self._add_sequence_to_list()
                
            sequences = [self.list_sequences.item(i).text() for i in range(self.list_sequences.count())]
            if not sequences:
                QMessageBox.warning(self, self.tr("Empty List"), self.tr("Please add at least one sequence to spawn."))
                return
                
            self.status_callback(self.tr("Spawning Storyboard sequences..."), "yellow")
            project_name = self.combo_projects.currentText()
            self.progress_modal = SpawningProgressDialog(self, self.tr("Batch Spawning Storyboards"))
            self.progress_modal.show()
            
            self.spawn_worker = StoryboardBatchWorker(self.pm_core, self.config_factory, self.current_project_id, project_name, sequences)
            self.spawn_worker.progress_updated.connect(self.progress_modal.update_progress)
            self.spawn_worker.log_stream.connect(self.progress_modal.append_log)
            
            def open_kitsu():
                kitsu_url = self.config_factory.get_kitsu_api_url().replace("/api", "")
                url = f"{kitsu_url}/productions/{self.current_project_id}/shots"
                QDesktopServices.openUrl(QUrl(url))
                self.progress_modal.accept()

            def on_sb_finished(success, msg):
                if success:
                    self.status_callback(self.tr(f"✓ {msg}"), "green")
                    self.list_sequences.clear()
                    self.advance_wizard(2)
                    self.progress_modal.finalize(True, self.tr("Success: Storyboards spawned."), "Assign Artists in Kitsu", open_kitsu)
                else:
                    self.status_callback(self.tr(f"✗ Error: {msg}"), "red")
                    self.progress_modal.finalize(False, self.tr("Process completed with errors. Check logs."))

            self.spawn_worker.finished_batch.connect(on_sb_finished)
            self.spawn_worker.start()
            
        elif step_id == 2:
            project_name = self.combo_projects.currentText()
            self.progress_modal = SpawningProgressDialog(self, self.tr("Spawning EDIT Master"))
            self.progress_modal.show()
            
            self.spawn_worker = MasterSpawningWorker(self.config_factory, project_name, "EDIT")
            self.spawn_worker.progress_updated.connect(self.progress_modal.update_progress)
            self.spawn_worker.log_stream.connect(self.progress_modal.append_log)
            
            def on_finished(success, msg):
                if success:
                    self.status_callback(self.tr(f"✓ {msg}"), "green")
                    self.advance_wizard(3)
                    self.progress_modal.finalize(True, self.tr("Success: EDIT Master forged."))
                else:
                    self.status_callback(self.tr(f"✗ Error: {msg}"), "red")
                    self.progress_modal.finalize(False, self.tr("Process completed with errors. Check logs."))
                    
            self.spawn_worker.finished_spawn.connect(on_finished)
            self.spawn_worker.start()

        elif step_id in [3, 4]:
            self.status_callback(self.tr("Batch Creating Entities..."), "yellow")
            self._trigger_batch_creation()

    def _trigger_batch_creation(self):
        selected_entities = [self.table.item(r, 0).data(Qt.UserRole) for r in range(self.table.rowCount()) if self.table.item(r, 0).checkState() == Qt.Checked]
        if not selected_entities:
            self.status_callback(self.tr("No entities selected for file creation."), "yellow")
            return
            
        template_name = self.combo_templates.currentText()
        if template_name.startswith("--"):
            QMessageBox.warning(self, self.tr("Missing Template"), self.tr("Select a valid base .blend template."))
            return

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
        if success:
            self.status_callback(self.tr("✓ {0}").format(message), "green")
            self.load_entities_from_kitsu()
        else:
            self.status_callback(self.tr("✗ Batch Error: {0}").format(message), "red")
            QMessageBox.critical(self, self.tr("Batch Creation Failed"), message)
