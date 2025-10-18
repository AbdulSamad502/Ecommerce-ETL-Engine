import pandas as pd
import numpy as np
from data_cleaning import log_error
from pprint import pprint
import os 

def load_cleaned_data(file_path):
    """
    Load cleaned invoices CSV or SQL table, verify standard columns,
    fill missing columns, and log any missing columns.
    """
    preferred_cols = [
        "Invoice Number", "Invoice Type", "Invoice Date", "Order ID", "Shipment ID",
        "Shipment Item ID", "Platform", "Item Description", "Quantity", "Item Price",
        "Item Discount", "Item Promotional Discount", "Item Shipping Discount",
        "Shipping Charge", "Packing Fee", "COD Fee", "Platform Fee",
        "Marketplace Fee Amount", "NetRevenue", "Payment Method", "SuspiciousFlag"
    ]
    
    
    df = pd.read_csv(rf"{file_path}")
    
   
    missing_cols = [col for col in preferred_cols if col not in df.columns]
    
    if missing_cols:
        print(f"Missing columns detected: {missing_cols}")  # 
        log_error(
            "etl_log/missing_columns_insights.csv",
            f"Missing columns: {missing_cols}",
            {"file": file_path}
        )
        
       
        for col in missing_cols:
            if col in [
                "Quantity", "Item Price", "Item Discount", "Item Promotional Discount", 
                "Item Shipping Discount", "Shipping Charge", "Packing Fee", 
                "COD Fee", "Platform Fee", "Marketplace Fee Amount", "NetRevenue", "SuspiciousFlag"
            ]:
                df[col] = 0
            else:
                df[col] = "Unknown"
    
    return df
# -----------------
df = load_cleaned_data("cleanedfiles/cleaned_invoices.csv")
# ----------------------
def calculate_sales_metrics(df):
    # Gross Sales (already present in your df, but ensure correct calc too)
    df["GrossSales"] = df["Quantity"] * df["Item Price"]

    # Combine all discount types
    df["TotalDiscount"] = (
        df.get("Item Discount", 0)
        + df.get("Item Promotional Discount", 0)
        + df.get("Item Shipping Discount", 0)
    )

    # Net Revenue calculation (if not already in df)
    df["NetRevenue"] = (
        df["GrossSales"]
        - df["TotalDiscount"]
        - df.get("Shipping Charge", 0)
        - df.get("Packing Fee", 0)
        - df.get("COD Fee", 0)
        - df.get("Platform Fee", 0)
        - df.get("Marketplace Fee Amount", 0)
    )

    order_count = df["Invoice Number"].nunique()
    units_sold = df["Quantity"].sum()
    platform_split = df.groupby("Platform")["NetRevenue"].sum()
    average_sp = df["NetRevenue"].sum() / units_sold if units_sold != 0 else 0

    if "Invoice Date" in df.columns:
        df["Invoice Date"] = pd.to_datetime(df["Invoice Date"], errors="coerce")
        weekly_sales = df.groupby(df["Invoice Date"].dt.to_period("W"))["NetRevenue"].sum()
        week_growth = weekly_sales.pct_change() * 100
        daily_sales = df.groupby(df["Invoice Date"].dt.date)["NetRevenue"].sum()
        peak_day = daily_sales.idxmax() if not daily_sales.empty else None
    else:
        weekly_sales, week_growth, daily_sales, peak_day = {}, {}, {}, None

    metrics = {
        "Total Gross Sales": df["GrossSales"].sum(),
        "Total Net Revenue": df["NetRevenue"].sum(),
        "Orders Count": order_count,
        "Units Sold": units_sold,
        "Platform Split": platform_split.to_dict(),
        "Average_SP": average_sp,
        "Weekly Growth %": week_growth.to_dict() if not isinstance(week_growth, dict) else week_growth,
        "Daily Sales Trend": daily_sales.to_dict() if not isinstance(daily_sales, dict) else daily_sales,
        "Peak Day": peak_day,
    }

    return metrics


