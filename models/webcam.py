import os
import re
import time
import json
import cv2
import numpy as np

try:
    from ai_edge_litert.interpreter import Interpreter
except ImportError:
    import tensorflow as tf
    Interpreter = tf.lite.Interpreter

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "efficientdet_lite2_448_ptq.tflite")
LABELS_PATH = os.path.join(BASE_DIR, "coco_labels.txt")

ROOM_ID = "A102"
CHECK_INTERVAL_SECONDS = 10.0  # Change to 120.0 (2 min) for production
PERSON_CONFIDENCE = 0.45

# Left-item detection tuning (class-agnostic: catches phones, headphones, bottles, bags)
DIFF_THRESHOLD = 32            # Sensitivity to new objects (lower = more sensitive)
MIN_ITEM_AREA_PX = 750         # Minimum size in pixels (~27x27 px) to ignore sensor noise
MAX_CHANGE_RATIO = 0.45        # Skip diff if >45% of room changed (lights switched on/off)
MIN_NOVEL_EDGE_RATIO = 0.010   # Rejects smooth shadows/glare while keeping phone/headphone edges
IGNORED_FURNITURE = {"chair", "couch", "dining table", "bench", "bed", "tv"}


def load_labels(path):
    labels = {}
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            match = re.match(r"^(\d+)\s+(.+)$", line)
            if match:
                labels[int(match.group(1))] = match.group(2)
            else:
                labels[idx] = line
    return labels


def resolve_output_indices(output_details):
    """Maps boxes, classes, scores, count for 4-output post-processed TFLite models."""
    if len(output_details) < 4:
        raise ValueError(f"Expected 4-output model, got {len(output_details)}.")

    boxes_idx = count_idx = scores_idx = classes_idx = None
    two_d_indices = []

    for i, d in enumerate(output_details):
        shape = d["shape"]
        if len(shape) == 3 and shape[-1] == 4:
            boxes_idx = i
        elif int(np.prod(shape)) == 1:
            count_idx = i
        else:
            two_d_indices.append(i)

    for i in two_d_indices:
        name = output_details[i]["name"]
        if name.endswith(":1"):
            classes_idx = i
        elif name.endswith(":2"):
            scores_idx = i

    if scores_idx is None or classes_idx is None:
        classes_idx, scores_idx = two_d_indices[0], two_d_indices[1]

    return boxes_idx, classes_idx, scores_idx, count_idx


def prep_baseline_data(bgr_frame):
    """Stores blurred LAB color and gray images for Before/After comparison."""
    blurred = cv2.GaussianBlur(bgr_frame, (7, 7), 0)
    lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    return {"lab": lab, "gray": gray}


def run_detector(interpreter, input_details, output_details, out_map, labels, bgr_img, min_score=0.35):
    """Runs INT8 EfficientDet-Lite2 on a BGR image."""
    _, in_h, in_w, _ = input_details[0]["shape"]
    in_dtype = input_details[0]["dtype"]
    orig_h, orig_w = bgr_img.shape[:2]

    rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (in_w, in_h))

    if in_dtype == np.uint8:
        input_tensor = np.expand_dims(resized, axis=0).astype(np.uint8)
    elif in_dtype == np.int8:
        input_tensor = np.expand_dims(resized.astype(np.int16) - 128, axis=0).astype(np.int8)
    else:
        input_tensor = np.expand_dims(resized.astype(np.float32) / 255.0, axis=0)

    t0 = time.perf_counter()
    interpreter.set_tensor(input_details[0]["index"], input_tensor)
    interpreter.invoke()
    infer_ms = (time.perf_counter() - t0) * 1000.0

    boxes_idx, classes_idx, scores_idx, count_idx = out_map
    boxes = interpreter.get_tensor(output_details[boxes_idx]["index"])[0]
    classes = interpreter.get_tensor(output_details[classes_idx]["index"])[0]
    scores = interpreter.get_tensor(output_details[scores_idx]["index"])[0]
    count = int(interpreter.get_tensor(output_details[count_idx]["index"])[0])

    if len(scores) > 0 and (np.max(scores) > 1.01 or np.min(scores) < -0.01):
        scores, classes = classes, scores

    detections = []
    for i in range(min(count, len(scores))):
        score = float(scores[i])
        if score < min_score:
            continue
        class_id = int(round(float(classes[i])))
        label = labels.get(class_id, f"id_{class_id}")
        ymin, xmin, ymax, xmax = boxes[i]
        detections.append({
            "label": label,
            "score": round(score, 2),
            "box": (
                max(0, int(xmin * orig_w)),
                max(0, int(ymin * orig_h)),
                min(orig_w, int(xmax * orig_w)),
                min(orig_h, int(ymax * orig_h)),
            ),
        })
    return detections, infer_ms


