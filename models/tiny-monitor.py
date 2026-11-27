import os
import time
import json
import cv2
import numpy as np

try:
    from ai_edge_litert.interpreter import Interpreter
except ImportError:
    import tensorflow as tf
    Interpreter = tf.lite.Interpreter

# --- Config ---
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vww_96_int8.tflite")
ROOM_ID = "A102"
CHECK_INTERVAL = 5.0
PERSON_THRESHOLD = 0.60
DIFF_PIXEL_THRESH = 30
LEFT_ITEM_MIN_RATIO = 0.015
MAX_LIGHT_CHANGE = 0.45


def run_person_detect(interpreter, in_det, out_det, rgb_96):
    """Runs 325KB INT8 vww_96_int8.tflite on a 96x96 RGB image."""
    if in_det["dtype"] == np.int8:
        inp = (rgb_96.astype(np.int16) - 128).astype(np.int8)
    else:
        inp = rgb_96.astype(np.uint8)

    inp = inp.reshape(in_det["shape"])

    t0 = time.perf_counter()
    interpreter.set_tensor(in_det["index"], inp)
    interpreter.invoke()
    infer_ms = (time.perf_counter() - t0) * 1000.0

    raw = interpreter.get_tensor(out_det["index"])[0]
    scale, zero_pt = out_det["quantization"]
    scores = (raw.astype(np.float32) - zero_pt) * scale if scale > 0 else raw.astype(np.float32)

    # Index 0 = non-person, Index 1 = person
    return float(scores[1]), infer_ms


def check_left_item(baseline_96, current_96):
    """Lightweight 96x96 grayscale diff (9 KB RAM, trivial to port to C)."""
    diff = cv2.absdiff(baseline_96, current_96)
    changed_ratio = np.count_nonzero(diff > DIFF_PIXEL_THRESH) / float(diff.size)
    if changed_ratio > MAX_LIGHT_CHANGE:
        return False, changed_ratio
    return changed_ratio >= LEFT_ITEM_MIN_RATIO, changed_ratio


def prep_96(bgr_frame):
    small_bgr = cv2.resize(bgr_frame, (96, 96), interpolation=cv2.INTER_AREA)
    rgb_96 = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2RGB)
    gray_96 = cv2.GaussianBlur(cv2.cvtColor(small_bgr, cv2.COLOR_BGR2GRAY), (3, 3), 0)
    return rgb_96, gray_96


def main():
    interpreter = Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    in_det = interpreter.get_input_details()[0]
    out_det = interpreter.get_output_details()[0]

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    for _ in range(15):
        cap.read()
    ret, init_frame = cap.read()
    _, baseline_96 = prep_96(init_frame)

    was_occupied = False
    last_check = 0.0
    status = "EMPTY (BASELINE SET)"
    last_ms = 0.0
    last_prob = 0.0

    print("[KEYS] 'c' = check now | 'b' = reset empty baseline | 'q' = quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        now = time.time()
        key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            break

        rgb_96, gray_96 = prep_96(frame)

        if key == ord("b"):
            baseline_96 = gray_96.copy()
            was_occupied = False
            status = "EMPTY (BASELINE RESET)"
            last_check = now
            print("[INFO] Baseline reset.")

        if (now - last_check) >= CHECK_INTERVAL or key == ord("c"):
            last_check = now
            last_prob, last_ms = run_person_detect(interpreter, in_det, out_det, rgb_96)
            occupied = last_prob >= PERSON_THRESHOLD

            if occupied:
                was_occupied = True
                status = f"OCCUPIED ({last_prob:.2f})"
                print("[TELEMETRY]", json.dumps({
                    "room_id": ROOM_ID,
                    "is_room_empty": False,
                    "left_item_detected": False,
                }))
            else:
                if was_occupied:
                    item_left, ratio = check_left_item(baseline_96, gray_96)
                    was_occupied = False
                    if item_left:
                        status = f"EMPTY - ITEM LEFT ({ratio*100:.1f}%)"
                        print("[ALERT]", json.dumps({
                            "room_id": ROOM_ID,
                            "is_room_empty": True,
                            "left_item_detected": True,
                        }))
                    else:
                        baseline_96 = gray_96.copy()
                        status = "EMPTY (CLEAN)"
                        print("[TELEMETRY]", json.dumps({
                            "room_id": ROOM_ID,
                            "is_room_empty": True,
                            "left_item_detected": False,
                        }))
                else:
                    status = "EMPTY (CLEAN)" if "ITEM LEFT" not in status else status

        hud = f"{ROOM_ID} | {status} | P:{last_prob:.2f} | {last_ms:.1f}ms"
        cv2.putText(frame, hud, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        cv2.imshow("Tiny Room Monitor (325KB Model)", frame)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()