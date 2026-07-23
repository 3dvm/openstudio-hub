# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/workers/spawning_workers.py
# Rol: Hilos asíncronos y modales para la I/O pesada del Production Manager
# =========================================================================================

import gazu
import subprocess
import os
import glob
import platform
from pathlib import Path

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTextEdit, QPushButton
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QTextCursor

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

class MasterSpawningWorker(QThread):
    progress_updated = Signal(int, str)
    log_stream = Signal(str)
    finished_spawn = Signal(bool, str)

    def __init__(self, config_factory, project_name, build_target):
        super().__init__()
        self.config = config_factory
        self.project_name = project_name
        self.build_target = build_target

    def run(self):
        try:
            self.progress_updated.emit(10, self.tr("Locating project and sandbox..."))
            nas_root = self.config.get_workspace_root()
            vfs_local = self.config.get_vfs_local_name()
            folder_name = self.project_name.strip().lower().replace(" ", "-")
            project_root = nas_root / folder_name
            
            base_blender_dir = project_root / vfs_local / "blender-build"
            os_name = platform.system().lower()
            if os_name == "windows":
                exe_list = glob.glob(str(base_blender_dir / "**" / "blender.exe"), recursive=True)
            elif os_name == "darwin":
                exe_list = glob.glob(str(base_blender_dir / "**" / "MacOS" / "Blender"), recursive=True)
            else:
                exe_list = glob.glob(str(base_blender_dir / "**" / "blender"), recursive=True)
                
            if not exe_list:
                raise FileNotFoundError("Blender binary not found in sandbox.")
            blender_bin = exe_list[0]

            self.progress_updated.emit(20, self.tr("Preparing environment variables..."))
            env = os.environ.copy()
            env["OPENSTUDIO_BUILD_TARGET"] = self.build_target
            env["OPENSTUDIO_PROJECT_ROOT"] = str(project_root)
            env["BLENDER_USER_RESOURCES"] = str(project_root / vfs_local / "blender_data")
            
            script_path = Path(__file__).parent.parent.parent / "core" / "templates" / "headless_builder.py"
            
            self.progress_updated.emit(30, self.tr("Booting Blender Engine..."))
            cmd = [str(blender_bin), "-b", "--python", str(script_path)]
            proceso = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            for line in proceso.stdout:
                line_clean = line.strip()
                if not line_clean: continue
                self.log_stream.emit(line_clean)
                
                if "Cargando App-Template" in line_clean:
                    self.progress_updated.emit(50, self.tr("Loading UI Template..."))
                elif "Restaurando contexto Kitsu" in line_clean:
                    self.progress_updated.emit(70, self.tr("Authenticating with server..."))
                elif "GUARDADO FORZADO EXITOSO" in line_clean:
                    self.progress_updated.emit(90, self.tr("Writing physical file..."))
            
            proceso.wait()
            if proceso.returncode == 0:
                self.progress_updated.emit(100, self.tr("Master File Forged Successfully!"))
                self.finished_spawn.emit(True, f"{self.build_target} created.")
            else:
                raise RuntimeError(f"Blender crashed with return code {proceso.returncode}")
                
        except Exception as e:
            self.finished_spawn.emit(False, str(e))

