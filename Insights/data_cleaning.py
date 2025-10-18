import pandas as pd
import numpy as np
import os
from datetime import datetime
from sqlalchemy import create_engine


pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

# -------------------------
# ERROR LOGGING
# -------------------------
def log_error(log_file, error_msg, context=None):
    os.makedirs("etl_log", exist_ok=True)
    log_path = os.path.join("etl_log", log_file)
    entry = f"[{datetime.now()}] ERROR: {error_msg} | Context: {context}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)

# -------------------------
# FILE HANDLING
# -------------------------
def file_list(raw_folder="data/raw/"):
    files = []
    if not os.path.exists(raw_folder):
        log_error("load_errors.csv", "Raw folder not found", {"folder": raw_folder})
        return files
    for file in os.listdir(raw_folder):
        if file.endswith((".csv", ".xlsx", ".xls")):
            files.append(file)
    if not files:
        log_error("load_errors.csv", "No valid files found", {"folder": raw_folder})
    return files

def load_files(file_list, raw_folder="data/raw/"):
    dfs = []
    for file in file_list:
        try:
            file_path = os.path.join(raw_folder, file)
            if file.endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            platform = "unknown"
            fname = file.lower()
            if "amazon" in fname:
                platform = "amazon"
            elif "flipkart" in fname:
                platform = "flipkart"
            elif "meesho" in fname:
                platform = "meesho"
            df["Platform"] = platform
            dfs.append(df)
        except Exception as e:
            log_error("load_errors.csv", str(e), {"file": file})
    return dfs

# -------------------------
# COLUMN MAPPING
# -------------------------
def map_marketplace_columns(df, mapping):
    """
    mapping: dictionary for marketplace columns → standard columns
    """
    platform = df["Platform"].iloc[0].lower() if "Platform" in df.columns else "unknown"
    if platform not in mapping:
        log_error("column_errors.csv", "Unknown platform mapping", {"platform": platform})
        return df
    df = df.rename(columns=mapping[platform])

    # Fill required standard columns
    required_cols = ["Order ID", "Item Description", "Quantity", "Item Price", "Payment Method"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0 if col in ["Quantity", "Item Price"] else "Unknown"
            log_error("column_errors.csv", f"Missing column filled: {col}", {"platform": platform})
    return df
def ensure_key_columns(df, platform):
    """
    Ensures that Platform, Invoice Number, Order ID, and Shipment Item ID
    exist in the dataframe. Tries to map common raw column names automatically.
    """
    df = df.copy()
    
    # Add Platform if missing
    if "Platform" not in df.columns:
        df["Platform"] = platform

    # Mapping of common raw names to standard names
    column_mapping = {
        "Invoice Number": ["Invoice No", "InvoiceNumber", "INV", "Invoice ID"],
        "Order ID": ["Order Number", "OrderID", "ORD", "Order No"],
        "Shipment Item ID": ["Shipment Item ID", "SHIPITEM", "Sub-Order Number", "Line Item ID"]
    }
    
    for standard_col, possible_cols in column_mapping.items():
        if standard_col not in df.columns:
            for col in possible_cols:
                # Find if any column contains this substring (case-insensitive)
                match = [c for c in df.columns if col.lower() in c.lower()]
                if match:
                    df = df.rename(columns={match[0]: standard_col})
                    break
            # If still missing, create empty column
            if standard_col not in df.columns:
                df[standard_col] = "Unknown"
    
    return df

# -------------------------
# CLEANING FUNCTIONS
# -------------------------
def remove_duplicates(df):
    """
    Drops duplicate rows based on Invoice Number + Order ID.
    Preserves Platform column.
    """
    if "Invoice Number" in df.columns and "Order ID" in df.columns:
        duplicates = df[df.duplicated(subset=["Invoice Number", "Order ID"], keep=False)]
        if not duplicates.empty:
            os.makedirs("etl_log", exist_ok=True)
            duplicates[["Invoice Number","Order ID", "Platform"]].to_csv(
                "etl_log/duplicate_rows.csv", index=False, mode="a", header=False
            )
        df = df.drop_duplicates(subset=["Invoice Number", "Order ID"], keep="first")
    return df
def handle_missing_values(df):
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(df[col].median())
        else:
            df[col] = df[col].fillna("Unknown")
    return df

def normalize_product_names(df):
    if "Item Description" in df.columns:
        df["Item Description"] = df["Item Description"].str.lower().str.strip()
    return df

def convert_datatypes(df):
    # Date conversion
    date_cols = ["Order Date", "Shipment Date", "Credit Note Date"]
    for col in date_cols:
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=False)  # Use dayfirst=False for mm/dd/yyyy
            except Exception as e:
                log_error("datatype_errors.csv", f"Date conversion failed: {col}", str(e))

    # Numeric conversion
    num_cols = ["Quantity", "Item Price", "Shipping Charge", "Packing Fee", "COD Fee", "Platform Fee", "Marketplace Fee Amount"]
    for col in num_cols:
        if col in df.columns:
            try:
                if isinstance(df[col], pd.Series):
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    df[col] = 0  # If column exists but is malformed, fill with 0
            except Exception as e:
                log_error("datatype_errors.csv", f"Numeric conversion failed: {col}", str(e))
    return df


