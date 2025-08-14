"""Intent analyzer that runs test cases and uses AI to suggest improvements.

This script:
1. Loads test cases from intent_cases.json
2. Runs each case against the backend
3. Generates a detailed report
4. Uses OpenAI to analyze results and suggest improvements
"""
import os
import json
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

import openai
from openai import AsyncOpenAI

# Load test cases
def load_test_cases() -> List[Dict[str, Any]]:
    """Load test cases from JSON file."""
    path = Path(__file__).parent / "intent_cases.json"
    with open(path) as f:
        return json.load(f)["cases"]

class IntentTestResult:
    def __init__(
        self,
        text: str,
        expected_source: str,
        expected_tool: str,
        expected_args: Dict[str, Any],
        comment: str,
    ):
        self.text = text
        self.expected_source = expected_source
        self.expected_tool = expected_tool
        self.expected_args = expected_args
        self.comment = comment
        self.actual_source: Optional[str] = None
        self.actual_tool: Optional[str] = None
        self.actual_args: Optional[Dict[str, Any]] = None
        self.executed: Optional[bool] = None
        self.tool_latency_ms: Optional[float] = None
        self.response_time_ms: float = 0
        self.passed = False
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "expected": {
                "source": self.expected_source,
                "tool": self.expected_tool,
                "args": self.expected_args,
                "comment": self.comment,
            },
            "actual": {
                "source": self.actual_source,
                "tool": self.actual_tool,
                "args": self.actual_args,
                "executed": self.executed,
                "tool_latency_ms": self.tool_latency_ms,
                "response_time_ms": self.response_time_ms,
            },
            "passed": self.passed,
            "error": self.error,
        }

class IntentAnalysisReport:
    def __init__(self):
        self.results: List[IntentTestResult] = []
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.ai_feedback: Optional[str] = None

    def add_result(self, result: IntentTestResult):
        self.results.append(result)

    def finalize(self):
        self.end_time = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        router_hits = sum(1 for r in self.results if r.actual_source == "router")
        harmony_hits = sum(1 for r in self.results if r.actual_source == "harmony")
        executed = sum(1 for r in self.results if r.executed)

        return {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": round(100 * passed / max(1, total), 1),
                "router_hits": router_hits,
                "harmony_hits": harmony_hits,
                "executed_rate": round(100 * executed / max(1, total), 1),
                "avg_tool_latency_ms": round(
                    sum(r.tool_latency_ms or 0 for r in self.results) / max(1, total),
                    1,
                ),
                "avg_response_ms": round(
                    sum(r.response_time_ms for r in self.results) / max(1, total),
                    1,
                ),
            },
            "results": [r.to_dict() for r in self.results],
            "start_time": self.start_time.isoformat() + "Z",
            "end_time": self.end_time.isoformat() + "Z" if self.end_time else None,
            "ai_feedback": self.ai_feedback,
        }

    def save_json(self, path: str):
        """Save report as JSON."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def save_markdown(self, path: str):
        """Save report as Markdown with tables and AI feedback."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        d = self.to_dict()
        with open(path, "w") as f:
            f.write("# Intent Analysis Report\n\n")
            
            # Summary table
            f.write("## Summary\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            s = d["summary"]
            f.write(f"| Total Tests | {s['total']} |\n")
            f.write(f"| Passed | {s['passed']} |\n")
            f.write(f"| Failed | {s['failed']} |\n")
            f.write(f"| Pass Rate | {s['pass_rate']}% |\n")
            f.write(f"| Router Hits | {s['router_hits']} |\n")
            f.write(f"| Harmony Hits | {s['harmony_hits']} |\n")
            f.write(f"| Tool Execution Rate | {s['executed_rate']}% |\n")
            f.write(f"| Avg Tool Latency | {s['avg_tool_latency_ms']} ms |\n")
            f.write(f"| Avg Response Time | {s['avg_response_ms']} ms |\n")
            f.write("\n")

            # Results table
            f.write("## Detailed Results\n\n")
            f.write("| Phrase | Expected | Actual | Tool Latency | Response Time | Passed |\n")
            f.write("|---------|-----------|---------|--------------|---------------|--------|\n")
            for r in d["results"]:
                exp = f"{r['expected']['tool']} via {r['expected']['source']}"
                act = f"{r['actual']['tool'] or '?'} via {r['actual']['source'] or '?'}"
                tool_lat = f"{r['actual']['tool_latency_ms']:.1f}ms" if r['actual']['tool_latency_ms'] is not None else "?"
                resp_lat = f"{r['actual']['response_time_ms']:.1f}ms"
                passed = "✅" if r["passed"] else "❌"
                f.write(f"| `{r['text']}` | {exp} | {act} | {tool_lat} | {resp_lat} | {passed} |\n")
            f.write("\n")

            # AI Feedback
            if d["ai_feedback"]:
                f.write("## AI Analysis & Recommendations\n\n")
                f.write(d["ai_feedback"])
                f.write("\n\n")

            # Timestamp
            f.write(f"\nTest run: {d['start_time']} → {d['end_time']}\n")

async def analyze_results(report: IntentAnalysisReport) -> str:
    """Use OpenAI to analyze results and suggest improvements."""
    client = AsyncOpenAI()

    # Prepare context
    d = report.to_dict()
    context = {
        "summary": d["summary"],
        "results": [
            {
                "text": r["text"],
                "expected": r["expected"],
                "actual": r["actual"],
                "passed": r["passed"],
            }
            for r in d["results"]
        ],
    }

    # Prompt
    prompt = f"""You are analyzing the results of an intent classification test for a voice assistant.
The system has two paths for handling commands:
1. Router: Fast rule-based matching for exact commands
2. Harmony: LLM-based understanding for natural language

Here are the test results:
{json.dumps(context, indent=2)}

Please analyze the results and provide recommendations in this format:

1. Failed Cases Analysis
- List each failed test case and explain why it failed
- Identify patterns in the failures

2. Router vs Harmony Balance
- Are commands going to the right path?
- Should confidence thresholds be adjusted?

3. Prompt Improvements
- Suggestions for improving the Harmony prompt
- Example phrases to add to router rules

4. Performance Analysis
- Tool latency patterns
- Response time patterns
- Any concerning metrics

Keep your analysis concise and actionable. Focus on concrete steps to improve the system.
"""

    # Get AI feedback
    response = await client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1000,
    )

    return response.choices[0].message.content

