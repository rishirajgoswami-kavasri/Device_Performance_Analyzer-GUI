import tkinter
import customtkinter
import psutil
import platform
import socket
import uuid
import requests
import time
import threading
import sys

# --- Optional Dependencies ---
# Windows-specific info (Model Name, GPU Name)
try:
    import wmi
    _wmi_available = True
except ImportError:
    _wmi_available = False
    print("WMI library not found. Install with 'pip install wmi pywin32' for Model Name and detailed GPU info.")

# Detailed GPU stats (Usage, Memory)
try:
    import GPUtil
    _gputil_available = True
except ImportError:
    _gputil_available = False
    print("GPUtil library not found. Install with 'pip install gputil' for detailed GPU performance metrics.")

# --- Constants ---
UPDATE_INTERVAL_MS = 1000  # Refresh interval in milliseconds
NETWORK_TEST_URL = "http://www.google.com"
NETWORK_TIMEOUT = 3  # Seconds for internet connectivity check

# --- Helper Functions ---
def bytes_to_gb(bytes_val):
    """Convert bytes to gigabytes."""
    return round(bytes_val / (1024 ** 3), 2)

def bytes_to_mbs(bytes_val):
    """Convert bytes per second to megabits per second."""
    return round((bytes_val * 8) / (1024 ** 2), 2)

