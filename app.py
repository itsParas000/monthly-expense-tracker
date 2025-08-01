
import streamlit as st
import datetime
from firebase_auth import signup_user, login_user
from session_manager import save_session, load_session, clear_session
from firestore_db import add_expense,get_user_expenses, save_monthly_salary, get_user_salary, delete_expense
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
from fpdf import FPDF
from streamlit_cookies_manager import EncryptedCookieManager
from firestore_db import db

# Setup secure cookie manager
cookies = EncryptedCookieManager(prefix="moex_", password="your_very_secret_key")
if not cookies.ready():
    st.stop()

# Restore login if cookie is valid
if (
    "is_logged_in" not in st.session_state or not st.session_state["is_logged_in"]
) and cookies.get("email") and cookies.get("token"):
    st.session_state["is_logged_in"] = True
    st.session_state["current_user"] = cookies.get("email")
    st.session_state["user_token"] = cookies.get("token")

    #Restore Username from firestore
    user_doc = db.collection("users").document(cookies.get("email")).get()
    if user_doc.exists:
        st.session_state["username"] = user_doc.to_dict().get("username", "")

# Initialize session defaults
# Ensure default values in session_state
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Login"


# LOGIN / SIGNUP 
if not st.session_state.is_logged_in:
    st.title("Login or Sign Up")
    
    mode = st.radio("Select Option", ["Login", "Sign Up"], index=0 if st.session_state.auth_mode == "Login" else 1)
    st.session_state.auth_mode = mode

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if mode == "Sign Up":
        username = st.text_input("Username")
        if st.button("Sign Up"):
            if not email or not password or not username:
                st.warning("All fields are required.")
            else:
                result = signup_user(email, password)
                if isinstance(result, dict):
                    db.collection("users").document(email).set({
                        "username": username,
                        "email": email
                    })
                    st.success("Signup successful! Please login.")
                    st.session_state.auth_mode = "Login"
                else:
                    st.error(f"Error: {result}")

    else:  # Login
        if st.button("Login"):
            if not email or not password:
                st.warning("Please enter both email and password.")
            else:
                result = login_user(email, password)
                if isinstance(result, dict):
                    user_doc = db.collection("users").document(email).get()
                    if user_doc.exists:
                        user_data = user_doc.to_dict()
                        st.session_state["username"] = user_data.get("username", "")
                        st.session_state["is_logged_in"] = True
                        st.session_state["current_user"] = email
                        st.session_state["user_token"] = result["idToken"]

                        cookies["email"] = email
                        cookies["token"] = result["idToken"]
                        st.rerun()
                    else:
                        st.error("User not found.")
                else:
                    st.error(f"Error: {result}")


