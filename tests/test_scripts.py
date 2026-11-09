#!/usr/bin/env python3
"""Tests for the stdlib repo scripts, on temp fixtures only. Run: python3 tests/test_scripts.py"""
import json
import os
import struct
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "skills"
MOVE_MAP = SKILLS / "model-500-library/scripts/make_move_map.py"
STICK = SKILLS / "model-500-export/scripts/stick_vs_mac.py"
READ_PDB = SKILLS / "model-500-export/scripts/read_pdb.py"


def run(script, *args):
    return subprocess.run([sys.executable, "-I", str(script), *map(str, args)], capture_output=True, text=True)


def touch(path, data=b"x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class MakeMoveMap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_builds_map_and_moves_nothing(self):
        touch(self.root / "old/a.aiff")
        touch(self.root / "old/sub/b.MP3")
        touch(self.root / "old/note.txt")
        touch(self.root / "old/._a.aiff")
        out = self.root / "moves.json"
        r = run(MOVE_MAP, self.root / "old", self.root / "new", "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        moves = json.loads(out.read_text())
        self.assertEqual({m["to"] for m in moves}, {str(self.root / "new/a.aiff"), str(self.root / "new/sub/b.MP3")})
        self.assertIn("note.txt", r.stdout)
        self.assertTrue((self.root / "old/a.aiff").exists())
        self.assertFalse((self.root / "new").exists())

    def test_refuses_missing_folder_and_nested_target(self):
        out = self.root / "moves.json"
        self.assertEqual(run(MOVE_MAP, self.root / "none", self.root / "new", "--out", out).returncode, 1)
        touch(self.root / "old/a.aiff")
        self.assertEqual(run(MOVE_MAP, self.root / "old", self.root / "old/new", "--out", out).returncode, 1)
        self.assertFalse(out.exists())


class StickVsMac(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.stick = self.root / "stick"
        self.mac = self.root / "mac"
        self.stick.mkdir()
        self.mac.mkdir()
        self.addCleanup(self.tmp.cleanup)

    def compare(self):
        out = self.root / "res.json"
        r = run(STICK, self.stick, "--mac-root", self.mac, "--json", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(out.read_text()), r.stdout

    def test_empty_export_lists_vendor_file(self):
        touch(self.stick / "DJM-A9_122.upd")
        touch(self.stick / ".fseventsd/x")
        touch(self.stick / "._junk")
        res, _ = self.compare()
        self.assertEqual(res["non_rekordbox"], ["DJM-A9_122.upd"])
        self.assertEqual(res["stick_only"], [])

    def test_classifies_tracks(self):
        name = "Café.aiff"
        touch(self.mac / unicodedata.normalize("NFD", name), b"same")
        touch(self.stick / "Contents/A/B" / name, b"same")
        touch(self.stick / "Contents/A/B/gone.mp3", b"only here")
        touch(self.mac / "resized.mp3", b"mac")
        touch(self.stick / "Contents/A/B/resized.mp3", b"stick copy")
        touch(self.stick / "Loose Folder/loose.wav", b"loose")
        res, stdout = self.compare()
        self.assertEqual(len(res["matched"]), 1)
        self.assertEqual(sorted(res["stick_only"]), ["Contents/A/B/gone.mp3", "Loose Folder/loose.wav"])
        self.assertEqual(res["size_differs"], ["Contents/A/B/resized.mp3"])
        self.assertEqual(res["non_rekordbox"], ["Loose Folder/loose.wav"])
        self.assertIn("stick_only=2", stdout)

    def test_writes_nothing_to_stick(self):
        touch(self.stick / "Contents/a.mp3")
        before = sorted(p for p in self.stick.rglob("*"))
        self.compare()
        self.assertEqual(sorted(p for p in self.stick.rglob("*")), before)

    def test_not_mounted(self):
        self.assertEqual(run(STICK, self.root / "none").returncode, 1)


class ReadPdb(unittest.TestCase):
    def test_no_export_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run(READ_PDB, tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn("No export.pdb", r.stdout)


class UsbReportSafety(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.stick = self.root / "STICK"
        self.mac = self.root / "mac"
        self.mac.mkdir()
        self.audio = self.stick / "Contents/only-copy.wav"
        touch(self.audio, b"only copy of the audio")
        self.pdb = self.stick / "PIONEER/rekordbox/export.pdb"
        touch(self.pdb, struct.pack("<7I", 0, 4096, 0, 0, 0, 0, 0))

    def audit(self, script, destination):
        args = [self.stick, "--json", destination]
        if script == STICK:
            args.extend(["--mac-root", self.mac])
        return run(script, *args)

    def snapshot(self):
        return {str(p.relative_to(self.stick)): p.read_bytes() if p.is_file() else None
                for p in self.stick.rglob("*")}

    def assert_refused(self, destination):
        before = self.snapshot()
        for script in (STICK, READ_PDB):
            with self.subTest(script=script.name):
                result = self.audit(script, destination)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("outside the audited volume", result.stderr)
                self.assertEqual(self.snapshot(), before)

    def test_report_on_stick_is_not_created(self):
        self.assert_refused(self.stick / "audit.json")

    def test_relative_report_on_stick_is_refused(self):
        self.assert_refused(Path(os.path.relpath(self.stick / "audit.json")))

    def test_existing_audio_and_database_are_not_overwritten(self):
        for destination in (self.audio, self.pdb):
            self.assert_refused(destination)

    def test_volume_itself_is_refused(self):
        self.assert_refused(self.stick)

    def test_symlinked_file_and_parent_are_refused(self):
        link = self.root / "linked-report.json"
        link.symlink_to(self.audio)
        self.assert_refused(link)
        parent = self.root / "linked-folder"
        parent.symlink_to(self.stick, target_is_directory=True)
        self.assert_refused(parent / "report.json")

    def test_report_named_on_stick_cannot_follow_a_symlink_outside(self):
        outside = self.root / "outside.json"
        outside.write_bytes(b"keep outside data")
        link = self.stick / "linked-report.json"
        link.symlink_to(outside)
        self.assert_refused(link)
        self.assertEqual(outside.read_bytes(), b"keep outside data")
        parent = self.stick / "linked-folder"
        parent.symlink_to(self.mac, target_is_directory=True)
        self.assert_refused(parent / "report.json")

    def test_case_alias_is_refused_on_case_insensitive_filesystems(self):
        alias = self.root / "stick"
        if not alias.exists() or not alias.samefile(self.stick):
            self.skipTest("filesystem is case-sensitive")
        self.assert_refused(alias / "report.json")

    def test_outside_reports_can_be_created_and_replaced(self):
        before = self.snapshot()
        outside = self.root / "STICK-backup"
        outside.mkdir()
        for script in (STICK, READ_PDB):
            destination = outside / (script.stem + ".json")
            for existing in (False, True):
                with self.subTest(script=script.name, existing=existing):
                    if existing:
                        destination.write_text("old report")
                    result = self.audit(script, destination)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIsInstance(json.loads(destination.read_text()), dict)
                    self.assertEqual(self.snapshot(), before)

    def test_outside_hard_link_does_not_overwrite_audited_audio(self):
        before = self.snapshot()
        for script in (STICK, READ_PDB):
            destination = self.root / (script.stem + "-hardlink.json")
            os.link(self.audio, destination)
            result = self.audit(script, destination)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsInstance(json.loads(destination.read_text()), dict)
            self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
