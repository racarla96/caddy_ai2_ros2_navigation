#!/usr/bin/env python3
"""
SLAM launch — Caddy AI2.

Starts the simulation (optional) + slam_toolbox in online-async mode.
Drive the robot manually to build the map, then save it:

    ros2 service call /caddy_ai2/slam_toolbox/save_map \
      slam_toolbox/srv/SaveMap "{name: {data: 'maps/caddy_ai2_world'}}"

Usage:
    ros2 launch caddy_ai2_ros2_navigation slam.launch.py
    ros2 launch caddy_ai2_ros2_navigation slam.launch.py world:=navigation_test.sdf
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    nav_share = get_package_share_directory('caddy_ai2_ros2_navigation')
    sim_share = get_package_share_directory('caddy_ai2_ros2_sim')
    nav2_share = get_package_share_directory('nav2_bringup')

    default_slam_params = os.path.join(nav_share, 'config', 'slam_toolbox_params.yaml')

    namespace     = LaunchConfiguration('namespace')
    use_sim_time  = LaunchConfiguration('use_sim_time')
    world         = LaunchConfiguration('world')
    slam_params   = LaunchConfiguration('slam_params_file')
    include_sim   = LaunchConfiguration('include_sim')
    autostart     = LaunchConfiguration('autostart')

    return LaunchDescription([
        DeclareLaunchArgument('namespace',        default_value='caddy_ai2'),
        DeclareLaunchArgument('use_sim_time',     default_value='true'),
        DeclareLaunchArgument('world',            default_value='navigation_test.sdf',
                              description='Gazebo world SDF (relative or absolute path)'),
        DeclareLaunchArgument('slam_params_file', default_value=default_slam_params),
        DeclareLaunchArgument('include_sim',      default_value='true',
                              description='Set false if simulation is already running'),
        DeclareLaunchArgument('autostart',        default_value='true'),

        # Simulation
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(sim_share, 'launch', 'sim_gazebo.launch.py')
            ),
            launch_arguments={
                'namespace': namespace,
                'world':     world,
                'use_localization': 'true',
            }.items(),
            condition=IfCondition(include_sim),
        ),

        # slam_toolbox (online async)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_share, 'launch', 'slam_launch.py')
            ),
            launch_arguments={
                'namespace':    namespace,
                'use_sim_time': use_sim_time,
                'autostart':    autostart,
                'params_file':  slam_params,
            }.items(),
        ),
    ])
