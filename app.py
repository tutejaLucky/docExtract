from flask import Flask, render_template, request, jsonify
from extractor import POScanner
import os
import pymysql

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["OUTPUT_FOLDER"] = "outputs"

API_KEY = "831ec4a4-b314-11f0-ab66-a62e6d220688"

# Initialize scanner
scanner = POScanner(api_key=API_KEY)

# ---------------------- Database Connection ----------------------
def get_db_connection():
    return pymysql.connect(
        host="167.235.12.115",
        user="mscorpre_ims_user",
        password="OWdbJTL3U=?U",
        database="mscorpre_bharatpay_ims",
        cursorclass=pymysql.cursors.DictCursor
    )


# ---------------------- Existing Upload Route ----------------------
@app.route("/")
def index():
    return render_template("index.html")
@app.route("/upload", methods=["POST"])

def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(pdf_path)

    try:
        # Extract from PDF
        po = scanner.process_pdf(pdf_path)

        json_path = os.path.join(app.config["OUTPUT_FOLDER"], "extracted_data.json")
        csv_path = os.path.join(app.config["OUTPUT_FOLDER"], "extracted_data.csv")
        scanner.save_to_json(po, json_path)
        scanner.save_to_csv(po, csv_path)

        # Return extracted data and also fetch DB data
        pdf_data = {
            "invoice_number": po.invoice_number,
            "po_number": po.po_number,
            "po_date": po.po_date,
            "vendor": {
                "name": po.vendor.name,
                "address": po.vendor.address,
                "gst": po.vendor.gst_number,
                "email": po.vendor.email,
            },
            "items": [vars(item) for item in po.items],
            "totals": {
                "subtotal": po.subtotal,
                "gst": po.total_gst,
                "grand_total": po.grand_total,
            }
        }

        # Now fetch from DB using po_number
        db_data = fetch_data_from_db(po.po_number)

        return jsonify({
            "success": True,
            "message": "PDF extracted and DB data fetched successfully",
            "pdf_extracted": pdf_data,
            "db_extracted": db_data
        })

    except Exception as e:
        print(f"Error processing PDF: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------- Fetch Data from DB ----------------------
def fetch_data_from_db(po_number):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:

            # Check PO status
            cursor.execute("""
                SELECT * FROM po_purchase_req 
                WHERE po_transaction = %s AND po_status != %s
            """, (po_number, "A"))
            invalid = cursor.fetchall()
            if invalid:
                return {"error": "PO is cancelled or completed"}

            # Get parts list
            cursor.execute("""
                SELECT DISTINCT po_part_no 
                FROM po_purchase_req 
                WHERE po_transaction = %s
            """, (po_number,))
            part_list = cursor.fetchall()

            if not part_list:
                return {"error": "No PO found"}

            # Fetch final joined data
            cursor.execute("""
                SELECT DISTINCT 
                    po_purchase_req.ID,
                    po_purchase_req.po_transaction,
                    po_purchase_req.po_part_no,
                    po_purchase_req.po_order_qty,
                    po_purchase_req.po_pending_qty,
                    po_purchase_req.po_order_rate,
                    po_purchase_req.po_exchange,
                    po_purchase_req.po_duedate,
                    po_purchase_req.po_remark,
                    po_purchase_req.po_hsncode,
                    po_purchase_req.po_gstrate,
                    po_purchase_req.po_gsttype,
                    po_purchase_req.po_cgst,
                    po_purchase_req.po_sgst,
                    po_purchase_req.po_igst,
                    po_purchase_req.po_vendor_type,
                    po_purchase_req.po_vendor_reg_id,
                    po_purchase_req.po_vendor_address,
                    po_purchase_req.po_currency,
                    components.c_name,
                    components.c_specification,
                    components.component_key,
                    components.c_part_no,
                    units.units_name,
                    ven_address_detail.ven_add_gst,
                    ven_basic_detail.ven_name,
                    ims_currency.currency_symbol
                FROM po_purchase_req 
                LEFT JOIN components ON po_purchase_req.po_part_no = components.component_key 
                LEFT JOIN units ON units.units_id = components.c_uom 
                LEFT JOIN ven_address_detail ON po_purchase_req.po_ven_add_id = ven_address_detail.ven_address_id 
                LEFT JOIN ven_basic_detail ON po_purchase_req.po_vendor_reg_id = ven_basic_detail.ven_register_id 
                LEFT JOIN ims_currency ON po_purchase_req.po_currency = ims_currency.currency_id 
                WHERE po_purchase_req.po_transaction = %s 
                AND po_purchase_req.po_part_status = %s
                GROUP BY po_purchase_req.po_part_no, po_purchase_req.po_vendor_reg_id
            """, (po_number, "ACTIVE"))

            rows = cursor.fetchall()

            if not rows:
                return {"error": "No active items found"}

            # Build structured response
            vendor_info = {
                "vendorname": rows[0]["ven_name"],
                "gstin": rows[0]["ven_add_gst"],
                "currency": rows[0]["po_currency"],
                "currency_symbol": rows[0]["currency_symbol"],
                "exchange_rate": float(rows[0]["po_exchange"]),
                "vendorcode": rows[0]["po_vendor_reg_id"],
                "vendortype": rows[0]["po_vendor_type"],
                "vendoraddress": rows[0]["po_vendor_address"]
            }

            items = []
            for i, row in enumerate(rows, 1):
                items.append({
                    "serial_no": i,
                    "hsncode": row["po_hsncode"],
                    "gstrate": row["po_gstrate"],
                    "orderid": row["po_transaction"],
                    "component_name": row["c_name"],
                    "description": row["c_specification"],
                    "units": row["units_name"],
                    "part_no": row["po_part_no"],
                    "order_qty": row["po_order_qty"],
                    "order_rate": float(row["po_order_rate"]),
                    "total_value": float(row["po_order_qty"]) * float(row["po_order_rate"]),
                    "duedate": str(row["po_duedate"]),
                    "remark": row["po_remark"]
                })

            return {"vendor": vendor_info, "items": items}

    except Exception as e:
        return {"error": str(e)}
    finally:
        connection.close()


# ---------------------- Run App ----------------------
if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    app.run()
