import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial
import csv
import re
import os
import time
from datetime import datetime
from collections import deque

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# ==================================================
# CONFIGURATION
# ==================================================

PORT = "COM7"
BAUD = 9600

CSV_FILE = "nightwatch_events.csv"

WARNING_DISTANCE = 18
RECOVERY_DISTANCE = 25
REQUIRED_READINGS = 3


# ==================================================
# NIGHTWATCH DASHBOARD
# ==================================================

class NightwatchDashboard:

    def __init__(self, root):

        self.root = root
        self.root.title("PROJECT NIGHTWATCH | V2.0")
        self.root.geometry("1150x760")
        self.root.configure(bg="#101820")

        self.paused = False
        self.connection = None

        self.last_rx_time = 0

        self.distance = 0
        self.status = "NORMAL"

        self.candidate_status = None
        self.candidate_count = 0
        self.no_echo_count = 0

        self.start_time = time.time()

        self.distances = deque(maxlen=60)
        self.history = []

        self.total_events = 0
        self.warning_events = 0
        self.normal_events = 0

        self.load_history()
        self.connect_serial()

        self.build_interface()
        self.update_dashboard()

    # ==================================================
    # SERIAL CONNECTION
    # ==================================================

    def connect_serial(self):

        try:

            if self.connection:
                self.connection.close()

            self.connection = serial.Serial(
                PORT,
                BAUD,
                timeout=0
            )

            time.sleep(2)
            self.last_rx_time = time.time()

            print("Connected to", PORT)

        except Exception as error:

            self.connection = None

            print("Serial connection error:", error)

    def read_serial(self):

        if not self.connection:
            return

        try:

            while self.connection.in_waiting:

                line = self.connection.readline().decode(
                    "utf-8",
                    errors="ignore"
                ).strip()

                if not line:
                    continue

                self.last_rx_time = time.time()

                if self.paused:
                    continue

                if "No echo" in line:

                    self.no_echo_count += 1

                    if self.no_echo_count >= 3:
                        self.change_status("SENSOR FAULT")

                    continue

                match = re.search(
                    r"Distance:\s*([\d.]+)\s*cm",
                    line
                )

                if match:

                    distance = float(match.group(1))

                    if not 0 < distance <= 500:
                        continue

                    self.no_echo_count = 0
                    self.distance = distance

                    self.distances.append(distance)

                    self.process_distance(distance)

        except Exception as error:

            print("Serial reading error:", error)

            try:
                self.connection.close()
            except Exception:
                pass

            self.connection = None

    # ==================================================
    # SMART DETECTION
    # ==================================================

    def process_distance(self, distance):

        if distance <= WARNING_DISTANCE:

            new_status = "WARNING"

        elif distance >= RECOVERY_DISTANCE:

            new_status = "NORMAL"

        else:

            new_status = self.status

        if new_status == self.status:

            self.candidate_status = None
            self.candidate_count = 0

            return

        if new_status == self.candidate_status:

            self.candidate_count += 1

        else:

            self.candidate_status = new_status
            self.candidate_count = 1

        if self.candidate_count >= REQUIRED_READINGS:

            self.change_status(new_status)

            self.candidate_status = None
            self.candidate_count = 0

    def change_status(self, new_status):

        if new_status == self.status:
            return

        self.status = new_status

        self.log_event()

    # ==================================================
    # CSV HISTORY AND MIGRATION
    # ==================================================

    def load_history(self):

        if not os.path.exists(CSV_FILE):
            return

        try:

            with open(CSV_FILE, "r", newline="") as file:

                reader = csv.DictReader(file)

                for row in reader:

                    event = {
                        "Date": row.get("Date", ""),
                        "Time": row.get("Time", ""),
                        "Distance": row.get(
                            "Distance",
                            row.get("Distance (cm)", "")
                        ),
                        "Status": row.get("Status", "")
                    }

                    self.history.append(event)

            # Rewrite old CSV format using consistent column names.

            with open(CSV_FILE, "w", newline="") as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "Date",
                        "Time",
                        "Distance",
                        "Status"
                    ]
                )

                writer.writeheader()
                writer.writerows(self.history)

            for event in self.history:

                status = event["Status"].upper()

                if status == "WARNING":
                    self.warning_events += 1

                elif status == "NORMAL":
                    self.normal_events += 1

            self.total_events = len(self.history)

        except Exception as error:

            print("History loading error:", error)

    def log_event(self):

        now = datetime.now()

        event = {
            "Date": now.strftime("%d-%m-%Y"),
            "Time": now.strftime("%H:%M:%S"),
            "Distance": f"{self.distance:.2f}",
            "Status": self.status
        }

        try:

            file_exists = os.path.exists(CSV_FILE)

            with open(CSV_FILE, "a", newline="") as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "Date",
                        "Time",
                        "Distance",
                        "Status"
                    ]
                )

                if not file_exists or os.path.getsize(CSV_FILE) == 0:
                    writer.writeheader()

                writer.writerow(event)

            self.history.append(event)

            self.total_events += 1

            if self.status == "WARNING":
                self.warning_events += 1

            elif self.status == "NORMAL":
                self.normal_events += 1

            self.refresh_history()

        except Exception as error:

            messagebox.showerror(
                "Logging Error",
                str(error)
            )

    # ==================================================
    # INTERFACE
    # ==================================================

    def build_interface(self):

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background="#202C39",
            foreground="white",
            fieldbackground="#202C39",
            rowheight=28
        )

        style.configure(
            "Treeview.Heading",
            background="#263746",
            foreground="white"
        )

        title = tk.Label(
            self.root,
            text="PROJECT NIGHTWATCH  |  V2.0",
            font=("Arial", 23, "bold"),
            fg="#00D9FF",
            bg="#101820"
        )

        title.pack(pady=15)

        # CONNECTION BAR

        top = tk.Frame(
            self.root,
            bg="#182530"
        )

        top.pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.connection_label = tk.Label(
            top,
            text="SERIAL: CHECKING",
            fg="yellow",
            bg="#182530",
            font=("Arial", 11, "bold")
        )

        self.connection_label.pack(
            side="left",
            padx=15,
            pady=10
        )

        tk.Button(
            top,
            text="RECONNECT",
            command=self.connect_serial,
            bg="#263746",
            fg="white"
        ).pack(
            side="right",
            padx=10
        )

        # STATUS CARDS

        cards = tk.Frame(
            self.root,
            bg="#101820"
        )

        cards.pack(
            fill="x",
            padx=20,
            pady=12
        )

        self.distance_label = self.create_card(
            cards,
            "DISTANCE",
            "-- cm"
        )

        self.status_label = self.create_card(
            cards,
            "SYSTEM STATUS",
            "NORMAL"
        )

        self.uptime_label = self.create_card(
            cards,
            "UPTIME",
            "00:00:00"
        )

        # GRAPH

        graph_frame = tk.Frame(
            self.root,
            bg="#182530"
        )

        graph_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=8
        )

        tk.Label(
            graph_frame,
            text="LIVE DISTANCE MONITOR",
            font=("Arial", 13, "bold"),
            fg="white",
            bg="#182530"
        ).pack(pady=5)

        self.figure, self.ax = plt.subplots(
            figsize=(8, 3)
        )

        self.figure.patch.set_facecolor("#182530")

        self.ax.set_facecolor("#202C39")

        self.ax.set_ylabel(
            "Distance (cm)",
            color="white"
        )

        self.ax.set_xlabel(
            "Recent readings",
            color="white"
        )

        self.ax.tick_params(colors="white")
        self.ax.grid(True, alpha=0.2)

        self.ax.axhline(
            WARNING_DISTANCE,
            linestyle="--",
            label="Warning threshold"
        )

        self.ax.axhline(
            RECOVERY_DISTANCE,
            linestyle="--",
            label="Recovery threshold"
        )

        self.ax.legend(
            facecolor="#202C39",
            labelcolor="white"
        )

        self.figure.tight_layout()

        self.canvas = FigureCanvasTkAgg(
            self.figure,
            master=graph_frame
        )

        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True
        )

        # STATISTICS

        stats = tk.Frame(
            self.root,
            bg="#182530"
        )

        stats.pack(
            fill="x",
            padx=20,
            pady=8
        )

        self.stats_label = tk.Label(
            stats,
            text="",
            fg="#00D9FF",
            bg="#182530",
            font=("Arial", 11, "bold")
        )

        self.stats_label.pack(pady=10)

        # EVENT HISTORY

        history_frame = tk.Frame(
            self.root,
            bg="#182530"
        )

        history_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=8
        )

        tk.Label(
            history_frame,
            text="EVENT HISTORY",
            fg="white",
            bg="#182530",
            font=("Arial", 13, "bold")
        ).pack(pady=5)

        search_frame = tk.Frame(
            history_frame,
            bg="#182530"
        )

        search_frame.pack(fill="x")

        self.search_entry = tk.Entry(
            search_frame,
            width=30
        )

        self.search_entry.pack(
            side="left",
            padx=8,
            pady=5
        )

        self.search_entry.insert(
            0,
            "Search events..."
        )

        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.refresh_history()
        )

        self.filter_var = tk.StringVar(
            value="ALL"
        )

        filter_box = ttk.Combobox(
            search_frame,
            textvariable=self.filter_var,
            values=[
                "ALL",
                "NORMAL",
                "WARNING",
                "SENSOR FAULT"
            ],
            state="readonly",
            width=15
        )

        filter_box.pack(
            side="left",
            padx=8
        )

        filter_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.refresh_history()
        )

        columns = (
            "Date",
            "Time",
            "Distance",
            "Status"
        )

        self.tree = ttk.Treeview(
            history_frame,
            columns=columns,
            show="headings",
            height=6
        )

        for column in columns:

            self.tree.heading(
                column,
                text=column
            )

            self.tree.column(
                column,
                anchor="center",
                width=150
            )

        self.tree.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8
        )

        self.refresh_history()

        # BUTTONS

        buttons = tk.Frame(
            self.root,
            bg="#101820"
        )

        buttons.pack(pady=12)

        self.pause_button = tk.Button(
            buttons,
            text="PAUSE",
            command=self.toggle_pause,
            width=14,
            bg="#263746",
            fg="white"
        )

        self.pause_button.pack(
            side="left",
            padx=8
        )

        tk.Button(
            buttons,
            text="EXPORT CSV",
            command=self.export_csv,
            width=14,
            bg="#263746",
            fg="white"
        ).pack(
            side="left",
            padx=8
        )

        tk.Button(
            buttons,
            text="GENERATE REPORT",
            command=self.generate_report,
            width=18,
            bg="#007C91",
            fg="white"
        ).pack(
            side="left",
            padx=8
        )

    # ==================================================
    # STATUS CARDS
    # ==================================================

    def create_card(self, parent, title, value):

        frame = tk.Frame(
            parent,
            bg="#202C39",
            padx=25,
            pady=15
        )

        frame.pack(
            side="left",
            expand=True,
            fill="x",
            padx=6
        )

        tk.Label(
            frame,
            text=title,
            fg="#9DB4C0",
            bg="#202C39",
            font=("Arial", 10, "bold")
        ).pack()

        label = tk.Label(
            frame,
            text=value,
            fg="#00D9FF",
            bg="#202C39",
            font=("Arial", 19, "bold")
        )

        label.pack(pady=5)

        return label

    # ==================================================
    # EVENT HISTORY
    # ==================================================

    def refresh_history(self):

        if not hasattr(self, "tree"):
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        search = self.search_entry.get().lower()

        if search == "search events...":
            search = ""

        selected_status = self.filter_var.get()

        for event in reversed(self.history):

            status = event.get(
                "Status",
                ""
            ).upper()

            if selected_status != "ALL":

                if status != selected_status:
                    continue

            text = " ".join(
                str(value)
                for value in event.values()
            ).lower()

            if search not in text:
                continue

            self.tree.insert(
                "",
                "end",
                values=(
                    event.get("Date", ""),
                    event.get("Time", ""),
                    event.get("Distance", ""),
                    status
                )
            )

    # ==================================================
    # CONTROLS
    # ==================================================

    def toggle_pause(self):

        self.paused = not self.paused

        if self.paused:

            self.pause_button.config(
                text="RESUME"
            )

        else:

            self.pause_button.config(
                text="PAUSE"
            )

    # ==================================================
    # CSV EXPORT - FIXED
    # ==================================================

    def export_csv(self):

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="nightwatch_v2_export.csv"
        )

        if not filename:
            return

        try:

            fieldnames = [
                "Date",
                "Time",
                "Distance",
                "Status"
            ]

            normalized_history = []

            for event in self.history:

                normalized_history.append({

                    "Date": event.get(
                        "Date",
                        ""
                    ),

                    "Time": event.get(
                        "Time",
                        ""
                    ),

                    "Distance": event.get(
                        "Distance",
                        event.get("Distance (cm)", "")
                    ),

                    "Status": event.get(
                        "Status",
                        ""
                    )

                })

            with open(filename, "w", newline="") as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=fieldnames
                )

                writer.writeheader()
                writer.writerows(normalized_history)

            messagebox.showinfo(
                "Export Complete",
                "CSV exported successfully!"
            )

        except Exception as error:

            messagebox.showerror(
                "Export Error",
                str(error)
            )

    # ==================================================
    # REPORT GENERATION
    # ==================================================

    def generate_report(self):

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="nightwatch_report.txt"
        )

        if not filename:
            return

        uptime = int(time.time() - self.start_time)

        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        seconds = uptime % 60

        report = f"""
========================================
       PROJECT NIGHTWATCH V2.0
          SYSTEM REPORT
========================================

Generated: {datetime.now()}

Current Distance: {self.distance:.2f} cm
Current Status: {self.status}

Uptime: {hours:02}:{minutes:02}:{seconds:02}

Total Events: {self.total_events}
Warning Events: {self.warning_events}
Normal Events: {self.normal_events}

Detection Threshold: {WARNING_DISTANCE} cm
Recovery Threshold: {RECOVERY_DISTANCE} cm

========================================
             RECENT EVENTS
========================================
"""

        for event in self.history[-20:]:

            report += (
                f"{event.get('Date', '')} "
                f"{event.get('Time', '')} | "
                f"{event.get('Distance', '')} cm | "
                f"{event.get('Status', '')}\n"
            )

        report += """
========================================
This is an educational monitoring prototype.
========================================
"""

        try:

            with open(filename, "w") as file:
                file.write(report)

            messagebox.showinfo(
                "Report Generated",
                "Report saved successfully."
            )

        except Exception as error:

            messagebox.showerror(
                "Report Error",
                str(error)
            )

    # ==================================================
    # DASHBOARD UPDATE
    # ==================================================

    def update_dashboard(self):

        self.read_serial()

        # CONNECTION STATUS

        if self.connection:

            if time.time() - self.last_rx_time < 3:

                self.connection_label.config(
                    text="SERIAL: CONNECTED",
                    fg="#00FF88"
                )

            else:

                self.connection_label.config(
                    text="SERIAL: NO RECENT DATA",
                    fg="yellow"
                )

        else:

            self.connection_label.config(
                text="SERIAL: DISCONNECTED",
                fg="#FF5555"
            )

        # DISTANCE

        self.distance_label.config(
            text=f"{self.distance:.2f} cm"
        )

        # SYSTEM STATUS

        self.status_label.config(
            text=self.status
        )

        if self.status == "WARNING":

            self.status_label.config(
                fg="#FF5555"
            )

        elif self.status == "SENSOR FAULT":

            self.status_label.config(
                fg="#FFA500"
            )

        else:

            self.status_label.config(
                fg="#00FF88"
            )

        # UPTIME

        uptime = int(time.time() - self.start_time)

        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        seconds = uptime % 60

        self.uptime_label.config(
            text=f"{hours:02}:{minutes:02}:{seconds:02}"
        )

        # STATISTICS

        self.stats_label.config(
            text=(
                f"TOTAL EVENTS: {self.total_events}     |     "
                f"WARNINGS: {self.warning_events}     |     "
                f"NORMAL: {self.normal_events}"
            )
        )

        # GRAPH

        self.ax.clear()

        self.ax.set_facecolor("#202C39")

        self.ax.set_title(
            "Distance Monitoring",
            color="white"
        )

        self.ax.set_ylabel(
            "Distance (cm)",
            color="white"
        )

        self.ax.set_xlabel(
            "Recent readings",
            color="white"
        )

        self.ax.tick_params(colors="white")
        self.ax.grid(True, alpha=0.2)

        self.ax.axhline(
            WARNING_DISTANCE,
            linestyle="--",
            label="Warning threshold"
        )

        self.ax.axhline(
            RECOVERY_DISTANCE,
            linestyle="--",
            label="Recovery threshold"
        )

        if self.distances:

            self.ax.plot(
                list(self.distances),
                marker="o",
                markersize=3,
                label="Distance"
            )

        self.ax.legend(
            facecolor="#202C39",
            labelcolor="white"
        )

        self.figure.tight_layout()
        self.canvas.draw_idle()

        self.root.after(
            300,
            self.update_dashboard
        )


# ==================================================
# START APPLICATION
# ==================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = NightwatchDashboard(root)

    root.mainloop()
