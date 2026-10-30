#!/usr/bin/env python3
"""
SLAM con Cartographer — Caddy AI2.

Arranca simulación + Cartographer 2D + occupancy_grid_node.

Una vez recorrido el entorno, guarda el mapa:

  # Mapa PNG/YAML para AMCL:
  ros2 run nav2_map_server map_saver_cli \\
    -f .../maps/navigation_test \\
    --ros-args -r map:=/map -p map_subscribe_transient_local:=true

  # Estado interno de Cartographer (.pbstream) para continuar después:
  ros2 service call /finish_trajectory cartographer_ros_msgs/srv/FinishTrajectory "{trajectory_id: 0}"
  ros2 service call /write_state cartographer_ros_msgs/srv/WriteState \\
    "{filename: '.../maps/navigation_test.pbstream', include_unfinished_submaps: true}"

Usage:
    ros2 launch caddy_ai2_ros2_navigation slam_cartographer.launch.py
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
    nav_share = get_package_share_directory('caddy_ai2_ros2_navigation')
    sim_share = get_package_share_directory('caddy_ai2_ros2_sim')

    lua_config_dir  = os.path.join(nav_share, 'config')
    lua_config_file = 'caddy_ai2_cartographer.lua'

    namespace        = LaunchConfiguration('namespace')
    use_sim_time     = LaunchConfiguration('use_sim_time')
    world            = LaunchConfiguration('world')
    include_sim      = LaunchConfiguration('include_sim')
    use_localization = LaunchConfiguration('use_localization')

    return LaunchDescription([
        DeclareLaunchArgument('namespace',        default_value='caddy_ai2'),
        DeclareLaunchArgument('use_sim_time',     default_value='true'),
        DeclareLaunchArgument('world',            default_value='navigation_test.sdf'),
        DeclareLaunchArgument('include_sim',      default_value='true'),
        # EKF off during SLAM — reduces CPU load
        DeclareLaunchArgument('use_localization', default_value='false'),

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

        # Cartographer node
        Node(
            package='cartographer_ros',
            executable='cartographer_node',
            name='cartographer_node',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
            arguments=[
                '-configuration_directory', lua_config_dir,
                '-configuration_basename',  lua_config_file,
            ],
            remappings=[
                # LiDAR scan
                ('scan',   '/caddy_ai2/sick_lms_291/scan'),
                # Wheel odometry
                ('odom',   '/caddy_ai2/bicycle_steering_controller/odometry'),
                # Global TF topics (required when running under namespace)
                ('tf',        '/tf'),
                ('tf_static', '/tf_static'),
            ],
        ),

        # Occupancy grid publisher (converts Cartographer submaps → /map)
        Node(
            package='cartographer_ros',
            executable='cartographer_occupancy_grid_node',
            name='cartographer_occupancy_grid_node',
            output='screen',
            parameters=[
                {'use_sim_time': use_sim_time},
                {'resolution': 0.05},
                {'publish_period_sec': 1.0},
            ],
        ),
    ])
