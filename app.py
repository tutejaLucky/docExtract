from flask import Flask, render_template, request, jsonify
from extractor import POScanner
import os
# from dotenv import load_dotenv

# Load environment variables from .env file
# load_dotenv()

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["OUTPUT_FOLDER"] = "outputs"

# Get API key from environment variable
# API_KEY = os.getenv("NANONETS_API_KEY")
API_KEY = "831ec4a4-b314-11f0-ab66-a62e6d220688"

# Initialize scanner with API key (no browser auth needed)
scanner = POScanner(api_key=API_KEY)

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

    try:
        # Process PDF
        po = scanner.process_pdf(pdf_path)

        # Save outputs
        json_path = os.path.join(app.config["OUTPUT_FOLDER"], "extracted_data.json")
        csv_path = os.path.join(app.config["OUTPUT_FOLDER"], "extracted_data.csv")
        scanner.save_to_json(po, json_path)
        scanner.save_to_csv(po, csv_path)

        # Return extracted data as JSON to frontend
        return jsonify({
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
        })
    
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    
    # Check if API key is loaded
    if not API_KEY:
        print("⚠️  WARNING: No API key found in .env file!")
        print("Please add NANONETS_API_KEY to your .env file")
    else:
        print("✅ API key loaded successfully")
    
    app.run(debug=True)