def is_valid_new_object(before_gray_patch, after_gray_patch):
    """
    Confirms the region introduces NEW edges (an object placed down) rather than
    smooth window glare or a 'ghost hole' where an existing item was picked up.
    """
    before_edges = cv2.Canny(before_gray_patch, 45, 130)
    after_edges = cv2.Canny(after_gray_patch, 45, 130)

    before_count = np.count_nonzero(before_edges)
    after_count = np.count_nonzero(after_edges)

    # If edges disappeared compared to baseline, an item was removed—not left behind
    if before_count > 15 and after_count < (before_count * 0.70):
        return False

    before_dilated = cv2.dilate(before_edges, np.ones((3, 3), np.uint8), iterations=1)
    novel_edges = cv2.bitwise_and(after_edges, cv2.bitwise_not(before_dilated))
    novel_ratio = np.count_nonzero(novel_edges) / float(max(1, after_gray_patch.size))
    return novel_ratio >= MIN_NOVEL_EDGE_RATIO


def detect_left_items(baseline, after_bgr, interpreter, input_details, output_details, out_map, labels):
    """
    Compares Before vs. After frames using LAB lightness + color difference.
    Returns bounding boxes of any newly left-behind objects without guessing their names.
    """
    h, w = after_bgr.shape[:2]
    current = prep_baseline_data(after_bgr)

    # Combine Lightness (L) and Color (A, B) differences so dark & colored items both stand out
    diff_l = cv2.absdiff(baseline["lab"][:, :, 0], current["lab"][:, :, 0]).astype(np.float32)
    diff_a = cv2.absdiff(baseline["lab"][:, :, 1], current["lab"][:, :, 1]).astype(np.float32)
    diff_b = cv2.absdiff(baseline["lab"][:, :, 2], current["lab"][:, :, 2]).astype(np.float32)
    combined_diff = np.clip(0.75 * diff_l + 1.25 * diff_a + 1.25 * diff_b, 0, 255).astype(np.uint8)

    _, thresh = cv2.threshold(combined_diff, DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)

    if (np.count_nonzero(thresh) / float(thresh.size)) > MAX_CHANGE_RATIO:
        print("[WARN] Major lighting shift detected; skipping left-item check.")
        return []

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    left_boxes = []

    for cnt in contours:
        if cv2.contourArea(cnt) < MIN_ITEM_AREA_PX:
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)

        # Reject smooth shadows/glare and removed-object ghost holes
        if not is_valid_new_object(
            baseline["gray"][y:y + bh, x:x + bw],
            current["gray"][y:y + bh, x:x + bw]
        ):
            continue

        # Check zoomed crop with NPU solely to ignore shifted chairs/sofas
        pad_x, pad_y = int(bw * 0.35) + 20, int(bh * 0.35) + 20
        cx1, cy1 = max(0, x - pad_x), max(0, y - pad_y)
        cx2, cy2 = min(w, x + bw + pad_x), min(h, y + bh + pad_y)
        crop_dets, _ = run_detector(
            interpreter, input_details, output_details, out_map, labels,
            after_bgr[cy1:cy2, cx1:cx2], min_score=0.38
        )
        if any(d["label"] in IGNORED_FURNITURE for d in crop_dets):
            continue

        left_boxes.append((x, y, x + bw, y + bh))

    return left_boxes


