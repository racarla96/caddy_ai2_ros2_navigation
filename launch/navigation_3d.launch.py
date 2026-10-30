#!/usr/bin/env python3
"""
3D navigation launch — Caddy AI2 in the multi-floor parking garage.

Runs EasyNav (Bonxai + NavMap maps, NavMap AMCL, A* over the NavMap, Regulated Pure Pursuit) fed by
the RS-Helios-5515 3D LiDAR. The Helios sees the Caddy's own body (~15 % of its points), so a
pcl_ros CropBox removes the robot box before EasyNav gets the cloud:
    /caddy_ai2/rs_helios_5515/points  ->  /caddy_ai2/rs_helios_5515/points_filtered

The simulation is NOT started here. Preferably use the single entry point, which starts both:
    ros2 launch caddy_ai2_ros2_sim sim.launch.py world:=parking_garage.sdf nav:=3d

or start the simulation first and this launch afterwards:
    ros2 launch caddy_ai2_ros2_sim sim.launch.py world:=parking_garage.sdf
    ros2 launch caddy_ai2_ros2_navigation navigation_3d.launch.py
Goals: RViz "2D Goal Pose" (topic /goal_pose).
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    nav_share = get_package_share_directory('caddy_ai2_ros2_navigation')

    default_params = os.path.join(nav_share, 'config', 'easynav_3d_params.yaml')

    params_file = LaunchConfiguration('params_file')

    # Caddy body in base_link (front at x=1.08, collision box 2.66 x 1.23, ground at z=-0.235,
    # top at 1.7 m above ground), with margin. Points inside the box are dropped (negative=true).
    crop_box = ComposableNode(
        package='pcl_ros',
        plugin='pcl_ros::CropBox',
        name='helios_self_filter',
        parameters=[{
            'use_sim_time': True,
            'input_frame': 'base_link',
            'output_frame': 'base_link',
            'negative': True,
            'keep_organized': False,
            'min_x': -1.75, 'max_x': 1.25,
            'min_y': -0.80, 'max_y': 0.80,
            'min_z': -0.60, 'max_z': 1.55,
        }],
        remappings=[
            ('input',  '/caddy_ai2/rs_helios_5515/points'),
            ('output', '/caddy_ai2/rs_helios_5515/points_filtered'),
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument('params_file', default_value=default_params),

        ComposableNodeContainer(
            name='helios_filter_container',
            namespace='',
            package='rclcpp_components',
            executable='component_container',
            composable_node_descriptions=[crop_box],
            output='screen',
        ),

        # Unnamespaced on purpose: the params file is keyed by EasyNav's node names, and a
        # namespace would also split /tf away from the global tree the EKF publishes to.
        Node(
            package='easynav_system',
            executable='system_main',
            output='screen',
            arguments=['--ros-args', '--params-file', params_file],
            remappings=[
                ('cmd_vel_stamped', '/caddy_ai2/bicycle_steering_controller/reference'),
            ],
        ),
    ])
