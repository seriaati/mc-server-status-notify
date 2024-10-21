from typing import TypedDict
from loguru import logger
import requests
import pathlib
import datetime
from mcstatus import JavaServer

import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--address", type=str, required=True)
parser.add_argument("--webhook-url", type=str, required=True)
args = parser.parse_args()

address = args.address
webhook_url = args.webhook_url

data_path = pathlib.Path("server_status.json")


class ServerStatus(TypedDict):
    online: bool
    time: str


def get_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def is_server_online() -> bool:
    try:
        server = JavaServer.lookup(address)
        status = server.status()
        if status.players.max == 0:
            return False
        return True
    except Exception:
        logger.exception("Failed to get server status")
        return False


def get_server_status() -> ServerStatus:
    try:
        with data_path.open("r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
        with data_path.open("w") as f:
            json.dump(data, f, indent=4)

    return data.get(address, {"online": False, "time": get_now()})


def save_server_status(status: ServerStatus) -> None:
    with data_path.open("r") as f:
        data = json.load(f)

    data[address] = status
    with data_path.open("w") as f:
        json.dump(data, f, indent=4)


def send_webhook(status: ServerStatus, last_status: ServerStatus) -> None:
    if status["online"]:
        time_diff = datetime.datetime.fromisoformat(
            get_now()
        ) - datetime.datetime.fromisoformat(last_status["time"])
        time_diff_str = str(time_diff).split(".")[0]
        message = f"伺服器 {address} 已上線, 距離上次離線時間: {time_diff_str}"
    else:
        message = f"伺服器 {address} 已離線"

    data = {"content": message}
    response = requests.post(webhook_url, json=data)
    logger.info(f"Webhook response: {response.status_code}")


def main():
    current_status = is_server_online()
    logger.info(f"Current status: {current_status}")
    last_status = get_server_status()
    logger.info(f"Last status: {last_status}")

    if current_status != last_status["online"]:
        server_status = ServerStatus(online=current_status, time=get_now())
        logger.info("Status changed, sending webhook...")
        save_server_status(server_status)
        send_webhook(server_status, last_status)


if __name__ == "__main__":
    logger.add("logs/log.log", rotation="1 day", retention="7 days")
    main()
