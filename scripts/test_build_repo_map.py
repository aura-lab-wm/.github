"""The map's one hard rule, checked rather than trusted: a public file never names a private repo.

Run: python3 -m unittest discover -s scripts -q
"""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from build_repo_map import UNFILED, check_no_private_leak, fetch_repos, group, main, render, room_of, splice

ORG = "aura-lab-wm"


def repo(name, private=True, desc="", pushed="2026-09-14T10:00:00Z"):
    return {"name": name, "private": private, "description": desc, "pushed_at": pushed, "archived": False}


FIXTURE = [
    repo("student-aura-joseph-call", desc="AURA Lab — Joseph Call (Ph.D.)"),
    repo("student-aura-saima-afrin", desc="AURA Lab — Saima Afrin (Ph.D. candidate)"),
    repo("research-swebench-dominance", desc="Research — dominance and regret analysis"),
    repo("teaching-coll100-codelab", desc="codelab.sh — COLL 100 teaching platform (W&M)."),
    repo("teaching-genai4se-2026-ajhart01"),
    repo("project-rocco-web", private=False, desc="Rocco browser automation."),
    repo("project-auracron", desc="AuraCron — research lab management platform"),
    repo("design-kit", desc="AURA Lab visual language."),
    repo(".github", private=False, desc="Org profile and filing manifesto."),
    repo("ops-toast", private=False, desc="macOS toast."),
    repo("skills", desc="AURA Lab agent skills."),
    repo("wm-daily-companion", desc="W&M lab receipt harvest (CLI)"),
]


class Rooms(unittest.TestCase):
    def test_every_name_walks_into_the_manifesto_room_it_belongs_to(self):
        self.assertEqual(room_of("student-aura-joseph-call"), "people")
        self.assertEqual(room_of("research-swebench-dominance"), "research")
        self.assertEqual(room_of("teaching-genai4se-2026-ajhart01"), "teaching")
        self.assertEqual(room_of("project-rocco-web"), "products")
        self.assertEqual(room_of("design-kit"), "identity")
        self.assertEqual(room_of("web-auralab"), "identity")
        self.assertEqual(room_of(".github"), "identity")
        self.assertEqual(room_of("ops-toast"), "ops")
        self.assertEqual(room_of("skills"), "ops")

    def test_a_name_the_naming_table_does_not_cover_is_surfaced_not_hidden(self):
        # wm-daily-companion matches no rule: the map should say so rather than silently drop it.
        self.assertEqual(room_of("wm-daily-companion"), UNFILED)
        self.assertIn("wm-daily-companion", [r["name"] for r in group(FIXTURE)[UNFILED]])

    def test_grouping_keeps_every_repo_exactly_once(self):
        rooms = group(FIXTURE)
        self.assertEqual(sum(len(v) for v in rooms.values()), len(FIXTURE))


class PublicMode(unittest.TestCase):
    def setUp(self):
        self.block = render(ORG, FIXTURE, "public", "2026-09-18 21:00 UTC")

    def test_no_private_repo_name_appears(self):
        for r in FIXTURE:
            if r["private"]:
                self.assertNotIn(r["name"], self.block, f"{r['name']} leaked into the public map")

    def test_no_private_description_appears(self):
        for r in FIXTURE:
            if r["private"] and r["description"]:
                self.assertNotIn(r["description"], self.block)

    def test_public_repos_are_named_and_linked(self):
        for name in ("project-rocco-web", "ops-toast", ".github"):
            self.assertIn(f"https://github.com/{ORG}/{name}", self.block)

    def test_private_repos_are_still_counted(self):
        # Every private repo is invisible by name but present in the arithmetic: the table's Private
        # column has to add up to the real number, and the header has to state the real total.
        counted = sum(int(row.split("|")[4]) for row in self.block.splitlines()
                      if row.startswith("| **"))
        self.assertEqual(counted, sum(1 for r in FIXTURE if r["private"]))
        self.assertIn(f"{len(FIXTURE)} repos", self.block)

    def test_the_block_is_byte_identical_across_runs(self):
        # The hourly job commits only when the map changes, which is only true if rendering the same
        # org twice gives the same bytes (a hash()-derived node id would not).
        again = render(ORG, FIXTURE, "public", "2026-09-18 21:00 UTC")
        self.assertEqual(self.block, again)

    def test_the_leak_check_raises_instead_of_writing(self):
        bad = self.block + "\nstudent-aura-joseph-call\n"
        with self.assertRaises(SystemExit):
            check_no_private_leak(bad, FIXTURE)

    def test_the_leak_check_passes_the_real_block(self):
        check_no_private_leak(self.block, FIXTURE)   # must not raise


class AllMode(unittest.TestCase):
    def test_all_mode_names_private_repos_on_purpose(self):
        block = render(ORG, FIXTURE, "all", "2026-09-18 21:00 UTC")
        self.assertIn("research-swebench-dominance", block)


