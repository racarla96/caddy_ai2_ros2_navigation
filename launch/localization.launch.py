#!/usr/bin/env python3
"""
Localization-only launch — Caddy AI2.

Starts map_server + AMCL with a pre-built map.
Requires the simulation to be already running (include_sim:=false by default).

Usage:
    # With simulation:
    ros2 launch caddy_ai2_ros2_navigation localization.launch.py \
      map:=/path/to/maps/caddy_ai2_world.yaml include_sim:=true

    # Standalone (simulation already running):
    ros2 launch caddy_ai2_ros2_navigation localization.launch.py \
      map:=/path/to/maps/caddy_ai2_world.yaml
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

    default_amcl_params = os.path.join(nav_share, 'config', 'amcl_params.yaml')

    namespace    = LaunchConfiguration('namespace')
    use_sim_time = LaunchConfiguration('use_sim_time')
    map_yaml     = LaunchConfiguration('map')
    amcl_params  = LaunchConfiguration('amcl_params_file')
    include_sim  = LaunchConfiguration('include_sim')
    autostart    = LaunchConfiguration('autostart')
    world        = LaunchConfiguration('world')

    return LaunchDescription([
        DeclareLaunchArgument('namespace',         default_value='caddy_ai2'),
        DeclareLaunchArgument('use_sim_time',      default_value='true'),
        DeclareLaunchArgument('map',               default_value='',
                              description='Full path to map YAML file'),
        DeclareLaunchArgument('amcl_params_file',  default_value=default_amcl_params),
        DeclareLaunchArgument('include_sim',       default_value='false',
                              description='Set true to also launch the simulation'),
        DeclareLaunchArgument('autostart',         default_value='true'),
        DeclareLaunchArgument('world',             default_value='navigation_test.sdf'),

        # Simulation (optional)
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

        # AMCL + map_server
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_share, 'launch', 'localization_launch.py')
            ),
            launch_arguments={
                'namespace':    namespace,
                'use_sim_time': use_sim_time,
                'autostart':    autostart,
                'map':          map_yaml,
                'params_file':  amcl_params,
            }.items(),
        ),
    ])
