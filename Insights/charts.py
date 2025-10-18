import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
from data_cleaning import log_error
import ast
import re
from datetime import datetime
import matplotlib.dates as mdates

# ------------------- Load Insights -------------------
def load_and_verify_insights(insights_path="All_Analysis/"):
    os.makedirs("etl_log", exist_ok=True)

    expected_metrics = [
        "sales_Analysis.csv",
        "gst_Analysis.csv",
        "profit_Analysis.csv",
        "product_Analysis.csv",
        "customer_Analysis.csv",
        "marketplace_Analysis.csv"
    ]

    loaded_insights = {}
    missing_metrics = []

    for metric_file in expected_metrics:
        file_path = os.path.join(insights_path, metric_file)
        if os.path.exists(file_path):
            try:
                loaded_insights[metric_file] = pd.read_csv(file_path)
            except Exception as e:
                log_error("etl_log/visuals_missing_metrics.csv",
                          f"Failed to load {metric_file}",
                          {"error": str(e)})
                missing_metrics.append(metric_file)
        else:
            missing_metrics.append(metric_file)

    if missing_metrics:
        log_error("etl_log/visuals_missing_metrics.csv",
                  "Missing metrics detected",
                  {"missing_files": missing_metrics})
        print(f"❌ Missing or failed metric files: {missing_metrics}")
    else:
        print("✅ All metrics loaded successfully.")

    return loaded_insights

# ------------------- Chart Functions -------------------
def sales_chart(insights, save_path=None):
    sales_df = insights.get("sales_Analysis.csv")
    if sales_df is not None:
        daily_sales_str = sales_df.loc[sales_df['Metric'] == 'Daily Sales Trend', 'Value'].values[0]
        pattern = r"datetime\.date\((\d+), (\d+), (\d+)\): ([\d\.]+)"
        matches = re.findall(pattern, daily_sales_str)
        data = [(datetime(int(y), int(m), int(d)), float(val)) for y, m, d, val in matches]
        df = pd.DataFrame(data, columns=["Date", "NetRevenue"]).sort_values("Date")

        plt.figure(figsize=(8,5))
        plt.plot(df['Date'], df['NetRevenue'], marker='o', color='green', linewidth=2)
        plt.title("Sales Trend - Net Revenue Over Time", fontsize=16)
        plt.xlabel("Date")
        plt.ylabel("Net Revenue")
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.xticks(rotation=45)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    else:
        print("❌ Sales insights not found.")

