
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

# Initialize session defaults
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# LOGIN / SIGNUP 
if not st.session_state.is_logged_in:
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "Login"

    st.title("Login or Sign Up")

    mode = st.radio("Select Option", ["Login", "Sign Up"], index=0 if st.session_state.auth_mode == "Login" else 1)
    st.session_state.auth_mode = mode

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.session_state.auth_mode == "Sign Up":
        if st.button("Sign Up"):
            result = signup_user(email, password)
            if isinstance(result, dict):
                st.success("Signup successful! Please login now.")
                st.session_state.auth_mode = "Login"
            else:
                st.error(f"Error: {result}")

    elif st.session_state.auth_mode == "Login":
        if st.button("Login"):
            result = login_user(email, password)
            if isinstance(result, dict):
                st.success("Login successful!")
                st.session_state["is_logged_in"] = True
                st.session_state["current_user"] = email
                st.session_state["user_token"] = result["idToken"]

                # Save in cookies
                cookies["email"] = email
                cookies["token"] = result["idToken"]
                st.rerun()

# MAIN APP 
else:
    st.subheader("Monthly Salary")
    current_month = datetime.date.today().strftime("%B")
    monthly_salary = st.number_input("Enter your Monthly Salary (₹)", min_value=0.0, format="%.2f")

    if st.button("Save Salary"):
        save_monthly_salary(st.session_state.current_user, current_month, monthly_salary)
        st.success(f"Salary for {current_month} saved!")

    st.title("+ Add New Expense")
    st.subheader(f"Welcome, {st.session_state.current_user}")
    date = st.date_input("Date", value=datetime.date.today())
    category = st.selectbox("Category", ["Food", "Grocery", "Transport", "Shopping", "Bills", "Entertainment", "Other"])
    amount = st.number_input("Amount (₹)", min_value=0.0, format="%.2f")
    note = st.text_input("Note (optional)")

    if st.button("+ Add Expense"):
        if amount > 0:
            add_expense(st.session_state.current_user, str(date), category, amount, note)
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

        st.subheader("Expense Table")

        # Column headers
        cols = st.columns([2, 2, 2, 3, 1])
        cols[0].markdown("**Date**")
        cols[1].markdown("**Category**")
        cols[2].markdown("**Amount**")
        cols[3].markdown("**Note**")
        cols[4].markdown("**Action**")
        # Loop through each expense row
        for idx, row in df.iterrows():
          cols = st.columns([2, 2, 2, 3, 1])
          cols[0].markdown(f"{row['date'].date()}")
          cols[1].markdown(row["category"])
          cols[2].markdown(f"₹{row['amount']}")
          cols[3].markdown(row["note"] if row["note"] else "-")
          with cols[4]:
            delete_btn = st.button("🗑️", key=f"del_{idx}")
            if delete_btn:
              delete_expense(row["id"])
              st.success("Deleted!")
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