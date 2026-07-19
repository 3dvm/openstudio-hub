# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/project_card.py
# Rol Arquitectónico: UI Component / Reusable Project Card (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.0 (Self-Healing NAS Rebuild)
# =========================================================================================

"""
Componente visual reutilizable para las Tarjetas de Proyectos en la vista del TD.
Implementa un diseño moderno con dimensiones optimizadas (320x280).
Lee dinámicamente el estado físico en el NAS y expone el flujo de Autorrecuperación (Rebuild)
en caso de extravío de la topografía.
"""

import requests
import json
from pathlib import Path
from typing import Callable

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
    def __init__(self, parent: QWidget, project_data: dict, auth_manager, nextcloud_dir: Path, on_rebuild_callback: Callable = None):
        super().__init__(parent)
        
        self.project_data = project_data
        self.auth = auth_manager
        self.nextcloud_dir = Path(nextcloud_dir) if nextcloud_dir else None
        self.project_dir = None
        self.on_rebuild_callback = on_rebuild_callback
        
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
        # Fila 1: Cabecera (Estado del proyecto)
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
        
        project_name = self.project_data.get("name", "Proyecto Desconocido")
        self.lbl_title = QLabel(project_name)
        self.lbl_title.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: bold;")
        title_layout.addWidget(self.lbl_title)
        
        title_layout.addStretch()
        
        # Badge con paleta limpia (Gris sutil) para no competir con el CTA primario
        self.lbl_badge = QLabel(self.tr("Checking..."))
        self.lbl_badge.setAlignment(Qt.AlignCenter)
        self.lbl_badge.setFixedHeight(22)
        self.lbl_badge.setStyleSheet("""
            background-color: #0F172A;
            color: #94A3B8;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 0 8px;
            font-size: 10px;
            font-weight: bold;
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
        
        # Botón de Autorrecuperación (Oculto por defecto)
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

    def _check_nas_status(self):
        """Valida físicamente la existencia del directorio e intercepta metadatos inmutables."""
        if not self.nextcloud_dir:
            self.lbl_sync_status.setText(self.tr("🗄️ 🔴 Disconnected"))
            self.lbl_sync_status.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: bold;")
            self.lbl_badge.setText(self.tr("Unknown"))
            self.btn_rebuild.setVisible(False)
            return

        p_name = self.project_data.get("name", "Unknown")
        p_code = self.project_data.get("code", p_name)

        # Mapear ruta por nombre del proyecto o código abreviado
        self.project_dir = self.nextcloud_dir / p_name
        if not self.project_dir.exists() and p_code:
            self.project_dir = self.nextcloud_dir / p_code

        # Evaluar existencia en el FileSystem local/compartido
        if self.project_dir.exists():
            self.lbl_sync_status.setText(self.tr("🗄️ 🟢 Synced"))
            self.lbl_sync_status.setStyleSheet("color: #10B981; font-size: 12px; font-weight: bold;")
            self.btn_rebuild.setVisible(False)
            
            # Buscar archivo de variables de entorno oculto del Hub
            meta_file = self.project_dir / ".openstudio.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    blender_ver = meta.get("blender_version", "Blender 4.2.0")
                    self.lbl_badge.setText(blender_ver)
                except Exception:
                    self.lbl_badge.setText(self.tr("Meta Error"))
            else:
                self.lbl_badge.setText(self.tr("Blender 4.2.0")) # Fallback tolerado
        else:
            # Exponer la vía de autorrecuperación si la topografía está desaparecida
            self.lbl_sync_status.setText(self.tr("🗄️ 🔴 Not Mounted"))
            self.lbl_sync_status.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: bold;")
            self.lbl_badge.setText(self.tr("Missing Folder"))
            self.btn_rebuild.setVisible(True)

    def _on_rebuild_clicked(self):
        """Despacha la señal de autorrecuperación a la vista padre."""
        if self.on_rebuild_callback:
            self.on_rebuild_callback(self.project_data)

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
