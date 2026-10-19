#!/usr/bin/env python3
"""Regressoes do editor YAML deadband (sem ROS)."""
import copy
import importlib.util
import pathlib
import sys
import unittest

import yaml

script = pathlib.Path(__file__).resolve().parents[1] / "scripts/geometry_set_deadband.py"
spec = importlib.util.spec_from_file_location("geometry_set_deadband", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestDeadband(unittest.TestCase):
    def yaml_text(self, deadband):
        return (
            "controller_server:\n  ros__parameters:\n    x: 5\n"
            "velocity_smoother:\n  ros__parameters:\n"
            + deadband +
            "    max_velocity: [0.05, 0.035, 0.08]\n"
            "collision_monitor:\n  ros__parameters:\n    enabled: true\n"
        )

    def verify(self, text):
        before = yaml.safe_load(text)
        old, updated = module.edit_yaml(text)
        after = yaml.safe_load(updated)
        expected = copy.deepcopy(before)
        expected["velocity_smoother"]["ros__parameters"]["deadband_velocity"] = [0.005, 0.005, 0.015]
        self.assertEqual(old, [0.015, 0.015, 0.015])
        self.assertEqual(after, expected)
        self.assertTrue(updated.startswith("controller_server:\n"))
        self.assertIn("collision_monitor:", updated)

    def test_inline(self):
        self.verify(self.yaml_text("    deadband_velocity: [0.015, 0.015, 0.015]\n"))

    def test_block_indented(self):
        self.verify(self.yaml_text("    deadband_velocity:\n      - 0.015\n      - 0.015\n      - 0.015\n"))

    def test_block_indentless(self):
        self.verify(self.yaml_text("    deadband_velocity:\n    - 0.015\n    - 0.015\n    - 0.015\n"))

    def test_block_with_comments(self):
        self.verify(self.yaml_text("    deadband_velocity: # linear x y e angular\n    - 0.015 # x\n    - 0.015 # y\n    - 0.015 # ang\n"))

    def test_angular_unexpected_fails(self):
        text = self.yaml_text("    deadband_velocity: [0.015, 0.015, 0.025]\n")
        with self.assertRaises(ValueError):
            module.edit_yaml(text)

    def test_missing_fails(self):
        text = self.yaml_text("    deadband_velocity_not_real: [0.015, 0.015, 0.015]\n")
        with self.assertRaises(ValueError):
            module.edit_yaml(text)


if __name__ == "__main__":
    unittest.main()
