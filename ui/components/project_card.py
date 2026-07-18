# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/project_card.py
# Rol Arquitectónico: UI Component / Reusable Project Card (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.2.0
# =========================================================================================

"""
Componente visual reutilizable para las Tarjetas de Proyectos en la vista del TD.
Implementa un diseño moderno con dimensiones optimizadas (320x280) para mejorar 
la densidad visual, y badges semánticos con la versión de Blender (SemVer).
"""

import requests
from pathlib import Path

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QWidget)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QImage


class ProjectThumbnailWorker(QThread):
    """QThread dedicado a la descarga HTTP asíncrona de los avatares de proyectos."""
    image_downloaded = Signal(bytes)
    error_occurred = Signal(str)

    def __init__(self, project_id: str, token: str, host_url: str):
        super().__init__()
        self.project_id = project_id
        self.token = token
        self.host_url = host_url

    def run(self):
        if not self.project_id:
            self.error_occurred.emit("ID de proyecto no disponible")
            return

        try:
            # Endpoint nativo de Gazu para avatares de proyectos
            img_url = f"{self.host_url}/pictures/thumbnails/projects/{self.project_id}.png"
            headers = {"Authorization": f"Bearer {self.token}"}
            
            response = requests.get(img_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.image_downloaded.emit(response.content)
            else:
                self.error_occurred.emit("Sin miniatura")
                
        except Exception as e:
            print(f"[UI PROJECT THUMBNAIL ERROR] Fallo en la red: {e}")
            self.error_occurred.emit("Error de conexión")


class ProjectCard(QFrame):
    def __init__(self, parent: QWidget, project_data: dict, auth_manager):
        super().__init__(parent)
        
        self.project_data = project_data
        self.auth = auth_manager
        
        # Dimensiones reducidas para densidad óptima (320x280)
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
        self._cargar_miniatura()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # ---------------------------------------------------------
        # Fila 1: Cabecera (Estado del proyecto y Menú de opciones)
        # ---------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        project_status = self.project_data.get("project_status_name", "Active Project")
        lbl_status = QLabel(project_status)
        lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(lbl_status)
        
        header_layout.addStretch()
        
        btn_options = QPushButton("•••")
        btn_options.setFixedSize(30, 20)
        btn_options.setCursor(Qt.PointingHandCursor)
        btn_options.setStyleSheet("color: #94A3B8; background: transparent; border: none; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(btn_options)
        
        main_layout.addLayout(header_layout)

        # ---------------------------------------------------------
        # Fila 2: Miniatura del Proyecto (Escalada para 320px)
        # ---------------------------------------------------------
        self.thumb_label = QLabel("Cargando miniatura...")
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setFixedHeight(140)
        self.thumb_label.setStyleSheet("background-color: #0F172A; border-radius: 8px; color: #475569; font-style: italic;")
        main_layout.addWidget(self.thumb_label)

        # ---------------------------------------------------------
        # Fila 3: Título del Proyecto y Badge (SemVer Blender)
        # ---------------------------------------------------------
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 5, 0, 0)
        
        project_name = self.project_data.get("name", "Proyecto Desconocido")
        self.lbl_title = QLabel(project_name)
        self.lbl_title.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: bold;")
        title_layout.addWidget(self.lbl_title)
        
        title_layout.addStretch()
        
        # Ajuste a formato de 3 dígitos (Ej. 4.2.0)
        self.lbl_badge = QLabel("Blender 4.2.0")
        self.lbl_badge.setAlignment(Qt.AlignCenter)
        self.lbl_badge.setFixedHeight(22)
        self.lbl_badge.setStyleSheet("""
            background-color: transparent;
            color: #F97316;
            border: 1px solid #F97316;
            border-radius: 10px;
            padding: 0 8px;
            font-size: 10px;
            font-weight: bold;
        """)
        title_layout.addWidget(self.lbl_badge)
        
        main_layout.addLayout(title_layout)

        # ---------------------------------------------------------
        # Fila 4: Footer (Estado de Sincronización del Servidor)
        # ---------------------------------------------------------
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 5, 0, 0)
        
        lbl_sync_type = QLabel("🗄️ Server Sync")
        lbl_sync_type.setStyleSheet("color: #64748B; font-size: 12px;")
        footer_layout.addWidget(lbl_sync_type)
        
        footer_layout.addStretch()
        
        self.lbl_sync_status = QLabel("🟢 Synced")
        self.lbl_sync_status.setStyleSheet("color: #10B981; font-size: 12px; font-weight: bold;")
        footer_layout.addWidget(self.lbl_sync_status)
        
        main_layout.addLayout(footer_layout)

    def _cargar_miniatura(self):
        project_id = self.project_data.get("id")
        token = self.auth.get_current_token()
        base_url = self.auth.kitsu_host
        
        self.worker = ProjectThumbnailWorker(project_id, token, base_url)
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
            self._on_thumbnail_error("Archivo corrupto")

    def _on_thumbnail_error(self, message: str):
        self.thumb_label.setText(message)
