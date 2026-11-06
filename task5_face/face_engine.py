"""
CodSoft AI Internship - Task 5: Face Detection and Recognition (engine)

Detection   : Haar cascade (OpenCV)
Recognition : LBPH (Local Binary Patterns Histograms), trained on photos YOU capture

Install:  pip install opencv-contrib-python numpy
          (use opencv-contrib-python, NOT opencv-python, because the face module lives in "contrib")

Quick test on a photo:  python face_engine.py path\\to\\photo.jpg
Full app with webcam:   python face_app.py
"""

import json
import os
import shutil
import sys
import urllib.request

import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "face_data")

FACE_SIZE = (200, 200)          # every face is resized to this before training/recognizing
DEFAULT_THRESHOLD = 75.0        # LBPH distance: LOWER = more similar. Above this -> "Unknown"

# BGR colours
GREEN = (128, 222, 74)
RED = (113, 113, 248)
CYAN = (238, 211, 34)
DARK = (30, 20, 11)


CASCADE_NAME = "haarcascade_frontalface_default.xml"
CASCADE_URL = "https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/" + CASCADE_NAME


def check_opencv():
    """Stop early, with a clear fix, if OpenCV is damaged (usually from mixing opencv-python and contrib)."""
    missing = [name for name in ("CascadeClassifier", "face") if not hasattr(cv2, name)]
    if missing or not hasattr(cv2, "__file__"):
        raise RuntimeError(
            "Your OpenCV install is broken or incomplete (missing: " + ", ".join(missing or ["files"]) + ").\n"
            "This usually happens when opencv-python and opencv-contrib-python were installed together.\n\n"
            "Fix it with a clean reinstall (run these in PowerShell):\n"
            "  pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless opencv-contrib-python-headless\n"
            "  pip install --no-cache-dir opencv-contrib-python==4.11.0.86\n"
        )


def find_cascade(data_dir):
    """
    Locate the Haar cascade file. Some OpenCV builds (for example the 5.0 pip wheels) do not
    include it and have no cv2.data, so if it is not found we download it once from OpenCV's GitHub.
    """
    folders = []
    data = getattr(cv2, "data", None)
    if data is not None and hasattr(data, "haarcascades"):
        folders.append(data.haarcascades)
    package = os.path.dirname(cv2.__file__)
    folders += [os.path.join(package, "data"), package, data_dir]
    for folder in folders:
        path = os.path.join(folder, CASCADE_NAME)
        if os.path.exists(path):
            return path

    target = os.path.join(data_dir, CASCADE_NAME)
    os.makedirs(data_dir, exist_ok=True)
    try:
        print("Downloading the face detector file (one time only)...")
        urllib.request.urlretrieve(CASCADE_URL, target)
    except Exception as err:
        if os.path.exists(target):
            os.remove(target)
        raise RuntimeError(
            "Could not find or download the Haar cascade file.\n"
            f"Download it manually from:\n  {CASCADE_URL}\n"
            f"and save it here:\n  {target}\n"
            f"(reason: {err})"
        )
    return target


def imread_unicode(path):
    """cv2.imread that also works with non-English characters in the path (Windows)."""
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def imwrite_unicode(path, image):
    ext = os.path.splitext(path)[1] or ".png"
    ok, buf = cv2.imencode(ext, image)
    if ok:
        buf.tofile(path)
    return ok


def augment(face):
    """Make a few extra training images from one: mirror and small rotations."""
    h, w = face.shape[:2]
    out = [face, cv2.flip(face, 1)]
    for angle in (5, -5):
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        out.append(cv2.warpAffine(face, m, (w, h), borderMode=cv2.BORDER_REPLICATE))
    return out


