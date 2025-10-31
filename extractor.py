import json
import csv
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from docstrange import DocumentExtractor

@dataclass
class VendorDetails:
    name: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    gst_number: str = ""

@dataclass
class LineItem:
    item_name: str = ""
    hsn_code: str = ""
    quantity: float = 0
    unit_price: float = 0
    gst_rate: float = 0
    total_amount: float = 0

@dataclass
class PurchaseOrder:
    po_number: str = ""
    po_date: str = ""
    invoice_number: str = ""
    vendor: VendorDetails = None
    buyer: VendorDetails = None
    items: List[LineItem] = None
    subtotal: float = 0
    total_gst: float = 0
    grand_total: float = 0
    
    def __post_init__(self):
        if self.vendor is None:
            self.vendor = VendorDetails()
        if self.buyer is None:
            self.buyer = VendorDetails()
        if self.items is None:
            self.items = []

class POScanner:
    def __init__(self, api_key: str = None, use_local: bool = False):
        """
        Initialize PO Scanner with DocStrange
        
        Args:
            api_key: API key for cloud mode (no browser auth needed)
            use_local: If True, uses local CPU processing (requires Ollama)
        """
        if use_local:
            self.extractor = DocumentExtractor(cpu=True)
            print("✅ Using local processing mode (Ollama)")
        else:
            self.extractor = DocumentExtractor(api_key=api_key)
            if api_key:
                print("✅ Using cloud mode with API key (no browser auth)")
            else:
                print("⚠️  WARNING: No API key - may require browser authentication")
    
    def process_pdf(self, pdf_path: str) -> PurchaseOrder:
        """
        Main method to process PDF and extract PO data using DocStrange
        """
        print(f"📄 Processing: {pdf_path}")
        
        # Extract document using DocStrange
        result = self.extractor.extract(pdf_path)
        
        # Define the schema for Purchase Order extraction
        po_schema = {
            "invoice_number": "string",
            "po_number": "string",
            "po_date": "string",
            "vendor": {
                "name": "string",
                "address": "string",
                "phone": "string",
                "email": "string",
                "gst_number": "string"
            },
            "buyer": {
                "name": "string",
                "address": "string",
                "gst_number": "string"
            },
            "line_items": [{
                "item_name": "string",
                "hsn_code": "string",
                "quantity": "number",
                "unit_price": "number",
                "gst_rate": "number",
                "total_amount": "number"
            }],
            "subtotal": "number",
            "total_gst": "number",
            "grand_total": "number"
        }
        
        # Extract structured data
        try:
            print("🔍 Extracting with schema...")
            structured_data = result.extract_data(json_schema=po_schema)
            po = self._convert_to_po_object(structured_data)
            print("✅ Schema extraction successful")
        except Exception as e:
            print(f"⚠️  Schema extraction failed: {e}")
            print("🔄 Trying field extraction...")
            # Fallback to specific field extraction
            po = self._extract_with_fields(result)
        
        return po
    
    def _convert_to_po_object(self, data: Dict) -> PurchaseOrder:
        """Convert extracted data to PurchaseOrder object"""
        
        # Handle both 'structured_data' key and direct data
        if 'structured_data' in data:
            data = data['structured_data']
        
        po = PurchaseOrder()
        
        # Basic fields
        po.invoice_number = data.get('invoice_number', '')
        po.po_number = data.get('po_number', '')
        po.po_date = data.get('po_date', '')
        
        # Vendor details
        if 'vendor' in data and data['vendor']:
            vendor_data = data['vendor']
            po.vendor = VendorDetails(
                name=vendor_data.get('name', ''),
                address=vendor_data.get('address', ''),
                phone=vendor_data.get('phone', ''),
                email=vendor_data.get('email', ''),
                gst_number=vendor_data.get('gst_number', '')
            )
        
        # Buyer details
        if 'buyer' in data and data['buyer']:
            buyer_data = data['buyer']
            po.buyer = VendorDetails(
                name=buyer_data.get('name', ''),
                address=buyer_data.get('address', ''),
                gst_number=buyer_data.get('gst_number', '')
            )
        
        # Line items
        if 'line_items' in data and data['line_items']:
            for item_data in data['line_items']:
                item = LineItem(
                    item_name=item_data.get('item_name', ''),
                    hsn_code=item_data.get('hsn_code', ''),
                    quantity=float(item_data.get('quantity', 0)),
                    unit_price=float(item_data.get('unit_price', 0)),
                    gst_rate=float(item_data.get('gst_rate', 0)),
                    total_amount=float(item_data.get('total_amount', 0))
                )
                po.items.append(item)
        
        # Totals
        po.subtotal = float(data.get('subtotal', 0))
        po.total_gst = float(data.get('total_gst', 0))
        po.grand_total = float(data.get('grand_total', 0))
        
        return po
    
    def _extract_with_fields(self, result) -> PurchaseOrder:
        """Fallback method using specific field extraction"""
        
        fields = [
            "invoice_number", "po_number", "po_date",
            "vendor_name", "vendor_address", "vendor_gst", "vendor_email",
            "buyer_name", "buyer_address", "buyer_gst",
            "item_name", "hsn_code", "quantity", "rate", "gst_rate",
            "subtotal", "total_gst", "grand_total"
        ]
        
        extracted = result.extract_data(specified_fields=fields)
        
        # Handle both 'extracted_fields' key and direct data
        if 'extracted_fields' in extracted:
            extracted = extracted['extracted_fields']
        
        po = PurchaseOrder()
        po.invoice_number = extracted.get('invoice_number', '')
        po.po_number = extracted.get('po_number', '')
        po.po_date = extracted.get('po_date', '')
        
        po.vendor = VendorDetails(
            name=extracted.get('vendor_name', ''),
            address=extracted.get('vendor_address', ''),
            email=extracted.get('vendor_email', ''),
            gst_number=extracted.get('vendor_gst', '')
        )
        
        po.buyer = VendorDetails(
            name=extracted.get('buyer_name', ''),
            address=extracted.get('buyer_address', ''),
            gst_number=extracted.get('buyer_gst', '')
        )
        
        # Try to extract item from available data
        if extracted.get('item_name'):
            item = LineItem(
                item_name=extracted.get('item_name', ''),
                hsn_code=extracted.get('hsn_code', ''),
                quantity=float(extracted.get('quantity', 0)),
                unit_price=float(extracted.get('rate', 0)),
                gst_rate=float(extracted.get('gst_rate', 0))
            )
            po.items.append(item)
        
        po.subtotal = float(extracted.get('subtotal', 0))
        po.total_gst = float(extracted.get('total_gst', 0))
        po.grand_total = float(extracted.get('grand_total', 0))
        
        return po
    
    def save_to_json(self, po: PurchaseOrder, output_path: str):
        """Save PO data to JSON file"""
        data = {
            'invoice_number': po.invoice_number,
            'po_number': po.po_number,
            'po_date': po.po_date,
            'vendor': asdict(po.vendor),
            'buyer': asdict(po.buyer),
            'items': [asdict(item) for item in po.items],
            'subtotal': po.subtotal,
            'total_gst': po.total_gst,
            'grand_total': po.grand_total
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved to: {output_path}")
    
    def save_to_csv(self, po: PurchaseOrder, output_path: str):
        """Save PO items to CSV file"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'Invoice Number', 'PO Number', 'PO Date', 'Vendor Name',
                'HSN Code', 'Item Name', 'Quantity', 'Unit Price',
                'GST Rate', 'Total Amount'
            ])
            
            # Write items
            for item in po.items:
                writer.writerow([
                    po.invoice_number,
                    po.po_number,
                    po.po_date,
                    po.vendor.name,
                    item.hsn_code,
                    item.item_name,
                    item.quantity,
                    item.unit_price,
                    item.gst_rate,
                    item.total_amount
                ])
        
        print(f"✅ Saved to: {output_path}")