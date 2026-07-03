#!/usr/bin/env python3
"""
Full navigation launch — Caddy AI2.

Starts simulation + localization (SLAM or AMCL) + Nav2 + twist_stamper.

twist_stamper bridges:
    /caddy_ai2/cmd_vel  (Twist, from Nav2)
  → /caddy_ai2/bicycle_steering_controller/reference  (TwistStamped)

Install if missing:
    sudo apt install ros-jazzy-twist-stamper

Usage — SLAM mode (build map while navigating):
    ros2 launch caddy_ai2_ros2_navigation navigation.launch.py use_slam:=true

Usage — AMCL mode (pre-built map):
    ros2 launch caddy_ai2_ros2_navigation navigation.launch.py \
      map:=/full/path/to/maps/caddy_ai2_world.yaml
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    nav_share  = get_package_share_directory('caddy_ai2_ros2_navigation')
    sim_share  = get_package_share_directory('caddy_ai2_ros2_sim')
    nav2_share = get_package_share_directory('nav2_bringup')

    default_nav2_params = os.path.join(nav_share, 'config', 'nav2_params.yaml')
    default_slam_params = os.path.join(nav_share, 'config', 'slam_toolbox_params.yaml')

    namespace    = LaunchConfiguration('namespace')
    use_sim_time = LaunchConfiguration('use_sim_time')
    map_yaml     = LaunchConfiguration('map')
    use_slam     = LaunchConfiguration('use_slam')
    nav2_params  = LaunchConfiguration('params_file')
    slam_params  = LaunchConfiguration('slam_params_file')
    include_sim  = LaunchConfiguration('include_sim')
    autostart    = LaunchConfiguration('autostart')
    world        = LaunchConfiguration('world')

    return LaunchDescription([
        DeclareLaunchArgument('namespace',        default_value='caddy_ai2'),
        DeclareLaunchArgument('use_sim_time',     default_value='true'),
        DeclareLaunchArgument('map',              default_value='',
                              description='Full path to map YAML (ignored when use_slam:=true)'),
        DeclareLaunchArgument('use_slam',         default_value='false',
                              description='true = slam_toolbox; false = AMCL with existing map'),
        DeclareLaunchArgument('params_file',      default_value=default_nav2_params),
        DeclareLaunchArgument('slam_params_file', default_value=default_slam_params),
        DeclareLaunchArgument('include_sim',      default_value='true',
                              description='Set false if simulation is already running'),
        DeclareLaunchArgument('autostart',        default_value='true'),
        DeclareLaunchArgument('world',            default_value='navigation_test.sdf'),

        # ── Simulation ────────────────────────────────────────────────────────
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

        # ── Localization: Nav2 bringup (handles both SLAM and AMCL via use_slam arg) ──
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_share, 'launch', 'bringup_launch.py')
            ),
            launch_arguments={
                'namespace':    namespace,
                'use_sim_time': use_sim_time,
                'autostart':    autostart,
                'slam':         use_slam,
                'map':          map_yaml,
                'params_file':  nav2_params,
            }.items(),
        ),

        # ── twist_stamper: Twist → TwistStamped adapter ───────────────────────
        # Nav2 controller_server publishes Twist on /caddy_ai2/cmd_vel.
        # bicycle_steering_controller expects TwistStamped on
        # /caddy_ai2/bicycle_steering_controller/reference.
        Node(
            package='twist_stamper',
            executable='twist_stamper',
            name='twist_stamper',
            namespace=namespace,
            output='screen',
            parameters=[{'use_sim_time': use_sim_time, 'frame_id': 'base_link'}],
            remappings=[
                ('cmd_vel_in',  'cmd_vel'),
                ('cmd_vel_out', 'bicycle_steering_controller/reference'),
            ],
        ),
    ])