async def run_intent_tests(base_url: str = "http://127.0.0.1:8000") -> IntentAnalysisReport:
    """Run all test cases and generate report with AI analysis."""
    report = IntentAnalysisReport()
    cases = load_test_cases()
    
    async with httpx.AsyncClient() as client:
        for case in cases:
            result = IntentTestResult(
                text=case["text"],
                expected_source=case["expect"]["source"],
                expected_tool=case["expect"]["tool"],
                expected_args=case["expect"]["args"],
                comment=case["expect"].get("comment", ""),
            )

            try:
                t0 = datetime.utcnow()
                r = await client.post(
                    f"{base_url}/api/chat",
                    json={"prompt": case["text"]},
                    timeout=10.0,
                )
                result.response_time_ms = (datetime.utcnow() - t0).total_seconds() * 1000

                if r.status_code != 200:
                    result.error = f"HTTP {r.status_code}"
                    report.add_result(result)
                    continue

                data = r.json()
                meta_tool = (data.get("meta") or {}).get("tool")
                if not meta_tool:
                    result.error = "No meta.tool in response"
                    report.add_result(result)
                    continue

                # Record actual values
                result.actual_tool = meta_tool.get("name")
                result.actual_source = meta_tool.get("source")
                result.actual_args = meta_tool.get("args")
                result.executed = meta_tool.get("executed")
                result.tool_latency_ms = meta_tool.get("latency_ms")

                # Check expectations
                result.passed = (
                    result.actual_tool == result.expected_tool
                    and result.actual_source == result.expected_source
                    # Loose args check - expected must be subset of actual
                    and all(
                        result.actual_args.get(k) == v
                        for k, v in result.expected_args.items()
                    )
                )

            except Exception as e:
                result.error = str(e)

            report.add_result(result)

    # Get AI analysis
    report.ai_feedback = await analyze_results(report)
    report.finalize()
    return report

async def main():
    """Run intent analysis and save reports."""
    base_url = os.getenv("SERVER_URL", "http://127.0.0.1:8000")
    report_dir = os.getenv("REPORT_DIR", "tests/reports")
    
    # Run tests and analysis
    report = await run_intent_tests(base_url)
    
    # Save reports
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report.save_json(f"{report_dir}/intent_analysis_{ts}.json")
    report.save_markdown(f"{report_dir}/intent_analysis_{ts}.md")
    
    # Print summary and AI feedback
    d = report.to_dict()
    print("\nIntent Analysis Summary:")
    print(f"Total: {d['summary']['total']}")
    print(f"Passed: {d['summary']['passed']}")
    print(f"Pass Rate: {d['summary']['pass_rate']}%")
    print(f"Router Hits: {d['summary']['router_hits']}")
    print(f"Harmony Hits: {d['summary']['harmony_hits']}")
    print("\nAI Recommendations:")
    print("=" * 80)
    print(d["ai_feedback"])
    print("=" * 80)
    print(f"\nFull reports saved to {report_dir}/")

    # Exit with status
    sys.exit(0 if d["summary"]["pass_rate"] > 95 else 1)

if __name__ == "__main__":
    asyncio.run(main())
