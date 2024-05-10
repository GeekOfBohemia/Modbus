import signal
import time


def sighandler(signal, frame):
    CoreControl.stop_flag = True
    print(" >>> Signal break caught...wait")


signal.signal(signal.SIGINT, sighandler)


class CoreControl:
    stop_flag: bool = False


def local_start(app):
    app.start()
    while not CoreControl.stop_flag:
        time.sleep(1)
    app.stop()
