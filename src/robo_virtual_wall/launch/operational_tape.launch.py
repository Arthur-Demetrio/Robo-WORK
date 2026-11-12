"""Run the existing operational Nav2 launch with additional tape filters."""
import os
import tempfile
from pathlib import Path
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnShutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def start(context):
    from robo_virtual_wall.projection import load_calibration
    from robo_virtual_wall.nav_config import add_tape_filters
    value = lambda name: LaunchConfiguration(name).perform(context)
    calibration = Path(value('homography_file')).expanduser()
    load_calibration(calibration)
    with open(value('params_file'),encoding='utf-8') as stream:
        base = yaml.safe_load(stream)
    with open(value('filters_file'),encoding='utf-8') as stream:
        overlay = yaml.safe_load(stream)
    merged = add_tape_filters(base,overlay)
    temporary = tempfile.NamedTemporaryFile(mode='w',suffix='-tape-nav2.yaml',delete=False)
    with temporary:
        yaml.safe_dump(merged,temporary,sort_keys=False)
    def cleanup(context):
        Path(temporary.name).unlink(missing_ok=True)
        return []
    sim_time = ParameterValue(LaunchConfiguration('use_sim_time'),value_type=bool)
    return [
        RegisterEventHandler(OnShutdown(on_shutdown=[OpaqueFunction(function=cleanup)])),
        Node(package='robo_virtual_wall',executable='virtual_wall',name='virtual_wall',
             output='screen',parameters=[dict(homography_file=str(calibration),
                preview_homography_file=value('preview_homography_file'),
                width=640,height=480,roi_top=0.,roi_bottom=.85,show_windows=ParameterValue(
                    LaunchConfiguration('show_windows'),value_type=bool),
                device=value('device'),use_sim_time=sim_time)]),
        Node(package='robo_virtual_wall',executable='tape_keepout',name='tape_keepout',
             output='screen',parameters=[dict(use_sim_time=sim_time)]),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(value('navigation_launch')),
            launch_arguments=dict(params_file=temporary.name,
                use_sim_time=LaunchConfiguration('use_sim_time')).items()),
    ]


def generate_launch_description():
    navigation = get_package_share_directory('robo_navigation')
    return LaunchDescription([
        DeclareLaunchArgument('homography_file'),
        DeclareLaunchArgument('filters_file'),
        DeclareLaunchArgument('preview_homography_file',default_value=''),
        DeclareLaunchArgument('params_file',default_value=os.path.join(navigation,'config','nav2_params.yaml')),
        DeclareLaunchArgument('navigation_launch',default_value=os.path.join(navigation,'launch','navigation.launch.py')),
        DeclareLaunchArgument('device',default_value='/dev/video2'),
        DeclareLaunchArgument('show_windows',default_value='true'),
        DeclareLaunchArgument('use_sim_time',default_value='false'),
        OpaqueFunction(function=start),
    ])
