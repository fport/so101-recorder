from pathlib import Path

from so101_recorder import command
from so101_recorder.settings import Camera, Settings


def xox() -> Settings:
    return Settings(
        follower_port="/dev/cu.usbmodem5AB01794851", leader_port="/dev/cu.usbmodem5A7C1232561",
        calibration_dir="calibration", namespace="fport", dataset="tic-tac-toe-so101-x-round1",
        task="put the red X in the middle right cell", episodes=5, episode_s=40, reset_s=90,
        sounds=True, data_dir="data",
    )


def test_matches_the_xox_command():
    args = command.record_args(xox(), cwd=Path("/w/so101-xox"))
    assert args[:4] == ["--robot.type=so101_follower", "--robot.port=/dev/cu.usbmodem5AB01794851",
                        "--robot.id=follower", "--robot.calibration_dir=calibration"]
    assert ("--robot.cameras={ top: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}, "
            "wrist: {type: opencv, index_or_path: 1, width: 640, height: 480, fps: 30}}") in args
    for a in ["--teleop.type=so101_leader", "--teleop.port=/dev/cu.usbmodem5A7C1232561", "--teleop.id=leader",
              "--teleop.calibration_dir=calibration", "--dataset.repo_id=fport/tic-tac-toe-so101-x-round1",
              "--dataset.root=/w/so101-xox/data/tic-tac-toe-so101-x-round1",
              "--dataset.single_task=put the red X in the middle right cell", "--dataset.num_episodes=5",
              "--dataset.episode_time_s=40", "--dataset.reset_time_s=90", "--dataset.streaming_encoding=true",
              "--dataset.encoder_threads=2", "--dataset.push_to_hub=true", "--dataset.private=true",
              "--dataset.no_stamp=true", "--display_data=true"]:
        assert a in args
    assert "--resume=true" not in args


def test_default_calibration_dir_is_left_to_lerobot():
    s = xox()
    s.calibration_dir = ""
    assert not any("calibration_dir" in a for a in command.record_args(s))


def test_resume_local_and_options():
    s = xox()
    s.push, s.display, s.streaming, s.episode_s = False, False, False, 12.5
    args = command.record_args(s, resume=True)
    assert "--resume=true" in args
    assert "--dataset.push_to_hub=false" in args and not any("private" in a for a in args)
    assert "--display_data=false" in args and not any("streaming" in a for a in args)
    assert "--dataset.episode_time_s=12.5" in args


def test_camera_path_is_quoted():
    s = xox()
    s.cameras = [Camera("top", "/dev/video2")]
    assert 'index_or_path: "/dev/video2"' in command.cameras_arg(s)


def test_shell_quotes_values_with_spaces():
    text = command.shell(command.record_args(xox()))
    assert text.startswith("lerobot-record \\\n  --robot.type=so101_follower")
    assert "--dataset.single_task='put the red X in the middle right cell'" in text
