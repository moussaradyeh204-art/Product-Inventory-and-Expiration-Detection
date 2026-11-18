import cv2
from pyzbar.pyzbar import decode, ZBarSymbol
import pytesseract
import pyttsx3
import os
import csv
import re
import winsound
from datetime import datetime, timedelta

engine = pyttsx3.init()
engine.setProperty('rate', 250)

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ------------------------------------ קובץ CSV ----------------------------------------------------
BASE_DIR = os.path.join(os.path.expanduser("~"), "OneDrive", "שולחן העבודה")
RESULT_CSV = os.path.join(BASE_DIR, "barcode_inventory.csv")

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

if not os.path.exists(RESULT_CSV):
    with open(RESULT_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Barcode", "EXP Date", "Name", "Quantity"])
    print(f"קובץ CSV חדש נוצר: {RESULT_CSV}")


# ---------------------------------------- פונקציות ----------------------------------------------------
def parse_date(date_str):
    if not date_str:
        return None

    date_str = date_str.strip()
    date_str = re.sub(r"\s+", " ", date_str)
    date_str = date_str.replace("-", "/").replace(".", "/")
    date_str = date_str.replace(" ", "/")

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


# -------------------------- בדיקה של מוצרים שפג תוקפם ----------------------------------------------
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
    messages = []
    if expired_items:
        messages.append("Warning. There are expired products.")
    if expiring_soon_items:
        messages.append("Attention. Some products will expire soon.")

    if messages:
        engine.say(" ".join(messages))
        engine.runAndWait()

    if expired_items:
        print(":מוצרים שפג תוקפם כבר")
        for it in expired_items:
            print(f"- {it['Name']} (Barcode={it['Barcode']}, EXP={it['EXP Date']}, Quantity={it['Quantity']})")
    else:
        print("אין מוצרים שפג תוקפם כבר")

    if expiring_soon_items:
        print("\n: מוצרים שפגי תוקף בעוד שבוע או פחות")
        for it in expiring_soon_items:
            print(f"- {it['Name']} (Barcode={it['Barcode']}, EXP={it['EXP Date']}, Quantity={it['Quantity']})")
    else:
        print("\n אין מוצרים שפגי תוקף בעוד שבוע או פחות")

    return expired_items, expiring_soon_items


# ------------------------------------- סריקה ברקוד בלבד ------------------------------------------------
def scan_barcode():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(" לא ניתן לפתוח את המצלמה")
        return None

    barcode_text = None
    print(" סריקה - החזיקו את המוצר מול המצלמה (ברקוד בלבד)")
    cv2.namedWindow("סריקה ברקוד", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("סריקה ברקוד", cv2.WND_PROP_TOPMOST, 1)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("שגיאה בקריאת התמונה מהמצלמה")
            break

        barcodes = decode(frame, symbols=[
            ZBarSymbol.EAN13, ZBarSymbol.EAN8, ZBarSymbol.UPCA,
            ZBarSymbol.UPCE, ZBarSymbol.CODE128, ZBarSymbol.CODE39
        ])

        if barcodes:
            barcode_text = barcodes[0].data.decode("utf-8")
            x, y, w, h = barcodes[0].rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.putText(frame, barcode_text, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            print(f" זוהה ברקוד: {barcode_text}")
            winsound.Beep(900, 500)
            cv2.imshow("סריקה ברקוד", frame)
            cv2.waitKey(3000)
            break

        cv2.imshow("סריקה ברקוד", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return barcode_text


# ------------------------------------- סריקת תאריך בלבד  ----------------------------------------
def scan_exp_date():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("לא ניתן לפתוח את המצלמה")
        return None

    exp_patterns = [
        # ------------------------------ EXP / E -------------------------------------------
        # EXP / E + תאריך מלא עם מפרידים
        r"(?:EXP|Exp|E)\s*[:.]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        # EXP / E + חודש/שנה (כמו 11.2027 או 11/2027)
        r"(?:EXP|Exp|E)\s*[:.]?\s*(\d{1,2}[./-]\d{2,4})",
        r"(?:EXP|Exp|E)\s*[:.]?\s*(\d{1,2}[.]\d{4})",
        # EXP / E + רווחים: 05 02 2025
        r"(?:EXP|Exp|E)\s*[:.]?\s*(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})",
        # EXP / E + חודש ושנה בלבד
        r"(?:EXP|Exp|E)\s*[:.]?\s*(\d{1,2})\s+(\d{2,4})",
        # -------------------------------EXP DATE / EXPIRY DATE ---------------------------
        # EXP DATE + תאריך מלא
        r"(?:EXP\s*DATE|Exp\s*Date|EXPIRY\s*DATE|Expiration\s*Date|EXPIRATION\s*DATE)\s*[:.]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        # EXP DATE + חודש/שנה
        r"(?:EXP\s*DATE|Exp\s*Date|EXPIRY\s*DATE|Expiration\s*Date|EXPIRATION\s*DATE)\s*[:.]?\s*(\d{1,2}[./-]\d{2,4})",
        r"(?:EXP\s*DATE|Exp\s*Date|EXPIRY\s*DATE|Expiration\s*Date|EXPIRATION\s*DATE)\s*[:.]?\s*(\d{1,2}[.]\d{4})",
        # EXP DATE + רווחים (05 02 2025)
        r"(?:EXP\s*DATE|Exp\s*Date|EXPIRY\s*DATE|Expiration\s*Date|EXPIRATION\s*DATE)\s*[:.]?\s*(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})",
        # EXP DATE + חודש ושנה (01 2030)
        r"(?:EXP\s*DATE|Exp\s*Date|EXPIRY\s*DATE|Expiration\s*Date|EXPIRATION\s*DATE)\s*[:.]?\s*(\d{1,2})\s+(\d{2,4})",

        # ----------------------------------------- EXD ------------------------------------
        # EXD + תאריך מלא עם מפרידים
        r"(?:EXD|Exd|exd)\s*[:.]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        # EXD + חודש/שנה (11/2027 או 11.2027)
        r"(?:EXD|Exd|exd)\s*[:.]?\s*(\d{1,2}[./-]\d{2,4})",
        r"(?:EXD|Exd|exd)\s*[:.]?\s*(\d{1,2}[.]\d{4})",
        # EXD + רווחים: 05 02 2025
        r"(?:EXD|Exd|exd)\s*[:.]?\s*(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})",
        # EXD + חודש ושנה בלבד
        r"(?:EXD|Exd|exd)\s*[:.]?\s*(\d{1,2})\s+(\d{2,4})",

        # ----------------------------- BEST BEFORE ---------------------------------------
        # BEST BEFORE + תאריך מלא עם מפרידים
        r"(?:BEST\s*BEFORE|Best\s*Before|best\s*before)\s*[:.]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        # BEST BEFORE + חודש/שנה (11/2027 או 11.2027)
        r"(?:BEST\s*BEFORE|Best\s*Before|best\s*before)\s*[:.]?\s*(\d{1,2}[./-]\d{2,4})",
        r"(?:BEST\s*BEFORE|Best\s*Before|best\s*before)\s*[:.]?\s*(\d{1,2}[.]\d{4})",
        # BEST BEFORE + רווחים: 05 02 2025
        r"(?:BEST\s*BEFORE|Best\s*Before|best\s*before)\s*[:.]?\s*(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})",
        # BEST BEFORE + חודש ושנה בלבד
        r"(?:BEST\s*BEFORE|Best\s*Before|best\s*before)\s*[:.]?\s*(\d{1,2})\s+(\d{2,4})",
        # חודש + שנה עם רווח אחד או יותר (01 2030 / 01  2030)
        r"(?:EXP\s*DATE|Exp\s*Date|EXPIRY\s*DATE|Expiration\s*Date|EXPIRATION\s*DATE|EXP|Exp|E|EXD|Exd|BEST\s*BEFORE|Best\s*Before|BB|BBD|BEST\s*BY|USE\s*BY)\s*[:.]?\s*(\d{1,2})\s+(\d{4})",

    ]
    exp_date = None
    print("סריקה - החזיקו את המוצר מול המצלמה (תאריך)")
    cv2.namedWindow("סריקת תאריך תפוגה", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("סריקת תאריך תפוגה", cv2.WND_PROP_TOPMOST, 1)


    while True:
        ret, frame = cap.read()
        if not ret:
            print("שגיאה בקריאת התמונה מהמצלמה")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


        text = pytesseract.image_to_string(gray, config="--psm 6")

        if not exp_date:
            for pattern in exp_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if not match:
                    continue

                if match.lastindex == 3:
                    d = int(match.group(1))
                    m = int(match.group(2))
                    y = int(match.group(3))
                    if not (1 <= d <= 31 and 1 <= m <= 12):
                        continue
                    raw_date = f"{d}/{m}/{y}"

                elif match.lastindex == 2:
                    m = int(match.group(1))
                    y = int(match.group(2))
                    if not (1 <= m <= 12):
                        continue
                    raw_date = f"1/{m}/{y}"

                else:
                    raw_date = match.group(1)

                parsed = parse_date(raw_date)
                if not parsed:
                    continue

                # אחידות תמיד DD/MM/YYYY
                exp_date = parsed.strftime("%d/%m/%Y")
                print(f" זוהה תאריך: {exp_date}")
                winsound.Beep(900, 500)
                break

        if exp_date:
            cv2.putText(frame, f"EXP: {exp_date}",
                        (30, 50), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 0), 2)
            cv2.putText(frame, "ENTER=OK | r=Retry",
                        (30, 90), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (255, 255, 0), 2)

        cv2.imshow("סריקת תאריך תפוגה", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == 13 and exp_date:
            print(f"תאריך אושר: {exp_date}")
            cap.release()
            cv2.destroyAllWindows()
            return exp_date
        elif key == ord('r'):
            print(" סריקה מחדש...")
            exp_date = None
        elif key == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            return None


    cap.release()
    cv2.destroyAllWindows()
    return exp_date


# ----------------------------------------הפעלה -----------------------------------------
if __name__ == "__main__":
    items = read_csv()
    check_expiring_soon(items)

    add_new = input("Do you want to add products(Y/N)?").lower()
    if add_new == "y":
        barcode_text = scan_barcode()
        if barcode_text:
            raw_exp_date = scan_exp_date()
            parsed_date = parse_date(raw_exp_date)

            if parsed_date:
                exp_date = parsed_date.strftime("%d/%m/%Y")
            else:
                exp_date = None

            if not exp_date:
                print(" לא זוהה תאריך תפוגה תקין")
                raise SystemExit

            name = input("הכנס שם לפריט: ").strip()
            while True:
                quantity_input = input("הכנס כמות: ").strip()
                if quantity_input.isdigit() and int(quantity_input) > 0:
                    quantity = int(quantity_input)
                    break
                else:
                    print(" הכנס מספר תקין עבור הכמות")


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
            print(" הפריט נשמר בהצלחה בקובץ CSV")
