# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_extra.json
- Mode: ollama
- Records: 200
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.62 | 0.92 | 0.3 |
| Avg attempts | 1 | 1.1 | 0.1 |
| Avg token estimate | 971.34 | 1103.47 | 132.13 |
| Avg latency (ms) | 2031.73 | 2832.88 | 801.15 |

## Failure modes
```json
{
  "react": {
    "none": 62,
    "wrong_final_answer": 38
  },
  "reflexion": {
    "none": 92,
    "wrong_final_answer": 8
  },
  "overall": {
    "none": 154,
    "wrong_final_answer": 46
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
Reflexion helps when the first attempt stops after the first hop or drifts to a wrong second-hop entity. The tradeoff is higher attempts, token cost, and latency. In a real report, students should explain when the reflection memory was useful, which failure modes remained, and whether evaluator quality limited gains.
