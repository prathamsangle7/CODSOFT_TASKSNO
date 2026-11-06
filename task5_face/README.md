# Task 5: Face Detection and Recognition

Live face detection and recognition from a webcam. Built in Python with OpenCV for the CodSoft AI internship.

## Features
- Face detection with a Haar cascade
- Face recognition with LBPH, trained on photos you capture in the app
- Unknown-face detection with an adjustable tolerance slider
- Add and delete people, open photos, save snapshots
- Tkinter GUI

## How it works
1. Detect faces in each frame (Haar cascade)
2. Crop each face, make it grayscale, resize to 200x200 and normalise contrast
3. LBPH compares the face's texture pattern with the people you trained
4. A small distance means a match. A large distance means "Unknown"

## Install and run
pip install opencv-contrib-python==4.11.0.86 numpy
python face_app.py

Install `opencv-contrib-python` only, not together with `opencv-python`.