class FaceEngine:
    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DATA_DIR
        self.faces_dir = os.path.join(self.data_dir, "faces")
        self.model_path = os.path.join(self.data_dir, "model.yml")
        self.labels_path = os.path.join(self.data_dir, "labels.json")
        os.makedirs(self.faces_dir, exist_ok=True)

        check_opencv()
        self.detector = cv2.CascadeClassifier(find_cascade(self.data_dir))
        if self.detector.empty():
            raise RuntimeError("Could not load the Haar cascade file. Delete face_data/" + CASCADE_NAME + " and retry.")

        self.recognizer = None
        self.labels = {}
        self.load_model()

    # ------------------------------------------------------------ detection
    def detect(self, frame, fast=True):
        """Return face boxes (x, y, w, h), biggest first.
        fast=True (webcam): detect on a half-size copy, much quicker, finds faces wider than ~60 px.
        fast=False (photos): full-size detection, also finds small faces in group photos."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        scale = 0.5 if (fast and gray.shape[1] > 400) else 1.0
        if scale != 1.0:
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        gray = cv2.equalizeHist(gray)
        min_side = int(60 * scale)
        boxes = self.detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                               minSize=(min_side, min_side))
        boxes = [tuple(int(v / scale) for v in b) for b in boxes]
        return sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)

    def face_patch(self, frame, box):
        """Crop the face, make it grayscale, 200x200 and contrast-normalised."""
        x, y, w, h = box
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        patch = cv2.resize(gray[y:y + h, x:x + w], FACE_SIZE)
        return cv2.equalizeHist(patch)

    # ------------------------------------------------------------- dataset
    def list_people(self):
        people = []
        for name in sorted(os.listdir(self.faces_dir)):
            folder = os.path.join(self.faces_dir, name)
            if os.path.isdir(folder):
                count = len([f for f in os.listdir(folder) if f.lower().endswith(".png")])
                people.append((name, count))
        return people

    def save_sample(self, name, frame, box):
        folder = os.path.join(self.faces_dir, name)
        os.makedirs(folder, exist_ok=True)
        index = len([f for f in os.listdir(folder) if f.lower().endswith(".png")]) + 1
        imwrite_unicode(os.path.join(folder, f"{index:03d}.png"), self.face_patch(frame, box))
        return index

    def delete_person(self, name):
        shutil.rmtree(os.path.join(self.faces_dir, name), ignore_errors=True)
        if self.list_people():
            self.train()
        else:
            self.recognizer, self.labels = None, {}
            for path in (self.model_path, self.labels_path):
                if os.path.exists(path):
                    os.remove(path)

    # ------------------------------------------------------------ training
    def train(self):
        """Train LBPH on everything in faces/. Returns (people, images used)."""
        images, ids, labels = [], [], {}
        for pid, (name, _) in enumerate(self.list_people()):
            labels[pid] = name
            folder = os.path.join(self.faces_dir, name)
            for fn in sorted(os.listdir(folder)):
                if not fn.lower().endswith(".png"):
                    continue
                face = cv2.imdecode(np.fromfile(os.path.join(folder, fn), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
                if face is None:
                    continue
                for variant in augment(face):
                    images.append(variant)
                    ids.append(pid)
        if not images:
            raise ValueError("No face samples yet. Add a person first.")

        recognizer = cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)
        recognizer.train(images, np.array(ids))
        recognizer.write(self.model_path)
        with open(self.labels_path, "w", encoding="utf-8") as f:
            json.dump(labels, f)
        self.recognizer, self.labels = recognizer, labels
        return len(labels), len(images)

    def load_model(self):
        if not (os.path.exists(self.model_path) and os.path.exists(self.labels_path)):
            return False
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(self.model_path)
        with open(self.labels_path, encoding="utf-8") as f:
            self.labels = {int(k): v for k, v in json.load(f).items()}
        self.recognizer = recognizer
        return True

    @property
    def has_model(self):
        return self.recognizer is not None

    # --------------------------------------------------------- recognition
    def identify(self, frame, box, threshold=DEFAULT_THRESHOLD):
        """Return (name, distance). Name is 'Unknown' if the face is too different from everyone."""
        label, distance = self.recognizer.predict(self.face_patch(frame, box))
        if distance > threshold:
            return "Unknown", float(distance)
        return self.labels.get(int(label), "Unknown"), float(distance)

    def process(self, frame, recognize=False, threshold=DEFAULT_THRESHOLD, fast=True):
        results = []
        for box in self.detect(frame, fast):
            name, distance = (None, None)
            if recognize and self.has_model:
                name, distance = self.identify(frame, box, threshold)
            results.append({"box": box, "name": name, "distance": distance})
        return results

    # ------------------------------------------------------------- drawing
    @staticmethod
    def draw(frame, results):
        for r in results:
            x, y, w, h = r["box"]
            if r["name"] is None:
                color, text = CYAN, "Face"
            elif r["name"] == "Unknown":
                color, text = RED, "Unknown"
            else:
                match = int(max(0, min(100, 100 - r["distance"])))
                color, text = GREEN, f"{r['name']}  {match}%"

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            top = y - th - 12 if y - th - 12 > 0 else y + h
            cv2.rectangle(frame, (x, top), (x + tw + 12, top + th + 12), color, -1)
            cv2.putText(frame, text, (x + 6, top + th + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, DARK, 2, cv2.LINE_AA)
        return frame

    def analyze_image(self, path, recognize=False, threshold=DEFAULT_THRESHOLD):
        """Detect (and optionally recognize) faces in a photo. Returns (annotated image, results)."""
        image = imread_unicode(path)
        if image is None:
            raise ValueError("Could not read that image.")
        results = self.process(image, recognize, threshold, fast=False)
        return self.draw(image, results), results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python face_engine.py path\\to\\photo.jpg")
        sys.exit(1)
    engine = FaceEngine()
    annotated, found = engine.analyze_image(sys.argv[1], recognize=engine.has_model)
    print(f"Found {len(found)} face(s):")
    for r in found:
        print("  ", r)
    out = os.path.splitext(sys.argv[1])[0] + "_result.png"
    imwrite_unicode(out, annotated)
    print("Saved:", out)
