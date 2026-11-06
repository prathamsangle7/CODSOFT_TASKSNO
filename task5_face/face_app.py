"""
CodSoft AI Internship - Task 5: Face Detection and Recognition (GUI app)

What you can do:
  1. Live face detection from your webcam
  2. Add a person (the app captures 30 face samples) and it trains automatically
  3. Live face recognition: known faces get a name, strangers get "Unknown"
  4. Open any photo and detect/recognize faces in it
  5. Save snapshots

Install:  pip install opencv-contrib-python numpy
Run:      python face_app.py        (keep face_engine.py in the same folder)
"""

import os
import re
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import cv2
import numpy as np

from face_engine import BASE_DIR, DEFAULT_THRESHOLD, FaceEngine, imread_unicode, imwrite_unicode

VW, VH = 640, 480                 # video area size
SAMPLES_TARGET = 30               # face samples captured per person
SAMPLE_EVERY = 4                  # save one sample every N frames (gives you time to move your head)

C = dict(
    bg="#0b1220", panel="#111a2e", card="#1e293b", text="#e2e8f0", muted="#94a3b8",
    accent="#22d3ee", good="#4ade80", bad="#f87171", warn="#facc15",
)
FONT = "Segoe UI"


def default_camera():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, VW)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VH)
    return cap


