from sqlalchemy import func  # ✅ Import this at the top of your script
import streamlit as st
import pdfkit
import os
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy.orm import sessionmaker
from database import engine, User, ColumnInfo, UsageEntry
from datetime import date
import qrcode
import base64
from io import BytesIO

# Set up database session
Session = sessionmaker(bind=engine)
session = Session()

# Initialize session state for login/logout
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.admin = False
    st.session_state.employee_id = None
    st.session_state.page = "Login"

# 🔑 Login Function
def login():
    st.title("🔬 Column Management System")
    st.header("🔑 User Login")
    employee_id = st.text_input("Employee ID")
    if st.button("Login"):
        user = session.query(User).filter(User.employee_id == employee_id).first()
        if user:
            st.session_state.logged_in = True
            st.session_state.employee_id = user.employee_id
            st.session_state.admin = user.is_admin
            st.success(f"✅ Login successful! {'(Admin)' if st.session_state.admin else '(User)'}")
            st.rerun()
        else:
            st.error("❌ Invalid Employee ID. Please try again.")

# 🔹 Logout Function
def logout():
    st.session_state.logged_in = False
    st.session_state.admin = False
    st.session_state.employee_id = None
    st.rerun()

# 🔹 Register New User (Admin Only)
def register_user():
    if not st.session_state.admin:
        st.error("⚠️ Access Denied: Admins Only")
        return
    st.header("👤 Admin: Register New User")
    name = st.text_input("Full Name")
    employee_id = st.text_input("Employee ID")
    is_admin = st.checkbox("Grant Admin Privileges")
    if st.button("Register User"):
        if name and employee_id:
            new_user = User(name=name, employee_id=employee_id, is_admin=is_admin)
            session.add(new_user)
            session.commit()
            st.success(f"✅ User {name} registered successfully! {'(Admin)' if is_admin else '(User)'}")

# 📌 Register New Column
def register_column():
    st.header("📌 Register a New Column")
    last_column = session.query(ColumnInfo).order_by(ColumnInfo.column_number.desc()).first()
    next_column_number = 1 if last_column is None else int(last_column.column_number) + 1
    st.info(f"Next Column Number: {next_column_number}")
    sn = st.text_input("Serial Number")
    reference = st.text_input("Reference")
    supplier = st.text_input("Supplier")
    dimension = st.text_input("Dimension")
    column_chemistry = st.text_input("Column Chemistry")
    if st.button("Register Column"):
        if sn and reference and supplier and dimension and column_chemistry:
            new_column = ColumnInfo(
                sn=sn,
                reference=reference,
                supplier=supplier,
                dimension=dimension,
                column_number=str(next_column_number),
                column_chemistry=column_chemistry
            )
            session.add(new_column)
            session.commit()
            st.success(f"✅ Column {sn} registered successfully! Assigned Column Number: {next_column_number}")

# 📊 Dashboard
def dashboard():
    st.header("📊 Column Management Dashboard")
    st.subheader("📈 Column Usage Trends")
    usage_counts = session.query(UsageEntry.column_id, ColumnInfo.column_number)\
        .join(ColumnInfo, UsageEntry.column_id == ColumnInfo.sn).all()
    if usage_counts:
        usage_df = pd.DataFrame(usage_counts, columns=["Column ID", "Column Number"])
        usage_chart_data = usage_df["Column Number"].value_counts()
        fig, ax = plt.subplots(figsize=(8, 4))
        usage_chart_data.plot(kind="bar", ax=ax)
        ax.set_xlabel("Column Number")
        ax.set_ylabel("Usage Count")
        ax.set_title("Column Usage Frequency")
        st.pyplot(fig)
    else:
        st.warning("No column usage data available.")


