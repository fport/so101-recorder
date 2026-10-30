"""Runs the real runner (lerobot's record()) with a stand-in follower and leader, so no hardware is needed.

    python tests/fake_rig.py <lerobot-record arguments>
"""

from __future__ import annotations

import sys

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]


class FakeArm:
    name = robot_type = "so_follower"

    def __init__(self, config=None):
        self.config = config
        self.cameras = {}
        self.is_connected = False
        self.id = getattr(config, "id", "fake")

    @property
    def action_features(self):
        return {f"{j}.pos": float for j in JOINTS}

    @property
    def observation_features(self):
        return {f"{j}.pos": float for j in JOINTS}

    def connect(self, calibrate: bool = True):
        self.is_connected = True

    def disconnect(self):
        self.is_connected = False

    def get_observation(self):
        return {f"{j}.pos": 0.0 for j in JOINTS}

    def get_action(self):
        return {f"{j}.pos": 0.0 for j in JOINTS}

    def send_action(self, action):
        return action


def main():
    import lerobot.scripts.lerobot_record as lr

    from so101_recorder import runner

    lr.Teleoperator.register(FakeArm)  # record_loop only takes actions from a Teleoperator
    lr.make_robot_from_config = FakeArm
    lr.make_teleoperator_from_config = FakeArm
    sys.exit(runner.main(sys.argv[1:]))


if __name__ == "__main__":
    main()