def message_frame(lines):
    """Dark placeholder image with some text (used when there is no camera)."""
    frame = np.full((VH, VW, 3), (46, 26, 17), np.uint8)
    for i, line in enumerate(lines):
        size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.putText(frame, line, ((VW - size[0]) // 2, VH // 2 - 20 + i * 36),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (230, 226, 226), 2, cv2.LINE_AA)
    return frame


class FaceApp:
    def __init__(self, root, camera_factory=None, data_dir=None):
        self.root = root
        root.title("Face Detection & Recognition · CodSoft AI")
        root.configure(bg=C["bg"])
        root.resizable(False, False)

        self.engine = FaceEngine(data_dir)
        self.cap = None
        self.camera_factory = camera_factory or default_camera
        self.static_image = None          # annotated photo shown instead of the camera
        self.current_display = None
        self.photo = None
        self.fps = 0.0
        self.last_time = time.time()
        self.frame_no = 0

        self.capturing = None             # name being captured, or None
        self.capture_count = 0

        self.mode = tk.StringVar(value="detect")
        self.threshold = tk.DoubleVar(value=DEFAULT_THRESHOLD)
        self.name_var = tk.StringVar()

        self.build_ui()
        self.refresh_people()
        self.open_camera()
        if self.engine.has_model:
            self.mode.set("recognize")
        self.loop()
        root.protocol("WM_DELETE_WINDOW", self.close)

    # ------------------------------------------------------------------ UI
    def build_ui(self):
        left = tk.Frame(self.root, bg=C["bg"])
        left.pack(side="left", padx=(14, 7), pady=14)
        self.video = tk.Label(left, bg=C["panel"], width=VW, height=VH, bd=0)
        self.video.pack()
        self.status = tk.Label(left, text="", font=(FONT, 10), bg=C["bg"], fg=C["muted"], anchor="w")
        self.status.pack(fill="x", pady=(8, 0))

        right = tk.Frame(self.root, bg=C["bg"], width=290)
        right.pack(side="right", fill="y", padx=(7, 14), pady=14)

        tk.Label(right, text="🧑‍💻  Face AI", font=(FONT, 17, "bold"), bg=C["bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(right, text="Haar detection + LBPH recognition", font=(FONT, 9),
                 bg=C["bg"], fg=C["muted"]).pack(anchor="w", pady=(0, 10))

        self.section(right, "MODE")
        for text, value in (("Detect faces", "detect"), ("Recognize faces", "recognize")):
            tk.Radiobutton(
                right, text=text, variable=self.mode, value=value, bg=C["bg"], fg=C["text"],
                selectcolor=C["card"], activebackground=C["bg"], activeforeground=C["text"],
                font=(FONT, 10), bd=0, highlightthickness=0, cursor="hand2",
            ).pack(anchor="w")

        self.tol_label = tk.Label(right, text="", font=(FONT, 9), bg=C["bg"], fg=C["muted"])
        self.tol_label.pack(anchor="w", pady=(8, 0))
        tk.Scale(
            right, from_=40, to=120, orient="horizontal", variable=self.threshold, showvalue=False,
            bg=C["bg"], troughcolor=C["card"], highlightthickness=0, bd=0, length=260,
            command=lambda v: self.update_tolerance(),
        ).pack(anchor="w")
        self.update_tolerance()

        self.section(right, "ADD A PERSON")
        self.entry = tk.Entry(right, textvariable=self.name_var, font=(FONT, 11), bg=C["card"], fg=C["text"],
                              insertbackground=C["text"], bd=0, highlightthickness=1,
                              highlightbackground=C["card"], highlightcolor=C["accent"])
        self.entry.pack(fill="x", ipady=7)
        self.add_btn = self.button(right, "📸  Capture 30 samples", self.toggle_capture, C["accent"], "#0b1220")
        self.add_btn.pack(fill="x", pady=(6, 0))

        self.section(right, "PEOPLE")
        self.people = tk.Listbox(right, height=5, bg=C["card"], fg=C["text"], bd=0, highlightthickness=0,
                                 font=(FONT, 10), selectbackground=C["accent"], selectforeground="#0b1220",
                                 activestyle="none")
        self.people.pack(fill="x")
        row = tk.Frame(right, bg=C["bg"])
        row.pack(fill="x", pady=(6, 0))
        self.button(row, "Train", self.train_clicked, C["card"], C["text"]).pack(side="left", expand=True, fill="x", padx=(0, 3))
        self.button(row, "Delete", self.delete_clicked, C["card"], C["bad"]).pack(side="left", expand=True, fill="x", padx=(3, 0))

        self.section(right, "PHOTOS & SNAPSHOTS")
        self.button(right, "🖼  Open image…", self.open_image, C["card"], C["text"]).pack(fill="x")
        self.button(right, "📷  Back to camera", self.back_to_camera, C["card"], C["text"]).pack(fill="x", pady=(6, 0))
        self.button(right, "💾  Save snapshot", self.save_snapshot, C["card"], C["text"]).pack(fill="x", pady=(6, 0))

    def section(self, parent, title):
        tk.Label(parent, text=title, font=(FONT, 8, "bold"), bg=C["bg"], fg=C["muted"]).pack(anchor="w", pady=(14, 4))

    def button(self, parent, text, command, bg, fg):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, bd=0, font=(FONT, 10, "bold"),
                         pady=7, cursor="hand2", activebackground=bg, activeforeground=fg)

    def update_tolerance(self):
        self.tol_label.config(text=f"Match tolerance: {int(self.threshold.get())}  (lower = stricter)")

    def set_status(self, text, color=None):
        self.status.config(text=text, fg=color or C["muted"])

    def refresh_people(self):
        self.people.delete(0, "end")
        for name, count in self.engine.list_people():
            self.people.insert("end", f"{name}  ({count} samples)")

    def selected_person(self):
        sel = self.people.curselection()
        if not sel:
            return None
        return self.engine.list_people()[sel[0]][0]

    # -------------------------------------------------------------- camera
    def open_camera(self):
        try:
            cap = self.camera_factory()
            self.cap = cap if cap is not None and cap.isOpened() else None
        except Exception:
            self.cap = None
        if self.cap is None:
            self.set_status("No camera found. You can still use 'Open image…'.", C["warn"])

    def close(self):
        if self.cap is not None:
            self.cap.release()
        self.root.destroy()

    def show(self, frame):
        h, w = frame.shape[:2]
        scale = min(VW / w, VH / h)
        if scale != 1:
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        h, w = frame.shape[:2]
        top, left = (VH - h) // 2, (VW - w) // 2
        frame = cv2.copyMakeBorder(frame, top, VH - h - top, left, VW - w - left,
                                   cv2.BORDER_CONSTANT, value=(46, 26, 17))
        self.current_display = frame
        data = cv2.imencode(".ppm", frame)[1].tobytes()       # PPM works in Tk with no extra libraries
        self.photo = tk.PhotoImage(data=data)
        self.video.config(image=self.photo)

    # ----------------------------------------------------------- main loop
    def loop(self):
        try:
            if self.static_image is not None:
                pass
            elif self.cap is None:
                self.show(message_frame(["No camera found", "Use 'Open image...' to try a photo"]))
            else:
                ok, frame = self.cap.read()
                if ok:
                    self.handle_frame(cv2.flip(frame, 1))      # mirror view, like a selfie camera
        finally:
            self.root.after(15, self.loop)

    def handle_frame(self, frame):
        self.frame_no += 1
        recognize = self.mode.get() == "recognize" and self.engine.has_model
        results = self.engine.process(frame, recognize, self.threshold.get())

        if self.capturing:
            self.capture_step(frame, results)

        display = frame.copy()
        self.engine.draw(display, results)
        if self.capturing:
            cv2.putText(display, f"Capturing {self.capture_count}/{SAMPLES_TARGET}  -  turn your head slowly",
                        (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (74, 222, 128), 2, cv2.LINE_AA)
        self.show(display)

        now = time.time()
        self.fps = 0.9 * self.fps + 0.1 * (1 / max(now - self.last_time, 1e-3))
        self.last_time = now
        if not self.capturing:
            if self.mode.get() == "recognize" and not self.engine.has_model:
                self.set_status("No trained model yet. Add a person first.", C["warn"])
            else:
                names = [r["name"] for r in results if r["name"]]
                extra = f"   |   {', '.join(names)}" if names else ""
                self.set_status(f"Faces: {len(results)}   |   {self.fps:.0f} FPS{extra}")

    # ------------------------------------------------------------- capture
    def toggle_capture(self):
        if self.capturing:
            self.finish_capture(cancelled=True)
            return
        name = re.sub(r"[^\w\- ]", "", self.name_var.get()).strip()[:30]
        if not name:
            messagebox.showinfo("Name needed", "Type the person's name first.")
            return
        if self.cap is None:
            messagebox.showinfo("No camera", "Capturing needs a camera.")
            return
        self.back_to_camera()
        self.capturing, self.capture_count = name, 0
        self.add_btn.config(text="⏹  Stop")
        self.mode.set("detect")

    def capture_step(self, frame, results):
        if len(results) != 1:
            self.set_status("Keep exactly ONE face in view.", C["warn"])
            return
        if self.frame_no % SAMPLE_EVERY:
            return
        self.engine.save_sample(self.capturing, frame, results[0]["box"])
        self.capture_count += 1
        self.set_status(f"Capturing {self.capture_count}/{SAMPLES_TARGET}", C["good"])
        if self.capture_count >= SAMPLES_TARGET:
            self.finish_capture()

    def finish_capture(self, cancelled=False):
        name, self.capturing = self.capturing, None
        self.add_btn.config(text="📸  Capture 30 samples")
        self.refresh_people()
        if cancelled and self.capture_count == 0:
            self.set_status("Capture stopped.")
            return
        self.train_clicked(quiet=True)
        self.mode.set("recognize")
        self.name_var.set("")
        self.set_status(f"Added {name}. Recognition is ON.", C["good"])

    # -------------------------------------------------------- train/delete
    def train_clicked(self, quiet=False):
        try:
            people, images = self.engine.train()
        except ValueError as err:
            messagebox.showinfo("Nothing to train", str(err))
            return
        if not quiet:
            self.set_status(f"Trained on {people} person(s), {images} images.", C["good"])

    def delete_clicked(self):
        name = self.selected_person()
        if not name:
            messagebox.showinfo("Pick someone", "Select a person in the list first.")
            return
        if messagebox.askyesno("Delete", f"Delete all samples of '{name}'?"):
            self.engine.delete_person(name)
            self.refresh_people()
            self.set_status(f"Deleted {name}.")

    # ----------------------------------------------------- photos/snapshot
    def open_image(self):
        path = filedialog.askopenfilename(
            title="Choose a photo", filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp"), ("All files", "*.*")])
        if path:
            self.load_image(path)

    def load_image(self, path):
        try:
            recognize = self.mode.get() == "recognize" and self.engine.has_model
            image, results = self.engine.analyze_image(path, recognize, self.threshold.get())
        except ValueError as err:
            messagebox.showerror("Error", str(err))
            return
        self.static_image = image
        self.show(image)
        names = [r["name"] for r in results if r["name"]]
        extra = f"   |   {', '.join(names)}" if names else ""
        self.set_status(f"Photo: found {len(results)} face(s){extra}", C["good"] if results else C["warn"])

    def back_to_camera(self):
        self.static_image = None

    def save_snapshot(self):
        if self.current_display is None:
            return
        folder = os.path.join(BASE_DIR, "snapshots")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, datetime.now().strftime("snapshot_%Y%m%d_%H%M%S.png"))
        imwrite_unicode(path, self.current_display)
        self.set_status(f"Saved: {path}", C["good"])


if __name__ == "__main__":
    root = tk.Tk()
    try:
        FaceApp(root)
    except RuntimeError as err:                 # e.g. OpenCV not installed properly
        print("\nSETUP PROBLEM:\n" + str(err))
        messagebox.showerror("Setup problem", str(err))
        root.destroy()
        raise SystemExit(1)
    root.mainloop()
