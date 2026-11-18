import cv2
from pyzbar.pyzbar import decode, ZBarSymbol
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
import os
import csv
import re
from datetime import datetime

# ------------------------------ קובץ CSV -------------------------------------
BASE_DIR = os.path.join(os.path.expanduser("~"), "OneDrive", "שולחן העבודה")
RESULT_CSV = os.path.join(BASE_DIR, "barcode_inventory.csv")

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# ---------------------------------- פונקציות עזר ------------------------------
def parse_date(date_str):
    if not date_str:
        return None
    date_str = date_str.replace("-", "/").replace(".", "/").strip()
    parts = date_str.split("/")
    try:
        if len(parts) == 3:
            day, month, year = map(int, parts)
        elif len(parts) == 2:
            day = 1
            month, year = map(int, parts)
        else:
            return None
        if year < 100:
            year += 2000
        return datetime(year, month, day)
    except:
        return None

def read_csv():
    items = []
    if not os.path.exists(RESULT_CSV):
        return items
    with open(RESULT_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append({
                "Barcode": str(row["Barcode"]).strip(),
                "EXP Date": row["EXP Date"],
                "Name": row["Name"],
                "Quantity": int(row["Quantity"])
            })
    return items

def write_csv(items):
    with open(RESULT_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Barcode", "EXP Date", "Name", "Quantity"])
        writer.writeheader()
        for item in items:
            # שמירה תמידית בפורמט DD/MM/YYYY
            item_date = parse_date(item["EXP Date"])
            item["EXP Date"] = item_date.strftime("%d/%m/%Y") if item_date else ""
            writer.writerow(item)

# ------------------------------- סריקת ברקוד ------------------------------------
def scan_barcode():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(" לא ניתן לפתוח את המצלמה")
        return None
    barcode_text = None
    print("סריקה - החזיקו את המוצר מול המצלמה (ברקוד בלבד)")
    cv2.namedWindow("סריקה ברקוד", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("סריקה ברקוד", cv2.WND_PROP_TOPMOST, 1)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        barcodes = decode(frame, symbols=[
            ZBarSymbol.EAN13, ZBarSymbol.EAN8, ZBarSymbol.UPCA,
            ZBarSymbol.UPCE, ZBarSymbol.CODE128, ZBarSymbol.CODE39
        ])
        if barcodes:
            barcode_text = barcodes[0].data.decode("utf-8")
            x, y, w, h = barcodes[0].rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, barcode_text, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            print(f"זוהה ברקוד: {barcode_text}")
            cv2.imshow("ברקוד זוהה", frame)
            cv2.waitKey(1000)
            break
        cv2.imshow("סריקה ברקוד", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    return barcode_text

# ------------------------------- סריקת תאריך EXP ------------------------------------
def scan_exp_date():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(" לא ניתן לפתוח את המצלמה")
        return None
    exp_patterns = [
        r"EXP\s*[:.]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        r"Exp\s*[:.]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        r"EXP\s*[:.]?\s*(\d{1,2}[./-]\d{2,4})",
        r"Exp\s*[:.]?\s*(\d{1,2}[./-]\d{2,4})",
        r"EXP\s*[:.]?\s*(\d{1,2})\s+(\d{2,4})",
        r"Exp\s*[:.]?\s*(\d{1,2})\s+(\d{2,4})"
    ]
    exp_date = None
    print(" סריקה - החזיקו את המוצר מול המצלמה (תאריך EXP)")
    cv2.namedWindow("סריקה EXP", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("סריקה EXP", cv2.WND_PROP_TOPMOST, 1)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray)
        if not exp_date:
            for pattern in exp_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if match.lastindex == 2:
                        month = int(match.group(1))
                        year = int(match.group(2))
                        day = 1
                        exp_date = f"{day}/{month}/{year}"
                    else:
                        exp_date = match.group(1)
                    parsed = parse_date(exp_date)
                    if parsed:
                        exp_date = parsed.strftime("%d/%m/%Y")
                    print(f"זוהה תאריך: {exp_date}")
                    break
        if exp_date:
            cv2.putText(frame, f"EXP: {exp_date}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, "ENTER=OK | r=Retry", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        cv2.imshow("סריקה EXP", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 13 and exp_date:
            cap.release()
            cv2.destroyAllWindows()
            break
        elif key == ord('r'):
            exp_date = None
        elif key == ord('q'):
            exp_date = None
            break
    cap.release()
    cv2.destroyAllWindows()
    return exp_date

# ------------------------------------- מחיקת פריט -----------------------------------
def delete_item_from_csv():
    items = read_csv()
    if not items:
        print("אין פריטים בקובץ למחיקה")
        return

    barcode = scan_barcode()
    if not barcode:
        print("ברקוד לא זוהה")
        return

    exp_date = scan_exp_date()
    if not exp_date:
        print(" תאריך EXP לא זוהה")
        return
    matched = None
    for item in items:
        if item["Barcode"].lstrip("'").strip() == barcode.strip() and item["EXP Date"].strip() == exp_date.strip():
            matched = item
            break

    if not matched:
        print(f" לא נמצא פריט עם ברקוד {barcode} ותאריך EXP {exp_date}")
        return

    print(f"פריט שנמצא: {matched['Name']} (Quantity={matched['Quantity']})")

    while True:
        qty_input = input("הכנס כמות למחיקה: ")
        if qty_input.isdigit() and int(qty_input) > 0:
            qty = int(qty_input)
            break
        else:
            print(" הכנס מספר תקין")

    if qty >= matched["Quantity"]:
        items.remove(matched)
        print(" כל הפריט הוסר מהקובץ")
    else:
        matched["Quantity"] -= qty
        print(f"הכמות עודכנה: {matched['Quantity']} שנותרה")

    write_csv(items)

# ---------------------------------- הפעלה --------------------------------------
if __name__ == "__main__":
    delete_item_from_csv()