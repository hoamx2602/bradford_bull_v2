import cv2

BOX_COLORS_BGR = {
    'Team A':  (255, 80,  80 ),   # blue
    'Team B':  (80,  80,  255),   # red
    'Other':   (0,   220, 220),   # cyan
    'Unknown': (180, 180, 180),   # grey
}


def draw_label_box(img_bgr, box, label: str, team: str) -> None:
    """Draw a coloured bounding box with a filled label badge."""
    x1, y1, x2, y2 = [int(v) for v in box]
    color = BOX_COLORS_BGR.get(team, BOX_COLORS_BGR['Unknown'])

    cv2.rectangle(img_bgr, (x1, y1), (x2, y2), color, 2)
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.50, 1)
    cv2.rectangle(img_bgr, (x1, y1 - th - 6), (x1 + tw + 6, y1), color, -1)
    cv2.putText(img_bgr, label, (x1 + 3, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)
