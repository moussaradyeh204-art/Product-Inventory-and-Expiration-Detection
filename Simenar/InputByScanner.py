import cv2
import pytesseract
import os
import csv
import re
from datetime import datetime, timedelta

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -------------------------------- קובץ CSV ------------------------------
BASE_DIR = os.path.join(os.path.expanduser("~"), "OneDrive", "שולחן העבודה")
RESULT_CSV = os.path.join(BASE_DIR, "barcode_inventory.csv")


if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# -------------------------------- יצירת קובץ CSV אם לא קיים -------------------
if not os.path.exists(RESULT_CSV):
    with open(RESULT_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Barcode", "EXP Date", "Name", "Quantity"])
    print(f"קובץ CSV חדש נוצר: {RESULT_CSV}")

# ------------------------------ פונקציות ---------------------------------
def parse_date(date_str):
    if not date_str:
        return None

    date_str = date_str.replace("-", "/").replace(".", "/").strip()
    parts = date_str.split("/")

    try:
        # DD/MM/YYYY
        if len(parts) == 3:
            day, month, year = map(int, parts)

        # MM/YYYY או MM/YY
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
            writer.writerow(item)

# --------------------------בדיקה של מוצרים שפגי תוקף בעוד שבוע ------------------
def check_expiring_soon(items):
    today = datetime.today().date()
    week_ahead = today + timedelta(days=7)

    expired_items = []
    expiring_soon_items = []

    for item in items:
        exp_str = item.get("EXP Date", "").strip()
        if not exp_str:
            continue

        item_date = parse_date(exp_str)
        if not item_date:
            continue

        exp_date = item_date.date()

        if exp_date < today:
            expired_items.append(item)

        elif today <= exp_date <= week_ahead:
            expiring_soon_items.append(item)

    # ----------------------------------- הדפסה --------------------------------------
    if expired_items:
        print("מוצרים שפג תוקפם כבר:")
        for it in expired_items:
            print(f"- {it['Name']} (Barcode={it['Barcode']}, EXP={it['EXP Date']}, Quantity={it['Quantity']})")
    else:
        print("אין מוצרים שפג תוקפם כבר")

    if expiring_soon_items:
        print("\n מוצרים שפגי תוקף בעוד שבוע או פחות:")
        for it in expiring_soon_items:
            print(f"- {it['Name']} (Barcode={it['Barcode']}, EXP={it['EXP Date']}, Quantity={it['Quantity']})")
    else:
        print("\n אין מוצרים שפגי תוקף בעוד שבוע או פחות")

    return expired_items, expiring_soon_items


# ---------------------------- קבלת ברקוד מהמשתמש  ----------------------------------
def input_barcode():
    print("הזינו את הברקוד דרך הסורק (הידנית הסורקת).")
    while True:
        barcode = input("Barcode: ").strip()

        barcode = barcode.lstrip("'").strip()


        if barcode.isdigit() and 6 <= len(barcode) <= 14:
            print(f" ברקוד התקבל: {barcode}")
            return barcode

        print(" ברקוד לא תקין. נסי שוב (ספרות בלבד, אורך 6–14).")


# ------------------------------------- סריקת תאריך בלבד ------------------------------
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
        r"EXP\s*[:.]?\s*(\d{1,2}\s*[./-]\s*\d{2})",
        r"Exp\s*[:.]?\s*(\d{1,2}\s*[./-]\s*\d{2})",
        r"EXP\s*[:.]?\s*(\d{1,2})\s+(\d{2,4})",
        r"Exp\s*[:.]?\s*(\d{1,2})\s+(\d{2,4})",
        r"EXP\s*[:.]?\s*(\d{1,2}[.]\d{4})",
        r"Exp\s*[:.]?\s*(\d{1,2}[.]\d{4})",
        r"E\s*[:.]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        r"E\s*[:.]?\s*(\d{1,2}[./-]\d{2,4})",
        r"E\s*[:.]?\s*(\d{1,2}[.]\d{4})",
        r"EXD\s*[:.]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        r"EXD\s*[:.]?\s*(\d{1,2}[./-]\d{2,4})",
        r"EXD\s*[:.]?\s*(\d{1,2})\s+(\d{2,4})",
        r"BEST BEFORE\s*[:.]?\s*(\d{1,2}[.]\d{4})",
        r"BEST BEFORE\s*[:.]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        r"BEST BEFORE\s*[:.]?\s*(\d{1,2}[./-]\d{2,4})",
        r"BEST BEFORE\s*[:.]?\s*(\d{1,2})\s+(\d{2,4})",
    ]

    exp_date = None
    print(" סריקה - החזיקו את המוצר מול המצלמה (תאריך EXP)")

    cv2.namedWindow("סריקה EXP", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("סריקה EXP", cv2.WND_PROP_TOPMOST, 1)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("שגיאה בקריאת התמונה מהמצלמה")
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

                    print(f" זוהה תאריך: {exp_date}")
                    break

        if exp_date:
            cv2.putText(frame, f"EXP: {exp_date}",
                        (30, 50), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 0), 2)

            cv2.putText(frame, "ENTER=OK | r=Retry",
                        (30, 90), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (255, 255, 0), 2)

        cv2.imshow("סריקה EXP", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == 13 and exp_date:
            print(f"תאריך אושר: {exp_date}")
            cap.release()
            cv2.destroyAllWindows()
            break

        elif key == ord('r'):
            print("סריקה מחדש...")
            exp_date = None

        elif key == ord('q'):
            exp_date = None
            break

    cap.release()
    cv2.destroyAllWindows()
    return exp_date


# -------------------------------------- הפעלה -------------------------------------
if __name__ == "__main__":
    items = read_csv()

    check_expiring_soon(items)

    add_new = input("רוצים להוסיף פריטים חדשים? (y/n): ").lower()
    if add_new == "y":

        barcode_text = input_barcode()

        if barcode_text:
            raw_exp_date = scan_exp_date()
            parsed_date = parse_date(raw_exp_date)

            if parsed_date:
                exp_date = parsed_date.strftime("%d/%m/%Y")
            else:
                exp_date = None

            name = input("הכנס שם לפריט: ")
            while True:
                quantity_input = input("הכנס כמות: ")
                if quantity_input.isdigit() and int(quantity_input) > 0:
                    quantity = int(quantity_input)
                    break
                else:
                    print("הכנס מספר תקין עבור הכמות")


            found = False
            for item in items:
                if item["Barcode"].lstrip("'").strip() == barcode_text.strip() and item["EXP Date"].strip() == exp_date.strip():
                    item["Quantity"] += quantity
                    found = True
                    break

            if not found:
                items.append({
                    "Barcode": f"'{barcode_text}",
                    "EXP Date": exp_date,
                    "Name": name,
                    "Quantity": quantity
                })

            write_csv(items)
            print("הפריט נשמר בהצלחה בקובץ CSV")
