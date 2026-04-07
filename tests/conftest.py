"""Root test configuration.

Exclude eval tests from default collection — they require the eval
dependency group (anthropic, langfuse) and are run separately via `just eval`.
"""

collect_ignore_glob = ["eval/*"]
