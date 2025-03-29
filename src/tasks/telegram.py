import requests


class TelegramBot:
    def __init__(self, token: str, chat_id: str, parse_mode: str = "HTML"):
        self.token = token
        self.chat_id = chat_id
        self.parse_mode = parse_mode

    def send_message(self, message: str):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage?chat_id={self.chat_id}&text={message}&parse_mode={self.parse_mode}"
        return requests.get(url).json()