def correct_rounding(df):
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    for col in num_cols:
        df[col] = df[col].round(1)
    return df

def derive_fields(df):
    # Remove duplicate columns
    df = df.loc[:, ~df.columns.duplicated()]

    discount_cols = ["Item Discount","Item Promotional Discount","Item Shipping Discount"]
    for col in discount_cols:
        if col not in df.columns:
            df[col] = 0

    df["GrossSales"] = df.get("Quantity",0) * df.get("Item Price",0)
    df["TotalDiscount"] = df[discount_cols].sum(axis=1)
    
    # Use get to safely handle missing columns
    df["NetRevenue"] = df["GrossSales"] - df["TotalDiscount"] - \
                       df.get("Shipping Charge",0) - df.get("Packing Fee",0) - \
                       df.get("COD Fee",0) - df.get("Platform Fee",0) - \
                       df.get("Marketplace Fee Amount",0)
    
    if "Shipment Date" in df.columns and "Order Date" in df.columns:
        df["DeliveryDelayDays"] = (df["Shipment Date"] - df["Order Date"]).dt.days
    else:
        df["DeliveryDelayDays"] = np.nan

    df["SuspiciousFlag"] = 0
    extreme_discount = (df["GrossSales"]>0) & ((df["TotalDiscount"]/df["GrossSales"])>0.8)
    negative_revenue = df["NetRevenue"]<0
    df.loc[extreme_discount | negative_revenue, "SuspiciousFlag"] = 1

    # Defragment to avoid PerformanceWarning
    df = df.copy()
    return df

def flag_suspicious_transactions(df):
    extreme_discount = (df["GrossSales"]>0) & ((df["TotalDiscount"]/df["GrossSales"])>0.8)
    negative_revenue = df["NetRevenue"]<0
    df["SuspiciousFlag"] = 0
    df.loc[extreme_discount | negative_revenue, "SuspiciousFlag"] = 1
    return df

def concat_all_platforms(dfs_list):
    if not dfs_list:
        return pd.DataFrame()
    
    # Preferred key order
    preferred_cols = [
        "Invoice Number", "Invoice Type", "Invoice Date", "Order ID", "Shipment ID",
        "Shipment Item ID", "Platform", "Item Description", "Quantity", "Item Price",
        "Item Discount", "Item Promotional Discount", "Item Shipping Discount",
        "Shipping Charge", "Packing Fee", "COD Fee", "Platform Fee",
        "Marketplace Fee Amount", "NetRevenue", "Payment Method", "SuspiciousFlag"
    ]
    
    # Gather all columns
    all_cols = list(dfs_list[0].columns)
    for df in dfs_list[1:]:
        for col in df.columns:
            if col not in all_cols:
                all_cols.append(col)
    
    # Final order: preferred_cols first, then remaining columns
    final_order = preferred_cols + [c for c in all_cols if c not in preferred_cols]
    
    # Reindex and concatenate
    aligned = [df.reindex(columns=final_order) for df in dfs_list]
    combined_df = pd.concat(aligned, ignore_index=True)
    
    return combined_df

def save_cleaned_csv(df, output_folder="cleanedfiles"):
    os.makedirs(output_folder, exist_ok=True)
    df.to_csv(os.path.join(output_folder, "cleaned_invoices.csv"), index=False)
