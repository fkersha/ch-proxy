from flask import Flask, request, jsonify
import base64
import requests
import os

app = Flask(__name__)

@app.route("/company", methods=["GET"])
def get_company_profile():
    company_number = request.args.get("company_number")
    if not company_number:
        return jsonify({"error": "company_number is required"}), 400

    url = f"https://api.company-information.service.gov.uk/company/{company_number}"
    api_key = os.environ.get("COMPANIES_HOUSE_API_KEY")
    auth_header = {
        "Authorization": "Basic " + base64.b64encode(f"{api_key}:".encode()).decode()
    }

    r = requests.get(url, headers=auth_header)
    return jsonify(r.json()), r.status_code
