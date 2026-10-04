import os
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from agent import run_agent
from db import init_db

load_dotenv()
app = Flask(__name__)
init_db()

@app.get("/health")
def health():
    return jsonify({"status":"healthy"})

@app.post("/chat")
def chat():
    data=request.get_json(silent=True)
    if not isinstance(data,dict) or not isinstance(data.get("message"),str) or not data["message"].strip():
        return jsonify({"error":"Provide a non-empty 'message' string."}),400
    try:
        answer, tools_used = run_agent(data["message"])
        return jsonify({"answer":answer,"tools_used":tools_used})
    except Exception as exc:
        # Keep internal details out of API responses; details can be inspected in the server terminal.
        app.logger.exception("Chat request failed")
        return jsonify({"error":"The assistant could not complete this request. Check the server log and try again."}),503

if __name__=="__main__":
    app.run(debug=False)
