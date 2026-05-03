import requests

questions = [
    "What is GitLab mission?",
    "What are the GitLab values?",
    "How does GitLab handle code review?",
    "What is GitLabs approach to remote work?",
    "What is GitLab direction for AI features?",
    "How does GitLab handle security vulnerabilities?",
    "What is GitLabs release process?",
    "How does GitLab support open source?",
    "What is GitLabs approach to hiring?",
    "What is GitLab CI/CD pipeline?",
]

results = []
for q in questions:
    res = requests.post("http://127.0.0.1:8000/chat", json={"question": q}, timeout=30)
    data = res.json()
    answer = data.get("answer", "")
    sources = data.get("sources", [])
    top_score = sources[0]["score"] if sources else 0
    results.append({
        "q": q,
        "answer": answer[:250],
        "top_score": round(top_score, 4),
        "num_sources": len(sources),
        "has_error": "Error during search" in answer or "missing" in answer.lower()
    })

print("\n===== ACCURACY TEST RESULTS =====\n")
good = 0
for i, r in enumerate(results, 1):
    status = "FAIL" if r["has_error"] else "PASS"
    if not r["has_error"]:
        good += 1
    print(f"[{status}] Q{i}: {r['q']}")
    print(f"      Top Cosine Score: {r['top_score']} | Sources returned: {r['num_sources']}")
    print(f"      Answer: {r['answer']}")
    print()

avg_score = sum(r["top_score"] for r in results) / len(results)
accuracy = (good / len(results)) * 100
print(f"===== SUMMARY =====")
print(f"Questions Tested : {len(results)}")
print(f"Passed           : {good}/{len(results)}")
print(f"Pass Rate        : {accuracy:.0f}%")
print(f"Avg Cosine Score : {avg_score:.4f}")
