# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_settings.py
# Rol Arquitectónico: UI Orchestrator / Global Settings Container (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.6.2 (Strict Dependency Injection Overhaul)
# =========================================================================================

"""
Global Configuration Panel for the Technical Director.
Groups decoupled molecular sub-tabs (Identity, Vault, VCS, Topography, Software).
Coordinates atomic payload assembly and routes data via ConfigFactory and VaultManager.
"""

import shutil
from pathlib import Path
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTabWidget, QFileDialog)
from PySide6.QtCore import Qt, QDir

# Importación de sub-pestañas modulares moleculares
from ui.settings_tabs.tab_identity import TabIdentity
from ui.settings_tabs.tab_vault import TabVault
from ui.settings_tabs.tab_vcs import TabVCS
from ui.settings_tabs.tab_topography import TabTopography
from ui.settings_tabs.tab_software import TabSoftware

# Importación del gestor de servicios del dominio
from core.vault_manager import VaultManager


class SettingsWidget(QFrame):
    def __init__(self, parent, config_factory, auth_manager, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.config_factory = config_factory
        self.auth_manager = auth_manager
        self.status_callback = status_callback
        
        # Canal unificado de servicios para el inventario de software
        self.vault_manager = VaultManager(self.config_factory)
        
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

        # Instanciación de Sub-Vistas Moleculares (Asignación limpia de responsabilidades)
        self.tab_identidad = TabIdentity(self.auth_manager, self.status_callback, parent=self.tabs)
        self.tab_boveda = TabVault(parent=self.tabs)
        self.tab_vcs = TabVCS(parent=self.tabs)
        self.tab_topo = TabTopography(parent=self.tabs)
        
        # CORRECCIÓN DE INYECCIÓN DE DEPENDENCIAS
        self.tab_software = TabSoftware(
            parent=self.tabs,
            vault_manager=self.vault_manager,
            status_callback=self.status_callback
        )

        # Enlace de pestañas al Tab Container
        self.tabs.addTab(self.tab_identidad, self.tr("Identity & API"))
        self.tabs.addTab(self.tab_boveda, self.tr("Vault Storage"))
        self.tabs.addTab(self.tab_vcs, self.tr("Pipeline & VCS"))
        self.tabs.addTab(self.tab_topo, self.tr("Project Topography"))
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

    def _conectar_senales_cambio(self):
        """Mapea las señales reactivas de las pestañas hijas hacia la alerta visual del Orquestador."""
        self.tab_identidad.modified.connect(self._on_field_modified)
        self.tab_boveda.modified.connect(self._on_field_modified)
        self.tab_vcs.modified.connect(self._on_field_modified)
        self.tab_topo.modified.connect(self._on_field_modified)
        self.tab_software.modified.connect(self._on_field_modified)

    def _on_field_modified(self):
        self.lbl_unsaved_warning.setText(self.tr("● Unsaved Changes"))
        self.lbl_unsaved_warning.setStyleSheet("color: #F59E0B; font-weight: bold; font-size: 13px; margin-left: 15px;")

    # ---------------------------------------------------------
    # ORCHESTRATION LOGIC (Data-Down, Actions-Up)
    # ---------------------------------------------------------

    def _cargar_datos_actuales(self):
        """Pide datos a los Singletons de Dominio y los distribuye hacia abajo (Data-Down)."""
        raw = self.config_factory.get_raw_config()
        vcs = raw.get("vcs_engine", {})
        topo = raw.get("project_topography", {})
        
        # 1. Hidratar Identidad y API
        self.tab_identidad.cargar_datos(raw)
        
        # 2. Hidratar Almacenamiento y Rutas
        projects_path = vcs.get("local_workspace_root", {}).get(self.config_factory._get_current_os(), "")
        if not projects_path:
            projects_path = str(self.config_factory.get_workspace_root())
            
        vault_path = str(self.config_factory.get_vault_path())
        self.tab_boveda.cargar_datos(projects_path, vault_path)

        # 3. Hidratar Control de Versiones (VCS) con Credenciales Override
        active_adapter = vcs.get("active_adapter", "svn")
        repo_url = vcs.get("repository_url", "")
        enable_sparse = vcs.get("enable_vendor_sparse_checkout", True)
        vcs_user = vcs.get("vcs_username", "")
        vcs_pwd = vcs.get("vcs_password", "")
        
        self.tab_vcs.cargar_datos(active_adapter, repo_url, enable_sparse, vcs_user, vcs_pwd)

        # 4. Hidratar Topografía Semántica
        self.tab_topo.cargar_datos(topo)
        
        # 5. Hidratar Catálogo de Software Compartido
        manifest_data = self.vault_manager.cargar_inventario()
        self.tab_software.cargar_datos(manifest_data)
        
        self.lbl_unsaved_warning.setText("")

    def _recopilar_payload(self) -> dict:
        """Solicita a cada subcomponente su diccionario y empaqueta un JSON unificado."""
        payload = {}
        
        # Fusionar diccionarios de las sub-vistas
        payload.update(self.tab_identidad.get_identity_payload())
        payload.update(self.tab_vcs.get_vcs_payload())
        payload.update(self.tab_topo.get_topography_payload())
        
        # Procesar almacenamiento e inyectar mapeo Multi-OS compatible
        vault_data = self.tab_boveda.get_vault_payload()
        projects_dir = vault_data.get("vcs_engine", {}).get("local_workspace_root", "")
        
        payload["infrastructure_topology"] = vault_data.get("infrastructure_topology", {})
        payload["vcs_engine"].update({
            "local_workspace_root": {
                "windows": projects_dir,
                "linux": projects_dir,
                "macos": projects_dir
            }
        })
        
        return payload

    def _guardar_configuracion(self):
        # 1. Aplicar Hero Image si existe una ruta pendiente en el componente de identidad
        if self.tab_identidad.pending_hero_image_path and self.tab_identidad.pending_hero_image_path.exists():
            try:
                dest_path = Path("assets/login_hero.png")
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.tab_identidad.pending_hero_image_path, dest_path)
                self.tab_identidad.entry_hero_image.clear()
                self.tab_identidad.pending_hero_image_path = None
            except Exception as e:
                self.status_callback(self.tr("⚠️ Settings saved, but failed to apply Hero Image: {0}").format(e), "yellow")

        # 2. Persistir payload de configuración local (settings.json)
        payload = self._recopilar_payload()
        exito_config = self.config_factory.guardar_configuracion(payload)
        
        # 3. Persistir payload del manifiesto del software compartido en el NAS (vault_manifest.json)
        software_payload = self.tab_software.get_software_payload()
        exito_vault = self.vault_manager.guardar_inventario(software_payload)
        
        if exito_config and exito_vault:
            self.lbl_unsaved_warning.setText("")
            self.status_callback(self.tr("✓ Local settings and Network Manifest saved successfully."), "green")
            self._cargar_datos_actuales()
        else:
            if not exito_config:
                self.status_callback(self.tr("✗ Critical error writing settings.json to local disk."), "red")
            if not exito_vault:
                self.status_callback(self.tr("✗ Network write error: Could not publish vault_manifest.json to the NAS."), "red")

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
