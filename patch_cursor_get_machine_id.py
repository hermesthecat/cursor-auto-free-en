#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import platform
import re
import shutil
import sys
import tempfile
from typing import Tuple


# Configure logging
def setup_logging() -> logging.Logger:
    """Configure and return logger instance"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = setup_logging()


def get_cursor_paths() -> Tuple[str, str]:
    """
    Get Cursor related paths based on different operating systems

    Returns:
        Tuple[str, str]: Tuple of (package.json path, main.js path)

    Raises:
        OSError: When valid path is not found or system is not supported
    """
    system = platform.system()

    paths_map = {
        "Darwin": {
            "base": "/Applications/Cursor.app/Contents/Resources/app",
            "package": "package.json",
            "main": "out/main.js",
        },
        "Windows": {
            "base": os.path.join(
                os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app"
            ),
            "package": "package.json",
            "main": "out/main.js",
        },
        "Linux": {
            "bases": ["/opt/Cursor/resources/app", "/usr/share/cursor/resources/app"],
            "package": "package.json",
            "main": "out/main.js",
        },
    }

    if system not in paths_map:
        raise OSError(f"Unsupported operating system: {system}")

    if system == "Linux":
        for base in paths_map["Linux"]["bases"]:
            pkg_path = os.path.join(base, paths_map["Linux"]["package"])
            if os.path.exists(pkg_path):
                return (pkg_path, os.path.join(base, paths_map["Linux"]["main"]))
        raise OSError("Cursor installation path not found on Linux system")

    base_path = paths_map[system]["base"]
    return (
        os.path.join(base_path, paths_map[system]["package"]),
        os.path.join(base_path, paths_map[system]["main"]),
    )


def check_system_requirements(pkg_path: str, main_path: str) -> bool:
    """
    Check system requirements

    Args:
        pkg_path: package.json file path
        main_path: main.js file path

    Returns:
        bool: Whether check passed
    """
    for file_path in [pkg_path, main_path]:
        if not os.path.isfile(file_path):
            logger.error(f"File does not exist: {file_path}")
            return False

        if not os.access(file_path, os.W_OK):
            logger.error(f"No write permission for file: {file_path}")
            return False

    return True


def version_check(version: str, min_version: str = "", max_version: str = "") -> bool:
    """
    Version number check

    Args:
        version: Current version number
        min_version: Minimum version requirement
        max_version: Maximum version requirement

    Returns:
        bool: Whether version number meets requirements
    """
    version_pattern = r"^\d+\.\d+\.\d+$"
    try:
        if not re.match(version_pattern, version):
            logger.error(f"Invalid version number format: {version}")
            return False

        def parse_version(ver: str) -> Tuple[int, ...]:
            return tuple(map(int, ver.split(".")))

        current = parse_version(version)

        if min_version and current < parse_version(min_version):
            logger.error(f"Version {version} is less than minimum requirement {min_version}")
            return False

        if max_version and current > parse_version(max_version):
            logger.error(f"Version {version} is greater than maximum requirement {max_version}")
            return False

        return True

    except Exception as e:
        logger.error(f"Version check failed: {str(e)}")
        return False


def modify_main_js(main_path: str) -> bool:
    """
    Modify main.js file

    Args:
        main_path: main.js file path

    Returns:
        bool: Whether modification was successful
    """
    try:
        # Get original file permissions and owner information
        original_stat = os.stat(main_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            with open(main_path, "r", encoding="utf-8") as main_file:
                content = main_file.read()

            # Perform replacements
            patterns = {
                r"async getMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMachineId(){return \1}",
                r"async getMacMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMacMachineId(){return \1}",
            }

            for pattern, replacement in patterns.items():
                content = re.sub(pattern, replacement, content)

            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Use shutil.copy2 to preserve file permissions
        shutil.copy2(main_path, main_path + ".old")
        shutil.move(tmp_path, main_path)

        # Restore original file permissions and owner
        os.chmod(main_path, original_mode)
        if os.name != "nt":  # Set owner on non-Windows systems
            os.chown(main_path, original_uid, original_gid)

        logger.info("File modification successful")
        return True

    except Exception as e:
        logger.error(f"Error occurred while modifying file: {str(e)}")
        if "tmp_path" in locals():
            os.unlink(tmp_path)
        return False


def backup_files(pkg_path: str, main_path: str) -> bool:
    """
    Backup original files

    Args:
        pkg_path: package.json file path (unused)
        main_path: main.js file path

    Returns:
        bool: Whether backup was successful
    """
    try:
        # Only backup main.js
        if os.path.exists(main_path):
            backup_main = f"{main_path}.bak"
            shutil.copy2(main_path, backup_main)
            logger.info(f"main.js backed up: {backup_main}")

        return True
    except Exception as e:
        logger.error(f"Failed to backup files: {str(e)}")
        return False


def restore_backup_files(pkg_path: str, main_path: str) -> bool:
    """
    Restore backup files

    Args:
        pkg_path: package.json file path (unused)
        main_path: main.js file path

    Returns:
        bool: Whether restoration was successful
    """
    try:
        # Only restore main.js
        backup_main = f"{main_path}.bak"
        if os.path.exists(backup_main):
            shutil.copy2(backup_main, main_path)
            logger.info(f"main.js restored")
            return True

        logger.error("Backup file not found")
        return False
    except Exception as e:
        logger.error(f"Failed to restore backup: {str(e)}")
        return False


def patch_cursor_get_machine_id(restore_mode=False) -> None:
    """
    Main function

    Args:
        restore_mode: Whether in restore mode
    """
    logger.info("Starting script...")

    try:
        # Get paths
        pkg_path, main_path = get_cursor_paths()

        # Check system requirements
        if not check_system_requirements(pkg_path, main_path):
            sys.exit(1)

        if restore_mode:
            # Restore backup
            if restore_backup_files(pkg_path, main_path):
                logger.info("Backup restored successfully")
            else:
                logger.error("Backup restore failed")
            return

        # Get version number
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                version = json.load(f)["version"]
            logger.info(f"Current Cursor version: {version}")
        except Exception as e:
            logger.error(f"Failed to read version number: {str(e)}")
            sys.exit(1)

        # Check version
        if not version_check(version, min_version="0.45.0"):
            logger.error("Version does not meet requirements (need >= 0.45.x)")
            sys.exit(1)

        logger.info("Version check passed, preparing to modify file")

        # Backup files
        if not backup_files(pkg_path, main_path):
            logger.error("Failed to backup files, terminating operation")
            sys.exit(1)

        # Modify file
        if not modify_main_js(main_path):
            sys.exit(1)

        logger.info("Script execution completed")

    except Exception as e:
        logger.error(f"Error occurred during execution: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    patch_cursor_get_machine_id()
