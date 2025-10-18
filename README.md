# 🧾 Multi-Marketplace MTR Data Analysis

**Developed by:** Abdul Samad  
**Date:** October 2025  
**Project Type:** Data Cleaning & Analysis (ETL + Insights)  
**Tools:** Python, Pandas, Matplotlib  

---

## 📘 Overview

This project automates the **end-to-end analysis of Monthly Transaction Reports (MTRs)** from multiple e-commerce marketplaces — **Amazon, Flipkart, and Meesho**.  
The system standardizes and merges all marketplaces into one format using **mapping files**, performs **data cleaning**, and generates **sales, profit, and GST analysis** automatically.

---

## ⚙️ Key Features

- ✅ Unified mapping for all marketplaces (Amazon, Flipkart, Meesho)  
- ✅ Cleans raw data, fixes date & numeric issues  
- ✅ Combines all MTRs into a single cleaned dataset  
- ✅ Generates analysis reports: sales, profit, GST, and product performance  
- ✅ Automatically logs ETL operations  
- ✅ Produces visualization charts for insights  

---


---

## 🧠 Workflow

1. **Raw Data:**  
   Place all raw MTRs (Amazon, Flipkart, Meesho) inside the `Data Raw/` folder.

2. **Mapping:**  
   Each platform’s mapping file in the `Mapping/` folder ensures all columns match the same standard schema.

3. **Cleaning:**  
   Run `data_cleaning.py` to fix missing data, incorrect dates, and invalid entries.  
   Output → `Cleaned_files/cleaned_invoices.csv`

4. **Analysis:**  
   Run `data_analyzing.py` or `run_all.py` to generate:
   - Profit, Sales, GST, Product, and Customer Analysis files  
   - Charts in `ETL_Log/charts/`

5. **Visualization:**  
   All summary insights are generated and saved automatically.

---

## 🧮 How to Run

Install all dependencies:
```bash
pip install -r requirements.txt

| Folder              | Output                                                     |
| ------------------- | ---------------------------------------------------------- |
| `Cleaned_files/`    | Final merged & cleaned invoice data                        |
| `All_Analysis/`     | Sales, Profit, GST, Product, Customer, Marketplace reports |
| `ETL_Log/charts/`   | Visualizations and graphs                                  |
| `ETL_Log/Insights/` | Summaries and conclusions                                  |
🧰 Libraries Used

pandas – data manipulation

numpy – numerical operations

matplotlib – charts and plots

openpyxl – Excel support

🚀 Future Scope

AI-based sales forecasting

Dynamic dashboard using Streamlit or Power BI

Automated alerts for profit and tax tracking

👨‍💻 Developer

Abdul Samad
Data & Automation Enthusiast
Built with ❤️ using Python and Pandas

