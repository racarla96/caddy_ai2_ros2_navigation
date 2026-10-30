#!/usr/bin/env python3
"""
SLAM launch — Caddy AI2.

Starts the simulation + slam_toolbox in online-ASYNC mode (lighter than sync).
EKF is enabled by default during SLAM: with it off, slam_toolbox's motion
prior comes from raw wheel/steering dead-reckoning odometry, which drifts in
heading fast enough on this Ackermann vehicle to break scan matching (map
ends up sheared/smeared and offset far outside the real room). The EKF fuses
IMU gyro yaw on top of wheel odometry and fixes this at a modest CPU cost.

Drive the robot manually to build the map, then save it:
  Terminal 2: teleop (see README)
  Terminal 3: ros2 run nav2_map_server map_saver_cli -f .../maps/navigation_test
                --ros-args -r map:=/map -p map_subscribe_transient_local:=true

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
    nav_share  = get_package_share_directory('caddy_ai2_ros2_navigation')
    sim_share  = get_package_share_directory('caddy_ai2_ros2_sim')
    slam_share = get_package_share_directory('slam_toolbox')

    default_slam_params = os.path.join(nav_share, 'config', 'slam_toolbox_params.yaml')

    namespace        = LaunchConfiguration('namespace')
    use_sim_time     = LaunchConfiguration('use_sim_time')
    world            = LaunchConfiguration('world')
    slam_params      = LaunchConfiguration('slam_params_file')
    include_sim      = LaunchConfiguration('include_sim')
    use_localization = LaunchConfiguration('use_localization')

    return LaunchDescription([
        DeclareLaunchArgument('namespace',        default_value='caddy_ai2'),
        DeclareLaunchArgument('use_sim_time',     default_value='true'),
        DeclareLaunchArgument('world',            default_value='navigation_test.sdf'),
        DeclareLaunchArgument('slam_params_file', default_value=default_slam_params),
        DeclareLaunchArgument('include_sim',      default_value='true',
                              description='false if simulation is already running'),
        # EKF on by default during SLAM — raw wheel odometry drifts in heading
        # too fast for scan matching on this vehicle (see module docstring).
        DeclareLaunchArgument('use_localization', default_value='true',
                              description='false to skip the EKF node (raw odom only, not recommended)'),

        # Simulation
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(sim_share, 'launch', 'sim.launch.py')
            ),
            launch_arguments={
                'namespace':        namespace,
                'world':            world,
                'use_localization': use_localization,
            }.items(),
            condition=IfCondition(include_sim),
        ),

        # slam_toolbox — online ASYNC (non-blocking, handles queue backpressure gracefully)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(slam_share, 'launch', 'online_async_launch.py')
            ),
            launch_arguments={
                'use_sim_time':  use_sim_time,
                'slam_params_file': slam_params,
            }.items(),
        ),
    ])