def platform_comparison_chart(insights, save_path=None):
    sales_df = insights.get("sales_Analysis.csv")
    if sales_df is not None:
        platform_str = sales_df.loc[sales_df['Metric'] == 'Platform Split', 'Value'].values[0]
        platform_dict = ast.literal_eval(platform_str)
        df = pd.DataFrame(list(platform_dict.items()), columns=['Platform', 'NetRevenue'])
        colors = {'amazon': '#146EB4', 'flipkart': '#F9A825', 'meesho': '#7B2CBF'}
        bar_colors = [colors.get(p.lower(), '#1f77b4') for p in df['Platform']]

        plt.figure(figsize=(8,6))
        bars = plt.bar(df['Platform'], df['NetRevenue'], color=bar_colors, edgecolor='black', linewidth=1.2)
        plt.title("Platform Comparison - Net Revenue by Marketplace", fontsize=16, fontweight='bold')
        plt.xlabel("Platform")
        plt.ylabel("Net Revenue")
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.xticks(fontsize=11)
        plt.yticks(fontsize=11)

        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, height + max(df['NetRevenue'])*0.01,
                     f"{height:,.0f}", ha='center', va='bottom', fontsize=10, fontweight='bold')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    else:
        print("❌ Sales insights not found.")

    profit_df = insights.get("profit_Analysis.csv")
    if profit_df is not None:
        profit_str = profit_df.loc[profit_df['Metric'] == 'Platform-wise Profit', 'Value'].values[0]
        profit_dict = ast.literal_eval(profit_str)
        fee_impact_pct = float(profit_df.loc[profit_df['Metric'] == 'Fee Impact %', 'Value'].values[0])
        discount_impact_pct = float(profit_df.loc[profit_df['Metric'] == 'Discount Impact %', 'Value'].values[0])
        df = pd.DataFrame(list(profit_dict.items()), columns=['Platform', 'NetProfit'])
        df['Revenue'] = df['NetProfit'] / (1 - fee_impact_pct - discount_impact_pct)
        df['Deductions'] = df['Revenue'] - df['NetProfit']

        plt.figure(figsize=(8,6))
        colors_map = {'amazon': '#146EB4', 'flipkart': '#F9A825', 'meesho': '#7B2CBF'}
        revenue_colors = [colors_map.get(p.lower(), '#1f77b4') for p in df['Platform']]
        deduction_colors = ['#A6CEE3', '#FFF176', '#D291BC']

        plt.bar(df['Platform'], df['Revenue'], color=revenue_colors, edgecolor='black', linewidth=1.2, label='Revenue')
        plt.bar(df['Platform'], df['Deductions'], bottom=df['NetProfit'], color=deduction_colors, edgecolor='black', linewidth=1.2, label='Deductions/Fees')

        for i, row in df.iterrows():
            plt.text(i, row['Revenue'] + row['Deductions']*0.01, f"{row['Revenue']:.0f}", ha='center', va='bottom', fontsize=10, fontweight='bold')
            plt.text(i, row['NetProfit']/2, f"{row['NetProfit']:.0f}", ha='center', va='center', fontsize=10, color='black', fontweight='bold')

        plt.title("P&L Breakdown by Platform", fontsize=18, fontweight='bold')
        plt.xlabel("Platform")
        plt.ylabel("Amount")
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.xticks(fontsize=11)
        plt.yticks(fontsize=11)
        plt.legend()
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    else:
        print("❌ Profit insights not found.")

def top_products_chart(insights, save_path=None):
    product_df = insights.get("product_Analysis.csv")
    if product_df is not None:
        top_str = product_df.loc[product_df['Metric'] == 'Top 10 Products by Revenue', 'Value'].values[0]
        top_dict = ast.literal_eval(top_str)
        df = pd.DataFrame(list(top_dict.items()), columns=['Product', 'NetRevenue']).sort_values('NetRevenue', ascending=True)

        plt.figure(figsize=(10,6))
        bars = plt.barh(df['Product'], df['NetRevenue'], color='darkgreen', edgecolor='black', linewidth=1.2)

        for bar in bars:
            width = bar.get_width()
            plt.text(width + max(df['NetRevenue'])*0.01, bar.get_y() + bar.get_height()/2,
                     f"{width:,.0f}", va='center', fontsize=10, fontweight='bold')

        plt.title("Top 10 Products by Net Revenue", fontsize=16, fontweight='bold')
        plt.xlabel("Net Revenue")
        plt.ylabel("Product")
        plt.grid(axis='x', linestyle='--', alpha=0.5)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    else:
        print("❌ Product insights not found.")

# ------------------- Remaining 5 charts -------------------
# -------------------------
def gst_summary_chart(insights, save_path=None):
    gst_df = insights.get("gst_Analysis.csv")
    if gst_df is not None:
        monthly_str = gst_df.loc[gst_df['Metric'] == 'Monthly GST Summary', 'Value'].values[0]
        pattern = r"Period\('(\d{4}-\d{2})', 'M'\): ([\d\.]+)"
        matches = re.findall(pattern, monthly_str)

        data = [(datetime.strptime(date, "%Y-%m").date(), float(value)) for date, value in matches]
        df = pd.DataFrame(data, columns=['Month', 'GSTCollected']).sort_values('Month')

        plt.figure(figsize=(10,6))
        bars = plt.bar(df['Month'], df['GSTCollected'], color='#F9A825', edgecolor='black', linewidth=1.2)

        for i, row in df.iterrows():
            plt.text(row['Month'], row['GSTCollected'] + max(df['GSTCollected'])*0.01,
                     f"{row['GSTCollected']:,.0f}", ha='center', va='bottom', fontsize=9, fontweight='bold')

        plt.title("Monthly GST Summary", fontsize=16, fontweight='bold')
        plt.xlabel("Month")
        plt.ylabel("GST Collected")
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.xticks(rotation=45)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    else:
        print("❌ GST insights not found.")

