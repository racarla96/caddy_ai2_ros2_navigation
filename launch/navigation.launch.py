#!/usr/bin/env python3
"""
2D navigation launch — Caddy AI2.

Starts EasyNav only (costmap maps manager, AMCL, A* planner, Regulated Pure Pursuit). The
simulation is started separately; the single entry point starts both:
    ros2 launch caddy_ai2_ros2_sim sim.launch.py world:=navigation_test.sdf nav:=2d

EasyNav publishes TwistStamped directly (controller_node.use_cmd_vel_stamped), so it is
remapped onto the bicycle_steering_controller reference input; no twist_stamper needed.

Usage (simulation already running):
    ros2 launch caddy_ai2_ros2_navigation navigation.launch.py

    # Another map (installed in a package's share dir, path relative to it):
    ros2 launch caddy_ai2_ros2_navigation navigation.launch.py \
      map_package:=my_maps_pkg map_file:=maps/my_map.yaml

Goals: RViz "2D Goal Pose" (topic /goal_pose). Initial pose: RViz "2D Pose Estimate".
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    nav_share = get_package_share_directory('caddy_ai2_ros2_navigation')

    default_params = os.path.join(nav_share, 'config', 'easynav_params.yaml')

    params_file = LaunchConfiguration('params_file')
    map_package = LaunchConfiguration('map_package')
    map_file    = LaunchConfiguration('map_file')

    return LaunchDescription([
        DeclareLaunchArgument('params_file', default_value=default_params),
        DeclareLaunchArgument('map_package', default_value='caddy_ai2_ros2_navigation',
                              description='Package whose share dir holds the map'),
        DeclareLaunchArgument('map_file',    default_value='maps/navigation_test.yaml',
                              description='Map YAML path, relative to map_package share dir'),

        # ── EasyNav ───────────────────────────────────────────────────────────
        # Runs unnamespaced on purpose: the params file is keyed by EasyNav's node names,
        # and a namespace would also split /tf away from the global tree the EKF and the
        # controllers publish to (same reasoning as the previous Nav2 setup).
        # The robot is reached through absolute topics: the laser in easynav_params.yaml and
        # the TwistStamped output remapped below.
        Node(
            package='easynav_system',
            executable='system_main',
            output='screen',
            # `-p node:param:=value` overrides the map only on maps_manager_node; a `parameters`
            # entry would be keyed to this process name, not to EasyNav's inner nodes.
            arguments=[
                '--ros-args',
                '--params-file', params_file,
                '-p', ['maps_manager_node:costmap.package:=', map_package],
                '-p', ['maps_manager_node:costmap.map_path_file:=', map_file],
            ],
            remappings=[
                ('cmd_vel_stamped',
                 '/caddy_ai2/bicycle_steering_controller/reference'),
            ],
        ),
    ])
