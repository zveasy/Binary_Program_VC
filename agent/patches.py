"""
Patch generation and SARIF output for CompLexAI findings.

Generates machine-readable SARIF reports and optional code fix suggestions.
"""

import json
import os
from typing import Any, Dict, List, Optional

from agent.base import AgentResult, AgentFinding, Severity, FindingCategory


def generate_sarif(result: AgentResult, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a SARIF 2.1.0 report from agent findings.

    SARIF (Static Analysis Results Interchange Format) is the standard
    format consumed by GitHub Code Scanning, Azure DevOps, and other tools.

    Args:
        result: AgentResult from any agent.
        output_path: If provided, write SARIF JSON to this file.

    Returns:
        SARIF report as a dict.
    """
    rules = []
    results_list = []

    for i, finding in enumerate(result.findings):
        rule_id = f"complexai/{finding.category.value}"

        level_map = {
            Severity.CRITICAL: "error",
            Severity.WARNING: "warning",
            Severity.INFO: "note",
        }

        rule = {
            "id": rule_id,
            "name": finding.category.value.replace("_", " ").title(),
            "shortDescription": {"text": finding.title},
            "fullDescription": {"text": finding.explanation},
            "defaultConfiguration": {
                "level": level_map.get(finding.severity, "note")
            },
        }
        if finding.recommendation:
            rule["help"] = {"text": finding.recommendation}

        if rule not in rules:
            rules.append(rule)

        sarif_result = {
            "ruleId": rule_id,
            "level": level_map.get(finding.severity, "note"),
            "message": {"text": finding.explanation},
        }

        if finding.addresses:
            sarif_result["locations"] = [{
                "physicalLocation": {
                    "artifactLocation": {"uri": result.input_path},
                    "address": {"absoluteAddress": addr}
                }
            } for addr in finding.addresses[:5]]

        if finding.recommendation:
            sarif_result["fixes"] = [{
                "description": {"text": finding.recommendation}
            }]

        results_list.append(sarif_result)

    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CompLexAI",
                    "version": "0.3.0",
                    "informationUri": "https://github.com/zveasy/Binary_Program_VC",
                    "rules": rules,
                }
            },
            "results": results_list,
            "invocations": [{
                "executionSuccessful": True,
                "properties": {
                    "agent": result.agent_name,
                    "riskScore": result.risk_score,
                    "safetyVerdict": result.safety_verdict,
                    "durationSeconds": result.duration_seconds,
                }
            }],
        }],
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(sarif, f, indent=2)

    return sarif


def suggest_patches(result: AgentResult) -> List[Dict[str, str]]:
    """
    Generate code fix suggestions for each finding.

    Returns a list of patch suggestions, each with:
    - finding: the finding title
    - description: what to change
    - before: example problematic code pattern
    - after: suggested fix pattern
    """
    patches = []

    for finding in result.findings:
        if finding.category == FindingCategory.INFINITE_LOOP:
            func = finding.function_name or "the function"
            patches.append({
                "finding": finding.title,
                "description": f"Add a timeout or iteration guard to the loop in {func}.",
                "before": "while (1) {\n    // busy wait\n}",
                "after": (
                    "int timeout = 10000;\n"
                    "while (timeout-- > 0) {\n"
                    "    // busy wait\n"
                    "    if (condition_met) break;\n"
                    "}\n"
                    "if (timeout <= 0) handle_timeout();"
                ),
            })

        elif finding.category == FindingCategory.HIGH_COMPLEXITY:
            patches.append({
                "finding": finding.title,
                "description": "Replace nested linear search with a hash-based lookup.",
                "before": (
                    "for (int i = 0; i < n; i++)\n"
                    "    for (int j = 0; j < n; j++)\n"
                    "        if (a[i] == b[j]) match();"
                ),
                "after": (
                    "// Build lookup set from b[]\n"
                    "HashSet seen;\n"
                    "for (int j = 0; j < n; j++) set_add(&seen, b[j]);\n"
                    "// Single pass over a[]\n"
                    "for (int i = 0; i < n; i++)\n"
                    "    if (set_contains(&seen, a[i])) match();"
                ),
            })

        elif finding.category == FindingCategory.UNREACHABLE_CODE:
            patches.append({
                "finding": finding.title,
                "description": "Remove dead code or connect unreachable blocks to the control flow.",
                "before": "// Code after unconditional return\nreturn result;\ncleanup();  // never reached",
                "after": "cleanup();\nreturn result;",
            })

    return patches