class StoryboardBatchWorker(QThread):
    progress_updated = Signal(int, str)
    log_stream = Signal(str)
    finished_batch = Signal(bool, str)

    def __init__(self, pm_core, config_factory, project_id: str, project_name: str, sequence_names: list):
        super().__init__()
        self.pm_core = pm_core
        self.config = config_factory
        self.project_id = project_id
        self.project_name = project_name
        self.sequence_names = sequence_names

    def run(self):
        try:
            total_seqs = len(self.sequence_names)
            if total_seqs == 0:
                self.finished_batch.emit(False, self.tr("The sequence list is empty."))
                return

            self.progress_updated.emit(5, self.tr("Verifying Kitsu Pipeline schema..."))
            storyboard_tt = self.pm_core.get_or_create_storyboard_task_type(self.project_id)
            tt_id = storyboard_tt["id"]
            
            nas_root = self.config.get_workspace_root()
            vfs_local = self.config.get_vfs_local_name()
            folder_name = self.project_name.strip().lower().replace(" ", "-")
            project_root = nas_root / folder_name
            base_blender_dir = project_root / vfs_local / "blender-build"
            
            os_name = platform.system().lower()
            if os_name == "windows":
                exe_list = glob.glob(str(base_blender_dir / "**" / "blender.exe"), recursive=True)
            elif os_name == "darwin":
                exe_list = glob.glob(str(base_blender_dir / "**" / "MacOS" / "Blender"), recursive=True)
            else:
                exe_list = glob.glob(str(base_blender_dir / "**" / "blender"), recursive=True)
                
            if not exe_list:
                raise FileNotFoundError("Blender binary not found in sandbox.")

            for idx, seq_name in enumerate(self.sequence_names):
                base_progress = 10 + int((idx / total_seqs) * 90)
                self.progress_updated.emit(base_progress, self.tr(f"Processing Sequence: {seq_name} ({idx+1}/{total_seqs})"))
                
                self.log_stream.emit(f"\n[{seq_name}] Registering Entity and Task in Kitsu API...")
                existing_seq = gazu.shot.get_sequence_by_name(self.project_id, seq_name)
                
                if not existing_seq:
                    existing_seq = self.pm_core.create_sequence_with_task(self.project_id, seq_name, tt_id)
                    self.log_stream.emit(f"[{seq_name}] ✓ Kitsu database updated.")
                else:
                    self.log_stream.emit(f"[{seq_name}] ⚠️ Sequence already exists. Skipping Kitsu creation.")
               
                # --- NUEVO: ASIGNAR RUTA A LA TAREA EN KITSU ---
                vfs_svn = self.config.get_vfs_svn_name()
                
                try:

                    storyboard_tt = self.pm_core.get_or_create_storyboard_task_type(self.project_id)
                    #breakpoint()
                    task = gazu.task.get_task_by_entity(existing_seq, storyboard_tt)
                    
                    if task is None:
                        self.log_stream.emit(f"[{seq_name}] Tarea no encontrada. Creando nueva tarea 'main'...")
                        default_status = gazu.task.get_default_task_status()
                        task = gazu.task.new_task(existing_seq, storyboard_tt, name="main", task_status=default_status)
                    
                    rel_path = f"{vfs_svn}/edit/storyboards/{seq_name.lower()}-storyboard.blend"
                    
                    # 1. Inyectar como Metadata (Custom Data) para lectura genérica
                    # task_data = task.get("data", {}) or {}
                    # task_data["file_path"] = rel_path
                    # task_data["file_name"] = f"{seq_name.lower()}-storyboard.blend"
                    # gazu.task.update_task_data(task["id"], task_data)

                    # 2. Inyectar en el campo personalizado de la SECUENCIA
                    seq_data = existing_seq.get("data")
                    if not seq_data:
                        seq_data = {}

                    seq_data["blend_file_path"] = rel_path

                    gazu.shot.update_sequence_data(existing_seq["id"], seq_data)
                    self.log_stream.emit(f"[{seq_name}] ✓ File path saved in Sequence metadata: {rel_path}")
                    
                    # 2. Registrar como Working File oficial de Kitsu
                    software = gazu.files.get_software_by_name("Blender")
                    if software and task:
                        gazu.files.new_working_file(task, software, name=rel_path)
                        
                    self.log_stream.emit(f"[{seq_name}] ✓ File path mapped to Kitsu Task.")
                except Exception as e:
                    self.log_stream.emit(f"[{seq_name}] ⚠️ Fallo al mapear archivo en Kitsu: {e}")
                # -----------------------------------------------

                self.log_stream.emit(f"[{seq_name}] Spawning physical .blend file via Headless Engine...")
                
                env = os.environ.copy()
                env["OPENSTUDIO_BUILD_TARGET"] = "STORYBOARD"
                env["OPENSTUDIO_PROJECT_ROOT"] = str(project_root)
                env["BLENDER_USER_RESOURCES"] = str(project_root / vfs_local / "blender_data")
                env["OPENSTUDIO_TARGET_SEQUENCE"] = seq_name 
                
                script_path = Path(__file__).parent.parent.parent / "core" / "templates" / "headless_builder.py"
                cmd = [exe_list[0], "-b", "--python", str(script_path)]
                
                proceso = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proceso.stdout:
                    if line.strip(): self.log_stream.emit(f"    ↳ {line.strip()}")
                proceso.wait()
                
                if proceso.returncode != 0:
                    self.log_stream.emit(f"[{seq_name}] ❌ ERROR: Blender Headless failed.")
                else:
                    self.log_stream.emit(f"[{seq_name}] ✓ Physical file spawned.")

            self.progress_updated.emit(100, self.tr("Batch Creation Complete!"))
            self.finished_batch.emit(True, f"{total_seqs} Storyboard sequences processed successfully.")
            
        except Exception as e:
            self.finished_batch.emit(False, str(e))

