from flask import Flask, render_template, request, jsonify
from extractor import POScanner
import os

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["OUTPUT_FOLDER"] = "outputs"

scanner = POScanner()

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

    # Save uploaded file
    pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(pdf_path)

    # Process PDF
    po = scanner.process_pdf(pdf_path)

    # Save outputs
    json_path = os.path.join(app.config["OUTPUT_FOLDER"], "extracted_data.json")
    csv_path = os.path.join(app.config["OUTPUT_FOLDER"], "extracted_data.csv")
    scanner.save_to_json(po, json_path)
    scanner.save_to_csv(po, csv_path)

    # Return extracted data as JSON to frontend
    return jsonify({
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
    })

if __name__ == "__main__":    
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

