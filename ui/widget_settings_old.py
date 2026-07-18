# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_settings.py
# Rol Arquitectónico: UI Component / Global Settings & Seed Generator (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.1.0
# =========================================================================================

"""
Global Configuration Panel for the Technical Director.
Groups B2B settings into logical tabs (Identity, Vault, VCS)
and exposes the dispatcher to generate the Studio Seed (.seed).
Now implementing Qt Native i18n via tr().
"""

from pathlib import Path
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QWidget, QLineEdit, QTabWidget,
                               QComboBox, QCheckBox, QFormLayout, QFileDialog)
from PySide6.QtCore import Qt, QDir

class SettingsWidget(QFrame):
    def __init__(self, parent, config_factory, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.config_factory = config_factory
        self.status_callback = status_callback
        
        self.setObjectName("SettingsWidgetBase")
        self.setStyleSheet("background: transparent;")
        
        self._build_ui()
        self._cargar_datos_actuales()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # HEADER
        header_layout = QHBoxLayout()
        lbl_title = QLabel(self.tr("Global Studio Settings"))
        lbl_title.setObjectName("H2Title")
        header_layout.addWidget(lbl_title)
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

    def _build_tab_identidad(self):
        layout = QFormLayout(self.tab_identidad)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.entry_studio_name = self._crear_input(self.tr("e.g. Macuare Studio"))
        self.entry_kitsu_url = self._crear_input(self.tr("e.g. https://kitsu.mydomain.com/api"))

        layout.addRow(self._styled_label(self.tr("Studio Name:")), self.entry_studio_name)
        layout.addRow(self._styled_label(self.tr("Kitsu API URL:")), self.entry_kitsu_url)

    def _build_tab_boveda(self):
        layout = QFormLayout(self.tab_boveda)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        path_layout = QHBoxLayout()
        self.entry_vault_path = self._crear_input(self.tr("e.g. Z:/openstudio_vault"))
        self.entry_vault_path.setReadOnly(True)
        path_layout.addWidget(self.entry_vault_path)

        btn_browse = QPushButton(self.tr("Browse..."))
        btn_browse.setObjectName("SecondaryButton")
        btn_browse.setFixedSize(90, 35)
        btn_browse.clicked.connect(self._seleccionar_boveda)
        path_layout.addWidget(btn_browse)

        layout.addRow(self._styled_label(self.tr("Vault Directory:")), path_layout)

        lbl_desc = QLabel(self.tr("Physical path on the NAS for installers and templates.\nIt must be isolated from the project repository folder."))
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
        self.entry_prod_folder = self._crear_input(self.tr("e.g. svn or 02_production_files"))

        self.chk_sparse = QCheckBox(self.tr("Enable Jailing (Vendor Sparse Checkout)"))
        self.chk_sparse.setStyleSheet("color: #F8FAFC; font-weight: bold;")
        self.chk_sparse.setCursor(Qt.PointingHandCursor)

        layout.addRow(self._styled_label(self.tr("Active VCS Engine:")), self.combo_vcs)
        layout.addRow(self._styled_label(self.tr("Root Repository URL:")), self.entry_repo_url)
        layout.addRow(self._styled_label(self.tr("Local Production Folder:")), self.entry_prod_folder)
        layout.addRow("", self.chk_sparse)

    def _styled_label(self, texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 13px;")
        return lbl

    # ---------------------------------------------------------
    # DATA LOGIC & ACTIONS
    # ---------------------------------------------------------

    def _cargar_datos_actuales(self):
        raw = self.config_factory.get_raw_config()
        
        # Identity
        self.entry_studio_name.setText(raw.get("studio_profile", {}).get("name", ""))
        self.entry_kitsu_url.setText(raw.get("kitsu_production", {}).get("api_url", ""))
        
        # Vault
        try:
            self.entry_vault_path.setText(str(self.config_factory.get_workspace_root() / "openstudio_vault"))
        except Exception:
            pass

        # VCS
        vcs = raw.get("vcs_engine", {})
        vcs_adapter = vcs.get("active_adapter", "svn")
        idx = self.combo_vcs.findText(vcs_adapter)
        if idx >= 0: self.combo_vcs.setCurrentIndex(idx)
        
        self.entry_repo_url.setText(vcs.get("repository_url", ""))
        self.entry_prod_folder.setText(vcs.get("production_folder_name", "svn"))
        self.chk_sparse.setChecked(vcs.get("enable_vendor_sparse_checkout", True))

    def _seleccionar_boveda(self):
        start_dir = QDir.homePath()
        actual = self.entry_vault_path.text()
        if actual and Path(actual).exists():
            start_dir = actual
            
        dir_path = QFileDialog.getExistingDirectory(self, self.tr("Select NAS Root (Vault)"), start_dir)
        if dir_path:
            self.entry_vault_path.setText(dir_path)

    def _recopilar_payload(self) -> dict:
        vault_raw = self.entry_vault_path.text().strip()
        nas_root = str(Path(vault_raw).parent) if vault_raw else ""

        return {
            "studio_profile": {
                "name": self.entry_studio_name.text().strip()
            },
            "kitsu_production": {
                "api_url": self.entry_kitsu_url.text().strip()
            },
            "vcs_engine": {
                "active_adapter": self.combo_vcs.currentText(),
                "repository_url": self.entry_repo_url.text().strip(),
                "production_folder_name": self.entry_prod_folder.text().strip(),
                "enable_vendor_sparse_checkout": self.chk_sparse.isChecked(),
                "local_workspace_root": {
                    "windows": nas_root,
                    "linux": nas_root,
                    "macos": nas_root
                }
            }
        }

    def _guardar_configuracion(self):
        """Envía el payload al backend para persistencia local en settings.json."""
        payload = self._recopilar_payload()
        exito = self.config_factory.guardar_configuracion(payload)
        
        if exito:
            self.status_callback(self.tr("✓ Local settings saved successfully."), "green")
        else:
            self.status_callback(self.tr("✗ Critical error writing settings to disk."), "red")

    def _exportar_semilla_estudio(self):
        """Invoca al motor criptográfico para empaquetar y exportar la configuración."""
        payload = self._recopilar_payload()
        
        # Pedirle al TD dónde quiere guardar el archivo
        dest_dir = QFileDialog.getExistingDirectory(self, self.tr("Select Destination Directory for Seed File"), QDir.homePath())
        
        if dest_dir:
            self.status_callback(self.tr("Encrypting and exporting Studio Seed..."), "yellow")
            exito, mensaje = self.config_factory.exportar_semilla(payload, Path(dest_dir))
            
            if exito:
                self.status_callback(self.tr("✓ Seed exported successfully: {0}").format(mensaje), "green")
            else:
                self.status_callback(self.tr("✗ Export failed: {0}").format(mensaje), "red")