class PublicScope(unittest.TestCase):
    def test_public_scope_does_not_claim_total_or_private_counts(self):
        block = render(ORG, FIXTURE, "public", "2026-10-19 01:00 UTC", "public")
        self.assertIn("PUBLIC REPOSITORY MAP · 3 public repos", block)
        self.assertIn("private repository counts are not included", block)
        self.assertNotIn("| Private |", block)
        self.assertNotIn("12 repos", block)
        self.assertNotIn("student-aura-joseph-call", block)

    def test_publishing_repo_commit_does_not_move_last_push_date(self):
        before = render(ORG, FIXTURE, "public", "same", "public")
        changed = [{**r, "pushed_at": "2026-10-20T10:00:00Z"} if r["name"] == ".github" else r for r in FIXTURE]
        self.assertEqual(before, render(ORG, changed, "public", "same", "public"))

    def test_fetch_scope_is_preserved_on_every_page(self):
        first = [repo(f"project-public-{i}", private=False) for i in range(100)]
        with patch("build_repo_map.urllib.request.urlopen", side_effect=[
            io.BytesIO(json.dumps(first).encode()), io.BytesIO(b"[]"),
        ]) as request:
            self.assertEqual(len(fetch_repos(ORG, "", "public")), 100)
        for call in request.call_args_list:
            self.assertIn("type=public", call.args[0].full_url)
            self.assertNotIn("Authorization", call.args[0].headers)
        self.assertIn("page=2", request.call_args_list[1].args[0].full_url)

    def test_leak_failure_does_not_repeat_private_names_in_public_logs(self):
        with self.assertRaises(SystemExit) as error:
            check_no_private_leak("student-aura-joseph-call", FIXTURE)
        self.assertNotIn("student-aura-joseph-call", str(error.exception))

    def test_missing_optional_token_still_generates_public_map(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            path.write_text("original intro\n")
            with patch.dict(os.environ, {}, clear=True), patch("sys.argv", ["map", "--write", str(path)]), \
                 patch("build_repo_map.fetch_repos", return_value=FIXTURE) as fetch, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            fetch.assert_called_once_with(ORG, "", "public")
            self.assertTrue(path.read_text().startswith("original intro\n"))
            self.assertIn("3 public repos", path.read_text())

    def test_all_scope_requires_token_and_preserves_existing_map(self):
        with patch.dict(os.environ, {}, clear=True), patch("sys.argv", ["map", "--scope", "all"]), \
             patch("build_repo_map.fetch_repos") as fetch, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(), 1)
            fetch.assert_not_called()

    def test_all_scope_retains_private_counts_without_logging_private_names(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-only"}, clear=True), \
             patch("sys.argv", ["map", "--scope", "all"]), \
             patch("build_repo_map.fetch_repos", return_value=FIXTURE) as fetch, \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(main(), 0)
        fetch.assert_called_once_with(ORG, "test-only", "all")
        self.assertIn("12 repos", output.getvalue())
        self.assertIn("unfiled repositories: 1", errors.getvalue())
        for r in FIXTURE:
            if r["private"]:
                self.assertNotIn(r["name"], output.getvalue() + errors.getvalue())

    def test_api_failure_does_not_replace_the_existing_map(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            path.write_text("last good map\n")
            with patch("sys.argv", ["map", "--write", str(path)]), \
                 patch("build_repo_map.fetch_repos", side_effect=urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)), \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(), 1)
            self.assertEqual(path.read_text(), "last good map\n")


class Splice(unittest.TestCase):
    def test_another_hour_does_not_rewrite_an_unchanged_map(self):
        before = render(ORG, FIXTURE, "public", "2026-10-19 01:00 UTC", "public")
        after = render(ORG, FIXTURE, "public", "2026-10-19 02:00 UTC", "public")
        doc = "intro\n" + before + "\ntail\n"
        self.assertEqual(splice(doc, after), doc)

    def test_changed_repositories_update_the_map_and_timestamp(self):
        before = render(ORG, FIXTURE, "public", "2026-10-19 01:00 UTC", "public")
        after = render(ORG, FIXTURE + [repo("project-new", private=False)], "public", "2026-10-19 02:00 UTC", "public")
        result = splice("intro\n" + before + "\ntail\n", after)
        self.assertIn("project-new", result)
        self.assertIn("2026-10-19 02:00 UTC", result)
        self.assertNotIn("2026-10-19 01:00 UTC", result)

    def test_replaces_only_the_marked_block(self):
        doc = "head\n<!-- REPO-MAP:START -->\nold\n<!-- REPO-MAP:END -->\ntail\n"
        out = splice(doc, "<!-- REPO-MAP:START -->\nnew\n<!-- REPO-MAP:END -->")
        self.assertIn("head", out)
        self.assertIn("tail", out)
        self.assertIn("new", out)
        self.assertNotIn("old", out)

    def test_appends_when_the_markers_are_absent(self):
        out = splice("just a readme\n", "<!-- REPO-MAP:START -->\nmap\n<!-- REPO-MAP:END -->")
        self.assertTrue(out.startswith("just a readme"))
        self.assertIn("map", out)


if __name__ == "__main__":
    unittest.main()