def calculate_gst_metrics(df):
    numeric_cols = ["CGST Amount", "SGST Amount", "IGST Amount", "TCS Amount", "TDS Amount", "Total Taxable Value"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    df["GST_Collected"] = df["CGST Amount"] + df["SGST Amount"] + df["IGST Amount"]
    
    if "Invoice Date" in df.columns:
        df["Invoice Date"] = pd.to_datetime(df["Invoice Date"], errors="coerce")
        monthly_gst = df.groupby(df["Invoice Date"].dt.to_period("M"))["GST_Collected"].sum()
    else:
        monthly_gst = pd.Series(dtype=float)

    hsn_col = "HSN / SAC" if "HSN / SAC" in df.columns else None
    if hsn_col:
        hsn_split = df.groupby(hsn_col)["GST_Collected"].sum()
    else:
        hsn_split = pd.Series(dtype=float)

    mismatch_tax = df[(df["Total Taxable Value"] > 0) & (df["GST_Collected"] == 0)]

    gst_on_returns = df.loc[df["Transaction Type"] == "Return", "GST_Collected"].sum()

    net_gst_payable = df["GST_Collected"].sum() - gst_on_returns - (df["TCS Amount"].sum() + df["TDS Amount"].sum())

    gst_anomalies = df[(df["Total Taxable Value"] > 0) & (df["GST_Collected"] == 0)]

    gst_metrics = {
        "Total GST Collected": df["GST_Collected"].sum(),
        "Monthly GST Summary": monthly_gst.to_dict(),
        "HSN-wise GST Split": hsn_split.to_dict(),
        "Tax Mismatches": mismatch_tax.to_dict("records"),
        "Net GST Payable": net_gst_payable,
        "GST Anomalies": gst_anomalies.to_dict("records")
    }

    return gst_metrics


def calculate_profit_metrics(df):
    df["Return_Impact"] = np.where(df["Transaction Type"]=="Return", df["NetRevenue"], 0)
    df["TCS Amount"] = df.get("TCS Amount", pd.Series(0, index=df.index))
    df["TDS Amount"] = df.get("TDS Amount", pd.Series(0, index=df.index))

    df["NetProfit"] = df["NetRevenue"] - (df["Platform Fee"] + df["Marketplace Fee Amount"]) \
                      - (df["Shipping Charge"] + df["Packing Fee"] + df["COD Fee"]) \
                      - df["Return_Impact"] - df["TCS Amount"] - df["TDS Amount"]

    df["Profit_Margin"] = np.where(df["NetRevenue"] > 0, (df["NetProfit"]/df["NetRevenue"])*100, 0)
    df["FeeImpact%"] = np.where(df["NetRevenue"] > 0, ((df["Platform Fee"] + df["Marketplace Fee Amount"]) / df["NetRevenue"]) * 100, 0)

    df["Invoice Date"] = pd.to_datetime(df["Invoice Date"], errors="coerce")
    Weekly_Profit = df.groupby(df["Invoice Date"].dt.to_period("W"))["NetProfit"].sum()
    df["BreakEven"] = df["NetRevenue"] - (df["Platform Fee"] + df["Marketplace Fee Amount"] + df["Shipping Charge"] + df["Packing Fee"] + df["COD Fee"] + df["TotalDiscount"])

    platform_profit = df.groupby("Platform")["NetProfit"].sum()
    discount_impact = (df["TotalDiscount"].sum() / df["NetRevenue"].sum()) * 100

    profit_metrics = {
        "Total Net Profit": df["NetProfit"].sum(),
        "Average Profit Margin %": df["Profit_Margin"].mean(),
        "Fee Impact %": df["FeeImpact%"].mean(),
        "Weekly Profit Trend": Weekly_Profit.to_dict(),
        "Platform-wise Profit": platform_profit.to_dict(),
        "Break-even Analysis": {
            "Profitable Orders": (df["BreakEven"] >= 0).sum(),
            "Loss Orders": (df["BreakEven"] < 0).sum()
        },
        "Discount Impact %": discount_impact
    }

    return profit_metrics

def calculate_product_metrics(df):
   
    results = {}

    top_products = (
        df.groupby("Item Description")["NetRevenue"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .to_dict()
    )
    results["Top 10 Products by Revenue"] = top_products

    grouped = (
        df.groupby("Item Description")
        .agg(
            Total_Orders=("Order ID", "count"),
            Returns=("Return Status", lambda x: (x == "Returned").sum()),
            NetRevenue=("NetRevenue", "sum"),
            GrossSales=("GrossSales", "sum")
        )
        .reset_index()
    )
    grouped["Return %"] = (grouped["Returns"] / grouped["Total_Orders"]) * 100
    grouped["Margin"] = grouped["NetRevenue"] - grouped["GrossSales"]

    worst_performers = grouped[
        (grouped["Return %"] > 20) | (grouped["Margin"] < 0)
    ].sort_values(by=["Return %", "Margin"], ascending=[False, True])
    results["Worst Performers"] = worst_performers.to_dict(orient="records")

    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    latest_date = df["Order Date"].max()
    cutoff_date = latest_date - pd.DateOffset(months=3)

    last_order = df.groupby("Item Description")["Order Date"].max().reset_index()
    dead_stock = last_order[last_order["Order Date"] < cutoff_date]
    results["Dead Stock Alerts"] = dead_stock["Item Description"].tolist()

    contribution = (
        df.groupby("Item Description")["NetRevenue"]
        .sum()
        .reset_index()
    )
    total_rev = contribution["NetRevenue"].sum()
    contribution["Contribution %"] = (contribution["NetRevenue"] / total_rev * 100).round(2)
    results["Contribution % per Product"] = contribution.to_dict(orient="records")

    revenue = (
        df.groupby("Item Description")["NetRevenue"]
        .sum()
        .reset_index()
        .sort_values(by="NetRevenue", ascending=False)
        .reset_index(drop=True)
    )
    total_revenue = revenue["NetRevenue"].sum()
    revenue["CumulativeRevenue%"] = revenue["NetRevenue"].cumsum() / total_revenue * 100

    def classify(pct):
        if pct <= 70:
            return "A"
        elif pct <= 90:
            return "B"
        else:
            return "C"

    revenue["Category"] = revenue["CumulativeRevenue%"].apply(classify)
    results["ABC Analysis"] = revenue[["Item Description", "NetRevenue", "Category"]].to_dict(orient="records")

    return results

def calculate_customer_metrics(df):
    results = {}

    # 1. Unique Customers
    if "Customer ID" in df.columns:
        cust_col = "Customer ID"
    else:
        cust_col = "Bill To Name"
    results["Unique Customers"] = df[cust_col].nunique()

    # 2. Repeat vs New Buyers
    cust_count = df.groupby(cust_col)["Order ID"].nunique()
    repeat_buyers = (cust_count > 1).sum()
    new_buyers = (cust_count == 1).sum()
    results["Repeat Buyers"] = int(repeat_buyers)
    results["New Buyers"] = int(new_buyers)

    # 3. Top 10 Customers by Revenue
    top_cust = (
        df.groupby(cust_col)["NetRevenue"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .to_dict()
    )
    results["Top 10 Customers by Revenue"] = top_cust

    # 4. Pareto 80/20 Analysis
    revenue_by_cust = (
        df.groupby(cust_col)["NetRevenue"]
        .sum()
        .sort_values(ascending=False)
    )
    cumulative_pct = revenue_by_cust.cumsum() / revenue_by_cust.sum() * 100
    cutoff = (cumulative_pct <= 80).sum()
    total_customers = results["Unique Customers"]
    pareto_pct = round((cutoff / total_customers) * 100, 2)
    results["Pareto 80/20"] = f"{pareto_pct}% of customers contribute 80% of revenue"

    # 5. Average Order Value (AOV) per Customer
    revenue_per_customer = df.groupby(cust_col)["NetRevenue"].sum()
    orders_per_customer = df.groupby(cust_col)["Order ID"].nunique()
    aov = (revenue_per_customer / orders_per_customer).mean()
    results["Average Order Value per Customer"] = round(aov, 2)

    # 6. High-Risk Customers (frequent returns >50%)
    returns_per_customer = (
        df[df["Return Status"] == "Returned"]
        .groupby(cust_col)["Order ID"]
        .nunique()
    )
    return_rate = (returns_per_customer / cust_count).fillna(0)
    high_risk_customers = return_rate[return_rate > 0.5].index.tolist()
    results["High-Risk Customers"] = high_risk_customers

    return results
def calculate_marketplace_metrics(df):
    revenue_orders_profit = (
        df.groupby("Platform")
        .agg(
            Revenue=("NetRevenue", "sum"),
            GrossSales=("GrossSales", "sum"),
            Orders=("Order ID", "nunique")
        )
        .reset_index()
    )
    revenue_orders_profit["Profit"] = revenue_orders_profit["Revenue"]
    revenue_orders_profit = revenue_orders_profit.to_dict(orient="records")

    return_rate = (
        df.groupby("Platform")["Return Status"]
        .apply(lambda x: (x == "Returned").mean() * 100)
        .to_dict()
    )

    rto_rate = (
        df.groupby("Platform")[["Return Status", "Payment Method"]]
        .apply(
            lambda x: ((x["Return Status"] == "Returned") & (x["Payment Method"] == "COD")).mean() * 100
        )
        .to_dict()
    )

    cashflow_visibility = (
        df.groupby("Platform")
        .agg(
            GrossSales=("GrossSales", "sum"),
            NetRevenue=("NetRevenue", "sum")
        )
        .reset_index()
    )
    cashflow_visibility["Gap"] = (
        cashflow_visibility["GrossSales"] - cashflow_visibility["NetRevenue"]
    )
    cashflow_visibility = cashflow_visibility.to_dict(orient="records")

    df["Order Date"] = pd.to_datetime(df["Order Date"])
    monthly_growth_trend = (
        df.groupby([pd.Grouper(key="Order Date", freq="M"), "Platform"])["NetRevenue"]
        .sum()
        .reset_index()
        .to_dict(orient="records")
    )

    return {
        "Revenue_Orders_Profit": revenue_orders_profit,
        "Return Rate %": return_rate,
        "RTO Rate %": rto_rate,
        "Cashflow Visibility": cashflow_visibility,
        "Monthly Growth Trend": monthly_growth_trend,
    }

def save_insights(df, output_path="All_Analysis/"):
    try:
        os.makedirs(output_path, exist_ok=True)

        # Run all metric functions
        insights = {
            "Sales": calculate_sales_metrics(df),
            "GST": calculate_gst_metrics(df),
            "Profit": calculate_profit_metrics(df),
            "Product": calculate_product_metrics(df),
            "Customer": calculate_customer_metrics(df),
            "Marketplace": calculate_marketplace_metrics(df),
        }

        # Save each insight in a clean DataFrame format
        for name, data in insights.items():
            file_path = os.path.join(output_path, f"{name.lower()}_Analysis.csv")

            if isinstance(data, dict):
                # Nested dicts (convert into key-value table)
                df_out = pd.DataFrame(list(data.items()), columns=["Metric", "Value"])
            elif isinstance(data, list):
                # List of dicts (already tabular)
                df_out = pd.DataFrame(data)
            else:
                # Single values
                df_out = pd.DataFrame([{"Metric": name, "Value": data}])

            df_out.to_csv(file_path, index=False)

        print(f"✅ All insights saved in structured format at {output_path}")

    except Exception as e:
        log_error(
            "etl_log/save_Analysis_errors.csv",
            "Failed to save Analysis",
            {"error": str(e)},
        )
        print("❌ Error while saving Analysis. Logged to etl_log/save_Analysis_errors.csv")

# ------------------Main Function------------------
def main():
    try:
        print("🚀 Loading cleaned data...")
        df = load_cleaned_data("cleanedfiles/cleaned_invoices.csv")

        print("📊 Generating insights...")
        save_insights(df, output_path="All_Analysis/")

        print("✅ Pipeline completed successfully! All insights saved in /insights folder.")

    except Exception as e:
        log_error(
            "etl_log/main_errors.csv",
            "Pipeline failed",
            {"error": str(e)}
        )
        print("❌ Pipeline failed. Check etl_log/main_errors.csv for details.")
        

if __name__ == "__main__":
    main()



    
