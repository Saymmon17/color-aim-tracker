# debug_aim.py
import cv2
import numpy as np
import pyautogui
import mss
import time
import math
import random

# Segurança: mantém fail-safe por padrão (mas o script faz clamp nas coordenadas)
pyautogui.FAILSAFE = True

# Parâmetros iniciais (ajuste com as trackbars)
DEFAULT_LH, DEFAULT_LS, DEFAULT_LV = 120, 50, 50
DEFAULT_HH, DEFAULT_HS, DEFAULT_HV = 160, 255, 255

sensitivity = 12.0        # quanto maior, mais lento o movimento (ajuste)
accuracy_threshold = 8    # quando parar (em pixels)
random_jitter = 1.5       # imprecisão para parecer humano
move_duration = 0.03      # duração do movimento do pyautogui
safe_margin = 40

time.sleep(1.0)

def nothing(x):
    pass
cv2.namedWindow('Trackbars', cv2.WINDOW_NORMAL)
cv2.createTrackbar('LH','Trackbars', DEFAULT_LH, 179, nothing)
cv2.createTrackbar('LS','Trackbars', DEFAULT_LS, 255, nothing)
cv2.createTrackbar('LV','Trackbars', DEFAULT_LV, 255, nothing)
cv2.createTrackbar('HH','Trackbars', DEFAULT_HH, 179, nothing)
cv2.createTrackbar('HS','Trackbars', DEFAULT_HS, 255, nothing)
cv2.createTrackbar('HV','Trackbars', DEFAULT_HV, 255, nothing)

movement_enabled = False
calibrated_center = None

with mss.mss() as sct:
    print("Monitores detectados:", sct.monitors)

    monitor = sct.monitors[1]
    left, top = monitor['left'], monitor['top']
    screen_w, screen_h = monitor['width'], monitor['height']
    calibrated_center = (left + screen_w // 2, top + screen_h // 2)

    print("Centro inicial (absoluto):", calibrated_center)
    print("Teclas: 'c' calibrar centro na posição atual do mouse, 'm' ativar/desativar movimento, 'q' sair")

    while True:
        lh = cv2.getTrackbarPos('LH','Trackbars')
        ls = cv2.getTrackbarPos('LS','Trackbars')
        lv = cv2.getTrackbarPos('LV','Trackbars')
        hh = cv2.getTrackbarPos('HH','Trackbars')
        hs = cv2.getTrackbarPos('HS','Trackbars')
        hv = cv2.getTrackbarPos('HV','Trackbars')

        lower = np.array([lh, ls, lv])
        upper = np.array([hh, hs, hv])

        sct_img = np.array(sct.grab(monitor))
        frame_bgr = cv2.cvtColor(sct_img, cv2.COLOR_BGRA2BGR)
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        center_rel_x = calibrated_center[0] - left
        center_rel_y = calibrated_center[1] - top
        cv2.drawMarker(frame_bgr, (int(center_rel_x), int(center_rel_y)),
                       (255,255,255), markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)

        if contours:
            c = max(contours, key=cv2.contourArea)
            x, y, w_box, h_box = cv2.boundingRect(c)
            target_rel_x = x + w_box // 2
            target_rel_y = y + h_box // 2
            target_abs_x = left + target_rel_x
            target_abs_y = top + target_rel_y

            cv2.rectangle(frame_bgr, (x,y), (x+w_box, y+h_box), (0,255,0), 2)
            cv2.circle(frame_bgr, (int(target_rel_x), int(target_rel_y)), 6, (0,0,255), -1)
            cv2.line(frame_bgr, (int(center_rel_x), int(center_rel_y)),
                     (int(target_rel_x), int(target_rel_y)), (255,0,0), 1)

            dx = target_abs_x - calibrated_center[0]
            dy = target_abs_y - calibrated_center[1]
            dist = math.hypot(dx, dy)

            cv2.putText(frame_bgr, f"Alvo abs: ({target_abs_x},{target_abs_y})", (10,30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 1)
            cv2.putText(frame_bgr, f"dx,dy: ({dx:.1f},{dy:.1f}) d={dist:.1f}", (10,55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 1)

            if movement_enabled and dist > accuracy_threshold:
                move_x = dx / sensitivity + random.uniform(-random_jitter, random_jitter)
                move_y = dy / sensitivity + random.uniform(-random_jitter, random_jitter)

                cur_x, cur_y = pyautogui.position()
                new_x = int(cur_x + move_x)
                new_y = int(cur_y + move_y)

                screen_total_w, screen_total_h = pyautogui.size()
                new_x = max(safe_margin, min(screen_total_w - safe_margin, new_x))
                new_y = max(safe_margin, min(screen_total_h - safe_margin, new_y))

                try:
                    pyautogui.moveTo(new_x, new_y, duration=move_duration)
                except Exception as e:
                    print("Erro movendo mouse:", e)
                    
        cv2.imshow("Detector (visual)", frame_bgr)
        cv2.imshow("Mask", mask)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('m'):
            movement_enabled = not movement_enabled
            print("Movement enabled:", movement_enabled)
        elif key == ord('c'):
            pos = pyautogui.position()
            calibrated_center = (pos[0], pos[1])
            print("Centro calibrado para (abs):", calibrated_center)

    cv2.destroyAllWindows()