# 📜 Generate PDF Report
def generate_pdf(usage):
   user = session.query(User).filter(User.id == usage.user_id).first()
   column = session.query(ColumnInfo).filter(ColumnInfo.sn == usage.column_id).first()
   employee_id = user.employee_id if user else "N/A"
   column_number = column.column_number if column else "N/A"
   # QR Code Data
   qr_data = f"""
   Column Number: {column_number}
   Serial Number: {column.sn}
   Reference: {column.reference}
   Last Used: {usage.date}
   User: {user.name}
   Project: {usage.project}
   Technique: {usage.technique}
   """
   # Generate QR Code
   qr = qrcode.make(qr_data)
   buffer = BytesIO()
   qr.save(buffer, format="PNG")
   qr_base64 = base64.b64encode(buffer.getvalue()).decode()
   # Path to GSK Logo
   logo_path = os.path.join(os.getcwd(), "gsk_logo.png")  # Ensure correct path
   # Read and encode the logo as Base64
   if os.path.exists(logo_path):
       with open(logo_path, "rb") as logo_file:
           logo_base64 = base64.b64encode(logo_file.read()).decode()
   else:
       logo_base64 = None
   # HTML for PDF
   html_content = f"""
<div style="text-align: center;">
   {f'<img src="data:image/png;base64,{logo_base64}" width="150"/>' if logo_base64 else ''}
<h2>Column Usage Report</h2>
</div>
<p><b>Employee ID:</b> {employee_id}</p>
<p><b>Column Number:</b> {column_number}</p>
<p><b>Project:</b> {usage.project}</p>
<p><b>Technique:</b> {usage.technique}</p>
<p><b>Mobile Phase A:</b> {usage.mobile_phase_a}</p>
<p><b>Mobile Phase B:</b> {usage.mobile_phase_b}</p>
<p><b>Date:</b> {usage.date}</p>
<p><b>QR Code (Scan for details):</b></p>
<img src="data:image/png;base64,{qr_base64}" width="200"/>
   """
   # Generate PDF
   pdf_path = f"usage_report_{usage.id}.pdf"
   config = pdfkit.configuration(wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe")
   pdfkit.from_string(html_content, pdf_path, configuration=config)
   return pdf_path

# 📝 Log Column Usage with Interactive Search
def log_usage():
   st.header("📝 Log Column Usage")
   if not st.session_state.logged_in:
       st.error("⚠️ You must be logged in to log usage.")
       return
   # Fetch logged-in user
   user = session.query(User).filter(User.employee_id == st.session_state.employee_id).first()
   # **Interactive Search for Column Number or Reference**
   search_query = st.text_input("🔍 Search Column by Number or Reference", "")
   # Fetch available columns dynamically based on search query
   columns_query = session.query(ColumnInfo).filter(ColumnInfo.is_obsolete == False)
   if search_query:
       columns_query = columns_query.filter(
           (ColumnInfo.column_number.contains(search_query)) |
           (ColumnInfo.reference.contains(search_query))
       )
   columns = columns_query.all()
   # **If No Matches Found, Show a Warning**
   if not columns:
       st.warning("⚠️ No matching columns found. Try a different search.")
       return
   # Since we have filtered down to one column, automatically select it
   selected_column = columns[0]
   # Other details
   project = st.text_input("📁 Project Name")
   technique = st.text_input("🧪 Technique")
   mobile_phase_a = st.text_input("💧 Mobile Phase A")
   mobile_phase_b = st.text_input("💧 Mobile Phase B")
   usage_date = st.date_input("📅 Date", date.today())
   if st.button("📝 Log Usage"):
       new_usage = UsageEntry(
           user_id=user.id,
           column_id=selected_column.sn,
           project=project,
           technique=technique,
           mobile_phase_a=mobile_phase_a,
           mobile_phase_b=mobile_phase_b,
           date=usage_date
       )
       session.add(new_usage)
       session.commit()
       st.success(f"✅ Usage entry logged successfully for Column {selected_column.column_number}!")
           
# Generate PDF and provide download option
       pdf_path = generate_pdf(new_usage)
       with open(pdf_path, "rb") as file:
           st.download_button("⬇️ Download PDF", file, file_name=f"Usage_Report_{new_usage.id}.pdf", mime="application/pdf")




# 🔍 Search & Usage Overview (Fully Fixed Employee ID Filtering)
def search_usage_overview():
   """Search & Usage Overview Page"""
   st.header("🔍 Search & Usage Overview")
   # Search filters
   col1, col2, col3 = st.columns(3)
   employee_query = col1.text_input("👤 Search by Employee ID (Case-Sensitive)")  # ✅ Case-sensitive
   column_query = col2.text_input("🔍 Search by Column Number")
   chemistry_query = col3.text_input("🧪 Search by Column Chemistry")
   col4, col5 = st.columns(2)
   reference_query = col4.text_input("📖 Search by Column Reference")
   supplier_query = col5.text_input("🏭 Search by Supplier")
   # **Debug Step 1: Check if Employee Exists**
   employee_exists = session.query(User).filter(User.employee_id == employee_query).first()
   if employee_query:
       if not employee_exists:
           st.warning(f"⚠️ No user found with Employee ID: {employee_query}")
           return  # Stop further execution if no match found
       else:
           st.success(f"✅ Found user: {employee_exists.name} (ID: {employee_exists.employee_id})")
   # Step 1: Get column IDs used by Employee ID (Case-sensitive)
   used_column_ids = []
   if employee_query and employee_exists:
       used_column_ids = (
           session.query(UsageEntry.column_id)
           .join(User, UsageEntry.user_id == User.id)
           .filter(User.employee_id == employee_query)  # ✅ Now strictly case-sensitive
           .distinct()
           .all()
       )
       used_column_ids = [col_id[0] for col_id in used_column_ids]  # Extract values
       # **Debug Step 2: Print Extracted Column IDs**
       st.write(f"🔍 Columns Used by {employee_query}: {used_column_ids}")
   # Step 2: Apply column filters
   column_query_result = session.query(ColumnInfo)
   if column_query:
       column_query_result = column_query_result.filter(ColumnInfo.column_number.contains(column_query))
   if chemistry_query:
       column_query_result = column_query_result.filter(ColumnInfo.column_chemistry.contains(chemistry_query))
   if reference_query:
       column_query_result = column_query_result.filter(ColumnInfo.reference.contains(reference_query))
   if supplier_query:
       column_query_result = column_query_result.filter(ColumnInfo.supplier.contains(supplier_query))
   filtered_columns = column_query_result.all()
   # Step 3: Apply Employee ID filter if used
   if employee_query and used_column_ids:
       filtered_columns = [col for col in filtered_columns if col.sn in used_column_ids]
   # **Debug Step 3: Print Final Filtered Columns**
   st.write(f"📋 Matching Columns after Employee ID Filter: {[col.column_number for col in filtered_columns]}")
   # Step 4: Get usage counts in a single query for efficiency
   usage_counts = dict(session.query(UsageEntry.column_id, func.count(UsageEntry.id))
                       .group_by(UsageEntry.column_id).all())
   # ✅ Column Inventory Table
   if filtered_columns:
       data = {
           "Column Number": [col.column_number for col in filtered_columns],
           "Serial Number": [col.sn for col in filtered_columns],
           "Supplier": [col.supplier for col in filtered_columns],
           "Chemistry": [col.column_chemistry for col in filtered_columns],
           "Dimension": [col.dimension for col in filtered_columns],
           "Total Times Used": [usage_counts.get(col.sn, 0) for col in filtered_columns],  # ✅ More efficient query
           "Status": ["🟢" if not col.is_obsolete else "🔴" for col in filtered_columns],  # ✅ Status column
       }
       df_inventory = pd.DataFrame(data)
       st.subheader("📋 Column Inventory Overview")
       st.dataframe(df_inventory)
       # CSV Download
       csv_inventory = df_inventory.to_csv(index=False).encode("utf-8")
       st.download_button("⬇️ Download Column Inventory CSV", csv_inventory, file_name="column_inventory.csv", mime="text/csv")
   else:
       st.warning("⚠️ No matching columns found.")
   # ✅ Detailed Column Usage History
   if filtered_columns:
       used_column_ids = [col.sn for col in filtered_columns]
       usage_records = (
           session.query(UsageEntry, User.employee_id, ColumnInfo.column_number)
           .join(User, UsageEntry.user_id == User.id)
           .join(ColumnInfo, UsageEntry.column_id == ColumnInfo.sn)
           .filter(UsageEntry.column_id.in_(used_column_ids))
           .all()
       )
       if usage_records:
           data_usage = {
               "Column Number": [col_number for _, _, col_number in usage_records],
               "Employee ID": [emp_id for _, emp_id, _ in usage_records],
               "Project": [usage.project for usage, _, _ in usage_records],
               "Mobile Phase A": [usage.mobile_phase_a for usage, _, _ in usage_records],
               "Mobile Phase B": [usage.mobile_phase_b for usage, _, _ in usage_records],
               "Technique": [usage.technique for usage, _, _ in usage_records],
               "Date Used": [usage.date for usage, _, _ in usage_records],
           }
           df_usage = pd.DataFrame(data_usage)
           st.subheader("📜 Detailed Column Usage History")
           st.dataframe(df_usage)
           # Download Usage CSV
           csv_usage = df_usage.to_csv(index=False).encode("utf-8")
           st.download_button("⬇️ Download Usage History CSV", csv_usage, file_name="column_usage_history.csv", mime="text/csv")





# 🛠 Modify Column Information (All Users)
def modify_column():
   """Allow users to modify existing column information."""
   st.header("🛠️ Modify Column Information")
   # Interactive Search for Column Number
   search_column = st.text_input("🔍 Enter Column Number to Modify & Press Enter", "")
   if search_column:
       column = session.query(ColumnInfo).filter(ColumnInfo.column_number == search_column).first()
       if column:
           st.success(f"✅ Column {column.column_number} found. Modify details below.")
           # Input Fields for Editing
           new_reference = st.text_input("📖 Reference", column.reference)
           new_supplier = st.text_input("🏭 Supplier", column.supplier)
           new_dimension = st.text_input("📏 Dimension", column.dimension)
           new_chemistry = st.text_input("🧪 Column Chemistry", column.column_chemistry)
           # Available vs. Obsolete Toggle
           is_obsolete = st.checkbox("🔴 Mark as Obsolete", column.is_obsolete)
           # Save Changes
           if st.button("💾 Save Changes"):
               column.reference = new_reference
               column.supplier = new_supplier
               column.dimension = new_dimension
               column.column_chemistry = new_chemistry
               column.is_obsolete = is_obsolete
               session.commit()
               st.success(f"✅ Column {column.column_number} updated successfully!")
       else:
           st.error(f"❌ Column {search_column} not found. Please enter a valid column number.")



# 🚀 Page Navigation
def main():
   if not st.session_state.logged_in:
       login()
       return
   pages = {
       "Log Usage": log_usage,
       "Search & Usage Overview": search_usage_overview,  # ✅ Merged Page
       "Modify Column Info": modify_column,  # ✅ Add this new page
       "Register Column": register_column,
       "Dashboard": dashboard,
   }
   if st.session_state.admin:
       pages["Register Users (Admin)"] = register_user
   selected_page = st.sidebar.selectbox("Select Page", list(pages.keys()))
   if st.sidebar.button("Logout 🔒", key="logout_button"):
       logout()
   pages[selected_page]()


if __name__ == "__main__":
    main()
