# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/project_card.py
# Rol Arquitectónico: UI Component / Reusable Project Card (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.9.0 (Controller Injection & Code Purge)
# =========================================================================================

"""
Componente visual reutilizable para las Tarjetas de Proyectos.
Actúa estrictamente como la capa de Presentación (View). Delega todas las operaciones
de red (HTTP/Gazu) al KitsuManager y las operaciones de disco (Shutil/JSON) al NasManager,
respetando el patrón MVC y el Principio de Responsabilidad Única.
"""

import subprocess
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QWidget, QToolButton, QMenu,
                               QDialog, QLineEdit, QMessageBox, QApplication)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QPixmap, QImage, QCursor, QAction, QDesktopServices

from core.kitsu_manager import KitsuManager
from core.nas_manager import NasManager


class ProjectThumbnailWorker(QThread):
    """QThread dedicado a la descarga HTTP asíncrona de los avatares de proyectos."""
    image_downloaded = Signal(bytes)
    error_occurred = Signal(str)

    def __init__(self, kitsu_manager: KitsuManager, project_id: str, token: str, host_url: str):
        super().__init__()
        self.kitsu_mgr = kitsu_manager
        self.project_id = project_id
        self.token = token
        self.host_url = host_url

    def run(self):
        img_bytes = self.kitsu_mgr.download_project_thumbnail(self.project_id, self.token, self.host_url)
        if img_bytes:
            self.image_downloaded.emit(img_bytes)
        else:
            self.error_occurred.emit("Sin miniatura")


class DeleteProjectDialog(QDialog):
    """Modal de Seguridad (Type-to-Delete) estilo GitHub."""
    def __init__(self, parent, project_name: str):
        super().__init__(parent)
        self.project_name = project_name
        self.setWindowTitle(self.tr("⚠️ Warning: Project Destruction"))
        self.setFixedSize(450, 220)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        lbl_warn = QLabel(self.tr("You are about to permanently delete the project:\n<b>{0}</b>\n\nThis action will destroy Kitsu data, the SVN repository, and local files.").format(self.project_name))
        lbl_warn.setWordWrap(True)
        lbl_warn.setStyleSheet("color: #EF4444; font-size: 13px;")
        layout.addWidget(lbl_warn)

        lbl_instruct = QLabel(self.tr("To confirm, type <b>{0}</b> below:").format(self.project_name))
        lbl_instruct.setStyleSheet("color: #94A3B8;")
        layout.addWidget(lbl_instruct)

        self.entry_confirm = QLineEdit()
        self.entry_confirm.setObjectName("FormInput")
        self.entry_confirm.setFixedHeight(35)
        self.entry_confirm.textChanged.connect(self._validar_input)
        layout.addWidget(self.entry_confirm)

        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton(self.tr("Cancel"))
        self.btn_cancel.setObjectName("SecondaryButton")
        self.btn_cancel.setFixedHeight(35)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_delete = QPushButton(self.tr("Permanently Delete"))
        self.btn_delete.setStyleSheet("background-color: #EF4444; color: white; font-weight: bold; border-radius: 6px;")
        self.btn_delete.setFixedHeight(35)
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

    def _validar_input(self, text: str):
        self.btn_delete.setEnabled(text == self.project_name)


