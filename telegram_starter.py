# ChickenFryBiryani

import os
import signal
from telegram_Interface import TelegramInterface


def main():
    receiver_instance = TelegramInterface()
    receiver_instance.receiver()


if __name__ == "__main__":
    main()
    os.kill(os.getpid(), signal.SIGINT)