# -------------------------
def customer_insights_chart(insights, save_path=None):
    customer_df = insights.get("customer_Analysis.csv")
    if customer_df is not None:
        repeat = int(customer_df.loc[customer_df['Metric'] == 'Repeat Buyers', 'Value'].values[0])
        new = int(customer_df.loc[customer_df['Metric'] == 'New Buyers', 'Value'].values[0])
        labels = ['Repeat Buyers', 'New Buyers']
        sizes = [repeat, new]
        colors = ['#146EB4', '#7B2CBF']  # Amazon blue & Meesho dark purple

        plt.figure(figsize=(6,6))
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140,
                wedgeprops={'edgecolor':'black'})
        plt.title("Customer Insights: Repeat vs New Buyers", fontsize=16, fontweight='bold')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    else:
        print("❌ Customer insights not found.")

# -------------------------
def returns_vs_rto_chart(insights, save_path=None):
    product_df = insights.get("product_Analysis.csv")
    if product_df is not None:
        worst_str = product_df.loc[product_df['Metric'] == 'Worst Performers', 'Value'].values[0]
        worst_list = ast.literal_eval(worst_str)
        data = [(item['Item Description'], item['Returns'], item['Total_Orders'] - item['Returns']) for item in worst_list]
        df = pd.DataFrame(data, columns=['Product', 'Returns', 'Delivered'])

        plt.figure(figsize=(12,6))
        bar_width = 0.4
        indices = range(len(df))

        plt.bar([i - bar_width/2 for i in indices], df['Delivered'], width=bar_width,
                color='green', edgecolor='black', label='Delivered')
        plt.bar([i + bar_width/2 for i in indices], df['Returns'], width=bar_width,
                color='red', edgecolor='black', label='Returns')

        for i, row in df.iterrows():
            plt.text(i - bar_width/2, row['Delivered'] + max(df['Delivered'])*0.01, f"{row['Delivered']}", ha='center', va='bottom', fontsize=9, fontweight='bold')
            plt.text(i + bar_width/2, row['Returns'] + max(df['Returns'])*0.01, f"{row['Returns']}", ha='center', va='bottom', fontsize=9, fontweight='bold')

        plt.xticks(indices, df['Product'], rotation=45, ha='right')
        plt.ylabel("Orders")
        plt.title("Returns vs Delivered Orders by Product", fontsize=16, fontweight='bold')
        plt.legend()
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    else:
        print("❌ Product insights not found.")

# -------------------------
def abc_analysis_chart(insights, save_path=None):
    product_df = insights.get("product_Analysis.csv")
    if product_df is not None:
        abc_str = product_df.loc[product_df['Metric'] == 'ABC Analysis', 'Value'].values[0]
        abc_list = ast.literal_eval(abc_str)
        df = pd.DataFrame(abc_list)
        category_summary = df.groupby('Category')['NetRevenue'].sum().reset_index()

        colors = {'A': '#146EB4', 'B': '#F9A825', 'C': '#7B2CBF'}

        plt.figure(figsize=(8,6))
        bars = plt.bar(category_summary['Category'], category_summary['NetRevenue'],
                       color=[colors[c] for c in category_summary['Category']],
                       edgecolor='black', linewidth=1.2)

        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, height + max(category_summary['NetRevenue'])*0.01,
                     f"{height:,.0f}", ha='center', va='bottom', fontsize=10, fontweight='bold')

        plt.title("ABC Analysis - Revenue by Product Category", fontsize=16, fontweight='bold')
        plt.xlabel("Category")
        plt.ylabel("Net Revenue")
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    else:
        print("❌ Product insights not found.")

