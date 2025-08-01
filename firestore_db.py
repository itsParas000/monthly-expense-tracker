import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase only once
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["service_account"]))
    firebase_admin.initialize_app(cred)

def add_expense(user_email, date, category, amount, note, username=""):
    expense = {
        "user": user_email,
        "username": username,
        "date": date,
        "category": category,
        "amount": amount,
        "note": note,
        "timestamp": firestore.SERVER_TIMESTAMP,
    }
    db.collection("expenses").add(expense)


def save_monthly_salary(user_email, month, salary):
    db.collection("salary").document(user_email).set({
        "month": month,
        "salary": salary
    })

def get_user_expenses(email):
    expenses_ref = db.collection("expenses").where("user", "==", email).stream()
    expenses = []
    for doc in expenses_ref:
        exp = doc.to_dict()
        exp["id"] = doc.id
        expenses.append(exp)
    return expenses

def get_user_salary(user_email):
    doc = db.collection("salary").document(user_email).get()
    if doc.exists:
        return doc.to_dict().get("salary", 0.0)
    return 0.0

def delete_expense(doc_id):
    db.collection("expenses").document(str(doc_id)).delete()
