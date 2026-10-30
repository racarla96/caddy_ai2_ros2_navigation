#!/usr/bin/env python3
"""
Visualization helper for remote RViz (runs where the simulation runs).

Downsamples the self-filtered Helios cloud so it fits through an SSH tunnel:
    /caddy_ai2/rs_helios_5515/points_filtered  ->  /caddy_ai2/rs_helios_5515/points_viz
(57 600 points at 10 Hz is ~18 MB/s; a 0.3 m voxel grid leaves a few thousand points).
This cloud is only for display; EasyNav keeps using points_filtered.
"""

from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode


def generate_launch_description():
    voxel = ComposableNode(
        package='pcl_ros',
        plugin='pcl_ros::VoxelGrid',
        name='helios_viz_downsample',
        parameters=[{'use_sim_time': True, 'leaf_size': 0.3}],
        remappings=[
            ('input',  '/caddy_ai2/rs_helios_5515/points_filtered'),
            ('output', '/caddy_ai2/rs_helios_5515/points_viz'),
        ],
    )
    return LaunchDescription([
        ComposableNodeContainer(
            name='helios_viz_container',
            namespace='',
            package='rclcpp_components',
            executable='component_container',
            composable_node_descriptions=[voxel],
            output='screen',
        ),
    ])