class ProjectCard(QFrame):
    def __init__(self, parent: QWidget, project_data: dict, auth_manager, nextcloud_dir: Path, on_rebuild_callback: Callable = None):
        super().__init__(parent)
        
        self.project_data = project_data
        self.auth = auth_manager
        self.on_rebuild_callback = on_rebuild_callback
        
        # Instanciar Controladores
        self.kitsu_mgr = KitsuManager()
        self.nas_mgr = NasManager(nextcloud_dir)
        
        self.project_dir = None
        
        self.setObjectName("FloatingCard")
        self.setFixedSize(320, 280)
        
        self.setStyleSheet("""
            QFrame#FloatingCard {
                background-color: #1E293B;
                border-radius: 12px;
                border: 1px solid #334155;
            }
            QFrame#FloatingCard:hover {
                border: 1px solid #3B82F6;
            }
        """)

        self._build_ui()
        self._check_nas_status()
        self._cargar_miniatura()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # ---------------------------------------------------------
        # Fila 1: Cabecera (Estado del proyecto y Menú)
        # ---------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        project_status = self.project_data.get("project_status_name", self.tr("Active Project"))
        lbl_status = QLabel(project_status)
        lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(lbl_status)
        
        header_layout.addStretch()
        
        self.btn_options = QToolButton()
        self.btn_options.setText("⋮")
        self.btn_options.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_options.setStyleSheet("""
            QToolButton { background: transparent; color: #94A3B8; font-size: 20px; font-weight: bold; border: none; padding-bottom: 5px; }
            QToolButton:hover { color: #F8FAFC; }
            QToolButton::menu-indicator { image: none; }
        """)
        self.btn_options.setPopupMode(QToolButton.InstantPopup)
        
        self.options_menu = QMenu(self)
        self.options_menu.setStyleSheet("""
            QMenu { background-color: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; }
            QMenu::item { padding: 8px 25px; }
            QMenu::item:selected { background-color: #3B82F6; }
        """)
        
        action_kitsu_shots = QAction(self.tr("🎬 Edit Shots"), self)
        action_kitsu_breakdown = QAction(self.tr("📝 Script Breakdown"), self)
        action_kitsu_team = QAction(self.tr("👥 Manage Team"), self)
        action_kitsu_settings = QAction(self.tr("⚙️ Project Settings"), self)
        
        action_archive = QAction(self.tr("📦 Archive Project"), self)
        action_delete = QAction(self.tr("🗑️ Delete Project"), self)
        
        action_kitsu_shots.triggered.connect(lambda: self._abrir_ruta_kitsu("/shots"))
        action_kitsu_breakdown.triggered.connect(lambda: self._abrir_ruta_kitsu("/breakdown"))
        action_kitsu_team.triggered.connect(lambda: self._abrir_ruta_kitsu("/team"))
        action_kitsu_settings.triggered.connect(lambda: self._abrir_ruta_kitsu("/production-settings"))
        action_delete.triggered.connect(self._on_delete_requested)

        self.options_menu.addAction(action_kitsu_shots)
        self.options_menu.addAction(action_kitsu_breakdown)
        self.options_menu.addAction(action_kitsu_team)
        self.options_menu.addAction(action_kitsu_settings)
        self.options_menu.addSeparator()
        self.options_menu.addAction(action_archive)
        self.options_menu.addSeparator()
        self.options_menu.addAction(action_delete)

        self.btn_options.setMenu(self.options_menu)
        header_layout.addWidget(self.btn_options)
        main_layout.addLayout(header_layout)

        # ---------------------------------------------------------
        # Fila 2: Miniatura del Proyecto
        # ---------------------------------------------------------
        self.thumb_label = QLabel(self.tr("Loading thumbnail..."))
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setFixedHeight(140)
        self.thumb_label.setStyleSheet("background-color: #0F172A; border-radius: 8px; color: #475569; font-style: italic;")
        main_layout.addWidget(self.thumb_label)

        # ---------------------------------------------------------
        # Fila 3: Título del Proyecto y Badge Dinámico
        # ---------------------------------------------------------
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 5, 0, 0)
        
        project_name = self.project_data.get("name", self.tr("Unknown Project"))
        self.lbl_title = QLabel(project_name)
        self.lbl_title.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: bold;")
        title_layout.addWidget(self.lbl_title)
        
        title_layout.addStretch()
        
        self.lbl_badge = QLabel(self.tr("Checking..."))
        self.lbl_badge.setAlignment(Qt.AlignCenter)
        self.lbl_badge.setFixedHeight(22)
        self.lbl_badge.setStyleSheet("""
            background-color: #0F172A; color: #94A3B8; border: 1px solid #334155;
            border-radius: 6px; padding: 0 8px; font-size: 10px; font-weight: bold;
        """)
        title_layout.addWidget(self.lbl_badge)
        main_layout.addLayout(title_layout)

        # ---------------------------------------------------------
        # Fila 4: Footer (Estado de Sincronización Real del NAS y CTA Rebuild)
        # ---------------------------------------------------------
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 5, 0, 0)
        
        self.lbl_sync_status = QLabel(self.tr("🗄️ Checking..."))
        self.lbl_sync_status.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
        footer_layout.addWidget(self.lbl_sync_status)
        
        footer_layout.addStretch()
        
        self.btn_rebuild = QPushButton(self.tr("Rebuild NAS"))
        self.btn_rebuild.setCursor(Qt.PointingHandCursor)
        self.btn_rebuild.setStyleSheet("""
            QPushButton { border: 1px solid #F59E0B; color: #F59E0B; background: transparent; border-radius: 6px; font-weight: bold; font-size: 11px; padding: 4px 10px; }
            QPushButton:hover { background-color: rgba(245, 158, 11, 0.1); }
        """)
        self.btn_rebuild.setVisible(False)
        self.btn_rebuild.clicked.connect(self._on_rebuild_clicked)
        footer_layout.addWidget(self.btn_rebuild)
        
        main_layout.addLayout(footer_layout)

    def _abrir_ruta_kitsu(self, sub_ruta: str):
        """Enruta al usuario directamente a un módulo específico del proyecto en Kitsu."""
        project_id = self.project_data.get("id")
        host = getattr(self.auth, 'kitsu_host', '')
        url = self.kitsu_mgr.build_web_url(host, project_id, sub_ruta)
        
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _check_nas_status(self):
        """Delega la validación física al NasManager y pinta el resultado."""
        if not self.nas_mgr.is_connected():
            self.lbl_sync_status.setText(self.tr("🗄️ 🔴 Disconnected"))
            self.lbl_sync_status.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: bold;")
            self.lbl_badge.setText(self.tr("Unknown"))
            self.btn_rebuild.setVisible(False)
            return

        p_name = self.project_data.get("name", "")
        p_code = self.project_data.get("code", "")

        self.project_dir = self.nas_mgr.resolve_project_dir(p_name, p_code)

        if self.project_dir:
            self.lbl_sync_status.setText(self.tr("🗄️ 🟢 Synced"))
            self.lbl_sync_status.setStyleSheet("color: #10B981; font-size: 12px; font-weight: bold;")
            self.btn_rebuild.setVisible(False)
            
            blueprint = self.nas_mgr.get_project_blueprint(self.project_dir)
            blender_ver = blueprint.get("blender_version", self.tr("Blender 4.2.0"))
            self.lbl_badge.setText(blender_ver)
        else:
            self.lbl_sync_status.setText(self.tr("🗄️ 🔴 Not Mounted"))
            self.lbl_sync_status.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: bold;")
            self.lbl_badge.setText(self.tr("Missing Folder"))
            self.btn_rebuild.setVisible(True)

    def _on_rebuild_clicked(self):
        if self.on_rebuild_callback:
            self.on_rebuild_callback()

    def _on_delete_requested(self):
        project_name = self.project_data.get("name", "")
        dialog = DeleteProjectDialog(self, project_name)
        
        if dialog.exec() == QDialog.Accepted:
            self._ejecutar_destruccion_nuclear(project_name)

    def _ejecutar_destruccion_nuclear(self, project_name: str):
        """Coordina la eliminación a través de los controladores y notifica al usuario."""
        project_id = self.project_data.get("id")
        folder_name = project_name.lower().replace(" ", "-")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            # 1. Kitsu DB
            success, msg = self.kitsu_mgr.delete_project(project_id)
            if not success:
                QMessageBox.warning(self, self.tr("Warning"), msg)

            # 2. SVN (Docker)
            try:
                subprocess.run(["docker", "exec", "openstudio_local_svn", "rm", "-rf", f"/home/svn/{folder_name}"], check=False)
            except Exception as e:
                print(f"[ProjectCard] Advertencia al limpiar SVN Docker: {e}")

            # 3. NAS Local
            self.nas_mgr.delete_project_folder(self.project_dir)

            QMessageBox.information(self, self.tr("Deleted"), self.tr("Project '{0}' has been permanently destroyed.").format(project_name))

            if self.on_rebuild_callback:
                self.on_rebuild_callback()

        finally:
            QApplication.restoreOverrideCursor()

    def _cargar_miniatura(self):
        project_id = self.project_data.get("id")
        token = self.auth.get_current_token()
        base_url = self.auth.kitsu_host
        
        self.worker = ProjectThumbnailWorker(self.kitsu_mgr, project_id, token, base_url)
        self.worker.image_downloaded.connect(self._on_thumbnail_ready)
        self.worker.error_occurred.connect(self._on_thumbnail_error)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _on_thumbnail_ready(self, img_bytes: bytes):
        image = QImage.fromData(img_bytes)
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            
            ancho_objetivo = 290
            alto_objetivo = 140
            
            pixmap = pixmap.scaled(ancho_objetivo, alto_objetivo, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            x_offset = (pixmap.width() - ancho_objetivo) // 2
            y_offset = (pixmap.height() - alto_objetivo) // 2
            final_pixmap = pixmap.copy(x_offset, y_offset, ancho_objetivo, alto_objetivo)
            
            self.thumb_label.setPixmap(final_pixmap)
            self.thumb_label.setText("") 
        else:
            self._on_thumbnail_error(self.tr("Archivo corrupto"))

    def _on_thumbnail_error(self, message: str):
        self.thumb_label.setText(message)