# -------------------------
def upload_to_mysql(df, db_config):
    """
    Uploads a pandas DataFrame to a MySQL table.
    df: DataFrame to upload
    db_config: dict with keys: host, user, password, database, table
    """
    try:
        engine = create_engine(
            f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}/{db_config['database']}"
        )
        df.to_sql(name=db_config['table'], con=engine, if_exists='replace', index=False)
        print(f"Data uploaded to MySQL table '{db_config['table']}' successfully.")
    except Exception as e:
        log_error("mysql_upload_errors.csv", str(e))

# -------------------------
# MAIN ETL PIPELINE
# -------------------------
def main(raw_folder="data/raw/", output_folder="cleanedfiles"):
    """
    Orchestrates the full ETL pipeline:
    1. Load files from raw folder
    2. Map marketplace columns
    3. Clean and process each DataFrame
    4. Concatenate all platforms
    5. Save cleaned CSV
    """
    marketplace_mapping = {
        "amazon": {
            "Seller GSTIN":"Seller GSTIN", "Invoice Number":"Invoice Number", "Invoice Date":"Invoice Date",
            "Invoice Type":"Invoice Type", "Transaction Type":"Transaction Type", "Order ID":"Order ID",
            "Shipment ID":"Shipment ID", "Shipment Date":"Shipment Date", "Order Date":"Order Date",
            "Shipment Item ID":"Shipment Item ID", "Quantity":"Quantity", "Item Description":"Item Description",
            "Item Price":"Item Price", "Item Discount":"Item Discount", "Item Promotional Discount":"Item Promotional Discount",
            "Item Shipping Discount":"Item Shipping Discount", "Shipping Charge":"Shipping Charge", "Packing Fee":"Packing Fee",
            "COD Fee":"COD Fee", "Platform Fee":"Platform Fee", "Marketplace Fee Amount":"Marketplace Fee Amount",
            "Payment Method":"Payment Method"
        },
    "flipkart" : {
    # mapping flipkart columns to standard columns
    "Seller GSTIN":"Seller GSTIN", "Invoice Number":"Invoice Number", "Invoice Type (B2B / B2C)":"Invoice Type",
    "Transaction Type":"Transaction Type", "Order ID":"Order ID", "Dispatch ID":"Shipment ID",
    "Dispatch Date":"Shipment Date", "Order Date":"Order Date", "Line Item ID":"Shipment Item ID",
    "Quantity":"Quantity", "Product Title":"Item Description", "FSN":"ASIN", "SKU":"SKU",
    "Item Serial No.":"Item Serial No.", "HSN / SAC":"HSN / SAC", "Product Tax Code":"Product Tax Code",
    "Ship From City":"Bill From City", "Ship From State":"Bill From State", "Ship From Pincode":"Bill From Pincode",
    "Bill To Name":"Bill To Name", "Bill To Address Line1":"Bill To Address Line1", "Bill To Address Line2":"Bill To Address Line2",
    "Bill To City":"Bill To City", "Bill To State":"Bill To State", "Bill To Pincode":"Bill To Pincode",
    "Bill To Country":"Bill To Country", "Customer GSTIN":"Customer GSTIN", "Place of Supply":"Place of Supply",
    "Shipping Address Name":"Shipping Address Name", "Shipping Address Line1":"Shipping Address Line1",
    "Shipping Address Line2":"Shipping Address Line2", "Shipping Address City":"Shipping Address City",
    "Shipping Address State":"Shipping Address State", "Shipping Address Pincode":"Shipping Address Pincode",
    "Shipping Address Country":"Shipping Address Country", "Product Price":"Item Price",
    "Seller Discount":"Item Discount", "Flipkart Discount":"Item Promotional Discount",
    "Cashback Discount":"Item Shipping Discount", "Shipping Fee":"Shipping Charge",
    "Shipping Discount":"Shipping Discount", "Packaging Fee":"Packing Fee", "Packaging Fee Taxable Value":"Packing Fee Taxable Value",
    "Collection Fee":"COD Fee", "Collection Fee Taxable Value":"COD Fee Taxable Value",
    "Fixed Fee":"Platform Fee", "Fixed Fee Taxable Value":"Platform Fee Taxable Value",
    "Commission Fee":"Marketplace Fee Amount", "Commission Fee Taxable Value":"Marketplace Fee GST Amount"
},

    "meesho": {
    "Order Date":"Order Date", "Order Number":"Order ID", "Sub-Order Number":"Shipment Item ID",
    "Item Name":"Item Description", "Quantity":"Quantity", "HSN Code":"HSN / SAC",
    "Item Price":"Item Price", "Discount":"Item Discount", "Shipping Fee":"Shipping Charge",
    "Packaging Fee":"Packing Fee", "Collection Fee":"COD Fee", "Fixed Fee":"Platform Fee",
    "Commission Fee":"Marketplace Fee Amount", "Total Taxable Value":"Total Item Taxable Value",
    "CGST Amount":"CGST Amount", "SGST Amount":"SGST Amount", "IGST Amount":"IGST Amount",
    "Total Tax Amount":"Total Tax Amount", "Total Invoice Value":"Total Invoice Value",
    "Payment Method":"Payment Method", "TCS Amount":"TCS Amount", "TDS Amount":"TDS Amount",
    "GST Filing Month":"GST Filing Month", "GST Filing Year":"GST Filing Year",
    "Customer Name":"Bill To Name", "Shipping Address Line 1":"Shipping Address Line1",
    "Shipping Address Line 2":"Shipping Address Line2", "Shipping City":"Shipping Address City",
    "Shipping State":"Shipping Address State", "Shipping Pincode":"Shipping Address Pincode",
    "Shipping Country":"Shipping Address Country", "Customer GSTIN":"Customer GSTIN",
    "Place of Supply":"Place of Supply", "Seller GSTIN":"Seller GSTIN",
    "PAN":"PAN of Seller", "TAN":"TAN of Seller", "ARN Number":"ARN No.",
    "Invoice Upload Status":"Invoice Upload Status", "Document Type (Invoice / Credit Note)":"Document Type (Invoice / Credit Note)",
    "Supply Type (Interstate / Intrastate)":"Supply Type (Interstate / Intrastate)",
    "Tax Category (Nil / Exempted / Taxable)":"Tax Category (Nil, Exempted, Taxable)",
    "Return Status":"Return Status", "Return Date":"Return Date", "Return Reason":"Return Reason",
    "Replacement Order Number":"Replacement Order ID", "Linked Original Order Number":"Linked Original Order ID",
    "Credit Note Number":"Credit Note Number", "Credit Note Date":"Credit Note Date",
    "Settlement ID":"Marketplace Fee Type", "Settlement Date":"Marketplace Fee %",
    "Settlement Amount":"Marketplace Fee Amount", "Settlement Currency":"Marketplace Fee GST %",
    "Upload Date":"Upload Date", "Report Run Date":"Report Run Date",
    "Report Period From":"Report Period From", "Report Period To":"Report Period To",
    "File Version":"File Version", "Cashback Discount":"Item Shipping Discount",
    "Seller Discount":"Item Promotional Discount", "Platform Charges / Fees":"Platform Fee"
}
    }


    # 1️⃣ Load files
    files = file_list(raw_folder)
    if not files:
        print("No files to process. Exiting.")
        return
    
    dfs = load_files(files, raw_folder)
    if not dfs:
        print("No valid data loaded. Exiting.")
        return

    # 2️⃣ Process each file
    processed_dfs = []
    for df in dfs:
        df = map_marketplace_columns(df, marketplace_mapping)
    
    # <-- Ensure key columns are present -->
        platform = df["Platform"].iloc[0] if "Platform" in df.columns else "unknown"
        df = ensure_key_columns(df, platform)
    
        df = remove_duplicates(df)
        df = handle_missing_values(df)
        df = normalize_product_names(df)
        df = convert_datatypes(df)
        df = correct_rounding(df)
        df = derive_fields(df)
        df = flag_suspicious_transactions(df)
        processed_dfs.append(df)


    # 3️⃣ Concatenate all platforms
    final_df = concat_all_platforms(processed_dfs)

    # 4️⃣ Save cleaned CSV
    save_cleaned_csv(final_df, output_folder)
    db_config = {
    "host": "localhost",
    "user": "root",
    "password": "Samad1234",
    "database": "ecom_db",
    "table": "cleaned_invoices"
}
    upload_to_mysql(final_df, db_config)

    print("ETL Complete. Final Data Shape:", final_df.shape)
    return final_df


# -------------------------
# ENTRY POINT
# -------------------------
if __name__ == "__main__":
    main()