class SpawningProgressDialog(QDialog):
    """Modal flotante que muestra el log de terminal en tiempo real con botones reactivos."""
    def __init__(self, parent, title: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(650, 420)
        self.setModal(True)
        self.setObjectName("FloatingCard")
        
        layout = QVBoxLayout(self)
        self.lbl_status = QLabel(self.tr("Initializing..."))
        self.lbl_status.setObjectName("H2Title")
        layout.addWidget(self.lbl_status)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(5)
        layout.addWidget(self.progress)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("FormInput")
        self.log_output.setStyleSheet("font-family: monospace; font-size: 12px; color: #94A3B8; background-color: #0F172A;")
        layout.addWidget(self.log_output)
        
        # --- Botonera Dinámica Inferior ---
        self.btn_layout = QHBoxLayout()
        self.btn_layout.addStretch()
        
        self.btn_action = QPushButton("")
        self.btn_action.setObjectName("PrimaryButton")
        self.btn_action.setFixedHeight(35)
        self.btn_action.hide() # Oculto por defecto
        
        self.btn_close = QPushButton(self.tr("Cancel"))
        self.btn_close.setObjectName("SecondaryButton")
        self.btn_close.setFixedHeight(35)
        self.btn_close.clicked.connect(self.accept)
        
        self.btn_layout.addWidget(self.btn_action)
        self.btn_layout.addWidget(self.btn_close)
        layout.addLayout(self.btn_layout)
        
    def update_progress(self, value: int, status_msg: str):
        if value > 0: self.progress.setValue(value)
        if status_msg: self.lbl_status.setText(status_msg)
        
    def append_log(self, text: str):
        self.log_output.append(text)
        from PySide6.QtGui import QTextCursor
        self.log_output.moveCursor(QTextCursor.End)
        
    def finalize(self, success: bool, main_msg: str, action_text: str = "", action_callback = None):
        """Transforma el modal al terminar el proceso para auditar el log."""
        self.lbl_status.setText(main_msg)
        self.lbl_status.setStyleSheet("color: #10B981;" if success else "color: #EF4444;")
        
        self.btn_close.setText(self.tr("Close Window"))
        self.btn_close.setStyleSheet("background-color: #334155;")
        
        if success and action_callback and action_text:
            self.btn_action.setText(action_text)
            self.btn_action.show()
            self.btn_action.clicked.connect(action_callback)
            
        # Si falló, la barra se pone roja
        if not success:
            self.progress.setStyleSheet("QProgressBar::chunk { background-color: #EF4444; }")