# MAIN APP 
else:
    st.subheader("Monthly Salary")
    current_month = datetime.date.today().strftime("%B")
    monthly_salary = st.number_input("Enter your Monthly Salary (₹)", min_value=0.0, format="%.2f")

    if st.button("Save Salary"):
        save_monthly_salary(st.session_state.current_user, current_month, monthly_salary)
        st.success(f"Salary for {current_month} saved!")

    st.title("+ Add New Expense")
    st.subheader(f"Welcome, {st.session_state.get('username', st.session_state.get('current_user', 'User'))}")
    date = st.date_input("Date", value=datetime.date.today())
    category = st.selectbox("Category", ["Food", "Grocery", "Transport", "Shopping", "Bills", "Entertainment", "Other"])
    amount = st.number_input("Amount (₹)", min_value=0.0, format="%.2f")
    note = st.text_input("Note (optional)")

    if st.button("+ Add Expense"):
        if amount > 0:
            add_expense(st.session_state.current_user, str(date), category, amount, note, st.session_state.get("username", ""))
            st.success("Expense added successfully!")
            st.rerun()
        else:
            st.warning("Amount must be greater than 0.")

    st.markdown("---")
    st.subheader("Your Expenses")

    data = get_user_expenses(st.session_state.current_user)

    
    if data:
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(by="date", ascending=False)
        
        st.subheader("Expense Table (Editable)")

        df.set_index("id", inplace=True)
        # Drop the 'id' column from display
        if "id" in df.columns:
            df.drop(columns=['id'], inplace=True)
            
        # Set index for document tracking
        visible_columns = ["date", "category", "amount", "note"]
        edited_df = st.data_editor(
            # df[["username", "date", "category", "amount", "note"]],
            df[visible_columns],
            column_config={"username": st.column_config.TextColumn(disabled=True)},
            num_rows="dynamic",
            use_container_width=True,
            key="expense_editor"
        )

        # Compare and detect deletions
        deleted_ids = df.index.difference(edited_df.index)
        if not deleted_ids.empty:
            for doc_id in deleted_ids:
                delete_expense(str(doc_id))
            st.success("Deleted selected rows.")
            

        # Save edited entries
        if st.button("Save Updates"):
            for doc_id, row in edited_df.iterrows():
                updated = {
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "category": row["category"],
                    "amount": float(row["amount"]),
                    "note": row["note"]
                }
                # Push to Firestore
                from firebase_admin import firestore
                db = firestore.client()
                doc_ref = db.collection("expenses").document(str(doc_id))
                if doc_ref.get().exists:
                    doc_ref.update(updated)
            st.success("Changes saved.")
            st.rerun()

        
        
        
        
              # Salary and warnings
        saved_salary = get_user_salary(st.session_state.current_user)
        current_month = datetime.datetime.now().month
        monthly_spent = df[df["date"].dt.month == current_month]["amount"].sum()
        savings = saved_salary - monthly_spent

        st.success(f"Total Monthly Spend: ₹{monthly_spent}")
        st.info(f"Remaining (Savings): ₹{savings}")

        if monthly_spent > saved_salary:
            st.warning("You're spending more than your income this month!")

        if not df.empty:
            top_category = df.groupby("category")["amount"].sum().idxmax()
            top_amount = df.groupby("category")["amount"].sum().max()
            if top_amount > 0.3 * saved_salary:
                st.error(f"Too much spent on **{top_category}** this month (₹{top_amount}). Try to control it!")

            max_day = df[df["amount"] == df["amount"].max()]
            st.info(f"Biggest expense on {max_day.iloc[0]['date']} in {max_day.iloc[0]['category']} — ₹{max_day.iloc[0]['amount']}")

        # Filters
        with st.expander("Filter Your Expenses"):
            category_filter = st.multiselect("Category", options=df["category"].unique())
            date_range = st.date_input("Date Range", [])

            if category_filter:
                df = df[df["category"].isin(category_filter)]

            if len(date_range) == 2:
                start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
                df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

        # Charts
        if not df.empty:
            st.subheader("Expense Charts")

            df = df.sort_values("date")
            fig, ax = plt.subplots()
            ax.plot(df["date"], df["amount"], marker="o", linestyle="-")
            ax.set_title("Expense Over Time")
            ax.set_xlabel("Date")
            ax.set_ylabel("Amount")
            fig.autofmt_xdate()
            st.pyplot(fig)

            fig, ax = plt.subplots()
            sns.barplot(data=df, x="category", y="amount", ax=ax)
            ax.set_title("Total Expense by Category")
            st.pyplot(fig)

            pie_data = df.groupby("category")["amount"].sum()
            fig, ax = plt.subplots()
            ax.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%", startangle=90)
            ax.set_title("Expense Distribution by Category")
            ax.axis("equal")
            st.pyplot(fig)

        # Export Data
        st.markdown("Export Your Data")

        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name="Expenses.csv",
            mime="text/csv",
        )

        def generate_pdf(dataframe):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            pdf.set_font("Arial", "B", size=14)
            pdf.cell(200, 10, "Expenses Report", ln=True, align="C")
            pdf.ln(10)

            pdf.set_font("Arial", "B", size=10)
            for col in dataframe.columns:
                pdf.cell(40, 8, col, border=1)
            pdf.ln()

            pdf.set_font("Arial", size=10)
            for _, row in dataframe.iterrows():
                for item in row:
                    pdf.cell(40, 8, str(item), border=1)
                pdf.ln()

            return pdf.output(dest="S").encode("latin-1")

        if not df.empty:
            pdf_bytes = generate_pdf(df)
            st.download_button(
                label="Download PDF",
                data=pdf_bytes,
                file_name="Expenses.pdf",
                mime="application/pdf",
            )

    else:
        st.info("No expenses added yet.")

    # Logout
    if st.button("Logout"):
        cookies["email"] = ""
        cookies["token"] = ""
        cookies.save()
        st.session_state["is_logged_in"] = False
        st.session_state["current_user"] = None
        st.session_state["user_token"] = None
        st.rerun()
