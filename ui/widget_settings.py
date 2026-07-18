# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_settings.py
# Rol Arquitectónico: UI Component / Global Settings & Seed Generator (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.4.0
# =========================================================================================

"""
Global Configuration Panel for the Technical Director.
Groups B2B settings into logical tabs (Identity, Vault, VCS, Topography).
Exposes the dispatcher to generate the Studio Seed (.seed) and manage the custom
VFS Topography mapping required by Blender Studio Tools conventions.
"""

import shutil
from pathlib import Path
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QWidget, QLineEdit, QTabWidget,
                               QComboBox, QCheckBox, QFormLayout, QFileDialog)
from PySide6.QtCore import Qt, QDir, QThread, Signal
from ui.widget_software import SoftwareProvisioningWidget


class SyncIdentityWorker(QThread):
    """Worker thread to handle the Kitsu network call for organisation metadata asynchronously."""
    finished_sync = Signal(dict)

    def __init__(self, auth_manager):
        super().__init__()
        self.auth_manager = auth_manager

    def run(self):
        identity_data = self.auth_manager.sync_studio_identity()
        self.finished_sync.emit(identity_data)


class SettingsWidget(QFrame):
    def __init__(self, parent, config_factory, auth_manager, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.config_factory = config_factory
        self.auth_manager = auth_manager
        self.status_callback = status_callback
        
        # Flag imperativo para mitigar colisiones de UI al cargar datos iniciales
        self._is_loading = True
        self._pending_hero_image_path = None
        
        self.setObjectName("SettingsWidgetBase")
        self.setStyleSheet("background: transparent;")
        
        self._build_ui()
        self._conectar_senales_cambio()
        self._cargar_datos_actuales()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # HEADER CON ALERTA VISUAL INTEGRADA
        header_layout = QHBoxLayout()
        lbl_title = QLabel(self.tr("Global Studio Settings"))
        lbl_title.setObjectName("H2Title")
        header_layout.addWidget(lbl_title)
        
        self.lbl_unsaved_warning = QLabel("")
        header_layout.addWidget(self.lbl_unsaved_warning)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # TAB SYSTEM
        self.tabs = QTabWidget()
        self.tabs.setObjectName("SettingsTabs")
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #334155; border-radius: 8px; background: #1E293B; }
            QTabBar::tab { background: #0F172A; color: #94A3B8; padding: 10px 20px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px; }
            QTabBar::tab:selected { background: #1E293B; color: #F8FAFC; font-weight: bold; border: 1px solid #334155; border-bottom: none; }
        """)

        # Tab 1: Identity & API
        self.tab_identidad = QWidget()
        self._build_tab_identidad()
        self.tabs.addTab(self.tab_identidad, self.tr("Identity & API"))

        # Tab 2: Storage & Vault
        self.tab_boveda = QWidget()
        self._build_tab_boveda()
        self.tabs.addTab(self.tab_boveda, self.tr("Vault Storage"))

        # Tab 3: Version Control
        self.tab_vcs = QWidget()
        self._build_tab_vcs()
        self.tabs.addTab(self.tab_vcs, self.tr("Pipeline & VCS"))

        # Tab 4: Project Topography
        self.tab_topo = QWidget()
        self._build_tab_topografia()
        self.tabs.addTab(self.tab_topo, self.tr("Project Topography"))

        self.tab_software = SoftwareProvisioningWidget(
            parent=self.tabs,
            config_factory=self.config_factory,
            status_callback=self.status_callback
        )
        self.tabs.addTab(self.tab_software, self.tr("Software & Manifest"))

        main_layout.addWidget(self.tabs, stretch=1)

        # FOOTER / MASTER ACTIONS
        footer_layout = QHBoxLayout()
        
        self.btn_guardar = QPushButton(self.tr("Save Local Changes"))
        self.btn_guardar.setObjectName("SecondaryButton")
        self.btn_guardar.setFixedSize(180, 40)
        self.btn_guardar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar.clicked.connect(self._guardar_configuracion)
        footer_layout.addWidget(self.btn_guardar)

        footer_layout.addStretch()

        self.btn_exportar_semilla = QPushButton(self.tr("Export Studio Seed (.seed)"))
        self.btn_exportar_semilla.setStyleSheet("background-color: #4F46E5; color: white; font-weight: bold; border-radius: 6px; font-size: 13px; border: none;")
        self.btn_exportar_semilla.setFixedSize(240, 40)
        self.btn_exportar_semilla.setCursor(Qt.PointingHandCursor)
        self.btn_exportar_semilla.clicked.connect(self._exportar_semilla_estudio)
        footer_layout.addWidget(self.btn_exportar_semilla)

        main_layout.addLayout(footer_layout)

    def _crear_input(self, placeholder: str = "") -> QLineEdit:
        campo = QLineEdit()
        campo.setObjectName("FormInput")
        campo.setFixedHeight(35)
        campo.setPlaceholderText(placeholder)
        return campo

    def _conectar_senales_cambio(self):
        """Mapea reactivamente los inputs para activar la alerta visual ante modificaciones."""
        self.entry_studio_name.textChanged.connect(self._on_field_modified)
        self.entry_kitsu_url.textChanged.connect(self._on_field_modified)
        self.entry_projects_path.textChanged.connect(self._on_field_modified)
        self.entry_vault_path.textChanged.connect(self._on_field_modified)
        self.entry_repo_url.textChanged.connect(self._on_field_modified)
        self.combo_vcs.currentIndexChanged.connect(self._on_field_modified)
        self.chk_sparse.stateChanged.connect(self._on_field_modified)

        # Topography Signals
        self.entry_topo_svn.textChanged.connect(self._on_field_modified)
        self.entry_topo_shared.textChanged.connect(self._on_field_modified)
        self.entry_topo_local.textChanged.connect(self._on_field_modified)
        self.entry_topo_pipeline.textChanged.connect(self._on_field_modified)
        self.entry_topo_custom1.textChanged.connect(self._on_field_modified)
        self.entry_topo_custom2.textChanged.connect(self._on_field_modified)

    def _on_field_modified(self):
        if self._is_loading:
            return
        self.lbl_unsaved_warning.setText(self.tr("● Unsaved Changes"))
        self.lbl_unsaved_warning.setStyleSheet("color: #F59E0B; font-weight: bold; font-size: 13px; margin-left: 15px;")

    def _build_tab_identidad(self):
        layout = QFormLayout(self.tab_identidad)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        name_layout = QHBoxLayout()
        self.entry_studio_name = self._crear_input(self.tr("e.g. Macuare Studio"))
        name_layout.addWidget(self.entry_studio_name)

        self.btn_sync_identity = QPushButton(self.tr("Sync from Kitsu"))
        self.btn_sync_identity.setObjectName("SecondaryButton")
        self.btn_sync_identity.setFixedSize(130, 35)
        self.btn_sync_identity.setCursor(Qt.PointingHandCursor)
        self.btn_sync_identity.clicked.connect(self._ejecutar_sincronizacion_identidad)
        name_layout.addWidget(self.btn_sync_identity)

        self.entry_kitsu_url = self._crear_input(self.tr("e.g. https://kitsu.mydomain.com/api"))

        # Studio Hero Image (UI Customization)
        hero_layout = QHBoxLayout()
        self.entry_hero_image = self._crear_input(self.tr("Select a PNG/JPG for the login background"))
        self.entry_hero_image.setReadOnly(True)
        hero_layout.addWidget(self.entry_hero_image)

        btn_browse_hero = QPushButton(self.tr("Browse..."))
        btn_browse_hero.setObjectName("SecondaryButton")
        btn_browse_hero.setFixedSize(90, 35)
        btn_browse_hero.clicked.connect(self._seleccionar_hero_image)
        hero_layout.addWidget(btn_browse_hero)

        layout.addRow(self._styled_label(self.tr("Studio Name:")), name_layout)
        layout.addRow(self._styled_label(self.tr("Kitsu API URL:")), self.entry_kitsu_url)
        layout.addRow(self._styled_label(self.tr("Studio Hero Image:")), hero_layout)

    def _build_tab_boveda(self):
        layout = QFormLayout(self.tab_boveda)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        proj_layout = QHBoxLayout()
        self.entry_projects_path = self._crear_input(self.tr("e.g. Z:/studio_projects"))
        self.entry_projects_path.setReadOnly(True)
        proj_layout.addWidget(self.entry_projects_path)

        btn_browse_proj = QPushButton(self.tr("Browse..."))
        btn_browse_proj.setObjectName("SecondaryButton")
        btn_browse_proj.setFixedSize(90, 35)
        btn_browse_proj.clicked.connect(self._seleccionar_proyectos)
        proj_layout.addWidget(btn_browse_proj)

        layout.addRow(self._styled_label(self.tr("Projects Directory:")), proj_layout)

        path_layout = QHBoxLayout()
        self.entry_vault_path = self._crear_input(self.tr("e.g. Z:/studio_projects/openstudio_vault"))
        self.entry_vault_path.setReadOnly(True)
        path_layout.addWidget(self.entry_vault_path)

        btn_browse_vault = QPushButton(self.tr("Browse..."))
        btn_browse_vault.setObjectName("SecondaryButton")
        btn_browse_vault.setFixedSize(90, 35)
        btn_browse_vault.clicked.connect(self._seleccionar_boveda)
        path_layout.addWidget(btn_browse_vault)

        layout.addRow(self._styled_label(self.tr("Vault Directory:")), path_layout)

        lbl_desc = QLabel(self.tr("Physical storage paths on the NAS.\nThe Projects Directory holds live production assets, while the Vault contains immutable software components and engine templates."))
        lbl_desc.setStyleSheet("color: #64748B; font-size: 12px;")
        layout.addRow("", lbl_desc)

    def _build_tab_vcs(self):
        layout = QFormLayout(self.tab_vcs)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        self.combo_vcs = QComboBox()
        self.combo_vcs.addItems(["svn", "git-lfs"])
        self.combo_vcs.setFixedHeight(35)
        self.combo_vcs.setStyleSheet("background-color: #0F172A; border: 1px solid #475569; color: #F8FAFC; border-radius: 6px; padding-left: 10px;")

        self.entry_repo_url = self._crear_input(self.tr("e.g. svn://mydomain.com/repo"))

        self.chk_sparse = QCheckBox(self.tr("Enable Jailing (Vendor Sparse Checkout)"))
        self.chk_sparse.setStyleSheet("color: #F8FAFC; font-weight: bold;")
        self.chk_sparse.setCursor(Qt.PointingHandCursor)

        layout.addRow(self._styled_label(self.tr("Active VCS Engine:")), self.combo_vcs)
        layout.addRow(self._styled_label(self.tr("Root Repository URL:")), self.entry_repo_url)
        layout.addRow("", self.chk_sparse)

    def _build_tab_topografia(self):
        layout = QFormLayout(self.tab_topo)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lbl_desc = QLabel(self.tr("Map Blender Studio Tool's core logic to your custom naming conventions.\nThe Hub relies on VFS Keys, allowing you to use numerical prefixes safely."))
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 12px; margin-bottom: 10px;")
        layout.addRow("", lbl_desc)

        # Core VFS Variables
        self.entry_topo_svn = self._crear_input(self.tr("e.g. 02_production (Maps to 'svn')"))
        self.entry_topo_shared = self._crear_input(self.tr("e.g. 04_shared_data (Maps to 'shared')"))
        self.entry_topo_local = self._crear_input(self.tr("e.g. 06_local_cache (Maps to 'local')"))
        self.entry_topo_pipeline = self._crear_input(self.tr("e.g. 05_studio_config (Maps to 'pipeline')"))

        layout.addRow(self._styled_label(self.tr("Active Workspace [vfs_svn]:")), self.entry_topo_svn)
        layout.addRow(self._styled_label(self.tr("NAS Cache / Refs [vfs_shared]:")), self.entry_topo_shared)
        layout.addRow(self._styled_label(self.tr("Sandbox Cache [vfs_local]:")), self.entry_topo_local)
        layout.addRow(self._styled_label(self.tr("Hub Database [vfs_pipeline]:")), self.entry_topo_pipeline)

        # Custom Studio Folders
        lbl_custom = QLabel(self.tr("Additional Organization Folders (NAS Only)"))
        lbl_custom.setStyleSheet("color: #F8FAFC; font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        layout.addRow("", lbl_custom)

        self.entry_topo_custom1 = self._crear_input(self.tr("e.g. 01_Brief_and_Refs"))
        self.entry_topo_custom2 = self._crear_input(self.tr("e.g. 03_renders"))

        layout.addRow(self._styled_label(self.tr("Custom Folder 1:")), self.entry_topo_custom1)
        layout.addRow(self._styled_label(self.tr("Custom Folder 2:")), self.entry_topo_custom2)

    def _styled_label(self, texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 13px;")
        return lbl

    # ---------------------------------------------------------
    # DATA LOGIC & ACTIONS
    # ---------------------------------------------------------

    def _cargar_datos_actuales(self):
        self._is_loading = True
        raw = self.config_factory.get_raw_config()
        vcs = raw.get("vcs_engine", {})
        topo = raw.get("project_topography", {})
        
        # Identity
        self.entry_studio_name.setText(raw.get("studio_profile", {}).get("name", ""))
        self.entry_kitsu_url.setText(raw.get("kitsu_production", {}).get("api_url", ""))
        
        # Mapeo Desacoplado VFS
        lw_root = vcs.get("local_workspace_root", {})
        projects_path = lw_root.get("windows") or lw_root.get("linux") or lw_root.get("macos") or ""
        self.entry_projects_path.setText(projects_path)

        try:
            self.entry_vault_path.setText(str(self.config_factory.get_workspace_root() / "openstudio_vault"))
        except Exception:
            pass

        # VCS
        vcs_adapter = vcs.get("active_adapter", "svn")
        idx = self.combo_vcs.findText(vcs_adapter)
        if idx >= 0: self.combo_vcs.setCurrentIndex(idx)
        
        self.entry_repo_url.setText(vcs.get("repository_url", ""))
        self.chk_sparse.setChecked(vcs.get("enable_vendor_sparse_checkout", True))

        # Topography (Defaults to Blender Studio names if missing)
        self.entry_topo_svn.setText(topo.get("vfs_svn", "svn"))
        self.entry_topo_shared.setText(topo.get("vfs_shared", "shared"))
        self.entry_topo_local.setText(topo.get("vfs_local", "local"))
        self.entry_topo_pipeline.setText(topo.get("vfs_pipeline", "pipeline"))
        
        custom_dirs = topo.get("custom_dirs", [])
        if len(custom_dirs) > 0: self.entry_topo_custom1.setText(custom_dirs[0])
        if len(custom_dirs) > 1: self.entry_topo_custom2.setText(custom_dirs[1])
        
        self.lbl_unsaved_warning.setText("")
        self._is_loading = False

    def _seleccionar_proyectos(self):
        start_dir = QDir.homePath()
        actual = self.entry_projects_path.text()
        if actual and Path(actual).exists():
            start_dir = actual
            
        dir_path = QFileDialog.getExistingDirectory(self, self.tr("Select Projects Root Directory"), start_dir)
        if dir_path:
            self.entry_projects_path.setText(dir_path)
            if not self.entry_vault_path.text():
                self.entry_vault_path.setText(str(Path(dir_path) / "openstudio_vault"))

    def _seleccionar_boveda(self):
        start_dir = QDir.homePath()
        actual = self.entry_vault_path.text()
        proj_dir = self.entry_projects_path.text()
        
        if actual and Path(actual).exists():
            start_dir = str(Path(actual).parent)
        elif proj_dir and Path(proj_dir).exists():
            start_dir = proj_dir
            
        dir_path = QFileDialog.getExistingDirectory(self, self.tr("Select NAS Root (Vault)"), start_dir)
        if dir_path:
            chosen_path = Path(dir_path)
            if chosen_path.name != "openstudio_vault":
                chosen_path = chosen_path / "openstudio_vault"
                
            self.entry_vault_path.setText(str(chosen_path))

    def _seleccionar_hero_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select Studio Hero Image"), "", self.tr("Images (*.png *.jpg *.jpeg)")
        )
        if file_path:
            self.entry_hero_image.setText(file_path)
            self._pending_hero_image_path = Path(file_path)
            self._on_field_modified()

    def _ejecutar_sincronizacion_identidad(self):
        self.btn_sync_identity.setEnabled(False)
        self.btn_sync_identity.setText(self.tr("Syncing..."))
        self.status_callback(self.tr("Connecting to Kitsu to pull production profile..."), "yellow")

        url = self.entry_kitsu_url.text().strip()
        if url:
            self.auth_manager.set_host(url)

        self.sync_worker = SyncIdentityWorker(self.auth_manager)
        self.sync_worker.finished_sync.connect(self._on_sync_identity_finished)
        self.sync_worker.finished.connect(self.sync_worker.deleteLater)
        self.sync_worker.start()

    def _on_sync_identity_finished(self, identity_data: dict):
        self.btn_sync_identity.setEnabled(True)
        self.btn_sync_identity.setText(self.tr("Sync from Kitsu"))
        
        if identity_data and "name" in identity_data:
            self.entry_studio_name.setText(identity_data["name"])
            self.status_callback(self.tr("✓ Studio identity synchronized from Kitsu successfully."), "green")
        else:
            self.status_callback(self.tr("✗ Failed to sync identity. Verify API URL or network connection."), "red")

    def _recopilar_payload(self) -> dict:
        projects_dir = self.entry_projects_path.text().strip()
        
        custom_dirs = []
        if self.entry_topo_custom1.text().strip(): custom_dirs.append(self.entry_topo_custom1.text().strip())
        if self.entry_topo_custom2.text().strip(): custom_dirs.append(self.entry_topo_custom2.text().strip())

        # Topography always guarantees the logical mapping variables.
        # Fallback to Blender Studio conventions if fields are maliciously left blank.
        return {
            "studio_profile": {
                "name": self.entry_studio_name.text().strip()
            },
            "kitsu_production": {
                "api_url": self.entry_kitsu_url.text().strip()
            },
            "project_topography": {
                "vfs_svn": self.entry_topo_svn.text().strip() or "svn",
                "vfs_shared": self.entry_topo_shared.text().strip() or "shared",
                "vfs_local": self.entry_topo_local.text().strip() or "local",
                "vfs_pipeline": self.entry_topo_pipeline.text().strip() or "pipeline",
                "custom_dirs": custom_dirs
            },
            "vcs_engine": {
                "active_adapter": self.combo_vcs.currentText(),
                "repository_url": self.entry_repo_url.text().strip(),
                "enable_vendor_sparse_checkout": self.chk_sparse.isChecked(),
                "local_workspace_root": {
                    "windows": projects_dir,
                    "linux": projects_dir,
                    "macos": projects_dir
                }
            }
        }

    def _guardar_configuracion(self):
        # 1. Copiar Hero Image si el usuario seleccionó una nueva
        if self._pending_hero_image_path and self._pending_hero_image_path.exists():
            try:
                dest_path = Path("assets/login_hero.png")
                # Crear dir assets/ si no existe
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self._pending_hero_image_path, dest_path)
                self.entry_hero_image.clear()
                self._pending_hero_image_path = None
            except Exception as e:
                self.status_callback(self.tr("⚠️ Settings saved, but failed to apply Hero Image: {0}").format(e), "yellow")

        # 2. Guardar JSON
        payload = self._recopilar_payload()
        exito = self.config_factory.guardar_configuracion(payload)
        
        if exito:
            self.lbl_unsaved_warning.setText("")
            self.status_callback(self.tr("✓ Local settings saved successfully."), "green")
        else:
            self.status_callback(self.tr("✗ Critical error writing settings to disk."), "red")

    def _exportar_semilla_estudio(self):
        payload = self._recopilar_payload()
        dest_dir = QFileDialog.getExistingDirectory(self, self.tr("Select Destination Directory for Seed File"), QDir.homePath())
        
        if dest_dir:
            self.status_callback(self.tr("Encrypting and exporting Studio Seed..."), "yellow")
            exito, mensaje = self.config_factory.exportar_semilla(payload, Path(dest_dir))
            
            if exito:
                self.status_callback(self.tr("✓ Seed exported successfully: {0}").format(mensaje), "green")
            else:
                self.status_callback(self.tr("✗ Export failed: {0}").format(mensaje), "red")