# -------------------------
def top_customers_contribution_chart(insights, save_path=None):
    customer_df = insights.get("customer_Analysis.csv")
    if customer_df is not None:
        top10_row = customer_df[customer_df['Metric'] == 'Top 10 Customers by Revenue']
        if not top10_row.empty:
            customers_dict = ast.literal_eval(top10_row['Value'].values[0])
            df = pd.DataFrame(list(customers_dict.items()), columns=['Customer', 'Revenue']).sort_values('Revenue', ascending=True)

            plt.figure(figsize=(10, 6))
            bars = plt.barh(df['Customer'], df['Revenue'], color='#146EB4', edgecolor='black')

            for index, value in enumerate(df['Revenue']):
                plt.text(value + max(df['Revenue'])*0.01, index, f"{value:,.0f}", va='center', fontsize=10, fontweight='bold')

            plt.xlabel('Revenue')
            plt.title('Top Customers Contribution', fontsize=16, fontweight='bold')
            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
            else:
                plt.show()
        else:
            print("❌ Top 10 Customers data not found.")
    else:
        print("❌ Customer insights not found.")
def profit_trend_chart(insights, save_path=None):
    profit_df = insights.get("profit_Analysis.csv")
    if profit_df is None:
        print("❌ Profit insights not found.")
        return

    trend_row = profit_df[profit_df['Metric'] == 'Weekly Profit Trend']
    if trend_row.empty:
        print("❌ Weekly Profit Trend data not found.")
        return

    trend_str = trend_row['Value'].values[0]

    # Regex to extract Period start date and profit
    pattern = r"Period\('(\d{4}-\d{2}-\d{2})/\d{4}-\d{2}-\d{2}', 'W-SUN'\): ([\d\.]+)"
    matches = re.findall(pattern, trend_str)

    if not matches:
        print("❌ Profit Trend data is empty or in wrong format.")
        return

    data = [(datetime.strptime(date, "%Y-%m-%d").date(), float(profit)) for date, profit in matches]
    df = pd.DataFrame(data, columns=["Date", "NetProfit"]).sort_values("Date")

    plt.figure(figsize=(8,5))
    plt.plot(df['Date'], df['NetProfit'], marker='o', color='#146EB4', linewidth=2)
    plt.title("Weekly Profit Trend", fontsize=16, fontweight='bold')
    plt.xlabel("Week Start Date")
    plt.ylabel("Net Profit")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.xticks(rotation=45)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()

# ------------------- Save All Charts -------------------
def save_all_charts(insights, folder_path="Insights/charts"):
    os.makedirs(folder_path, exist_ok=True)
    chart_funcs = {
        "Sales_Trend": sales_chart,
        "Platform_Comparison": platform_comparison_chart,
        "PL_Breakdown": profit_trend_chart,
        "Top_Products": top_products_chart,
        "Profit_Trend": profit_trend_chart,
        "GST_Summary": gst_summary_chart,
        "Customer_Insights": customer_insights_chart,
        "Returns_vs_RTO": returns_vs_rto_chart,
        "ABC_Analysis": abc_analysis_chart,
        "Top_Customers_Contribution": top_customers_contribution_chart
    }
    for name, func in chart_funcs.items():
        try:
            save_path = os.path.join(folder_path, f"{name}.png")
            func(insights, save_path=save_path)
            print(f"✅ {name} chart saved at {save_path}")
        except Exception as e:
            print(f"❌ Failed to generate {name} chart: {e}")

# ------------------- Main -------------------
def main():
    ch = load_and_verify_insights("All_Analysis/")
    save_all_charts(ch)

if __name__ == "__main__":
    main()
