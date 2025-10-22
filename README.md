# 💳 Credit Card Statement Parser

## 📘 Project Overview
The **Credit Card Statement Parser** is a Python-based solution built to automatically extract key financial information from credit card statements (in PDF format).  
It supports multiple banks and provides a **Streamlit-based user interface** to upload, parse, and view extracted data in a structured and user-friendly manner.

This project demonstrates the ability to handle **real-world document parsing challenges**, such as layout variations, text extraction, and pattern matching across different credit card providers.

---

## 🏦 Supported Credit Card Providers
The parser currently supports statements from the following five major issuers:
1. **American Express (Amex)**
2. **Chase Bank**
3. **Citi Bank**
4. **Bank of America**
5. **HSBC**

Each provider has unique formatting styles and layouts, which are handled using adaptable parsing logic and regex patterns.

---

## 🔍 Extracted Data Points
The parser extracts **five key data points** from each credit card statement:

| # | Data Point | Description |
|---|-------------|-------------|
| 1 | **Cardholder Name** | Name of the account holder as shown on the statement |
| 2 | **Card Last 4 Digits** | The last four digits of the credit card number |
| 3 | **Billing Cycle** | The start and end dates of the billing period |
| 4 | **Payment Due Date** | The final date by which payment must be made |
| 5 | **Total Amount Due** | The total balance or due amount for the billing period |

Additionally, the application displays **recent transactions** (date, merchant, and amount) if available in the statement.

---

## 🖥️ Tech Stack
| Component | Technology |
|------------|-------------|
| **Language** | Python 3.x |
| **Frontend/UI** | Streamlit |
| **PDF Parsing** | PyPDF2, pdfminer.six |
| **Data Processing** | Regular Expressions, Pandas |

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/<your-username>/credit-card-statement-parser.git
cd credit-card-statement-parser
