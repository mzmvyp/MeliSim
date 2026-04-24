import logging

log = logging.getLogger("notifications.push")


def send_push(user_id: int, title: str, message: str) -> None:
    log.info("PUSH to user=%s title=%r", user_id, title)
    print(f"[PUSH] user:{user_id} | {title} | {message}")
