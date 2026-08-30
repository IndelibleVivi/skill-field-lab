from __future__ import annotations

import unittest

from fieldlab.verify import evaluate_result_assertions


class FinalResponseVerificationTests(unittest.TestCase):
    def test_text_and_regex_assertions_target_final_agent_response(self) -> None:
        case = {
            "result_assertions": {
                "text_contains": ["binding authority"],
                "text_not_contains": ["invented citation"],
                "text_matches": [r"(?i)claim\s+ceiling"],
            }
        }
        results = evaluate_result_assertions(
            case,
            "The binding authority controls. The claim ceiling remains narrow.",
        )
        self.assertTrue(all(item["passed"] for item in results))

    def test_json_schema_subset_reports_structured_result(self) -> None:
        case = {
            "result_assertions": {
                "json_schema": {
                    "type": "object",
                    "required": ["decision", "reasons"],
                    "additionalProperties": False,
                    "properties": {
                        "decision": {"enum": ["DEFER", "REJECT"]},
                        "reasons": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string", "minLength": 1},
                        },
                    },
                }
            }
        }
        results = evaluate_result_assertions(
            case,
            '{"decision":"DEFER","reasons":["no local problem"]}',
        )
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["passed"], results[0])


if __name__ == "__main__":
    unittest.main()
