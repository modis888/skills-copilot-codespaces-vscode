import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import re

class GCodeEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("G-code X/Y Editor")

        self.load_button = tk.Button(root, text="Įkelti G-code", command=self.load_gcode)
        self.load_button.pack()

        self.axis_var = tk.StringVar(value="X")
        self.axis_menu = tk.OptionMenu(root, self.axis_var, "X", "Y")
        self.axis_menu.pack()

        self.spline_button = tk.Button(root, text="Splainas per pažymėtus", command=self.apply_spline)
        self.spline_button.pack()

        self.straighten_button = tk.Button(root, text="Ištiesinti trajektoriją", command=self.straighten_path)
        self.straighten_button.pack()

        self.undo_button = tk.Button(root, text="Atšaukti", command=self.undo)
        self.undo_button.pack()

        self.save_button = tk.Button(root, text="Išsaugoti naują G-code", command=self.save_gcode)
        self.save_button.pack()

        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.figure, master=root)
        self.canvas.get_tk_widget().pack()
        self.canvas.mpl_connect("button_press_event", self.on_click)
        self.canvas.mpl_connect("motion_notify_event", self.on_drag)

        self.gcode_lines = []
        self.points = []
        self.selected_indices = []
        self.dragging = False
        self.history = []

    def push_history(self):
        self.history.append([p.copy() for p in self.points])
        if len(self.history) > 50:
            self.history.pop(0)

    def undo(self):
        if self.history:
            self.points = self.history.pop()
            self.plot_points()
        else:
            messagebox.showinfo("Atšaukti", "Nėra ką atšaukti.")

    def load_gcode(self):
        path = filedialog.askopenfilename(filetypes=[("G-code Files", "*.gcode *.nc *.txt")])
        if not path:
            return

        with open(path, 'r') as f:
            self.gcode_lines = f.readlines()

        self.points = self.extract_coordinates(self.gcode_lines)
        self.history = []
        self.plot_points()

    def extract_coordinates(self, lines):
        coords = []
        x, y = 0, 0
        for line in lines:
            if line.startswith("G0") or line.startswith("G1"):
                x_match = re.search(r"X(-?\d+\.?\d*)", line)
                y_match = re.search(r"Y(-?\d+\.?\d*)", line)
                if x_match:
                    x = float(x_match.group(1))
                if y_match:
                    y = float(y_match.group(1))
                coords.append([x, y])
        return coords

    def plot_points(self):
        self.ax.clear()
        arr = np.array(self.points)
        if len(arr) > 0:
            self.ax.plot(arr[:, 0], arr[:, 1], 'k.-')
            self.ax.plot(arr[self.selected_indices, 0], arr[self.selected_indices, 1], 'ro')
        self.ax.set_title(f"Redagavimas ašyje {self.axis_var.get()}")
        self.canvas.draw()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return

        x, y = event.xdata, event.ydata
        distances = [np.hypot(px - x, py - y) for px, py in self.points]
        closest = np.argmin(distances)

        if closest not in self.selected_indices:
            self.selected_indices.append(closest)
        else:
            self.selected_indices.remove(closest)

        self.dragging = True
        self.plot_points()

    def on_drag(self, event):
        if not self.dragging or not self.selected_indices or event.inaxes != self.ax:
            return

        self.push_history()

        delta_axis = 0.1
        axis = self.axis_var.get()
        for i in self.selected_indices:
            if axis == "X":
                self.points[i][0] += delta_axis
            elif axis == "Y":
                self.points[i][1] += delta_axis
        self.plot_points()

    def apply_spline(self):
        if len(self.selected_indices) < 3:
            messagebox.showwarning("Trūksta taškų", "Spline reikia bent 3 taškų")
            return

        from scipy.interpolate import splprep, splev

        self.push_history()
        pts = np.array([self.points[i] for i in self.selected_indices])
        tck, u = splprep([pts[:, 0], pts[:, 1]], s=0)
        new_pts = np.array(splev(u, tck)).T

        for idx, new_val in zip(self.selected_indices, new_pts):
            self.points[idx] = list(new_val)
        self.plot_points()

    def straighten_path(self):
        if len(self.points) < 2:
            return

        self.push_history()

        start = self.points[0]
        end = self.points[-1]
        for i in range(len(self.points)):
            t = i / (len(self.points) - 1)
            self.points[i] = [
                start[0] + t * (end[0] - start[0]),
                start[1] + t * (end[1] - start[1])
            ]
        self.plot_points()

    def save_gcode(self):
        if not self.gcode_lines:
            return

        new_lines = []
        point_idx = 0
        for line in self.gcode_lines:
            if line.startswith("G0") or line.startswith("G1"):
                if point_idx < len(self.points):
                    x, y = self.points[point_idx]
                    newline = re.sub(r"X-?\d+\.?\d*", f"X{x:.3f}", line)
                    newline = re.sub(r"Y-?\d+\.?\d*", f"Y{y:.3f}", newline)
                    new_lines.append(newline)
                    point_idx += 1
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        path = filedialog.asksaveasfilename(defaultextension=".gcode")
        if path:
            with open(path, 'w') as f:
                f.writelines(new_lines)
            messagebox.showinfo("Išsaugota", "Failas išsaugotas sėkmingai.")

if __name__ == "__main__":
    root = tk.Tk()
    app = GCodeEditor(root)
    root.mainloop()
