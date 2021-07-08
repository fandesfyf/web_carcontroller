from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([
        Node(
            package="controlserver",
            node_namespace="controllwebsocketserver",
            node_executable='controller',
            node_name="nw_chassis_control_node"
        )
    ])
