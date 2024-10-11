import socket
from loguru import logger
import requests
import pathlib

import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--ip", type=str, required=True)
parser.add_argument("--port", type=int, required=True)
parser.add_argument("--webhook-url", type=str, required=True)
args = parser.parse_args()

ip = args.ip
port = args.port
webhook_url = args.webhook_url

data_path = pathlib.Path("server_status.json")


def check_server_status() -> bool:
    try:
        logger.info(f"Checking server {ip}:{port}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((ip, port))
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False
    except Exception:
        logger.exception("Error while checking server")
        return False


def get_server_status() -> bool:
    try:
        with data_path.open("r") as f:
            data = json.load(f)
    except FileNotFoundError:
        with data_path.open("w") as f:
            json.dump({}, f, indent=4)
        return False

    return data.get(f"{ip}:{port}", False)


def save_server_status(status: bool) -> None:
    with data_path.open("r") as f:
        data = json.load(f)

    data[f"{ip}:{port}"] = status
    with data_path.open("w") as f:
        json.dump(data, f, indent=4)


def send_webhook(status: bool) -> None:
    if status:
        message = f"伺服器 {ip}:{port} 已上線"
    else:
        message = f"伺服器 {ip}:{port} 已離線"

    data = {"content": message}
    response = requests.post(webhook_url, json=data)
    logger.info(f"Webhook response: {response.status_code}")


def main():
    current_status = check_server_status()
    logger.info(f"Current status: {current_status}")
    last_status = get_server_status()
    logger.info(f"Last status: {last_status}")

    if current_status != last_status:
        logger.info("Status changed, sending webhook...")
        save_server_status(current_status)
        send_webhook(current_status)


if __name__ == "__main__":
    main()
