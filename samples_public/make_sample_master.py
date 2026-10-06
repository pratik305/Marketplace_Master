"""Build a small, fake master sheet with the same columns as a real one (no real product data)."""
from pathlib import Path

import openpyxl

COLUMNS = ["CODE", "BRAND", "PLATFORM", "CATEGORY", "Sku Code", "Sku Name", "MRP", "Selling Price", "Sku Size",
           "MP SKU CODE/STYLE ID", "NET WEIGHT", "GROSS Weight", "Diamond Weight", "Diamond Count",
           "Diamond Shape", "Care Instruction", "Manufacture Name", "Manufacture Name.1", "PACK CONTAINS",
           "Country of Origin", "Color", "Certificate Type", "Metal Stamp/ Type/Material", "Image Url 1",
           "Image Url 2", "Image Url 3", "Image Url 4", "Gender", "Description", "Brand Name", "HSN Code",
           "Product Id Type", "Bullet Point", "Bullet Point.1", "Bullet Point.2", "Bullet Point.3"]

COMMON = {"CODE": "DEMO0001", "BRAND": "DM", "Sku Name": "Demo Diamond Ring", "Manufacture Name": "Demo Maker Pvt Ltd",
          "Manufacture Name.1": "Demo Maker Pvt Ltd", "Description": "A demo ring used to try the tool.",
          "HSN Code": "71131914", "Bullet Point": "Fake product for demonstration", "Bullet Point.1": "Not for sale",
          "Bullet Point.2": "Sample bullet point", "Bullet Point.3": "Another sample bullet point"}
PARENT = dict(COMMON, CATEGORY="PARENT", **{"Sku Code": "DEMO0001-PARENT"})


def child(n, color, size, price):
    row = dict(COMMON, CATEGORY="RING", MRP=price, **{
        "Sku Code": f"DEMO0001-{n}", "Selling Price": price, "Sku Size": size, "MP SKU CODE/STYLE ID": "DEMO0001",
        "NET WEIGHT": 2.1, "Diamond Weight": 0.5, "Diamond Count": 12, "Diamond Shape": "Round",
        "Care Instruction": "Clean gently with a soft cloth", "PACK CONTAINS": "1 Ring", "Country of Origin": "India",
        "Color": color, "Certificate Type": "IGI Certificate", "Metal Stamp/ Type/Material": "14K",
        "Image Url 1": f"https://example.com/demo/{n}_1.jpg", "Image Url 2": f"https://example.com/demo/{n}_2.jpg",
        "Image Url 3": f"https://example.com/demo/{n}_3.jpg", "Image Url 4": f"https://example.com/demo/{n}_4.jpg",
        "Gender": "Women", "Brand Name": "Demo Brand", "Product Id Type": "GTIN Exempt"})
    return row


ROWS = [PARENT, child(1, "White Gold", 7, 40000), child(2, "Yellow Gold", 8, 42000), child(3, "Rose Gold", 9, 43000)]

if __name__ == "__main__":
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(COLUMNS)
    for r in ROWS:
        ws.append([r.get(c) for c in COLUMNS])
    out = Path(__file__).with_name("demo_master.xlsx")
    wb.save(out)
    print("wrote", out)
