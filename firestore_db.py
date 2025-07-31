import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase only once
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["service_account"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

def add_expense(user_email, date, category, amount, note):
    expense_data = {
        "user": user_email,
        "date": date,
        "category": category,
        "amount": amount,
        "note": note,
    }
    db.collection("expenses").add(expense_data)

def save_monthly_salary(user_email, month, salary):
    db.collection("salary").document(user_email).set({
        "month": month,
        "salary": salary
    })

def get_user_expenses(user_email):
    docs = db.collection("expenses").where("user", "==", user_email).stream()
    return [doc.to_dict() for doc in docs]

def get_user_salary(user_email):
    doc = db.collection("salary").document(user_email).get()
    if doc.exists:
        return doc.to_dict().get("salary", 0.0)
    return 0.0

def delete_expense(doc_id):
    db.collection("expenses").document(doc_id).delete()
