#!/usr/bin/env python3
"""MCP Server for Qarnot Multiphysics platform."""

import os
import qarnot
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

QARNOT_TOKEN = os.getenv("QARNOT_TOKEN")
if not QARNOT_TOKEN:
    raise ValueError("QARNOT_TOKEN environment variable is required")

# Create MCP server
mcp = FastMCP("qarnot")

def get_connection() -> qarnot.connection.Connection:
    """Get a fresh Qarnot connection."""
    return qarnot.connection.Connection(client_token=QARNOT_TOKEN)

# ====== TOOLS THAT CAN BE USED BY THE MCP SERVER ==== #
@mcp.tool()
def list_tasks() -> str:
    """List all Qarnot tasks for your account."""
    conn = get_connection()
    tasks = conn.tasks()

    result = []
    for task in tasks:
        result.append({
            "uuid": task.uuid,
            "name": task.name,
            "state": task.state,
            "progress": f"{task.progress}%",
            "instance_count": task.instancecount,
            "running_instances": task.running_instance_count,
            "creation_date": str(task.creation_date),
            "end_date": str(task.end_date) if task.end_date else "N/A",
        })

    import json
    return json.dumps(result, indent=2)


@mcp.tool()
def get_task_status(uuid: str) -> str:
    """Get detailed status of a specific Qarnot task.

    Args:
        uuid: The UUID of the task
    """
    conn = get_connection()
    task = conn.retrieve_task(uuid)
    task.update(flushcache=True)

    # Check for SSH/forward connections
    ssh_info = []
    if hasattr(task, 'status') and task.status:
        running_info = getattr(task.status, 'running_instances_info', None)
        if running_info:
            for instance in getattr(running_info, 'per_running_instance_info', []):
                for fwd in getattr(instance, 'active_forwards', []):
                    ssh_info.append({
                        "instance_id": instance.instance_id,
                        "app_port": fwd.application_port,
                        "host": fwd.forwarder_host,
                        "port": fwd.forwarder_port,
                        "ssh_command": f"ssh -p {fwd.forwarder_port} user@{fwd.forwarder_host}"
                                       if fwd.application_port == 22 else None
                    })

    result = {
        "uuid": task.uuid,
        "name": task.name,
        "state": task.state,
        "progress": f"{task.progress}%",
        "instance_count": task.instancecount,
        "running_instances": task.running_instance_count,
        "running_cores": task.running_core_count,
        "execution_time": str(task.execution_time),
        "wall_time": str(task.wall_time),
        "creation_date": str(task.creation_date),
        "end_date": str(task.end_date) if task.end_date else "N/A",
        "ssh_connections": ssh_info if ssh_info else "No active SSH forwards",
    }

    import json
    return json.dumps(result, indent=2)


@mcp.tool()
def get_task_stdout(uuid: str, instance_id: int | None = None) -> str:
    """Get the standard output (stdout) of a Qarnot task.

    Args:
        uuid: The UUID of the task
        instance_id: Optional instance ID for multi-instance tasks
    """
    conn = get_connection()
    task = conn.retrieve_task(uuid)

    stdout = task.stdout(instance_id) if instance_id is not None else task.stdout()
    return stdout or "(no output)"


@mcp.tool()
def get_task_stderr(uuid: str, instance_id: int | None = None) -> str:
    """Get the standard error (stderr) of a Qarnot task.

    Args:
        uuid: The UUID of the task
        instance_id: Optional instance ID for multi-instance tasks
    """
    conn = get_connection()
    task = conn.retrieve_task(uuid)

    stderr = task.stderr(instance_id) if instance_id is not None else task.stderr()
    return stderr or "(no error output)"


@mcp.tool()
def cancel_task(uuid: str) -> str:
    """Cancel a running Qarnot task.

    Args:
        uuid: The UUID of the task to cancel
    """
    conn = get_connection()
    task = conn.retrieve_task(uuid)

    if task.state in ["Cancelled", "Success", "Failure"]:
        return f"Task {uuid} is already in state '{task.state}' and cannot be cancelled."

    task.abort()
    return f"Task {uuid} has been cancelled."


@mcp.tool()
def list_buckets() -> str:
    """List all storage buckets in your Qarnot account."""
    conn = get_connection()
    buckets = conn.buckets()

    import json
    result = []
    for bucket in buckets:
        result.append({
            "name": bucket.uuid,
        })

    return json.dumps(result, indent=2) if result else "No buckets found."


@mcp.tool()
def list_bucket_files(bucket_name: str) -> str:
    """List all files in a Qarnot storage bucket.

    Args:
        bucket_name: The name of the bucket
    """
    conn = get_connection()
    bucket = conn.retrieve_bucket(bucket_name)

    import json
    files = [f.key for f in bucket.list_files()]
    return json.dumps(files, indent=2) if files else "No files in bucket."


@mcp.tool()
def download_result(bucket_name: str, remote_path: str, local_path: str) -> str:
    """Download a file from a Qarnot bucket to your local machine.

    Args:
        bucket_name: The name of the bucket
        remote_path: The path of the file in the bucket
        local_path: Where to save the file locally. If not specified in the prompt, the AI may ask for it.
    """
    conn = get_connection()
    bucket = conn.retrieve_bucket(bucket_name)

    bucket.get_file(remote_path, local_path)
    return f"Downloaded '{remote_path}' from '{bucket_name}' to '{local_path}'"


if __name__ == "__main__":
    mcp.run()
