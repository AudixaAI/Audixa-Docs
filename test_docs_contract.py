import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parent


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


class DocsContractTests(unittest.TestCase):
    def test_paid_only_sampler_truth_is_consistent(self):
        pages = [read(path) for path in ("index.mdx", "quickstart.mdx", "guides/pricing.mdx")]
        for page in pages:
            self.assertIn("https://audixa.ai/voices", page)
            self.assertRegex(page, r"(?i)\$10 top-up|top-up of at least \*\*\$10")
            self.assertRegex(page, r"(?i)active\s+subscription|start a\s+subscription")

        combined = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.rglob("*.mdx"))
        for stale_promise in (
            "10,000 free credits",
            "$0.10 (Trial)",
            "$0.10 in free balance",
            "topup balance never expires",
            "carries over indefinitely",
        ):
            self.assertNotIn(stale_promise.lower(), combined.lower())

    def test_quickstart_matches_the_v3_async_contract(self):
        source = read("quickstart.mdx")
        self.assertIn("POST /v3/tts", source)
        self.assertIn("GET /v3/tts?generation_id=...", source)
        self.assertRegex(source, r"at\s+least \*\*1 character\*\*")
        self.assertIn("minimum billable length of **30 characters (8 tokens)**", source)
        for field in ("text", "voice_id", "model", "audio_format"):
            self.assertGreaterEqual(source.count(field), 4, field)
        for status in ("IN_QUEUE", "GENERATING", "COMPLETED", "FAILED"):
            self.assertIn(status, read("api-reference/introduction.mdx") + source)
        for client in ("fetch(", "requests.post(", "curl --fail-with-body"):
            self.assertIn(client, source)

    def test_no_fictional_audixa_sdk_usage_remains(self):
        combined = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.rglob("*.mdx"))
        for unsupported in (
            "pip install audixa",
            "npm install audixa",
            "import audixa\n",
            "from audixa import",
            "new Audixa(",
            "official SDK",
        ):
            self.assertNotIn(unsupported.lower(), combined.lower())

    def test_top_up_expiry_matches_backend_policy(self):
        combined = read("guides/pricing.mdx") + read("features/billing.mdx")
        self.assertRegex(combined, r"(?i)paused while a subscription is active|subscription is active, the expiry clock.*paused")
        self.assertGreaterEqual(len(re.findall(r"(?i)expire(?:s)? after (?:\*\*)?30", combined)), 2)

    def test_account_page_describes_soft_deactivation_and_separate_cancellation(self):
        source = read("features/account.mdx")
        self.assertRegex(source, r"(?i)soft account deactivation")
        self.assertRegex(source, r"(?i)does not cancel an\s+active subscription")
        self.assertIn("retained records", source)
        for unsupported_promise in (
            "Permanently remove all your personal data",
            "Delete all your **Generations** and **Clone Voices**",
            "Revoke all **API Keys**",
            "Cancel any active **Subscriptions**",
            "this data **cannot be recovered**",
        ):
            self.assertNotIn(unsupported_promise, source)

    def test_streaming_documents_only_supported_models(self):
        source = read("api-reference/streaming.mdx")
        self.assertNotIn("turbo", source.lower())
        self.assertIn("GET /v3/voices?model=base", source)
        self.assertIn("GET /v3/voices?model=advanced", source)
        self.assertIn("`cfg_weight` from `1.0` to `5.0`", source)
        self.assertIn("`speed` from `0.5` to `2.0`", source)

    def test_navigation_pages_and_internal_links_exist(self):
        config = json.loads(read("docs.json"))
        page_keys = {str(path.relative_to(ROOT).with_suffix("")) for path in ROOT.rglob("*.mdx")}

        for tab in config["navigation"]["tabs"]:
            for group in tab["groups"]:
                for page in group["pages"]:
                    self.assertIn(page, page_keys)

        link_pattern = re.compile(r'href="(/[^"]+)"|\]\((/[^)]+)\)')
        for path in ROOT.rglob("*.mdx"):
            for match in link_pattern.finditer(path.read_text(encoding="utf-8")):
                target = (match.group(1) or match.group(2)).split("#", 1)[0].strip("/")
                self.assertIn(target, page_keys, f"{path.relative_to(ROOT)} -> /{target}")

    def test_mdx_frontmatter_and_fences_are_balanced(self):
        for path in ROOT.rglob("*.mdx"):
            source = path.read_text(encoding="utf-8")
            self.assertTrue(source.startswith("---\n"), path)
            self.assertGreaterEqual(source.count("\n---\n"), 1, path)
            self.assertEqual(source.count("```") % 2, 0, path)


if __name__ == "__main__":
    unittest.main()