# --- Main Application Class ---
class PerformanceAnalyzerApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Device Performance Analyzer")
        self.minsize(650, 550)

        # Use system theme and default color theme
        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        # --- State Variables ---
        self.last_net_io = psutil.net_io_counters()
        self.last_net_time = time.time()
        self.network_speed = {"upload": 0.0, "download": 0.0}
        self.running = True  # Flag to control update thread

        # --- Main Frame ---
        self.main_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        # --- Exit Button ---
        self.exit_button = customtkinter.CTkButton(
            self,
            text="X",
            width=30,
            height=30,
            command=self.exit_app,
            corner_radius=5,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30")
        )
        self.exit_button.place(relx=1.0, rely=0.0, anchor='ne', x=-5, y=5)

        # --- UI Sections ---
        row_index = 0

        # 1. Device Information Section
        self.device_info_frame = customtkinter.CTkFrame(self.main_frame)
        self.device_info_frame.grid(row=row_index, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")
        self.device_info_frame.grid_columnconfigure(1, weight=1)

        customtkinter.CTkLabel(
            self.device_info_frame,
            text="Device Information",
            font=customtkinter.CTkFont(weight="bold")
        ).grid(row=0, column=0, columnspan=2, pady=(5, 10))
        self.model_label = customtkinter.CTkLabel(self.device_info_frame, text="Model Name: Fetching...", anchor="w")
        self.model_label.grid(row=1, column=0, columnspan=2, padx=10, pady=2, sticky="w")
        self.ip_label = customtkinter.CTkLabel(self.device_info_frame, text="IP Address: Fetching...", anchor="w")
        self.ip_label.grid(row=2, column=0, padx=10, pady=2, sticky="w")
        self.mac_label = customtkinter.CTkLabel(self.device_info_frame, text="MAC Address: Fetching...", anchor="w")
        self.mac_label.grid(row=3, column=0, padx=10, pady=2, sticky="w")
        self.os_label = customtkinter.CTkLabel(
            self.device_info_frame,
            text=f"OS: {platform.system()} {platform.release()}",
            anchor="w"
        )
        self.os_label.grid(row=4, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        row_index += 1

        # 2. Internet Connectivity Section
        self.connectivity_frame = customtkinter.CTkFrame(self.main_frame)
        self.connectivity_frame.grid(row=row_index, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.connectivity_frame.grid_columnconfigure(1, weight=1)

        customtkinter.CTkLabel(
            self.connectivity_frame,
            text="Internet Status",
            font=customtkinter.CTkFont(weight="bold")
        ).grid(row=0, column=0, pady=(5, 10), padx=10)
        self.connectivity_status_label = customtkinter.CTkLabel(
            self.connectivity_frame,
            text="Status: Checking...",
            text_color="orange",
            anchor="w"
        )
        self.connectivity_status_label.grid(row=0, column=1, pady=(5, 10), padx=10, sticky="w")

        row_index += 1

        # 3. Realtime Performance Monitoring Section
        self.performance_frame = customtkinter.CTkFrame(self.main_frame)
        self.performance_frame.grid(row=row_index, column=0, padx=10, pady=5, sticky="nsew")
        self.performance_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(row_index, weight=1)

        customtkinter.CTkLabel(
            self.performance_frame,
            text="Realtime Performance",
            font=customtkinter.CTkFont(weight="bold")
        ).grid(row=0, column=0, columnspan=2, pady=(5, 10))

        # CPU
        customtkinter.CTkLabel(self.performance_frame, text="CPU Usage:", anchor="w").grid(
            row=1, column=0, padx=10, pady=2, sticky="w"
        )
        self.cpu_label = customtkinter.CTkLabel(self.performance_frame, text="0%", anchor="w")
        self.cpu_label.grid(row=1, column=1, padx=10, pady=2, sticky="ew")
        self.cpu_bar = customtkinter.CTkProgressBar(self.performance_frame)
        self.cpu_bar.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")
        self.cpu_bar.set(0)

        # RAM
        customtkinter.CTkLabel(self.performance_frame, text="RAM Usage:", anchor="w").grid(
            row=3, column=0, padx=10, pady=2, sticky="w"
        )
        self.ram_label = customtkinter.CTkLabel(self.performance_frame, text="0% (0/0 GB)", anchor="w")
        self.ram_label.grid(row=3, column=1, padx=10, pady=2, sticky="ew")
        self.ram_bar = customtkinter.CTkProgressBar(self.performance_frame)
        self.ram_bar.grid(row=4, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")
        self.ram_bar.set(0)

        # Network Speed
        customtkinter.CTkLabel(self.performance_frame, text="Network:", anchor="w").grid(
            row=5, column=0, padx=10, pady=2, sticky="w"
        )
        self.net_label = customtkinter.CTkLabel(self.performance_frame, text="Up: 0 Mbps | Down: 0 Mbps", anchor="w")
        self.net_label.grid(row=5, column=1, padx=10, pady=2, sticky="ew")

        # GPU (Optional)
        self.gpu_name_label = customtkinter.CTkLabel(self.performance_frame, text="GPU:", anchor="w")
        self.gpu_name_label.grid(row=6, column=0, padx=10, pady=2, sticky="w")
        self.gpu_load_label = customtkinter.CTkLabel(self.performance_frame, text="Load: N/A", anchor="w")
        self.gpu_load_label.grid(row=7, column=0, columnspan=2, padx=10, pady=2, sticky="w")
        self.gpu_mem_label = customtkinter.CTkLabel(self.performance_frame, text="Memory: N/A", anchor="w")
        self.gpu_mem_label.grid(row=8, column=0, columnspan=2, padx=10, pady=(2, 5), sticky="w")

        # 4. Storage Analyzer Section
        self.storage_frame = customtkinter.CTkFrame(self.main_frame)
        self.storage_frame.grid(row=row_index, column=1, padx=10, pady=5, sticky="nsew")
        self.storage_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(row_index, weight=1)

        customtkinter.CTkLabel(
            self.storage_frame,
            text="Storage Analyzer",
            font=customtkinter.CTkFont(weight="bold")
        ).grid(row=0, column=0, pady=(5, 10))

        # --- Initial Data Fetch ---
        self.update_static_info()
        self.update_storage_info()

        # --- Start the Update Loop in a Separate Thread ---
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()

        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self.exit_app)

    def center_window(self, width=700, height=600):
        """Centers the tkinter window."""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        self.geometry(f'{width}x{height}+{x}+{y}')

    def update_loop(self):
        """Continuously update dynamic data."""
        while self.running:
            try:
                self.after(0, self.update_connectivity)
                self.after(0, self.update_performance_metrics)
            except Exception as e:
                print(f"Error in update loop: {e}")
            time.sleep(UPDATE_INTERVAL_MS / 1000)

    def update_static_info(self):
        """Fetch and update static device information."""
        # Get Model Name via WMI if available
        model = "N/A"
        if _wmi_available and platform.system() == "Windows":
            try:
                c = wmi.WMI()
                systems = c.Win32_ComputerSystem()
                if systems:
                    model = systems[0].Model
            except Exception as e:
                print(f"WMI Error getting model: {e}")
                model = "N/A (WMI Error)"
        else:
            model = f"{platform.machine()} (Requires WMI)"
        self.model_label.configure(text=f"Model Name: {model}")

        # Get IP and MAC Address
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))
                    ip_address = s.getsockname()[0]
            except Exception:
                ip_address = socket.gethostbyname(hostname)

            mac_num = uuid.getnode()
            mac_address = ':'.join(('%012X' % mac_num)[i:i+2] for i in range(0, 12, 2))
            if mac_address == "00:00:00:00:00:00":
                mac_address = "N/A (Error)"
        except socket.gaierror:
            ip_address = "N/A (Offline?)"
            mac_address = "N/A"
        except Exception as e:
            ip_address = f"N/A (Error: {type(e).__name__})"
            mac_address = "N/A (Error)"

        self.ip_label.configure(text=f"IP Address: {ip_address}")
        self.mac_label.configure(text=f"MAC Address: {mac_address}")

        # Get GPU Name using WMI or GPUtil
        gpu_name = "N/A"
        if _wmi_available and platform.system() == "Windows":
            try:
                c = wmi.WMI()
                gpu_info = c.Win32_VideoController()
                if gpu_info:
                    gpu_name = gpu_info[0].Name
            except Exception as e:
                print(f"WMI Error getting GPU name: {e}")
                gpu_name = "N/A (WMI Error)"
        elif _gputil_available:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_name = gpus[0].name
                else:
                    gpu_name = "N/A (Not Detected)"
            except Exception as e:
                print(f"GPUtil Error getting GPU name: {e}")
                gpu_name = "N/A (GPUtil Error)"
        else:
            gpu_name = "N/A (Requires WMI/GPUtil)"
        self.gpu_name_label.configure(text=f"GPU: {gpu_name}")

    def update_connectivity(self):
        """Check internet connectivity and update the label."""
        try:
            requests.get(NETWORK_TEST_URL, timeout=NETWORK_TIMEOUT)
            self.connectivity_status_label.configure(text="Status: Connected", text_color="green")
        except (requests.ConnectionError, requests.Timeout):
            self.connectivity_status_label.configure(text="Status: Disconnected", text_color="red")
        except Exception as e:
            self.connectivity_status_label.configure(text=f"Status: Error ({type(e).__name__})", text_color="orange")

    def update_performance_metrics(self):
        """Fetch and update CPU, RAM, Network, and GPU metrics."""
        # CPU Usage
        cpu_percent = psutil.cpu_percent(interval=None)
        self.cpu_label.configure(text=f"{cpu_percent:.1f}%")
        self.cpu_bar.set(cpu_percent / 100)

        # RAM Usage
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
        mem_used_gb = bytes_to_gb(mem.used)
        mem_total_gb = bytes_to_gb(mem.total)
        self.ram_label.configure(text=f"{mem_percent:.1f}% ({mem_used_gb}/{mem_total_gb} GB)")
        self.ram_bar.set(mem_percent / 100)

        # Network Speed
        current_net_io = psutil.net_io_counters()
        current_time = time.time()
        time_diff = current_time - self.last_net_time
        if time_diff > 0:
            bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
            bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
            upload_speed_bps = bytes_sent / time_diff
            download_speed_bps = bytes_recv / time_diff
            self.network_speed["upload"] = bytes_to_mbs(upload_speed_bps)
            self.network_speed["download"] = bytes_to_mbs(download_speed_bps)
        self.net_label.configure(
            text=f"Up: {self.network_speed['upload']:.2f} Mbps | Down: {self.network_speed['download']:.2f} Mbps"
        )
        self.last_net_io = current_net_io
        self.last_net_time = current_time

        # GPU Usage using GPUtil if available
        gpu_load_text = "Load: N/A"
        gpu_mem_text = "Memory: N/A"
        if _gputil_available:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    gpu_load_text = f"Load: {gpu.load * 100:.1f}%"
                    gpu_mem_text = f"Memory: {gpu.memoryUtil * 100:.1f}% ({gpu.memoryUsed:.1f}/{gpu.memoryTotal:.1f} MB)"
                else:
                    gpu_load_text = "Load: N/A (Not Detected)"
                    gpu_mem_text = "Memory: N/A (Not Detected)"
            except Exception as e:
                print(f"GPUtil Error getting stats: {e}")
                gpu_load_text = "Load: N/A (GPUtil Error)"
                gpu_mem_text = "Memory: N/A (GPUtil Error)"
        elif _wmi_available:
            gpu_load_text = "Load: N/A (Requires GPUtil)"
            gpu_mem_text = "Memory: N/A (Requires GPUtil)"
        self.gpu_load_label.configure(text=gpu_load_text)
        self.gpu_mem_label.configure(text=gpu_mem_text)

    def update_storage_info(self):
        """Fetch and display storage information for disk partitions."""
        # Clear previous storage widgets except the title
        for widget in self.storage_frame.winfo_children():
            if isinstance(widget, customtkinter.CTkLabel) and widget.cget("text") == "Storage Analyzer":
                continue
            widget.destroy()

        row_index = 1  # Start below the title
        try:
            partitions = psutil.disk_partitions(all=False)
            for partition in partitions:
                if partition.fstype:
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        drive_label = customtkinter.CTkLabel(
                            self.storage_frame,
                            text=f"{partition.device} ({partition.mountpoint})",
                            anchor="w"
                        )
                        drive_label.grid(row=row_index, column=0, padx=10, pady=(5, 0), sticky="w")
                        row_index += 1
                        usage_text = f"{bytes_to_gb(usage.used)} GB Used / {bytes_to_gb(usage.total)} GB Total ({usage.percent}%)"
                        usage_label = customtkinter.CTkLabel(self.storage_frame, text=usage_text, anchor="w")
                        usage_label.grid(row=row_index, column=0, padx=20, pady=0, sticky="w")
                        row_index += 1
                        progress_bar = customtkinter.CTkProgressBar(self.storage_frame)
                        progress_bar.grid(row=row_index, column=0, padx=10, pady=(0, 10), sticky="ew")
                        progress_bar.set(usage.percent / 100)
                        row_index += 1
                    except PermissionError:
                        drive_label = customtkinter.CTkLabel(
                            self.storage_frame,
                            text=f"{partition.device} - Access Denied",
                            text_color="orange",
                            anchor="w"
                        )
                        drive_label.grid(row=row_index, column=0, padx=10, pady=5, sticky="w")
                        row_index += 1
                    except Exception as e:
                        drive_label = customtkinter.CTkLabel(
                            self.storage_frame,
                            text=f"{partition.device} - Error ({type(e).__name__})",
                            text_color="red",
                            anchor="w"
                        )
                        drive_label.grid(row=row_index, column=0, padx=10, pady=5, sticky="w")
                        row_index += 1
        except Exception as e:
            error_label = customtkinter.CTkLabel(
                self.storage_frame,
                text=f"Error fetching disks: {e}",
                text_color="red",
                anchor="w"
            )
            error_label.grid(row=row_index, column=0, padx=10, pady=5, sticky="w")

    def exit_app(self):
        """Stop update thread and close the application."""
        print("Exiting application...")
        self.running = False
        # Allow a moment for the thread to finish
        time.sleep(0.1)
        self.destroy()
        sys.exit()

# --- Main Execution ---
if __name__ == "__main__":
    app = PerformanceAnalyzerApp()
    app.mainloop()
