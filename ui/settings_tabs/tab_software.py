# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/settings_tabs/tab_software.py
# Rol Arquitectónico: UI Component / Manifest View & Local Provisioning
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.5.0 (UI Pure Decoupling & ZIP Parsing)
# =========================================================================================

"""
Sub-vista de configuración purificada. Centraliza los controles en la tabla de la Bóveda.
Los checkboxes ahora interactúan directamente en la tabla y se permite cargar archivos 
.zip locales leyendo sus propiedades automáticamente.
"""

import re
import shutil
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPushButton, QTreeWidget, QTreeWidgetItem, 
                               QFrame, QProgressBar, QFileDialog)
from PySide6.QtCore import Qt, Signal

# Importación de la lógica separada del Core
from core.addon_inspector import AddonInspector
from core.provisioning_workers import (RepoFolderFetcherWorker, RepoFileFetcherWorker, 
                                       BlenderDirectDownloadWorker, StudioToolsFetchWorker)


class TabSoftware(QWidget):
    modified = Signal()

    def __init__(self, parent, vault_manager, status_callback):
        super().__init__(parent)
        self._is_loading = True
        self.vault_manager = vault_manager
        self.status_callback = status_callback
        self.manifest_data = {}
        
        self._folder_worker = None
        self._file_worker = None
        self._download_worker = None
        self._fetch_worker = None

        self._build_ui()
        self._conectar_crawler_inicial()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        # -----------------------------------------------------------------------------
        # 1. EXPLORADOR REMOTO
        # -----------------------------------------------------------------------------
        repo_browser_frame = QFrame()
        repo_browser_frame.setStyleSheet("background-color: #1E293B; border-radius: 6px; border: 1px solid #334155;")
        browser_layout = QVBoxLayout(repo_browser_frame)
        browser_layout.setContentsMargins(15, 15, 15, 15)

        lbl_section_title = QLabel(self.tr("🌐 Official Remote Repository Explorer (download.blender.org)"))
        lbl_section_title.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 13px; border: none; margin-bottom: 5px;")
        browser_layout.addWidget(lbl_section_title)

        selectors_layout = QHBoxLayout()
        
        lbl_rem_folder = QLabel(self.tr("Folder:"))
        lbl_rem_folder.setStyleSheet("color: #94A3B8; border: none; font-weight: bold;")
        selectors_layout.addWidget(lbl_rem_folder)

        self.combo_remote_folders = QComboBox()
        self.combo_remote_folders.setFixedHeight(35)
        self.combo_remote_folders.setFixedWidth(150)
        self.combo_remote_folders.setStyleSheet("QComboBox { background-color: #0F172A; color: white; border: 1px solid #475569; padding-left: 5px; }")
        self.combo_remote_folders.currentTextChanged.connect(self._on_remote_folder_changed)
        selectors_layout.addWidget(self.combo_remote_folders)

        lbl_rem_file = QLabel(self.tr("Package:"))
        lbl_rem_file.setStyleSheet("color: #94A3B8; border: none; font-weight: bold; margin-left: 10px;")
        selectors_layout.addWidget(lbl_rem_file)

        self.combo_remote_files = QComboBox()
        self.combo_remote_files.setFixedHeight(35)
        self.combo_remote_files.setStyleSheet("QComboBox { background-color: #0F172A; color: white; border: 1px solid #475569; padding-left: 5px; }")
        selectors_layout.addWidget(self.combo_remote_files, stretch=1)

        btn_refresh_repo = QPushButton(self.tr("🔄 Sync"))
        btn_refresh_repo.setObjectName("SecondaryButton")
        btn_refresh_repo.setFixedSize(80, 35)
        btn_refresh_repo.clicked.connect(self._conectar_crawler_inicial)
        selectors_layout.addWidget(btn_refresh_repo)

        browser_layout.addLayout(selectors_layout)

        buttons_layout = QHBoxLayout()
        self.btn_download_official = QPushButton(self.tr("📥 Download Selected Package to Vault"))
        self.btn_download_official.setStyleSheet("background-color: #4F46E5; color: white; font-weight: bold; border-radius: 6px; border: none;")
        self.btn_download_official.setFixedHeight(35)
        self.btn_download_official.clicked.connect(self._disparar_descarga_blender)
        buttons_layout.addWidget(self.btn_download_official, stretch=1)

        browser_layout.addLayout(buttons_layout)
        main_layout.addWidget(repo_browser_frame)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background-color: #0F172A; border: none; } QProgressBar::chunk { background-color: #10B981; }")
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # -----------------------------------------------------------------------------
        # 2. EDITOR DEL MANIFIESTO DE SOFTWARE Y HERRAMIENTAS
        # -----------------------------------------------------------------------------
        manifest_frame = QFrame()
        manifest_frame.setStyleSheet("background-color: transparent;")
        manifest_layout = QVBoxLayout(manifest_frame)
        manifest_layout.setContentsMargins(0, 10, 0, 0)

        # Barra de Control de Tabla Integrada
        control_layout = QHBoxLayout()
        lbl_active_v = QLabel(self.tr("Target Context (Active Blender Version):"))
        lbl_active_v.setStyleSheet("color: #10B981; font-weight: bold; font-size: 14px;")
        control_layout.addWidget(lbl_active_v)

        self.combo_versions = QComboBox()
        self.combo_versions.setFixedHeight(35)
        self.combo_versions.setFixedWidth(120)
        self.combo_versions.setStyleSheet("QComboBox { background-color: #1E293B; color: white; border: 1px solid #475569; padding-left: 5px; font-weight: bold; }")
        self.combo_versions.currentTextChanged.connect(self._redibujar_arbol_componentes)
        control_layout.addWidget(self.combo_versions)

        control_layout.addStretch()

        self.btn_fetch_studio_tools = QPushButton(self.tr("🚀 Auto-Fetch Blender Studio Tools"))
        self.btn_fetch_studio_tools.setStyleSheet("background-color: #06B6D4; color: white; font-weight: bold; border-radius: 6px; border: none;")
        self.btn_fetch_studio_tools.setFixedSize(250, 35)
        self.btn_fetch_studio_tools.clicked.connect(self._disparar_fetch_studio_tools)
        control_layout.addWidget(self.btn_fetch_studio_tools)

        manifest_layout.addLayout(control_layout)

        # Tabla del Manifiesto interactiva
        self.tree_manifest = QTreeWidget()
        self.tree_manifest.setColumnCount(4)
        self.tree_manifest.setHeaderLabels([self.tr("Component / Addon"), self.tr("Version"), self.tr("Description"), self.tr("Mandatory")])
        self.tree_manifest.setColumnWidth(0, 220)
        self.tree_manifest.setColumnWidth(1, 80)
        self.tree_manifest.setColumnWidth(2, 350)
        self.tree_manifest.setStyleSheet("""
            QTreeWidget { background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; color: #F8FAFC; }
            QHeaderView::section { background-color: #0F172A; color: #94A3B8; font-weight: bold; padding: 5px; border: 1px solid #334155; }
        """)
        self.tree_manifest.itemChanged.connect(self._on_tree_item_changed)
        manifest_layout.addWidget(self.tree_manifest, stretch=1)

        # Inyector de ZIP Locales
        inject_layout = QHBoxLayout()
        self.btn_load_local_zip = QPushButton(self.tr("📂 Add / Load Local .zip Addon"))
        self.btn_load_local_zip.setObjectName("SecondaryButton")
        self.btn_load_local_zip.setFixedHeight(35)
        self.btn_load_local_zip.clicked.connect(self._inyectar_zip_local)
        inject_layout.addWidget(self.btn_load_local_zip)
        
        inject_layout.addStretch()
        manifest_layout.addLayout(inject_layout)

        main_layout.addWidget(manifest_frame, stretch=1)

    def _on_field_modified(self):
        if not self._is_loading:
            self.modified.emit()

    # ---------------------------------------------------------
    # RENDER Y EDICIÓN INTERACTIVA DEL ÁRBOL
    # ---------------------------------------------------------

    def _redibujar_arbol_componentes(self):
        self.tree_manifest.blockSignals(True)
        self.tree_manifest.clear()
        version_activa = self.combo_versions.currentText()
        
        if not version_activa or version_activa not in self.manifest_data:
            self.tree_manifest.blockSignals(False)
            return

        bloque_categorias = self.manifest_data[version_activa]
        
        for cat_name, items in bloque_categorias.items():
            cat_item = QTreeWidgetItem(self.tree_manifest)
            cat_item.setText(0, f"{cat_name.upper()}")
            cat_item.setForeground(0, Qt.green)
            cat_item.setExpanded(True)
            
            for item_name, data in items.items():
                child = QTreeWidgetItem(cat_item)
                child.setText(0, item_name)
                child.setText(1, str(data.get("version", "1.0")))
                child.setText(2, data.get("description", ""))
                
                # Checkbox interactivo en la columna 3
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(3, Qt.Checked if data.get("mandatory", False) else Qt.Unchecked)
                
                # Guardar info en los UserRoles para poder actualizar el dict al hacer click
                child.setData(0, Qt.UserRole, cat_name)
                child.setData(1, Qt.UserRole, item_name)

        self.tree_manifest.blockSignals(False)

    def _on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        """Atrapa el click del usuario en el checkbox Mandatory y actualiza el dict en caliente."""
        if column == 3:
            cat_name = item.data(0, Qt.UserRole)
            item_name = item.data(1, Qt.UserRole)
            version_activa = self.combo_versions.currentText()
            
            if cat_name and item_name and version_activa in self.manifest_data:
                is_checked = (item.checkState(3) == Qt.Checked)
                self.manifest_data[version_activa][cat_name][item_name]["mandatory"] = is_checked
                self._on_field_modified()

    # ---------------------------------------------------------
    # OPERACIONES AUTOMATIZADAS
    # ---------------------------------------------------------

    def _conectar_crawler_inicial(self):
        self._folder_worker = RepoFolderFetcherWorker()
        self._folder_worker.folders_ready.connect(self._on_remote_folders_loaded)
        self._folder_worker.status.connect(self.status_callback)
        self._folder_worker.start()

    def _on_remote_folders_loaded(self, folder_list: list):
        self.combo_remote_folders.blockSignals(True)
        self.combo_remote_folders.clear()
        self.combo_remote_folders.addItems(folder_list)
        self.combo_remote_folders.blockSignals(False)
        
        if self._folder_worker:
            self._folder_worker.deleteLater()
            self._folder_worker = None
        
        if folder_list:
            self._on_remote_folder_changed(self.combo_remote_folders.currentText())

    def _on_remote_folder_changed(self, target_folder: str):
        if not target_folder: return
        if self._file_worker and self._file_worker.isRunning():
            self._file_worker.terminate()

        self._file_worker = RepoFileFetcherWorker(target_folder)
        self._file_worker.files_ready.connect(self._on_remote_files_loaded)
        self._file_worker.status.connect(self.status_callback)
        self._file_worker.start()

    def _on_remote_files_loaded(self, file_list: list):
        self.combo_remote_files.clear()
        self.combo_remote_files.addItems(file_list)
        if self._file_worker:
            self._file_worker.deleteLater()
            self._file_worker = None

    def _disparar_descarga_blender(self):
        folder = self.combo_remote_folders.currentText()
        filename = self.combo_remote_files.currentText()

        if not folder or not filename:
            return

        vault_root = self.vault_manager.manifest_path.parent
        blender_target_dir = vault_root / "blender_versions"

        self.btn_download_official.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self._download_worker = BlenderDirectDownloadWorker(folder, filename, blender_target_dir)
        self._download_worker.progress.connect(self.progress_bar.setValue)
        self._download_worker.status.connect(self.status_callback)
        self._download_worker.finished.connect(self._on_direct_download_finished)
        self._download_worker.start()

    def _on_direct_download_finished(self, exito: bool, filename: str):
        self.btn_download_official.setEnabled(True)
        self.progress_bar.hide()

        if exito and filename:
            match = re.search(r'blender-(\d+\.\d+\.\d+)', filename.lower())
            detected_version = match.group(1) if match else "4.2.0"
            
            if detected_version not in self.manifest_data:
                self.manifest_data[detected_version] = {"addons": {}, "templates": {}}
                self.combo_versions.blockSignals(True)
                self.combo_versions.clear()
                self.combo_versions.addItems(list(self.manifest_data.keys()))
                self.combo_versions.setCurrentText(detected_version)
                self.combo_versions.blockSignals(False)
                self._redibujar_arbol_componentes()
                self._on_field_modified()

        if self._download_worker:
            self._download_worker.deleteLater()
            self._download_worker = None

    def _disparar_fetch_studio_tools(self):
        version = self.combo_versions.currentText()
        if not version:
            return

        vault_root = self.vault_manager.manifest_path.parent
        templates_target_dir = vault_root / "project_templates"

        self.btn_fetch_studio_tools.setEnabled(False)

        self._fetch_worker = StudioToolsFetchWorker(version, templates_target_dir)
        self._fetch_worker.status.connect(self.status_callback)
        self._fetch_worker.finished.connect(self._on_studio_tools_finished)
        self._fetch_worker.start()

    def _on_studio_tools_finished(self, exito: bool, herramientas: dict):
        self.btn_fetch_studio_tools.setEnabled(True)
        if exito and herramientas:
            version_activa = self.combo_versions.currentText()
            self.manifest_data[version_activa].update(herramientas)
            self._redibujar_arbol_componentes()
            self._on_field_modified()
            
        if self._fetch_worker:
            self._fetch_worker.deleteLater()
            self._fetch_worker = None

    # ---------------------------------------------------------
    # OPERACIÓN MANUAL: CARGA DE ZIP
    # ---------------------------------------------------------

    def _inyectar_zip_local(self):
        version_activa = self.combo_versions.currentText()
        if not version_activa:
            self.status_callback(self.tr("✗ Please select a Target Context (Blender Version) first."), "yellow")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Select Addon .zip"), "", "ZIP Files (*.zip)")
        if not file_path:
            return

        zip_path = Path(file_path)
        meta = AddonInspector.inspect_zip(zip_path)

        if not meta or meta["name"] == "unknown_addon":
            self.status_callback(self.tr("✗ Invalid Addon: No blender_manifest.toml or bl_info found inside ZIP."), "red")
            return

        addon_name = meta["name"]
        addon_ver = meta["version"]
        desc = meta["description"]

        # Copiar y renombrar a la Bóveda con la convención estricta {nombre}-{version}.zip
        vault_root = self.vault_manager.manifest_path.parent
        addons_dir = vault_root / "addons"
        addons_dir.mkdir(parents=True, exist_ok=True)
        
        target_zip_name = f"{addon_name}-{addon_ver}.zip"
        target_zip_path = addons_dir / target_zip_name
        
        if not target_zip_path.exists():
            shutil.copy2(zip_path, target_zip_path)
            self.status_callback(self.tr("✓ Addon '{0}' imported to Vault successfully.").format(target_zip_name), "green")
        else:
            self.status_callback(self.tr("• Addon '{0}' already exists in Vault. Cache utilized.").format(target_zip_name), "yellow")

        if "addons" not in self.manifest_data[version_activa]:
            self.manifest_data[version_activa]["addons"] = {}

        self.manifest_data[version_activa]["addons"][addon_name] = {
            "version": addon_ver,
            "description": desc[:60] + "..." if len(desc) > 60 else desc,
            "mandatory": False,
            "requires": []
        }

        self._redibujar_arbol_componentes()
        self._on_field_modified()

    # ---------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------

    def cargar_datos(self, manifest_config: dict):
        self._is_loading = True
        self.manifest_data = {}

        for key, val in manifest_config.items():
            if isinstance(val, dict):
                raw_version = val.get("blender_version") or key
                clean_version = str(raw_version).lstrip("vV ")
                
                categories_block = val.get("categories") if "categories" in val else val
                if isinstance(categories_block, dict):
                    self.manifest_data[clean_version] = categories_block

        self.combo_versions.blockSignals(True)
        self.combo_versions.clear()
        self.combo_versions.addItems(list(self.manifest_data.keys()))
        self.combo_versions.blockSignals(False)
        
        self._redibujar_arbol_componentes()
        self._is_loading = False

    def get_software_payload(self) -> dict:
        full_payload = {}
        for version, categories in self.manifest_data.items():
            full_payload[version] = {
                "blender_version": version,
                "categories": categories
            }
        return full_payload
