"""Small provider evaluation; records observed outputs/timing, never fabricated scores."""
import json, os, tempfile, time
from pathlib import Path
from dotenv import load_dotenv
from agent import run_agent
from db import init_db, summarize

load_dotenv()
CASES=[
 {"q":"Add an expense of 200 in food with note lunch.","tool":"add_expense","check":"food"},
 {"q":"Record 85 for transport.","tool":"add_expense","check":"transport"},
 {"q":"I spent 120 on groceries, save it.","tool":"add_expense","check":"groceries"},
 {"q":"Add 45 for coffee.","tool":"add_expense","check":"coffee"},
 {"q":"Save 999 as shopping.","tool":"add_expense","check":"shopping"},
 {"q":"Record 60 for snacks.","tool":"add_expense","check":"snacks"},
 {"q":"Add 150 for books.","tool":"add_expense","check":"books"},
 {"q":"I paid 75 for bus fare, category travel.","tool":"add_expense","check":"travel"},
 {"q":"Add 310 for utilities.","tool":"add_expense","check":"utilities"},
 {"q":"Record 25 for tea.","tool":"add_expense","check":"tea"},
 {"q":"What is 25 + 35? Use calculator.","tool":"calculate","check":"60"},
 {"q":"Calculate (10 + 5) * 3.","tool":"calculate","check":"45"},
 {"q":"Use calculator for 144 / 12.","tool":"calculate","check":"12"},
 {"q":"Calculate 7 squared using the calculator.","tool":"calculate","check":"49"},
 {"q":"What is 100 minus 37? Calculate it.","tool":"calculate","check":"63"},
 {"q":"Calculate 9 * 8.","tool":"calculate","check":"72"},
 {"q":"Use calculator: (50-8)/2.","tool":"calculate","check":"21"},
 {"q":"Calculate 81 / 9.","tool":"calculate","check":"9"},
 {"q":"How much have I spent by category in the last 7 days? Use the summary tool.","tool":"get_expense_summary","check":"summary"},
 {"q":"Show my expense totals for the past 30 days by category.","tool":"get_expense_summary","check":"summary"},
]
def main():
    # Fresh isolated DB for each run; restore environment after evaluation.
    with tempfile.TemporaryDirectory() as tmp:
        old=os.environ.get("DB_PATH")
        os.environ["DB_PATH"]=str(Path(tmp)/"eval.sqlite")
        init_db()
        results=[]; durations=[]; errors=0
        for i,case in enumerate(CASES,1):
            start=time.perf_counter(); used=[]; answer=""; error=None
            for attempt in range(3):
                try:
                    answer,used=run_agent(case["q"]); break
                except Exception as exc:
                    error=str(exc)
                    if attempt<2 and any(x in error.lower() for x in ("429","503","rate","unavailable")):
                        time.sleep(2**(attempt+1))
                    else: break
            elapsed=time.perf_counter()-start; durations.append(elapsed)
            ok=error is None and case["tool"] in used
            if case["tool"]=="calculate" and ok: ok=case["check"] in str(answer)
            if case["tool"]=="add_expense" and ok:
                ok=case["check"] in summarize(3650)
            if error: errors+=1
            results.append({"id":i,"question":case["q"],"expected_tool":case["tool"],
                            "tools_used":used,"answer":str(answer),"seconds":round(elapsed,3),
                            "passed":bool(ok),"error":error})
            print(f"{i:02}/{len(CASES)} {'PASS' if ok else 'FAIL'} {elapsed:.2f}s")
        report={"provider":os.getenv("PROVIDER","gemini"),"model":os.getenv("GEMINI_MODEL","gemini-2.0-flash"),
                "cases":len(CASES),"correct":sum(r["passed"] for r in results),
                "accuracy":round(sum(r["passed"] for r in results)/len(results),4),
                "average_response_seconds":round(sum(durations)/len(durations),3),
                "tool_call_errors":errors,"results":results}
        Path("results.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(json.dumps({k:v for k,v in report.items() if k!="results"},indent=2))
        if old is None: os.environ.pop("DB_PATH",None)
        else: os.environ["DB_PATH"]=old
if __name__=="__main__": main()