def main():
    for path in (MODEL_PATH, LABELS_PATH):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Missing required file: {path}")

    labels = load_labels(LABELS_PATH)
    interpreter = Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    out_map = resolve_output_indices(output_details)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open laptop webcam.")

    # Let camera auto-exposure settle, then capture empty-room baseline automatically
    for _ in range(15):
        cap.read()
    ret, init_frame = cap.read()
    if not ret:
        raise RuntimeError("Failed to read initial frame from webcam.")

    baseline = prep_baseline_data(init_frame)
    was_occupied = False
    last_check_time = 0.0

    room_status = "EMPTY (AUTO-BASELINE SET)"
    last_people_boxes = []
    last_left_boxes = []
    last_infer_ms = 0.0

    print(f"[INFO] Room {ROOM_ID} Monitor Ready.")
    print("[KEYS] 'c' = check now | 'b' = reset empty baseline | 'q' = quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        now = time.time()
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key == ord("b"):
            baseline = prep_baseline_data(frame)
            was_occupied = False
            last_left_boxes = []
            room_status = "EMPTY (BASELINE RESET)"
            last_check_time = now
            print("[INFO] Empty-room baseline reset.")

        force_check = (key == ord("c"))
        time_due = (now - last_check_time) >= CHECK_INTERVAL_SECONDS

        if time_due or force_check:
            last_check_time = now
            full_dets, last_infer_ms = run_detector(
                interpreter, input_details, output_details, out_map, labels, frame, min_score=PERSON_CONFIDENCE
            )
            people = [d for d in full_dets if d["label"] == "person"]
            people_count = len(people)
            last_people_boxes = [d["box"] for d in people]

            if people_count > 0:
                was_occupied = True
                last_left_boxes = []
                room_status = f"OCCUPIED ({people_count} people)"
                print("[TELEMETRY]", json.dumps({
                    "room_id": ROOM_ID,
                    "is_room_empty": False,
                    "people_count": people_count,
                    "lights_can_be_off": False,
                    "timestamp": int(now),
                }))
            else:
                if was_occupied:
                    last_left_boxes = detect_left_items(
                        baseline, frame, interpreter, input_details, output_details, out_map, labels
                    )
                    was_occupied = False

                    if last_left_boxes:
                        room_status = f"EMPTY - {len(last_left_boxes)} ITEM(S) LEFT BEHIND"
                        print("\n[ALERT -> STAFF DASHBOARD]", json.dumps({
                            "room_id": ROOM_ID,
                            "is_room_empty": True,
                            "people_count": 0,
                            "lights_can_be_off": True,
                            "left_item_detected": True,
                            "left_item_count": len(last_left_boxes),
                            "timestamp": int(now),
                        }))
                    else:
                        baseline = prep_baseline_data(frame)
                        room_status = "EMPTY (CLEAN - BASELINE REFRESHED)"
                        print(f"[TELEMETRY] Room {ROOM_ID} empty and clean.")
                else:
                    room_status = "EMPTY (CLEAN)" if not last_left_boxes else room_status

        # --- Draw Preview Overlay ---
        for (x1, y1, x2, y2) in last_people_boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)
            cv2.putText(frame, "person", (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 0), 2)

        for idx, (x1, y1, x2, y2) in enumerate(last_left_boxes, start=1):
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(frame, f"LEFT ITEM #{idx}", (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        next_in = max(0, int(CHECK_INTERVAL_SECONDS - (now - last_check_time)))
        hud = f"Room {ROOM_ID} | {room_status} | Next: {next_in}s | NPU: {last_infer_ms:.0f}ms"
        cv2.putText(frame, hud, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)

        cv2.imshow("PSOC Edge E84 - Room Monitor", frame)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()