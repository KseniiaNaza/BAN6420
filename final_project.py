# The survey app with Flask and MongoDB :)
from flask import Flask, render_template, request, redirect, send_file
from pymongo import MongoClient
from dataclasses import dataclass
import pprint  # for printing stuff nicely
import csv     # for create csv file
import os
import pandas as pd  # for loading CSV into DataFrame
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # for visualization
import numpy as np  # for generating color values

app = Flask(__name__)

# Connection with MongoDB (use env variable if exists)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["survey_db"]
collection = db["participants"]

# A simple class to hold the user's info
@dataclass
class User:
    age: int
    gender: str
    total_income: float
    expenses: dict 

    def total_expenses(self):
        return sum(self.expenses.values())

    def to_dict(self):
        return {
            "age": self.age,
            "gender": self.gender,
            "total_income": round(self.total_income, 2),
            "expenses": {k: round(v, 2) for k, v in self.expenses.items()}
        }

# Main page where people fill the form
@app.route("/", methods=["GET", "POST"])
def survey():
    if request.method == "POST":
        data = request.form
        expenses = {}
        categories = ["utilities", "entertainment", "school_fees", "shopping", "healthcare"]
        for cat in categories:
            if data.get(cat):  # only if checkbox is checked
                try:
                    amount = round(float(data.get(f"{cat}_amount", 0)), 2)
                    expenses[cat] = amount
                except ValueError:
                    expenses[cat] = 0.0

        user = User(
            age=int(data.get("age")),
            gender=data.get("gender"),
            total_income=round(float(data.get("total_income")), 2),
            expenses=expenses
        )

        pprint.pprint(user.to_dict())
        collection.insert_one(user.to_dict())
        return redirect("/thanks")

    return render_template("survey.html")

@app.route("/thanks")
def thanks():
    return "<h1>Your data collected! Thank you for the applying!</h1>"

@app.route("/results")
def results():
    users = list(collection.find())

    # CSV file saving
    csv_filename = "results.csv"
    with open(csv_filename, mode="w", newline="") as csv_file:
        fieldnames = ["age", "gender", "total_income"] + ["utilities", "entertainment", "school_fees", "shopping", "healthcare"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        for user in users:
            row = {
                "age": user.get("age"),
                "gender": user.get("gender"),
                "total_income": user.get("total_income")
            }
            for category in ["utilities", "entertainment", "school_fees", "shopping", "healthcare"]:
                row[category] = user.get("expenses", {}).get(category, 0.0)
            writer.writerow(row)

    # Load entire CSV into pandas DataFrame and full table printing
    df = pd.read_csv(csv_filename, delimiter=';')
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    print("\nResults table:")
    print(df)

    # Vizualization for highest incomes by age
    df_sorted = df.sort_values(by="total_income", ascending=False).head(10)
    df_sorted = df_sorted.sort_values(by="age")

    plt.figure(figsize=(10, 6))
    colors = plt.cm.viridis(np.linspace(0, 1, len(df_sorted)))
    income_thousands = df_sorted["total_income"] / 1000
    plt.bar(df_sorted["age"].astype(str), income_thousands, color=colors)
    plt.xlabel("Age")
    plt.ylabel("Total Income (in thousands $)")
    plt.title("Top 10. Highest incomes by Age")
    plt.grid(True)
    plt.tight_layout()
    os.makedirs("static", exist_ok=True)
    plt.savefig("static/income_by_age.png")
    plt.close()

    # Vizualization for Gender-based spending categories
    category_cols = ["utilities", "entertainment", "school_fees", "shopping", "healthcare"]
    df_gender = df.groupby("gender")[category_cols].sum()
    df_gender.T.plot(kind="bar", figsize=(10, 6))
    plt.title("Spending by Category per Gender")
    plt.xlabel("Category")
    plt.ylabel("Total Spending ($)")
    plt.legend(title="Gender")
    plt.tight_layout()
    plt.savefig("static/gender_spending.png")
    plt.close()

    html = "<h1>Survey Results</h1><ul>"
    for user in users:
        html += f"<li><strong>Age:</strong> {user.get('age')} | "
        html += f"<strong>Gender:</strong> {user.get('gender')} | "
        html += f"<strong>Income:</strong> ${user.get('total_income')} | "
        html += f"<strong>Expenses:</strong> {user.get('expenses')}</li>"
    html += "</ul>"
    html += f"<p><a href='/download_csv'>Download CSV File</a></p>"
    html += f"<p><a href='/download_income_chart'>Download Income Chart</a></p>"
    html += f"<p><a href='/download_gender_chart'>Download Gender Spending Chart</a></p>"
    html += f"<img src='/static/income_by_age.png' alt='Income by Age Chart'>"
    html += f"<img src='/static/gender_spending.png' alt='Gender Spending Chart'>"
    return html

@app.route("/download_csv")
def download_csv():
    csv_path = os.path.join(os.getcwd(), "results.csv")
    return send_file(csv_path, as_attachment=True)

@app.route("/download_income_chart")
def download_income_chart():
    chart_path = os.path.join(os.getcwd(), "static/income_by_age.png")
    return send_file(chart_path, as_attachment=True)

@app.route("/download_gender_chart")
def download_gender_chart():
    chart_path = os.path.join(os.getcwd(), "static/gender_spending.png")
    return send_file(chart_path, as_attachment=True)

# Start the server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
