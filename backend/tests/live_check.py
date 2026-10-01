"""Live-server validation: boots uvicorn, exercises the full API surface."""
import subprocess
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
        cwd=".",
    )
    try:
        for _ in range(60):
            try:
                r = httpx.get(f"{BASE}/api/health", timeout=2)
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(0.5)
        else:
            print("SERVER DID NOT START")
            return 1

        print("health:", httpx.get(f"{BASE}/api/health").json())
        print("dashboard:", {k: v for k, v in httpx.get(f"{BASE}/api/dashboard").json().items()
                             if k in ("security_score", "active_incidents", "events_analyzed", "threat_level")})

        # demo run
        print("demo start:", httpx.post(f"{BASE}/api/demo/start").json()["state"])
        seen = []
        contained = False
        for _ in range(90):
            st = httpx.get(f"{BASE}/api/demo").json()
            if not seen or seen[-1] != (st["step"], st["state"]):
                seen.append((st["step"], st["state"]))
                print(f"  step {st['step']:>2} {st['state']:<10} {st['label']}")
            if st["state"] in ("timeout", "failed", "complete", "aborted"):
                break
            if st["state"] == "running" and st["step"] == 9 and not contained:
                inc_id = st.get("incident_id")
                if inc_id:
                    cr = httpx.post(f"{BASE}/api/incidents/{inc_id}/contain", timeout=10)
                    print("  contain ->", cr.status_code, cr.json().get("message"))
                    contained = True
            time.sleep(1)
        final = httpx.get(f"{BASE}/api/demo").json()
        print("demo final:", final["state"], final["label"], "steps:", len(seen))
        incs = httpx.get(f"{BASE}/api/incidents").json()
        print("incidents:", [(i["threat_type"], i["status"], i["risk_score"]) for i in incs["items"]])
        net = httpx.get(f"{BASE}/api/network").json()
        print("node statuses:", {n["id"]: n["status"] for n in net["nodes"]})
        d = httpx.get(f"{BASE}/api/dashboard").json()
        print("post-demo score:", d["security_score"], d["active_incidents"], d["threat_categories"])
        ok = final["state"] in ("complete", "timeout")
        print("RESULT:", "OK" if ok else "FAIL")
        return 0 if ok else 2
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
